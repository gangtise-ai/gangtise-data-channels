"""Leaf tool handlers for this skill."""
from .kb import rag_files_finder as kb

TOOL_HANDLERS = {"kb": kb}
