# arXiv for Claude Code

arXiv CLI — 在终端里浏览、搜索和下载 arXiv 论文。专为 [Claude Code](https://claude.ai/code) 工作流设计，同时可独立作为命令行工具使用。

## 安装

```bash
pip install git+https://github.com/KrisTHL181/arXiv4claudecode.git
```

或本地开发安装：

```bash
git clone https://github.com/KrisTHL181/arXiv4claudecode.git
cd arXiv4claudecode
pip install -e .
```

要求 Python >= 3.11。

## 快速开始

```bash
# 查看最新论文
arxiv browse new cs.AI

# 搜索论文
arxiv search "diffusion models" -c cs.CV -n 20

# 按日期追赶最新研究
arxiv catch-up "2026-04-01" -c cs.AI -c cs.CL

# 下载论文 PDF
arxiv download 2107.05580 -o ~/papers

# 查看统计
arxiv stats --year 2024

# 查看所有分类
arxiv categories
```

## 命令

### `browse` — 浏览论文

| 子命令 | 说明 |
|--------|------|
| `new [category]` | 最新一期 RSS 推送（默认 cs） |
| `recent [category]` | 最近 5 期列表 |
| `current [category]` | 当前月份列表 |
| `month YEAR MONTH [category]` | 指定月份列表 |

```bash
arxiv browse new              # 默认 CS 分类
arxiv browse new cs.AI        # 指定分类
arxiv browse month 2026 3 hep-th -n 30
```

### `search` — 搜索论文

```
arxiv search QUERY [OPTIONS]
```

- `-c, --category` — 按分类过滤（可重复，支持逗号分隔：`-c cs.AI,cs.CL`）
- `-n, --max-results` — 最大结果数（默认 50）
- `--sort-by [relevance|submitted|updated]`
- `--sort-order [desc|asc]`

支持字段前缀搜索：`ti:`, `au:`, `abs:`, `all:`, `cat:`

```bash
arxiv search 'au:"Yann LeCun" AND ti:learning' -c cs.LG
```

### `catch-up` — 日期追赶

指定截止日期，获取从那天至今的所有论文。

```bash
arxiv catch-up "2026-04-15" -c cs.AI -n 200
arxiv catch-up "2026-04-01"
```

### `download` — 下载论文

```
arxiv download PAPER_ID [OPTIONS]
```

- `-f, --format [pdf|src|html|eprint]` — 下载格式（默认 pdf）
- `-o, --output` — 输出目录（默认当前目录）
- `--filename` — 自定义文件名

```bash
arxiv download 2107.05580 -f pdf -o ~/papers
arxiv download 2107.05580 -f src      # LaTeX 源码
```

### `html2md` — 论文转 Markdown

将 arXiv 论文转换为 Markdown，内置多级回退策略：

1. 优先获取 arXiv 原生 HTML 版本（`arxiv.org/html/{id}`）
2. 若无 HTML，通过 **ar5ivist** 将 LaTeX 源码转为 HTML 再转 Markdown
3. 最终回退：输出原始 LaTeX 源码

```bash
arxiv html2md 2107.05580              # 自动选择最佳格式，输出到 stdout
arxiv html2md 2107.05580 -o paper.md  # 保存到文件
arxiv html2md paper.html              # 转换本地 HTML 文件
arxiv html2md 2107.05580 --timeout 600  # 自定义 ar5ivist 超时（默认 300s）
```

> **ar5ivist** 是 ar5iv.org 的本地工具，可将 LaTeX 论文转为 HTML5。需安装 Docker（推荐）或 latexml 才能使用此功能。详见下方 [ar5ivist 安装](#ar5ivist-安装) 章节。

### `stats` — 论文统计

```bash
arxiv stats                           # 全部统计总览
arxiv stats --year 2024               # 按年份过滤
arxiv stats -c cs --refresh           # 尝试抓取实时数据
```

### `categories` — 分类列表

```bash
arxiv categories                      # 所有 8 大组的 ~180 个分类
arxiv categories -g cs                # 只看 CS 分类
```

## ar5ivist 安装

ar5ivist 提供 LaTeX → HTML5 转换能力。对于没有原生 HTML 版本的 arXiv 论文（多数老论文），安装后可将 LaTeX 源码自动转为可读的 Markdown。

### 自动安装（推荐）

```bash
bash scripts/install_ar5ivist.sh
```

脚本按以下顺序尝试：
1. **Docker 拉取**预构建的 `latexml/ar5ivist:2512.17` 镜像
2. **本地 Docker 构建** — 从 GitHub 克隆源码并构建
3. 若均失败，打印手动安装说明

### 手动安装

```bash
# Docker 方式（推荐）
docker pull latexml/ar5ivist:2512.17

# 系统包管理器
sudo apt install latexml         # Debian/Ubuntu
brew install latexml             # macOS
cpan install LaTeXML             # 通用
```

### 验证

```bash
docker image inspect latexml/ar5ivist:2512.17   # Docker 方式
latexmlc --version                              # 本地安装
```

> 未安装 ar5ivist 时，`arxiv html2md` 对无 HTML 的论文会直接输出原始 LaTeX 源码。

## 输出格式

所有命令支持三种输出格式：

```bash
arxiv search "transformers" --json    # JSON 格式（适合管道处理）
arxiv search "transformers" --plain   # 纯文本（适合管道处理）
# 默认：Rich 终端格式化（带颜色、面板）
```

## 与 Claude Code 集成

在 CLAUDE.md 中添加：

```markdown
## arXiv Research

- 获取最新论文：`arxiv browse new cs.AI | head -100`
- 搜索论文：`arxiv search "query" --json -n 10`
- 下载并阅读：`arxiv html2md ID -o paper.md`
- 一键阅读（含 PDF 回退）：`bash skills/arxiv-reader/scripts/read_paper.sh ID`
```

### arxiv-reader Skill

项目内置了 `arxiv-reader` Claude Code skill，提供终端论文阅读能力：

```
/arxiv-reader 2107.05580
```

该 skill 调用 `read_paper.sh`，其回退链为：HTML → ar5ivist → LaTeX 源码 → PDF 文本提取。

建议在 Claude Code 设置中为 arxiv 命令开启 allowlist 权限以减少审批打断。

## 许可证

MIT
