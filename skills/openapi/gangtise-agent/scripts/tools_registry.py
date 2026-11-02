"""Leaf tool handlers for this skill."""
from .agent_api import (
    earnings_review,
    hot_topic,
    investment_logic,
    management_sentiment,
    peer_comparison,
    research_outline,
    security_clue,
    stock_one_line_summary,
    stock_one_pager,
    theme_tracking,
    viewpoint_debate,
)

TOOL_HANDLERS = {
    "stock_one_pager": stock_one_pager,
    "investment_logic": investment_logic,
    "peer_comparison": peer_comparison,
    "earnings_review": earnings_review,
    "viewpoint_debate": viewpoint_debate,
    "theme_tracking": theme_tracking,
    "research_outline": research_outline,
    "stock_one_line_summary": stock_one_line_summary,
    "hot_topic": hot_topic,
    "security_clue": security_clue,
    "management_sentiment": management_sentiment,
}
