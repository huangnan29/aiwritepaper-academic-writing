# 最终执行提示词的原生文件拼接

仅当 `python3 <SKILL_DIR>/scripts/compose_prompt.py` 不可用时读取本文件。目标是通过文件系统按顺序拼接，不让模型复述完整提示词。

拼接顺序固定为：

1. `<OUTPUT_DIR>/run-params.md`；
2. 唯一的 `<SKILL_DIR>/references/compiled-prompts/<PROMPT>-full.md`；
3. 可选的开题或答辩附加规则。

## macOS或Linux

```bash
prompt_tmp="<OUTPUT_DIR>/.final-execution-prompt.tmp"
{
  cat "<OUTPUT_DIR>/run-params.md"
  printf '\n\n'
  cat "<SKILL_DIR>/references/compiled-prompts/<PROMPT>-full.md"
} > "$prompt_tmp" && mv "$prompt_tmp" "<OUTPUT_DIR>/final-execution-prompt.md"
```

需要附加交付时，在结束大括号前增加一次换行和对应文件：

```bash
printf '\n\n'
cat "<SKILL_DIR>/references/deliverables/proposal-report.md"
```

答辩材料改用 `defense-presentation.md`。

## Windows PowerShell

```powershell
$promptParts = @(
  "<OUTPUT_DIR>/run-params.md",
  "<SKILL_DIR>/references/compiled-prompts/<PROMPT>-full.md"
)
$promptTmp = "<OUTPUT_DIR>/.final-execution-prompt.tmp"
$promptOut = "<OUTPUT_DIR>/final-execution-prompt.md"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$promptText = ($promptParts | ForEach-Object { [IO.File]::ReadAllText($_) }) -join "`n`n"
[IO.File]::WriteAllText($promptTmp, $promptText + "`n", $utf8NoBom)
Move-Item -Force $promptTmp $promptOut
```

需要附加交付时，把对应deliverable文件加入 `$promptParts`。

## 拼接后检查

- 输出文件非空；
- 参数头只出现一次；
- 所选完整提示词的开头与结尾均存在；
- 未混入第二个方向提示词；
- UTF-8中文可读；
- 从头到尾完整读取 `final-execution-prompt.md` 一次后再执行。
