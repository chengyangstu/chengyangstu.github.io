# Yancheng · 文章每周简报

个人主页：https://chengyangstu.github.io/

论文周报：https://chengyangstu.github.io/plasma/

计算教材：https://chengyangstu.github.io/cuda/

## CUDA 与 GPU 高性能等离子体计算教材

24 章中文教材，正文为宋体、标题为黑体，英文优先 Times New Roman，淡紫色学术排版，配章节/正文搜索、连续阅读与打印。各章增加入门概念解释，第五章用线程分组图和具体索引演算解释 thread/block/grid。公式采用 TeX / KaTeX，代码使用带语言标识的独立代码块，可在手机局部横向滚动。覆盖量纲与硬件、CUDA 内核与性能、静电与电磁 PIC、守恒电流沉积、Harris/GEM、重联诊断、MPI 多 GPU 与云端、Vlasov、回旋动理学与微撕裂，并提供论文、官方文档、视频与 24 周代码训练。

配套 `cuda/labs/` 有完整 1D1V 静电 PIC CPU 参考、幅值拟合脚本、CUDA 向量和粒子内核，以及 MPI/CUDA halo 练习。CPU 数值检查已运行；CUDA/MPI 示例尚未编译或在对应硬件执行，网页与代码说明均明确标注。多卡章节包含 2/4/8 卡验证、粒子迁移、边界电流加和、强弱扩展和重启训练。它们不冒充已完成的生产级重联求解器。

检查教材链接与章节：`python scripts/check_tutorial.py`。CPU 数值检查：`python cuda/labs/pic1d.py --check`（需 NumPy）。

每周三北京时间 09:00 由 Codex 定时检索 arXiv，优先**聚变等离子体中的磁重联理论和模拟**：撕裂模、微撕裂模、磁岛、新经典撕裂模、锯齿/内扭结、误差场穿透及破裂中的重联。实验室重联为相关补充，天体重联及通用工具优先级较低。

每次严格按首次提交时间筛选过去七天的新论文，保留相关候选清单，并为选中的论文生成中文简报，注明真实阅读范围、方法、主要发现、局限与原文位置。arXiv 的索引和公布可能有延迟，关键词检索也可能漏检；Codex 更新时补查相关关键词。不把历史修订当成本周新投稿，不用旧文凑数。

## 历史和收藏

- 每期位于 `plasma/data/issues/<UTC截止时间>.json`。只能新增，重复生成同一期会拒绝覆盖。
- `plasma/data/index.json` 是全部历史文件的可重建索引，不是保留最近若干期的滚动窗口。
- 页面可以切换周次、按方向/方法筛选、搜索并打开中文简报，支持简报 Markdown 下载和论文直达链接。
- 宋体与浅紫底色；点击后在文章下方展开简报。每期最前面的「本周总体报告」逐篇说明该期简报涵盖的工作。
- 收藏在当前浏览器 localStorage 中保存论文和简报的完整快照。支持 JSON 导出与合并导入；不自动跨设备同步。清理浏览器数据会清除本地收藏，请定期导出。
- 简报中点击「开启高亮工具」，即可逐段标记或取消重点。高亮独立保存，刷新后保留；在「我的收藏」分别导出/导入收藏与高亮。标记按期次与段落绑定，新修订不会改动旧版本的标记。
- 扩充/纠错用 `publish --revision-of 原期ID --briefs 稿件路径`，新文件按创建时间命名，保留原检索窗口并标注扩充版；旧 JSON 不改写。

## 自动更新

定时阅读使用 Codex 桌面自动化，运行时电脑和 Codex 需要可用；不需要 AI API Key。错过后按未发布的周三窗口补做。GitHub Actions 在内容 push 后发布网站，网站阅读不依赖电脑开机。只在新一期发布、失败或需要用户处理时通知。

固定编辑流程见 [EDITORIAL.md](EDITORIAL.md)，执行入口见 [AGENTS.md](AGENTS.md)。流程包含相关性分级、原文证据记录、结构化解读、事实/阅读/排版三轮复核和永久归档。自动检查不代替科学事实核对。安装 PDF 提取依赖后：

```powershell
python -m pip install -r requirements.txt
python -X utf8 scripts/weekly.py prepare --limit 10
# 阅读 .cache/packet.json 及 PDF 正文，生成 .cache/briefs.json
node scripts/check_reader.cjs .cache/briefs.json
python -X utf8 scripts/weekly.py publish
python -X utf8 scripts/check.py
```

临时文件和 PDF 不发布。Pages 工作流只上传公开主页、阅读样式与脚本、图标、`plasma/`、`cuda/` 与 `vendor/`，网页无需服务器或前端构建。KaTeX 固定版本、自托管脚本与字体，不依赖第三方 CDN；版本和 MIT 许可证位于 `vendor/katex/`。`node scripts/check_reader.cjs` 检查数学语法、字体文件、排序、高亮数据和索引练习。

## 信息来源

[arXiv API 文档](https://info.arxiv.org/help/api/user-manual.html) · [GitHub Pages](https://docs.github.com/en/pages/quickstart)

整理方式参考 [arxiv-sanity-lite](https://github.com/karpathy/arxiv-sanity-lite) 的标签与阅读库思路，以及 [paper-digest](https://github.com/X-PG13/paper-digest) 的总览、逐篇贡献与局限结构。本站代码独立编写；简报依据原始论文，未转载这些项目的论文解读。

简报是 AI 辅助整理，不替代原文或同行评审。所有论文均保留 arXiv 版本、提交日期、PDF 来源和原文定位。
