# 适配：Grok Build / Grok Bot

记录`AGENT_ADAPTER=grok`。检查执行器、父代理和客户端是否真实提供Imagine/GenerateImage；任一层可用即完成全部imagegen_eligible任务，不只生成首图。执行器先写逐图事实与Prompt，父代理回传原图和回执；核对后将真实生图或中文覆盖PNG设为final_embed_file。只有各层均无工具或真实调用失败并留回执时才SVG降级。打包后复核DOCX/PDF名称与摘要。
