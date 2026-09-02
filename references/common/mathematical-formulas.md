# 公共规则十：公式

<!-- compact-core:start -->
先核对公式含义、符号、单位、前提、边界和代入，再处理渲染。Markdown统一使用`$...$`与`$$...$$`；代码中安全处理反斜杠。DOCX公式必须是可编辑OMML，PDF不得显示TeX源码，不能用生图模型重画精确公式。重要公式分配稳定ID并记录源定位；不能只比较Markdown公式数与OMML节点数。
<!-- compact-core:end -->

先用本稿实际需要的分式、上下标、根式、希腊字母、矩阵和中文说明做最小导出测试，再复用同一路径。不可通过python-docx读取整段后重新赋值破坏数学对象。长公式按数学结构分行，编号右对齐，检查溢出、缺字和上下标。

equations/formula-audit.md记录重要公式ID、位置、含义检查和问题，不复制全文。verify_formula_rendering.py绑定Markdown、DOCX和PDF摘要。无公式记录真实零项；缺视觉或转换能力记CAPABILITY_GAP。
