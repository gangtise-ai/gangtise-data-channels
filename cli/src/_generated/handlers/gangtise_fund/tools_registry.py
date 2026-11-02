# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/tools_registry.py
# Regenerate: python3 scripts/generate.py
"""Leaf tool handlers for this skill."""
from .allocation import fund_allocation as allocation
from .asset_size import fund_asset_size as asset_size
from .etf_components import etf_components
from .etf_header import etf_header
from .etf_share import etf_share
from .holder_structure import fund_holder_structure as holder_structure
from .manager import fund_manager as manager
from .indicator import fund_indicator as indicator
from .nav import fund_nav as nav
from .portfolio import fund_portfolio as portfolio
from .profile import fund_profile as profile
from .security import security_search as security
from .top_holders import fund_top_holders as top_holders

CLI_PREFIX = "fund"

TOOL_HANDLERS = {
    "security": security,
    "profile": profile,
    "allocation": allocation,
    "portfolio": portfolio,
    "asset_size": asset_size,
    "holder_structure": holder_structure,
    "top_holders": top_holders,
    "indicator": indicator,
    "nav": nav,
    "manager": manager,
    "etf_header": etf_header,
    "etf_components": etf_components,
    "etf_share": etf_share,
}
