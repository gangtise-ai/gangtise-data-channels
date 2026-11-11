# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-agent/scripts/agent_api.py
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

from typing import List, Optional

from .agents import openapi_agent
from .expert_intel import expert_intel
from .hot_topic import run_hot_topic_list as hot_topic
from .management_sentiment import management_sentiment
from .security_clue import run_security_clue_list as security_clue

def stock_one_pager(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "stock-one-pager",
        security=security,
        securities=securities,
        output_dir=output_dir,
    )


def investment_logic(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "investment-logic",
        security=security,
        securities=securities,
        output_dir=output_dir,
    )


def peer_comparison(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "peer-comparison",
        security=security,
        securities=securities,
        output_dir=output_dir,
    )


def earnings_review(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    period: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "earnings-review",
        security=security,
        securities=securities,
        period=period,
        output_dir=output_dir,
    )


def viewpoint_debate(
    viewpoint: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "viewpoint-debate",
        viewpoint=viewpoint,
        output_dir=output_dir,
    )


def theme_tracking(
    theme_id: Optional[str] = None,
    date: Optional[str] = None,
    types: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "theme-tracking",
        theme_id=theme_id,
        date=date,
        types=types,
        output_dir=output_dir,
    )


def research_outline(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "research-outline",
        security=security,
        securities=securities,
        output_dir=output_dir,
    )


def stock_one_line_summary(
    security: Optional[str] = None,
    securities: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
):
    return openapi_agent(
        "stock-one-line-summary",
        security=security,
        securities=securities,
        output_dir=output_dir,
    )

__all__ = [
    "stock_one_pager",
    "investment_logic",
    "peer_comparison",
    "earnings_review",
    "viewpoint_debate",
    "theme_tracking",
    "research_outline",
    "stock_one_line_summary",
    "hot_topic",
    "security_clue",
    "management_sentiment",
    "expert_intel",
]
