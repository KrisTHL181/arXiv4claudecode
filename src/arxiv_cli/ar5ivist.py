"""ar5ivist integration: LaTeX source → HTML conversion for papers without native HTML.

ar5ivist (github.com/dginev/ar5ivist) converts LaTeX to HTML5 via latexml.
It is distributed as a Docker image: latexml/ar5ivist:2512.17
"""

from __future__ import annotations

import enum
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, Callable
import warnings

if TYPE_CHECKING:
    from arxiv_cli.client import ArxivClient


_DOCKER_IMAGE = "latexml/ar5ivist:2512.17"
_backend_cache: Ar5ivistBackend | None = None


class Ar5ivistError(Exception):
    """Base exception for ar5ivist-related errors."""


class Ar5ivistNotFoundError(Ar5ivistError):
    """ar5ivist backend (Docker or local) is not available."""


class SourceExtractionError(Ar5ivistError):
    """Failed to download or extract LaTeX source from arXiv."""


class LaTeXConversionError(Ar5ivistError):
    """ar5ivist failed to convert the .tex file to HTML."""


class Ar5ivistBackend(enum.Enum):
    DOCKER = "docker"
    AR5IVIST = "ar5ivist"
    LATEXMLC = "latexmlc"
    LATEXML = "latexml"
    UNAVAILABLE = "unavailable"


def detect_backend() -> Ar5ivistBackend:
    """Detect available ar5ivist backend. Results cached after first call.

    Priority: Docker > ar5ivist > latexmlc > latexml+latexmlpost > unavailable.
    """
    global _backend_cache
    if _backend_cache is not None:
        return _backend_cache

    docker_path = shutil.which("docker")
    if docker_path:
        try:
            _ = subprocess.run(
                [docker_path, "image", "inspect", _DOCKER_IMAGE],
                capture_output=True, timeout=15, check=True,
            )
            _backend_cache = Ar5ivistBackend.DOCKER
            return _backend_cache
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

    if shutil.which("ar5ivist"):
        _backend_cache = Ar5ivistBackend.AR5IVIST
        return _backend_cache

    if shutil.which("latexmlc"):
        _backend_cache = Ar5ivistBackend.LATEXMLC
        return _backend_cache

    if shutil.which("latexml") and shutil.which("latexmlpost"):
        _backend_cache = Ar5ivistBackend.LATEXML
        return _backend_cache

    _backend_cache = Ar5ivistBackend.UNAVAILABLE
    return _backend_cache


def find_main_tex(extract_dir: str) -> Path | None:
    """Find the root .tex file in an extracted arXiv source archive.

    Heuristic:
    1. Collect all .tex files recursively.
    2. Scan each for \\documentclass — these are candidate root files.
    3. Prefer files with more \\input/\\include directives.
    4. Among ties, prefer files named main.tex, paper.tex, manuscript.tex,
       or the largest file.
    5. If no candidate has \\documentclass, fall back to the largest .tex file.
    """
    tex_files = list(Path(extract_dir).rglob("*.tex"))
    if not tex_files:
        return None

    candidates: list[tuple[Path, int, str]] = []
    for f in tex_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"\\documentclass", content):
            input_count = len(re.findall(r"\\(?:input|include)\{", content))
            candidates.append((f, input_count, content))

    if not candidates:
        return max(tex_files, key=lambda p: p.stat().st_size)

    preferred_names = {"main.tex", "paper.tex", "manuscript.tex"}

    def _key(item: tuple[Path, int, str]) -> tuple[int, int]:
        f, input_count, _ = item
        name_bonus = 2 if f.name in preferred_names else 0
        return (input_count + name_bonus, f.stat().st_size)

    candidates.sort(key=_key, reverse=True)
    return candidates[0][0]


def download_and_extract_source(
    paper_id: str,
    client: ArxivClient,
    temp_dir: str,
) -> Path:
    """Download arxiv.org/src/{paper_id}, extract, return path to main .tex.

    Raises SourceExtractionError on failure.
    """
    src_url = f"https://arxiv.org/src/{paper_id}"
    archive_path = os.path.join(temp_dir, "source.tar.gz")

    try:
        _ = client.download_file(src_url, archive_path)
    except Exception as e:
        raise SourceExtractionError(
            f"Failed to download LaTeX source for {paper_id}: {e}"
        ) from e

    extract_dir = os.path.join(temp_dir, "src")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extract_dir)
    except (tarfile.TarError, OSError) as e:
        raise SourceExtractionError(f"Failed to extract source archive: {e}") from e

    main_tex = find_main_tex(extract_dir)
    if main_tex is None:
        raise SourceExtractionError("No .tex file found in the source archive.")
    return main_tex


def run_ar5ivist(
    tex_path: Path,
    output_dir: str,
    backend: Ar5ivistBackend,
    *,
    progress_callback: Callable[[str], None] | None = None,
    timeout: int = 300,
) -> str:
    """Run ar5ivist on a .tex file. Returns path to the generated HTML file.

    Raises LaTeXConversionError on failure.
    """
    tex_abs = str(tex_path.resolve())
    html_filename = "index.html"
    warnings.warn("No native HTML available for this paper. Attempting conversion from LaTeX source via ar5ivist (this may take a while). Please wait.")

    try:
        if backend == Ar5ivistBackend.DOCKER:
            return _run_docker(tex_abs, html_filename, progress_callback, timeout)
        elif backend == Ar5ivistBackend.AR5IVIST:
            return _run_ar5ivist_binary(tex_abs, output_dir, html_filename, progress_callback, timeout)
        elif backend == Ar5ivistBackend.LATEXMLC:
            return _run_latexmlc(tex_path, output_dir, html_filename, progress_callback, timeout)
        elif backend == Ar5ivistBackend.LATEXML:
            return _run_latexml_pipeline(tex_path, output_dir, html_filename, progress_callback, timeout)
        else:
            raise Ar5ivistNotFoundError(f"Unknown or unavailable backend: {backend}")
    except (subprocess.CalledProcessError, OSError) as e:
        raise LaTeXConversionError(f"ar5ivist conversion failed: {e}") from e


def _run_docker(
    tex_path: str,
    html_filename: str,
    progress_callback: Callable[[str], None] | None,
    timeout: int,
) -> str:
    """Invoke ar5ivist via Docker."""
    tex_dir = os.path.dirname(tex_path)
    tex_basename = os.path.basename(tex_path)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{tex_dir}:/docdir:z",
        "-w", "/docdir",
        "--user", f"{os.getuid()}:{os.getgid()}",
        _DOCKER_IMAGE,
        f"--source={tex_basename}",
        f"--destination={html_filename}",
    ]

    _run_subprocess(cmd, progress_callback, timeout)

    result = os.path.join(tex_dir, html_filename)
    if not os.path.isfile(result):
        raise LaTeXConversionError(
            f"ar5ivist did not produce expected output: {result}"
        )
    return result


def _run_ar5ivist_binary(
    tex_path: str,
    output_dir: str,
    html_filename: str,
    progress_callback: Callable[[str], None] | None,
    timeout: int,
) -> str:
    """Invoke ar5ivist binary locally."""
    binary = shutil.which("ar5ivist")
    if not binary:
        raise Ar5ivistNotFoundError("No local ar5ivist binary found.")

    html_path = os.path.join(output_dir, html_filename)

    cmd = [
        binary,
        f"--source={tex_path}",
        f"--destination={html_path}",
    ]

    _run_subprocess(cmd, progress_callback, timeout)

    if not os.path.isfile(html_path):
        raise LaTeXConversionError(
            f"ar5ivist did not produce expected output: {html_path}"
        )
    return html_path


def _run_latexmlc(
    tex_path: Path,
    output_dir: str,
    html_filename: str,
    progress_callback: Callable[[str], None] | None,
    timeout: int,
) -> str:
    """One-step LaTeXML conversion: TeX → HTML via latexmlc."""
    tex_dir = str(tex_path.parent)
    tex_basename = tex_path.name
    html_path = os.path.join(output_dir, html_filename)

    cmd = ["latexmlc", "--dest", html_path, tex_basename]
    _run_subprocess(cmd, progress_callback, timeout, cwd=tex_dir)

    if not os.path.isfile(html_path):
        raise LaTeXConversionError(
            f"latexmlc did not produce expected output: {html_path}"
        )
    return html_path


def _run_latexml_pipeline(
    tex_path: Path,
    output_dir: str,
    html_filename: str,
    progress_callback: Callable[[str], None] | None,
    timeout: int,
) -> str:
    """Two-step LaTeXML conversion: TeX → XML → HTML via latexml + latexmlpost."""
    tex_dir = str(tex_path.parent)
    tex_basename = tex_path.name
    xml_path = os.path.join(output_dir, "output.xml")
    html_path = os.path.join(output_dir, html_filename)

    _run_subprocess(
        ["latexml", "--dest", xml_path, tex_basename],
        progress_callback,
        timeout // 2,
        cwd=tex_dir,
    )

    if not os.path.isfile(xml_path):
        raise LaTeXConversionError(
            f"latexml did not produce expected output: {xml_path}"
        )

    _run_subprocess(
        ["latexmlpost", "--dest", html_path, xml_path],
        progress_callback,
        timeout // 2,
        cwd=tex_dir,
    )

    if not os.path.isfile(html_path):
        raise LaTeXConversionError(
            f"latexmlpost did not produce expected output: {html_path}"
        )
    return html_path


def _run_subprocess(
    cmd: list[str],
    progress_callback: Callable[[str], None] | None,
    timeout: int,
    *,
    cwd: str | None = None,
) -> None:
    """Run a subprocess with timeout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        if result.returncode != 0:
            stderr_preview = result.stderr[:500] if result.stderr else "(no stderr)"
            raise LaTeXConversionError(
                f"ar5ivist exited with code {result.returncode}. Stderr: {stderr_preview}"
            )
    except subprocess.TimeoutExpired:
        raise LaTeXConversionError(
            f"ar5ivist timed out after {timeout} seconds."
        )


def tex_to_html(
    paper_id: str,
    client: ArxivClient,
    temp_dir: str,
    *,
    progress_callback: Callable[[str], None] | None = None,
    timeout: int = 300,
) -> str:
    """Full pipeline: download source → extract → find main tex → run ar5ivist.

    Returns the HTML string produced by ar5ivist.
    Raises Ar5ivistError on any failure (caller chains to LaTeX fallback).
    """
    backend = detect_backend()
    if backend == Ar5ivistBackend.UNAVAILABLE:
        raise Ar5ivistNotFoundError(
            "ar5ivist is not installed. Run scripts/install_ar5ivist.sh to install it, "
            "or the tool will output raw LaTeX source instead."
        )

    tex_path = download_and_extract_source(paper_id, client, temp_dir)

    html_file = run_ar5ivist(
        tex_path, temp_dir, backend,
        progress_callback=progress_callback,
        timeout=timeout,
    )

    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()
