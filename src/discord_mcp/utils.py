# src/discord_mcp/utils.py
"""
Utility functions for Discord operations
"""

import discord
import aiohttp
from typing import List, Optional

def parse_permissions(permission_list: List[str]) -> discord.Permissions:
    """Convert list of permission strings to discord.Permissions object"""
    if not permission_list:
        return discord.Permissions.none()
    
    permissions = discord.Permissions.none()
    
    # Map common permission names to discord.py attributes
    permission_mapping = {
        "administrator": "administrator",
        "admin": "administrator",
        "manage_server": "manage_guild",
        "manage_guild": "manage_guild",
        "manage_channels": "manage_channels",
        "manage_roles": "manage_roles",
        "manage_messages": "manage_messages",
        "manage_webhooks": "manage_webhooks",
        "manage_emojis": "manage_emojis_and_stickers",
        "manage_emojis_and_stickers": "manage_emojis_and_stickers",
        "kick_members": "kick_members",
        "ban_members": "ban_members",
        "create_instant_invite": "create_instant_invite",
        "view_channels": "view_channel",
        "view_channel": "view_channel",
        "send_messages": "send_messages",
        "send_tts_messages": "send_tts_messages",
        "embed_links": "embed_links",
        "attach_files": "attach_files",
        "read_message_history": "read_message_history",
        "mention_everyone": "mention_everyone",
        "use_external_emojis": "external_emojis",
        "external_emojis": "external_emojis",
        "add_reactions": "add_reactions",
        "connect": "connect",
        "speak": "speak",
        "mute_members": "mute_members",
        "deafen_members": "deafen_members",
        "move_members": "move_members",
        "use_voice_activation": "use_voice_activation",
        "priority_speaker": "priority_speaker",
        "stream": "stream",
        "change_nickname": "change_nickname",
        "manage_nicknames": "manage_nicknames",
        "use_application_commands": "use_application_commands",
        "request_to_speak": "request_to_speak",
        "manage_events": "manage_events",
        "manage_threads": "manage_threads",
        "create_public_threads": "create_public_threads",
        "create_private_threads": "create_private_threads",
        "use_external_stickers": "external_stickers",
        "send_messages_in_threads": "send_messages_in_threads",
        "use_embedded_activities": "use_embedded_activities",
        "moderate_members": "moderate_members"
    }
    
    for perm in permission_list:
        # Convert to lowercase and handle variations
        perm_lower = perm.lower().replace(" ", "_").replace("-", "_")
        
        # Map the permission
        discord_perm = permission_mapping.get(perm_lower, perm_lower)
        
        if hasattr(permissions, discord_perm):
            setattr(permissions, discord_perm, True)
    
    return permissions

def hex_to_color(hex_str: str) -> discord.Color:
    """Convert hex color string to discord.Color"""
    if not hex_str:
        return discord.Color.default()
    
    # Remove # if present
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    
    try:
        # Convert hex to integer
        color_int = int(hex_str, 16)
        return discord.Color(color_int)
    except ValueError:
        # Return default color if conversion fails
        return discord.Color.default()

async def fetch_image_bytes(url: str) -> Optional[bytes]:
    """Fetch image bytes from URL for emoji/sticker creation"""
    if not url:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None
    except Exception:
        return None

def format_channel_type(channel_type: discord.ChannelType) -> str:
    """Format channel type for display"""
    type_emojis = {
        discord.ChannelType.text: "💬",
        discord.ChannelType.voice: "🔊",
        discord.ChannelType.category: "📁",
        discord.ChannelType.news: "📢",
        discord.ChannelType.stage_voice: "🎤",
        discord.ChannelType.forum: "💭",
        discord.ChannelType.private_thread: "🧵",
        discord.ChannelType.public_thread: "🧵",
        discord.ChannelType.news_thread: "📰"
    }
    
    emoji = type_emojis.get(channel_type, "📋")
    return f"{emoji} {channel_type.name.replace('_', ' ').title()}"

def format_permissions(permissions: discord.Permissions) -> List[str]:
    """Format permissions object into readable list"""
    perm_list = []
    
    # Check important permissions
    important_perms = [
        ("administrator", "Administrator"),
        ("manage_guild", "Manage Server"),
        ("manage_channels", "Manage Channels"),
        ("manage_roles", "Manage Roles"),
        ("manage_messages", "Manage Messages"),
        ("kick_members", "Kick Members"),
        ("ban_members", "Ban Members"),
        ("send_messages", "Send Messages"),
        ("view_channel", "View Channels"),
        ("connect", "Connect to Voice"),
        ("speak", "Speak in Voice")
    ]
    
    for perm_attr, perm_name in important_perms:
        if getattr(permissions, perm_attr, False):
            perm_list.append(perm_name)
    
    return perm_list

def validate_server_id(server_id: str) -> bool:
    """Validate that server_id is a valid Discord ID"""
    try:
        # Discord IDs are 64-bit integers
        id_int = int(server_id)
        return 17 <= len(server_id) <= 20  # Discord IDs are typically 17-20 digits
    except ValueError:
        return False

def validate_channel_id(channel_id: str) -> bool:
    """Validate that channel_id is a valid Discord ID"""
    return validate_server_id(channel_id)  # Same validation

def validate_user_id(user_id: str) -> bool:
    """Validate that user_id is a valid Discord ID"""
    return validate_server_id(user_id)  # Same validation

def validate_role_id(role_id: str) -> bool:
    """Validate that role_id is a valid Discord ID"""
    return validate_server_id(role_id)  # Same validation

def truncate_text(text: str, max_length: int = 2000) -> str:
    """Truncate text to fit Discord message limits"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def format_member_activity(member: discord.Member) -> str:
    """Format member activity status"""
    status_emojis = {
        discord.Status.online: "🟢",
        discord.Status.idle: "🟡",
        discord.Status.dnd: "🔴",
        discord.Status.offline: "⚫"
    }
    
    emoji = status_emojis.get(member.status, "⚫")
    return f"{emoji} {member.status.name.title()}"

def calculate_setup_complexity(description: str) -> str:
    """Calculate setup complexity based on description"""
    complexity_indicators = {
        "simple": ["basic", "simple", "minimal", "small"],
        "medium": ["moderate", "standard", "normal", "team"],
        "complex": ["advanced", "complex", "enterprise", "large", "comprehensive"]
    }
    
    description_lower = description.lower()
    
    for level, indicators in complexity_indicators.items():
        if any(indicator in description_lower for indicator in indicators):
            return level
    
    # Default to medium complexity
    return "medium"

def extract_mentioned_features(description: str) -> List[str]:
    """Extract mentioned features from description"""
    feature_keywords = {
        "voice": ["voice", "talk", "call", "speaking"],
        "stage": ["stage", "presentation", "lecture", "announce"],
        "forum": ["forum", "discussion", "topic", "threads"],
        "moderation": ["moderation", "mod", "rules", "ban", "kick"],
        "roles": ["roles", "permissions", "hierarchy", "staff"],
        "channels": ["channels", "rooms", "areas", "sections"],
        "automation": ["auto", "bot", "automatic", "trigger"],
        "events": ["events", "schedule", "calendar", "meetings"],
        "categories": ["categories", "organization", "structure"]
    }
    
    description_lower = description.lower()
    found_features = []
    
    for feature, keywords in feature_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            found_features.append(feature)
    
    return found_features

class PermissionValidator:
    """Validate and check Discord permissions"""
    
    @staticmethod
    def has_required_permissions(member: discord.Member, required_perms: List[str]) -> tuple[bool, List[str]]:
        """Check if member has required permissions"""
        missing_perms = []
        
        for perm in required_perms:
            if not getattr(member.guild_permissions, perm.lower(), False):
                missing_perms.append(perm)
        
        return len(missing_perms) == 0, missing_perms
    
    @staticmethod
    def get_dangerous_permissions() -> List[str]:
        """Get list of dangerous permissions that should be carefully managed"""
        return [
            "administrator",
            "manage_guild",
            "manage_roles",
            "ban_members",
            "kick_members",
            "manage_channels",
            "manage_webhooks"
        ]
    
    @staticmethod
    def validate_permission_hierarchy(guild: discord.Guild, bot_member: discord.Member, target_role: discord.Role) -> bool:
        """Validate that bot can manage the target role"""
        return bot_member.top_role.position > target_role.position

class ErrorFormatter:
    """Format errors for user-friendly display"""
    
    @staticmethod
    def format_discord_error(error: Exception) -> str:
        """Format Discord errors for display"""
        if isinstance(error, discord.Forbidden):
            return "❌ Permission denied. The bot lacks necessary permissions for this action."
        elif isinstance(error, discord.NotFound):
            return "❌ Resource not found. The specified server, channel, or user doesn't exist."
        elif isinstance(error, discord.HTTPException):
            return f"❌ Discord API error: {error.text}"
        elif isinstance(error, ValueError):
            return f"❌ Invalid input: {str(error)}"
        else:
            return f"❌ Unexpected error: {str(error)}"
    
    @staticmethod
    def format_validation_error(field: str, value: str, expected: str) -> str:
        """Format validation errors"""
        return f"❌ Invalid {field}: '{value}'. Expected {expected}."

def get_channel_mention(channel_id: int) -> str:
    """Get Discord channel mention format"""
    return f"<#{channel_id}>"

def get_user_mention(user_id: int) -> str:
    """Get Discord user mention format"""
    return f"<@{user_id}>"

def get_role_mention(role_id: int) -> str:
    """Get Discord role mention format"""
    return f"<@&{role_id}>"

def format_timestamp(timestamp: str, format_type: str = "f") -> str:
    """Format timestamp for Discord"""
    return f"<t:{timestamp}:{format_type}>"

# Constants for easy reference
DISCORD_LIMITS = {
    "message_length": 2000,
    "embed_title": 256,
    "embed_description": 4096,
    "embed_field_name": 256,
    "embed_field_value": 1024,
    "embed_footer": 2048,
    "embed_author": 256,
    "channel_name": 100,
    "role_name": 100,
    "guild_name": 100,
    "emoji_name": 32,
    "webhook_name": 80
}

DEFAULT_COLORS = {
    "success": 0x00ff00,
    "error": 0xff0000,
    "warning": 0xffff00,
    "info": 0x0099ff,
    "default": 0x99aab5
}
