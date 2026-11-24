# 组会文献解读 Skill（group-meeting-paper-reading）

一个面向**博士组会 / journal club** 的 Claude / Cowork Skill：丢进一篇论文（PDF、arXiv/DOI 链接或标题），产出一份"把逻辑讲清楚、把图读透"的中文深度解读文档，同时输出 **Markdown** 和**单文件 HTML**（论文图表内嵌其中），方便直接投屏汇报或改成讲稿。

## 它解决什么问题

组会解读最见功力的，不是翻译摘要，而是**重建作者的推理链**——问题从哪来、缺口在哪、增量靠什么设计实现、每张图如何为故事线服务，以及经不经得起追问。这个 skill 把这套流程固化下来。

## 解读文档结构

0. 论文信息卡
1. 一句话总结
2. 核心问题：回答了什么问题、为什么值得回答
3. 研究现状与缺口：同行回答到什么程度了
4. 本文增量：提供了什么、怎么提供的（区分真新 vs 组合式）
5. 研究方法
6. **结果与图表解读**（核心章节）：逐图逐面板，每张图按"这图怎么来的 → 逐面板精读 → 故事线定位"三段式，多面板图一个面板一个面板讲
7. 批判性评价（具体到"我审稿会问什么"）
8. 期刊定位：已发表判**高攀/低就**；未发表给**冲刺/匹配/保底**投稿策略（参考中科院分区、新锐分区、预警名单；区分英文刊/中文刊标尺）
9. 国内期刊适配（单独一节）
10. 附录 A：组会讲稿提纲（分环节用时 + 老师最可能追问的问题及参考回答）
11. 附录 B：术语表 + **完整文献信息**的延伸阅读

## 目录结构

```
group-meeting-paper-reading/
├── SKILL.md                      # 主流程与文档结构
├── references/
│   ├── figure-reading.md         # 读图方法：怎么把一张图讲透
│   └── journal-analysis.md       # 期刊定位分析（英文刊/中文刊双标尺）
├── scripts/
│   ├── extract_figures.py        # 从 PDF 提取/渲染图表（PyMuPDF）
│   ├── extract_docx_media.py     # 从 docx 提取正文与图片
│   ├── generate_html.py          # Markdown → 单文件 HTML
│   └── link_to_zotero.py         # 把解读关联回 Zotero 条目并打标签
└── assets/
    └── template.html             # 单文件 HTML 输出模板（KaTeX + 内嵌图）
```

## 安装与使用

**Cowork / Claude 桌面端**：把打包的 `.skill` 文件拖进对话，点卡片上的「保存技能」即可安装。

**Claude Code / 项目内**：把 `group-meeting-paper-reading/` 整个文件夹放进 `~/.claude/skills/`（全局）或项目的 `.claude/skills/`（项目内）。

安装后，只要说一句"帮我把这篇论文做一份组会解读"并给出论文，即可触发。

依赖：图表提取需要 `pip install pymupdf`；生成 HTML 需要 `pip install markdown`。

## 关联回 Zotero（可选）

```bash
python3 scripts/link_to_zotero.py <解读.html> --doi <DOI> --dry-run   # 先空跑
python3 scripts/link_to_zotero.py <解读.html> --doi <DOI>
```

前提：Zotero 正在运行并启用本地 API（端口 23119），安装 Zotero MCP Plugin 并开启写权限（端口 23120）。
脚本会把 HTML 放到 PDF 同一文件夹并挂为链接附件（PDF 在 Zotero storage 时改为导入），给条目加标签 `📖 状态:已精读`（可用 `--tag` 改），不删任何标签；重跑只更新原附件。条目不唯一、PDF 不唯一或同名文件冲突时停下，不猜、不覆盖。

## 许可

MIT License。
