"""Leaf tool handlers for this skill."""
from .web_search import web_search

TOOL_HANDLERS = {
    "web_search": web_search,
}
