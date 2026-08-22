# 模型与客户端图片能力边界

本表是 2026-08-22 的核验快照。目录名只代表本项目测试入口，不自动等于模型 API 的全部能力。

| 项目入口 | 原生图片输出判断 | 可用的同平台或客户端路径 | 本项目证据 |
| --- | --- | --- | --- |
| `5.6-luna` | GPT-5.6 Luna 是推理与代码模型，不应当作图片输出模型 | Codex 若暴露内置图片工具，可调用 GPT Image 系列 | 仅见 SVG 与其 PNG 渲染，未见图片模型调用 |
| `GLM-5.3-test` | GLM 文本模型与 GLM-Image/CogView 图片模型是不同入口 | 智谱平台可显式调用 GLM-Image 或 CogView | 未见图片 API 调用 |
| `ds4-flash`、`dsh`、`dsh-pro` | 当前项目按文本/代码代理处理 | 只能在客户端另接图片工具或专用图片模型 | PNG 多为 SVG/HTML 渲染或截图，未见图片模型调用 |
| `gemini-3.7-flash` | Gemini 3.7 Flash 是通用模型；官方另列 Nano Banana 图片模型 | 显式切换到 `gemini-3.1-flash-image`、Lite Image 或 Pro Image | 目录中没有论文图片产物 |
| `grok-4.6`、`grok-build` | Grok 4.6 本身与 Grok Imagine 图片模型分开 | Grok 应用可用 Imagine；API 可显式调用 Grok Imagine Image | 有 SVG/PNG，但未发现本项目调用 Imagine 的证据 |
| `kimi-app`、`kimi-code`、`workbuddy-k3` | 仅凭目录名无法核实原生图片输出 | 若客户端暴露图片工具，可按工具能力调用 | 未见图片模型调用，按 `CAPABILITY_GAP` 处理 |
| `opus-5` | 当前目录按文本/代码代理处理，不假定原生图片输出 | 只能依赖当前客户端的外部图片工具 | 仅见 SVG 与 PNG 渲染 |
| `qoder-qwen-3.8`、`qwen-3.8-27b`、`qwen-3.8-max` | Qwen 通用/视觉理解模型不等于 Qwen-Image | 阿里云百炼可显式调用 Qwen-Image 图片模型 | 未见图片 API 调用 |

## 当前可核验的专用图片模型族

- OpenAI：GPT Image 2；Codex 的内置图片工具是否可用取决于当前运行环境。
- Google：Nano Banana 2、Nano Banana 2 Lite、Nano Banana Pro 等图片模型；通用 Flash 型号不自动继承图片输出。
- xAI：Grok Imagine Image；Grok 应用也可通过 Imagine 生成图片。
- 阿里云：Qwen-Image 系列；与 Qwen 文本、视觉理解型号分开调用。
- 智谱：GLM-Image、CogView 系列；与 GLM 文本型号分开调用。

任何未在当前运行中实际出现的工具或模型均只能记为“平台可选”，不能在能力报告中写成“已具备”或“已生成”。

## 官方核验入口

- OpenAI 模型目录与 GPT Image 2：`https://developers.openai.com/api/docs/models/all`、`https://developers.openai.com/api/docs/models/gpt-image-2`
- Google Gemini 图片生成：`https://ai.google.dev/gemini-api/docs/image-generation`
- xAI Grok Imagine 图片生成：`https://docs.x.ai/developers/model-capabilities/images/generation`
- 阿里云 Qwen-Image：`https://help.aliyun.com/en/model-studio/image-model/`
- 智谱 GLM-Image：`https://docs.bigmodel.cn/cn/guide/models/image-generation/glm-image`

这些页面和型号可能变化。新运行应重新核验官方页面，并把核验日期写入能力报告。
