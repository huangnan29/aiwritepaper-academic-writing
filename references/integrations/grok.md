# Agent适配：Grok Build / Grok Bot

本附加规则解决论文执行器与拥有Imagine的父代理之间的能力分离，不改变论文内容决策。

- `AGENT_ADAPTER` 固定记录为 `grok`。
- 同时检查当前论文执行器、父代理和客户端是否真实暴露 Grok Imagine、`GenerateImage` 或等价图片调用。任一层可调用时，`image_generation.available=true`，并在 `callers[]` 记录真实调用层。
- 论文执行器先完成全部 `figure_plan[]` 与逐图Prompt；父代理必须遍历所有 `imagegen_eligible=true` 的任务逐张生图，不能只补第一张概念图。
- 父代理把每张原始生成图、调用回执和Prompt摘要交回同一论文输出目录。论文执行器核对节点、箭头、文字与正文事实后再设置 `final_embed_file`。
- 只有当前执行器、父代理和客户端均无图片调用时才允许 `SVG_FALLBACK`。不得把“子执行器无工具”误写成整个任务无工具。
- 最终打包不得移除正式DOCX/PDF时间戳或重命名Manifest记录的文件；打包完成后再次核对路径与SHA-256。

