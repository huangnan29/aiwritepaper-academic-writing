# 公共规则十：数学公式与跨格式渲染

公式既是学术论证的一部分，也是最终文档中的结构化对象。不得把 LaTeX 源码直接复制进 Word 或 PDF，也不得只看 Markdown 正常就宣称公式交付完成。

## 公式内容与符号审计

- 每个公式先确认其用途、来源或推导依据、适用条件和所在论证位置；不能为了显得“学术”而堆放与上下文无关的公式。
- 同一符号在全文保持唯一含义。首次出现时定义符号、上下标和单位；向量、矩阵、随机变量、估计量、集合与标量的字体约定保持一致。
- 等号两侧量纲必须一致；代入计算记录单位换算、数量级和有效数字。没有真实测量值时，不得把示例参数写成实测结果。
- 重要独立公式按章节连续编号并在正文中真实引用；行内短式不强制编号。编号、公式与解释不得相互脱节。
- `FULL_BUILD` 输出 `equations/formula-audit.md`。逐项记录重要独立公式的编号、章节、语义用途、符号与单位、假设、量纲/数量级检查和修订结果；全文没有公式时明确写“未使用数学公式”，不要虚构条目。

## Markdown 唯一源稿

`07-paper-full.md` 是公式内容的唯一源稿。最终整合时采用 Pandoc 兼容的 TeX 数学语法：行内公式统一为 `$...$`，独立公式统一为 `$$...$$`。模型草稿中的 `\(...\)` 与 `\[...\]` 必须在导出前等价归一化，不得把分隔符显示在正文中。

- 数学命令必须位于公式分隔符内部；分隔符、花括号和 `\begin`/`\end` 必须成对。
- 使用Python、JavaScript或其他程序写入Markdown时，必须保留TeX反斜杠本身，避免 `\text`、`\frac`、`\nabla` 被字符串转义解释成制表、换页或换行控制字符。写入后检查公式中不存在TAB、FORM FEED、NUL等异常控制字符；发现后从公式语义源修复，不能只删除不可见字符。
- 公式内部使用 TeX 命令表达数学结构，例如 `\frac`、`\sqrt`、`\mathbf`、`\mathrm`；中文解释放在公式外。必须在公式内写短文本时使用目标转换器支持的 `\text{}`，并在DOCX/PDF中实际验证。
- 标题、图片画布和 Markdown 表格单元格中尽量不放复杂公式。确有必要时改为正文独立公式或使用可被当前导出链正确转换的简式。
- 不以普通Unicode字符、空格拼接或截图公式替代结构化公式；不能用 `C_f = ...` 普通文本冒充可编辑数学对象。

## DOCX 与 PDF 导出

正式 DOCX 中的公式必须转换为 Word 可编辑公式对象，即 OOXML Math（OMML，`m:oMath`/`m:oMathPara`）。`w:t` 普通文本中不得残留 `$`、`$$`、`\(`、`\[`、`\frac`、`\sqrt`、`\text`、`\mathbf`、`\partial`、`\nabla` 等 TeX 源码。

优先使用能把 Markdown/TeX 数学转换为 OMML 的导出链，例如 Pandoc 读取启用 `tex_math_dollars` 的 Markdown 后生成 DOCX。后续设置页面、字体、标题、题注和目录时必须保留已有 OMML 节点；禁止用 `python-docx` 或自定义 XML 程序读取整段纯文本后重建段落，因为这会把公式扁平化为普通字符。若必须使用自定义Word生成器，应先完成 TeX→OMML 转换并验证节点数量，不能直接写入 LaTeX 字符串。

PDF必须由同一份已通过公式检查的定稿生成，优先由已验证 DOCX 转换或由同一 Markdown 经成熟数学排版链导出。PDF可见文本中不得出现公式分隔符和 TeX 命令。公式截图或栅格化仅可作为明确记录的无障碍受损降级，不能用于 `THESIS` 或 `JOURNAL` 的 `PASS`；转换能力缺失时记录 `CAPABILITY_GAP`，交付不得虚报完成。

## 公式机械验收与视觉复核

导出后必须运行公式检查器，并把报告保存为 `equations/formula-verification.json`：

```bash
python3 "<SKILL_DIR>/scripts/verify_formula_rendering.py" \
  --root "<OUTPUT_DIR>" \
  --markdown "07-paper-full.md" \
  --run-manifest "run-manifest.json" \
  --audit "equations/formula-audit.md" \
  --report "equations/formula-verification.json"
```

检查器只检查分隔符/花括号、DOCX中的OMML与残留源码、PDF中的可见残留、文件摘要和审计文件，不判断公式的学术含义。存在公式时，DOCX的OMML数量不得少于源稿识别出的公式数量；DOCX或PDF出现任何可见TeX残留即失败。PDF文本无法解析时标记 `CAPABILITY_GAP` 并失败，不能以“肉眼可能正常”代替核验。

机械检查通过后仍需抽查最终DOCX与PDF的公式页面，确认分式、根号、上下标、希腊字母、矩阵、换行、编号和中文说明没有裁切、错位、缺字或乱码。至少抽查首个公式、最复杂公式、含中文/单位的公式和最后一个公式，并把结果写入 `equations/formula-audit.md`。公式报告的 `status` 必须为 `FORMULA_OK`，且其中绑定的Markdown、DOCX和PDF SHA-256与最终文件一致，完整交付才可标记 `PASS`。
