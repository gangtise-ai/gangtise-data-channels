if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import os
import sys
from io import TextIOWrapper
from typing import List, Optional

from .utils import (
    FUND_MANAGER_INFO_URL,
    add_output_arg,
    build_headers,
    error_response,
    execute_jobs,
    parse_str_list,
)

METHOD_NAME = "manager"
FIELD_CN = {
    "managerName": "基金经理",
    "education": "学历",
    "gender": "性别",
    "nationality": "国籍",
    "birthYear": "出生年份",
    "careerStartDate": "证券从业日期",
    "workingYears": "从业年限(年)",
    "managedFundScale": "在管规模(亿元)",
    "managedFundCount": "在管产品数(只)",
    "historyFundCount": "历任管理基金数(只)",
    "historyCompanyCount": "历任基金公司数(家)",
    "currentCompany": "当前公司",
    "currentCompanyYears": "当前公司任职年限(年)",
    "introduction": "简介",
}


def fund_manager(names: List[str], output_dir: Optional[str] = None) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    cleaned = []
    for name in names:
        text = str(name).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    if not cleaned:
        return error_response(METHOD_NAME, "请指定基金经理姓名", output_dir)
    headline = cleaned[0] if len(cleaned) == 1 else f"{cleaned[0]}等{len(cleaned)}位基金经理"
    return execute_jobs(
        method_name=METHOD_NAME,
        headers=headers,
        jobs=[{
            "url": FUND_MANAGER_INFO_URL,
            "payload": {"managerNameList": cleaned},
            "module": "manager_info",
            "label": "基金经理信息",
            "field_cn": FIELD_CN,
        }],
        headline=headline,
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="基金经理基本信息（open-fundamental / fund/manager-info，按姓名精确匹配）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--names", required=True, help="基金经理姓名，逗号分隔，如 张坤,葛兰")
    add_output_arg(parser)
    args = parser.parse_args()
    names = parse_str_list(args.names)
    if not names:
        parser.error("请指定 --names")
    print(fund_manager(names, output_dir=args.output_dir or None))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
