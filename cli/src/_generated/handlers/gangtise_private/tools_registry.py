# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/scripts/tools_registry.py
# Regenerate: python3 scripts/generate.py
"""Leaf tool handlers for this skill."""
from .private_cloud import private_cloud_finder as private_cloud
from .private_meeting import private_meeting_finder as private_meeting
from .private_record import private_record_finder as private_record
from .stockpool import stockpool_finder as stockpool
from .wechat_message import wechat_message_finder as wechat_message

TOOL_HANDLERS = {
    "private_record": private_record,
    "private_meeting": private_meeting,
    "private_cloud": private_cloud,
    "stockpool": stockpool,
    "wechat_message": wechat_message,
}
