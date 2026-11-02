# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/scripts/tools_registry.py
# Regenerate: python3 scripts/generate.py
"""Leaf tool handlers for this skill."""
from .block_constituents import block_constituents_data as block_constituents
from .company_indicator import company_indicator_data as company_indicator
from .concept import concept_data as concept
from .earning_forecast import earning_forecast_data as earning_forecast
from .financial import financial_data as financial
from .fund_flow import fund_flow_data as fund_flow
from .industry_indicator import industry_indicator_data as industry_indicator
from .main_business import main_business_data as main_business
from .quote import quote_data as quote
from .security import security_search as security
from .shareholder import shareholder_data as shareholder
from .valuation import valuation_data as valuation

TOOL_HANDLERS = {
    "block_constituents": block_constituents,
    "company_indicator": company_indicator,
    "concept": concept,
    "earning_forecast": earning_forecast,
    "financial": financial,
    "fund_flow": fund_flow,
    "industry_indicator": industry_indicator,
    "main_business": main_business,
    "quote": quote,
    "security": security,
    "shareholder": shareholder,
    "valuation": valuation,
}
