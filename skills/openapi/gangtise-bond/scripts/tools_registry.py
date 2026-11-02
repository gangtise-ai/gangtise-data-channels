"""Leaf tool handlers for this skill."""
from .announcement import bond_announcement as announcement
from .basic_info import bond_basic_info as basic_info
from .cash_flow import bond_cash_flow as cash_flow
from .default_list import bond_default_list as default_list
from .exercise_notice import bond_exercise_notice as exercise_notice
from .financial import bond_financial as financial
from .indicator import bond_indicator as indicator
from .issuance import bond_issuance_detail as issuance
from .issuance_plan import bond_issuance_plan as issuance_plan
from .issuer_info import bond_issuer_info as issuer_info
from .issuer_rating_change import bond_issuer_rating_change as issuer_rating_change
from .quote import bond_daily_quote as quote
from .rating import bond_rating_overview as rating
from .rating_change import bond_rating_change as rating_change
from .security import security_search as security
from .valuation import bond_valuation_shclearing as valuation

CLI_PREFIX = "bond"

TOOL_HANDLERS = {
    "security": security,
    "basic_info": basic_info,
    "quote": quote,
    "valuation": valuation,
    "cash_flow": cash_flow,
    "announcement": announcement,
    "issuance": issuance,
    "rating": rating,
    "rating_change": rating_change,
    "issuance_plan": issuance_plan,
    "issuer_info": issuer_info,
    "issuer_rating_change": issuer_rating_change,
    "exercise_notice": exercise_notice,
    "financial": financial,
    "indicator": indicator,
    "default_list": default_list,
}
