#!/usr/bin/env python3
"""按用户值、文档类型、层次和语言解析正文目标，不生成正文。"""
import argparse,json
ZH={"JOURNAL":10000,"REPORT":12000,"UNDERGRADUATE":20000,"MASTER":30000,"DOCTORAL":50000,"UNSPECIFIED":25000}
EN={"JOURNAL":8000,"REPORT":6000,"UNDERGRADUATE":8000,"MASTER":15000,"DOCTORAL":30000,"UNSPECIFIED":12000}
def resolve(profile,level,language,explicit=None):
    if explicit is not None: target=explicit;source="USER_EXPLICIT"
    elif profile=="CUSTOM": raise ValueError("CUSTOM必须提供用户或模板目标字数")
    elif profile in {"JOURNAL","REPORT"}: target=(ZH if language.startswith("zh") else EN)[profile];source="DOCUMENT_PROFILE_DEFAULT"
    else: target=(ZH if language.startswith("zh") else EN)[level];source="PAPER_LEVEL_DEFAULT" if level!="UNSPECIFIED" else "FALLBACK_DEFAULT"
    return {"target":target,"minimum":round(target*.9),"maximum":round(target*1.1),"unit":"effective_units" if language.startswith("zh") else "english_words","source":source}
def main():
    p=argparse.ArgumentParser();p.add_argument("--document-profile",choices=["THESIS","JOURNAL","REPORT","CUSTOM"],required=True);p.add_argument("--paper-level",choices=["UNDERGRADUATE","MASTER","DOCTORAL","UNSPECIFIED"],default="UNSPECIFIED");p.add_argument("--language",default="zh-CN");p.add_argument("--explicit-target",type=int);a=p.parse_args();print(json.dumps(resolve(a.document_profile,a.paper_level,a.language.lower(),a.explicit_target),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
