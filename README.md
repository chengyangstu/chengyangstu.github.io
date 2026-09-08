# Yancheng · 文章每周简报

个人主页：https://chengyangstu.github.io/

论文周报：https://chengyangstu.github.io/plasma/

每周三北京时间 09:00 由 Codex 定时检索 arXiv，优先**聚变等离子体中的磁重联理论和模拟**：撕裂模、微撕裂模、磁岛、新经典撕裂模、锯齿/内扭结、误差场穿透及破裂中的重联。实验室重联为相关补充，天体重联及通用工具优先级较低。

每次严格按首次提交时间筛选过去七天的新论文，保留相关候选清单，并为选中的论文生成中文简报，注明真实阅读范围、方法、主要发现、局限与原文位置。arXiv 的索引和公布可能有延迟，关键词检索也可能漏检；Codex 更新时补查相关关键词。不把历史修订当成本周新投稿，不用旧文凑数。

## 历史和收藏

- 每期位于 `plasma/data/issues/<UTC截止时间>.json`。只能新增，重复生成同一期会拒绝覆盖。
- `plasma/data/index.json` 是全部历史文件的可重建索引，不是保留最近若干期的滚动窗口。
- 页面可以切换周次、按方向/方法筛选、搜索并打开中文简报，支持简报 Markdown 下载和论文直达链接。
- 宋体与浅紫底色；点击后在文章下方展开简报。每期最前面的「本周总体报告」逐篇说明该期简报涵盖的工作。
- 收藏在当前浏览器 localStorage 中保存论文和简报的完整快照。支持 JSON 导出与合并导入；不自动跨设备同步。清理浏览器数据会清除本地收藏，请定期导出。

## 自动更新

定时阅读使用 Codex 桌面自动化，运行时电脑和 Codex 需要可用；不需要 AI API Key。错过后按未发布的周三窗口补做。GitHub Actions 在内容 push 后发布网站，网站阅读不依赖电脑开机。只在新一期发布、失败或需要用户处理时通知。

本地准备和发布流程见 [AGENTS.md](AGENTS.md)。安装 PDF 提取依赖后：

```powershell
python -m pip install -r requirements.txt
python -X utf8 scripts/weekly.py prepare --limit 10
# 阅读 .cache/packet.json 及 PDF 正文，生成 .cache/briefs.json
python -X utf8 scripts/weekly.py publish
python -X utf8 scripts/check.py
```

临时文件和 PDF 不发布。Pages 工作流只上传主页、样式、图标和 `plasma/`，网页无需服务器或前端构建依赖。

## 信息来源

[arXiv API 文档](https://info.arxiv.org/help/api/user-manual.html) · [GitHub Pages](https://docs.github.com/en/pages/quickstart)

整理方式参考 [arxiv-sanity-lite](https://github.com/karpathy/arxiv-sanity-lite) 的标签与阅读库思路，以及 [paper-digest](https://github.com/X-PG13/paper-digest) 的总览、逐篇贡献与局限结构。本站代码独立编写；简报依据原始论文，未转载这些项目的论文解读。

简报是 AI 辅助整理，不替代原文或同行评审。所有论文均保留 arXiv 版本、提交日期、PDF 来源和原文定位。
