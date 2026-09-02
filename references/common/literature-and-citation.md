# 公共规则三：文献检索与引用

<!-- compact-core:start -->
先写检索式和纳排标准，再写正文。发现层用于找候选，证据层读取全文/法源/标准/官方数据，核验层核对题名、作者、年份、版本与DOI；发现记录不能冒充全文。文献状态仅为VERIFIED_FULLTEXT、VERIFIED_METADATA、UNVERIFIED、REJECTED。核心主张须由有页/节定位的VERIFIED_FULLTEXT支撑；只核元数据不能转述样本、方法、数字或引语。正文引用、文末文献、references.bib和证据矩阵必须闭合。
<!-- compact-core:end -->

02-search-log.md记录真实数据库、访问路径、检索式、日期、筛选和限制。访问模式为OPEN_API、OPEN_WEB、LOGIN_REQUIRED、INSTITUTION_REQUIRED或MANUAL_ONLY；知道库名不等于已经访问。订阅库不可用时记录CAPABILITY_GAP，转OpenAlex、Crossref、PubMed/PMC/Europe PMC、arXiv、DOAJ及官方网站。

03-evidence-matrix.csv至少含source_id、题名、作者、年份、类型、来源、卷期页、DOI/URL、访问日期、核验来源、支持主张、章节、状态、evidence_role、access_mode、publication_status、fulltext_locator、page_locator、备注；本地全文另记文件与SHA。evidence_role用DISCOVERY/EVIDENCE/VERIFICATION，publication_status区分正式、预印本、工作论文、标准、官方文件和数据集。

预印本与正式版按工作身份去重，核心因果、疗效和性能优先正式版。中文核心标注CSSCI、CSCD、北大核心或科技核心及目录版本。系统综述至少双库并保留完整流程。Crossref未收录不自动等于虚构；DOI解析后题名明确错配为Critical。法条、标准、案例、手册和数据集按各自版本、条款、页码、许可与下载日期核验。

NUMERIC正文和文末使用同一编号；AUTHOR_YEAR不得保留编号列表，并为每条来源记录唯一citation_token。达不到最低文献目标时先扩展同义词、英文词、标准和官方文档；仍不足则报告PARTIAL，不能凑假文献。
