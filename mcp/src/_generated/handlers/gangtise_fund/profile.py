# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/profile.py
# Regenerate: python3 scripts/generate.py
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
    FUND_BASIC_INFO_URL,
    FUND_FEE_RATE_URL,
    FUND_MANAGER_HISTORY_URL,
    add_output_arg,
    error_response,
    normalize_securities_arg,
    parse_choices,
    parse_types,
    query_by_codes,
    resolve_field_list,
)

METHOD_NAME = "profile"
TYPE_ORDER = ("basic", "fee", "manager")
TYPE_ALIAS = {
    "basic": "basic",
    "info": "basic",
    "基本信息": "basic",
    "基金基本信息": "basic",
    "fee": "fee",
    "费率": "fee",
    "基金费率": "fee",
    "manager": "manager",
    "history": "manager",
    "历任": "manager",
    "历任基金经理": "manager",
    "基金经理": "manager",
}
FEE_ALIAS = {
    "purchasefee": "purchaseFee",
    "purchase": "purchaseFee",
    "申购费": "purchaseFee",
    "申购": "purchaseFee",
    "redemptionfee": "redemptionFee",
    "redemption": "redemptionFee",
    "赎回费": "redemptionFee",
    "赎回": "redemptionFee",
    "managementfee": "managementFee",
    "management": "managementFee",
    "管理费": "managementFee",
    "custodianfee": "custodianFee",
    "custodian": "custodianFee",
    "托管费": "custodianFee",
    "salefee": "saleFee",
    "sale": "saleFee",
    "销售服务费": "saleFee",
}

BASIC_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "fullName": "基金全称",
    "mainFundCode": "基金主代码",
    "investTypeCodeLevel1": "一级分类代码",
    "investTypeNameLevel1": "一级分类",
    "investTypeCodeLevel2": "二级分类代码",
    "investTypeNameLevel2": "二级分类",
    "mgrComp": "基金管理人",
    "custodianBank": "基金托管人",
    "setupDate": "成立日期",
    "maturityDate": "存续截止日",
    "operationStatus": "运行状态",
    "operationMode": "运作方式",
    "exchange": "交易场所",
    "purchaseStatus": "申购状态",
    "minPurchaseAmount": "单笔申购下限(元)",
    "largePurchaseLimit": "大额申购上限(元)",
    "minRedemptionShare": "单笔赎回下限(份)",
    "redemptionArrivalDays": "赎回到账天数(天)",
    "benchmark": "业绩比较基准",
    "riskLevel": "风险等级",
    "investScope": "投资范围",
    "isIndexFund": "是否指数型基金",
    "trackIndexCode": "跟踪指数代码",
    "trackIndexName": "跟踪指数名称",
}
FEE_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "feeType": "费率类型",
    "feeCondition": "费率条件",
    "feeRate": "费率",
}
MANAGER_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "managerName": "基金经理",
    "startDate": "任职开始日期",
    "endDate": "任职结束日期",
    "managedDays": "管理天数(天)",
    "managedReturn": "任职回报(%)",
}


def fund_profile(
    securities: List[str],
    query_type: Optional[str] = None,
    fee_types: Optional[List[str]] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    types, err = parse_types(query_type, TYPE_ALIAS, TYPE_ORDER, ("basic",))
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    fee_types, err = parse_choices(fee_types, FEE_ALIAS, "费率类型")
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    if field_list and "basic" not in types:
        return error_response(METHOD_NAME, "--field-list 仅在查询基金基本信息时生效", output_dir)
    if fee_types and "fee" not in types:
        return error_response(METHOD_NAME, "--fee-type 仅在查询基金费率时生效", output_dir)

    fields: List[str] = []
    if "basic" in types:
        fields, err = resolve_field_list(field_list, BASIC_FIELD_CN, ("fundCode",))
        if err:
            return error_response(METHOD_NAME, err, output_dir)

    jobs = []
    if "basic" in types:
        extra = {}
        keep = None
        if fields:
            send = fields if "fundCode" in fields else ["fundCode", *fields]
            extra["fieldList"] = send
            keep = send
        jobs.append({
            "url": FUND_BASIC_INFO_URL,
            "module": "basic_info",
            "label": "基金基本信息",
            "field_cn": BASIC_FIELD_CN,
            "extra": extra,
            "keep": keep,
        })
    if "fee" in types:
        extra = {"feeTypeList": list(fee_types)} if fee_types else {}
        jobs.append({
            "url": FUND_FEE_RATE_URL,
            "module": "fee_rate",
            "label": "基金费率",
            "field_cn": FEE_FIELD_CN,
            "extra": extra,
        })
    if "manager" in types:
        jobs.append({
            "url": FUND_MANAGER_HISTORY_URL,
            "module": "manager_history",
            "label": "历任基金经理",
            "field_cn": MANAGER_FIELD_CN,
        })
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=jobs,
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="基金档案：基本信息（默认）/ 费率 / 历任基金经理，可单独查或 --type all",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--securities", required=True, help="基金代码/简称/拼音，逗号分隔；亦可传 .csv 路径")
    parser.add_argument(
        "--type",
        "-t",
        default="basic",
        help="basic(基本信息) / fee(费率) / manager(历任基金经理)，逗号分隔；all 三项都查",
    )
    parser.add_argument(
        "--fee-type",
        default=None,
        help="费率类型，逗号分隔：purchaseFee/redemptionFee/managementFee/custodianFee/saleFee；不传返回全部",
    )
    parser.add_argument(
        "--field-list",
        default=None,
        help="仅基本信息：字段英文名或中文名，逗号分隔；不传返回全部，传 all 同样返回全部",
    )
    add_output_arg(parser)
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    fee_types, err = parse_choices(args.fee_type, FEE_ALIAS, "费率类型")
    if err:
        parser.error(err)

    print(
        fund_profile(
            securities,
            query_type=args.type,
            fee_types=fee_types or None,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
