# 公共规则三：文献检索与引用

先设计检索式和纳入排除标准，再写正文。来源优先级为同行评议论文、学位论文、政府或标准机构、出版社页面、官方技术文档。聚合页、采集站、营销页和匿名内容只能作为线索。

## 信源三层分工

- 发现层：Web of Science、Scopus、Engineering Village（Ei Compendex、Inspec）、DBLP、CNKI检索结果页等索引与引文库，用于查找候选文献和引文追踪；索引记录本身不是全文证据。
- 证据层：出版社全文、机构知识库或作者合法存档版本、正式法源、标准原文、官方指南、官方数据集和监管披露，用于实际阅读并支撑论文主张；出版平台上的文章是否适合作核心证据仍需逐篇判断。
- 核验层：Crossref、DOI解析、出版社官方页、PubMed或SinoMed记录，用于核对题名、作者、年份、卷期页、DOI和版本；元数据核验不能代替全文阅读。

当前方向提示词内置“文献信源”清单，按其顺序开库。信源跟随证据形态和方向路由，不跟随专业名称。

## 访问方式与真实检索

信源访问方式标记为 `OPEN_API`、`OPEN_WEB`、`LOGIN_REQUIRED`、`INSTITUTION_REQUIRED` 或 `MANUAL_ONLY`。方向清单中的标记描述典型访问条件，不代表本次运行已经具备权限；同一来源存在多种路径时用 `|` 连接。纸质教材与手册、授权内部材料、无法自动读取的馆藏或标准原文标记为 `MANUAL_ONLY`。知道数据库名称不等于具备访问权限：`02-search-log.md` 的每条检索必须记录实际使用的数据库和访问路径，未实际访问的库不得出现在检索记录中，不得虚构“已在Web of Science、Scopus、SciFinder中检索”之类的过程。

首选库需要机构订阅且当前环境不可访问时，记录 `CAPABILITY_GAP` 并转入开放路线继续检索：OpenAlex、Crossref、PubMed、PMC、Europe PMC、arXiv、DOAJ、Semantic Scholar以及官方政府、标准、统计和法源网站。开放路线是无订阅环境下的正当检索方式，不是质量缺陷，但应在检索日志中说明库覆盖面的限制。

## 中文题录入口

中文学位论文和国内期刊题录，多数方向都要开中文库：CNKI及海外镜像 `oversea.cnki.net` 为 `OPEN_WEB` 题录入口，多数全文属于 `LOGIN_REQUIRED|INSTITUTION_REQUIRED`；万方、维普按实际访问条件标记，用于与CNKI交叉去重补漏；医学与护理方向优先使用中国生物医学文献服务系统SinoMed中的中国生物医学文献数据库CBM做主题词检索，并按本次访问记录 `OPEN_WEB|LOGIN_REQUIRED|INSTITUTION_REQUIRED`。表述“CNKI核心刊”时必须区分CSSCI、CSCD、北大核心或中国科技核心，并记录所依据的目录版本。

## 预印本与工作论文

arXiv、bioRxiv、ChemRxiv、SSRN、NBER工作论文可以收录，但必须在证据矩阵中标注 `publication_status` 为预印本或工作论文，并检查是否已有正式发表版本；两者去重后优先引用正式版。核心因果、疗效或性能主张优先使用正式发表来源，仅有预印本支持时降低表述强度。系统综述中预印本单独报告，除非检索协议明确允许，不混入正式纳入集。

## 检索与证据记录

在 `02-search-log.md` 记录数据库、实际访问路径、检索式、日期、筛选步骤和访问限制。在 `03-evidence-matrix.csv` 记录 source_id、题名、作者、年份、类型、来源、卷期页、DOI、URL、访问日期、核验来源、支持主张、章节、状态、evidence_role、access_mode、publication_status 和备注。

上述字段是最低证据契约，不是可选示例。只包含 `source_id,DOI,status` 或缺少题名、作者、年份、支持主张、章节和访问/发表状态的极简表不属于完整证据矩阵，不能通过最终交付验收。

新增字段使用受控值：`evidence_role` 只能为 `DISCOVERY`、`EVIDENCE`、`VERIFICATION`，兼具多种角色时用 `|` 连接；`access_mode` 只能使用上述五种访问标记，实际路径与典型条件不一致时以本次观察为准；`publication_status` 使用 `PUBLISHED`、`PREPRINT`、`WORKING_PAPER`、`STANDARD`、`OFFICIAL_DOCUMENT`、`DATASET` 或 `OTHER`。空值必须解释，不能自行创造近义状态。

状态只能为：

- `VERIFIED_FULLTEXT`：元数据与相关全文内容已核验；
- `VERIFIED_METADATA`：只核验元数据，只能支持存在性和书目信息；
- `UNVERIFIED`：不得进入正式引用；
- `REJECTED`：重复、低质量或不匹配。

核心论点只能由已阅读且匹配的来源支持。每条文内引用必须匹配参考文献，每条参考文献必须在正文出现。无法访问全文时降低表述强度，不得假装读过。输出 `references.bib` 与 `04-reference-audit.md`。

`VERIFIED_METADATA` 不得用于转述全文实验参数、样本、定量结果、详细方法或原文引语；正式摘要能够直接确认的研究范围须明确写成摘要层。支撑全文级主张时使用 `VERIFIED_FULLTEXT` 并保留定位。法条、标准、案例数字和技术手册参数分别记录法源版本/条款、标准号/范围页、来源文件/页码/期间/计算和手册版本/页码。

最低参考文献数量是生产目标，不是最后才检查的备注。检索和核验应持续到达到 `MIN_REFERENCES`，或已经穷尽当前可用来源与工具。未达到最低数量时不得标记 `PASS`；但应先扩大同义词、英文关键词、相关方法、标准和官方文档检索，不得只用少量来源反复支撑全文。
