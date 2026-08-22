# 证据清单与执行记录

当论文包含性能、准确率、实验、问卷、病例、用户量或系统运行结果时，使用 `evidence-manifest.json`。每条记录至少包含：

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定且唯一的证据编号 |
| `claim` | 该证据直接支持的最小主张 |
| `evidence_level` | `OBSERVED_REAL_SYSTEM`、`SIMULATED`、`SYNTHETIC_DATA`、`HARDCODED_EXAMPLE`、`VERIFIED_EXTERNAL` 或 `PLANNED` |
| `sources` | 原始数据、外部权威来源或输入材料 |
| `command` | 参数数组或可安全解析的命令文本；真实系统观察必须与执行记录一致 |
| `outputs` | 项目目录内的原始输出文件；不能使用绝对路径或 `..` |
| `sha256` | 输出路径到 SHA-256 的映射；真实系统观察必须匹配实际文件 |
| `limitations` | 证据不能支持什么，尤其说明模拟、合成或硬编码边界 |
| `execution_record` | `OBSERVED_REAL_SYSTEM` 必需；由 `scripts/run_evidence.py` 生成的项目内 JSON 路径 |

## 真实系统观察

不要手写一个命令字符串并声称已经运行。使用安全执行器：

```bash
uv run python /path/to/skill/scripts/run_evidence.py \
  --root /path/to/paper \
  --id EXP-01 \
  --claim "真实系统测试主张" \
  --output-log evidence/exp-01.log \
  --record-output evidence/exp-01-execution.json \
  -- python tests/run_real_experiment.py
```

执行器不使用 shell，限制运行时间和日志大小，记录命令参数、项目目录、开始与结束时间、返回码、超时状态、日志路径和 SHA-256。命令参数疑似包含凭证时拒绝运行。

随后在 `evidence-manifest.json` 的对应条目中引用相同命令、日志路径、摘要和 `execution_record`。`scripts/validate_evidence.py` 会交叉核对记录、日志与清单。

## 非真实证据

`SIMULATED`、`SYNTHETIC_DATA` 和 `HARDCODED_EXAMPLE` 可以用于方法演示，但必须明确限制。校验器会检查清单、项目内文本输出、分章、整合稿和 QA，阻止相同模拟数值被改写成“真实系统实测”。

`VERIFIED_EXTERNAL` 必须提供可核验来源；清单结构通过不等于外部来源权威，引用审计仍需独立完成。
