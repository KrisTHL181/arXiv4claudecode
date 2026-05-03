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

### `html2md` — HTML 转 Markdown

将 arXiv HTML 论文转换为 Markdown，方便在 Claude Code 中直接阅读。

```bash
arxiv html2md 2107.05580              # 下载并转换，输出到 stdout
arxiv html2md 2107.05580 -o paper.md  # 保存到文件
arxiv html2md paper.html              # 转换本地 HTML 文件
```

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
- 下载并阅读：`arxiv download ID && arxiv html2md ID -o paper.md`
```

建议在 Claude Code 设置中为 arxiv 命令开启 allowlist 权限以减少审批打断。

## 许可证

MIT
