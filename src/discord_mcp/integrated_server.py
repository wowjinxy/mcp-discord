# src/discord_mcp/server.py
"""
Complete Discord MCP Server with AI-driven setup capabilities
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Union
from functools import wraps
import discord
from discord.ext import commands
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Import our modular components
from .core_tool_handlers import CoreToolHandlers
from .advanced_tool_handlers import AdvancedToolHandlers
from .server_setup_templates import setup_server_from_description, execute_setup_plan
from .advanced_discord_features import ServerAnalytics, ServerBackupManager, handle_advanced_tools
from .utils import validate_server_id, ErrorFormatter

def _configure_windows_stdout_encoding():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

_configure_windows_stdout_encoding()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")

# Discord bot setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("discordToken")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN or discordToken environment variable is required")

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
intents.voice_states = True
intents.presences = True
intents.auto_moderation_configuration = True
intents.auto_moderation_execution = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize MCP server
app = Server("discord-server")

# Store Discord client reference
discord_client = None

@bot.event
async def on_ready():
    global discord_client
    discord_client = bot
    logger.info(f"Logged in as {bot.user.name} - Ready for AI-driven server management!")

# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not discord_client:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)
    return wrapper

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available Discord tools for comprehensive server management."""
    return [
        # AI-DRIVEN SERVER SETUP
        Tool(
            name="setup_complete_server",
            description="🤖 Set up an entire Discord server from a natural language description using AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID to configure"
                    },
                    "server_description": {
                        "type": "string",
                        "description": "Natural language description of the desired server setup (e.g., 'Create a competitive gaming server for Valorant with team coordination areas')"
                    },
                    "server_name": {
                        "type": "string",
                        "description": "Optional new name for the server"
                    },
                    "server_type": {
                        "type": "string",
                        "enum": ["gaming", "community", "education", "business", "creative", "general"],
                        "description": "Type of server for template-based setup"
                    }
                },
                "required": ["server_id", "server_description"]
            }
        ),

        # ADVANCED SERVER MANAGEMENT
        Tool(
            name="edit_server_settings",
            description="Edit comprehensive server settings including verification, notifications, and branding",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Discord server ID"},
                    "name": {"type": "string", "description": "Server name"},
                    "description": {"type": "string", "description": "Server description"},
                    "icon_url": {"type": "string", "description": "URL to server icon image"},
                    "banner_url": {"type": "string", "description": "URL to server banner image"},
                    "verification_level": {
                        "type": "string",
                        "enum": ["none", "low", "medium", "high", "highest"],
                        "description": "Verification level for new members"
                    },
                    "default_notifications": {
                        "type": "string",
                        "enum": ["all_messages", "only_mentions"],
                        "description": "Default notification setting"
                    },
                    "explicit_content_filter": {
                        "type": "string",
                        "enum": ["disabled", "members_without_roles", "all_members"],
                        "description": "Explicit content filter level"
                    },
                    "afk_timeout": {"type": "number", "description": "AFK timeout in seconds"}
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="create_server_template",
            description="Create a reusable server template from current server configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID to create template from"},
                    "name": {"type": "string", "description": "Template name"},
                    "description": {"type": "string", "description": "Template description"}
                },
                "required": ["server_id", "name"]
            }
        ),

        # ADVANCED CHANNEL MANAGEMENT
        Tool(
            name="create_channel_category",
            description="Create a channel category for organization",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Category name"},
                    "position": {"type": "number", "description": "Category position"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="create_voice_channel",
            description="Create a voice channel with custom settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Channel name"},
                    "category_id": {"type": "string", "description": "Optional category ID"},
                    "user_limit": {"type": "number", "description": "User limit (0 for unlimited)"},
                    "bitrate": {"type": "number", "description": "Audio bitrate"},
                    "position": {"type": "number", "description": "Channel position"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="create_stage_channel",
            description="Create a stage channel for presentations and lectures",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Stage channel name"},
                    "category_id": {"type": "string", "description": "Optional category ID"},
                    "topic": {"type": "string", "description": "Stage topic"},
                    "position": {"type": "number", "description": "Channel position"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="create_forum_channel",
            description="Create a forum channel for organized discussions",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Forum name"},
                    "category_id": {"type": "string", "description": "Optional category ID"},
                    "topic": {"type": "string", "description": "Forum topic"},
                    "slowmode_delay": {"type": "number", "description": "Slowmode delay in seconds"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="create_announcement_channel",
            description="Create an announcement channel for important updates",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Channel name"},
                    "category_id": {"type": "string", "description": "Optional category ID"},
                    "topic": {"type": "string", "description": "Channel topic"},
                    "position": {"type": "number", "description": "Channel position"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="edit_channel",
            description="Edit existing channel properties and settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "name": {"type": "string", "description": "New channel name"},
                    "topic": {"type": "string", "description": "New channel topic"},
                    "position": {"type": "number", "description": "New channel position"},
                    "nsfw": {"type": "boolean", "description": "Whether channel is NSFW"},
                    "slowmode_delay": {"type": "number", "description": "Slowmode delay in seconds"},
                    "user_limit": {"type": "number", "description": "User limit for voice channels"},
                    "bitrate": {"type": "number", "description": "Bitrate for voice channels"}
                },
                "required": ["channel_id"]
            }
        ),

        Tool(
            name="set_channel_permissions",
            description="Set granular channel permissions for roles or users",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "target_id": {"type": "string", "description": "Role or user ID"},
                    "target_type": {"type": "string", "enum": ["role", "member"], "description": "Target type"},
                    "allow_permissions": {"type": "array", "items": {"type": "string"}, "description": "Permissions to allow"},
                    "deny_permissions": {"type": "array", "items": {"type": "string"}, "description": "Permissions to deny"},
                    "reason": {"type": "string", "description": "Reason for permission change"}
                },
                "required": ["channel_id", "target_id", "target_type"]
            }
        ),

        # COMPREHENSIVE ROLE MANAGEMENT
        Tool(
            name="create_role",
            description="Create a new role with detailed permissions and appearance",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Role name"},
                    "color": {"type": "string", "description": "Role color (hex code like #ff0000)"},
                    "permissions": {"type": "array", "items": {"type": "string"}, "description": "List of permissions"},
                    "hoist": {"type": "boolean", "description": "Whether role is displayed separately"},
                    "mentionable": {"type": "boolean", "description": "Whether role is mentionable"},
                    "position": {"type": "number", "description": "Role position in hierarchy"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="edit_role",
            description="Edit an existing role's properties and permissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "role_id": {"type": "string", "description": "Role ID"},
                    "name": {"type": "string", "description": "New role name"},
                    "color": {"type": "string", "description": "New role color (hex)"},
                    "permissions": {"type": "array", "items": {"type": "string"}, "description": "New permissions"},
                    "hoist": {"type": "boolean", "description": "Whether role is displayed separately"},
                    "mentionable": {"type": "boolean", "description": "Whether role is mentionable"},
                    "position": {"type": "number", "description": "New role position"},
                    "reason": {"type": "string", "description": "Reason for edit"}
                },
                "required": ["server_id", "role_id"]
            }
        ),

        Tool(
            name="delete_role",
            description="Delete a role from the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "role_id": {"type": "string", "description": "Role ID to delete"},
                    "reason": {"type": "string", "description": "Reason for deletion"}
                },
                "required": ["server_id", "role_id"]
            }
        ),

        Tool(
            name="create_role_hierarchy",
            description="Create multiple roles with proper hierarchy in one operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "roles": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "color": {"type": "string"},
                                "permissions": {"type": "array", "items": {"type": "string"}},
                                "hoist": {"type": "boolean"},
                                "mentionable": {"type": "boolean"}
                            },
                            "required": ["name"]
                        },
                        "description": "List of roles to create (in hierarchy order)"
                    }
                },
                "required": ["server_id", "roles"]
            }
        ),

        # CONTENT & CUSTOMIZATION
        Tool(
            name="create_emoji",
            description="Create a custom emoji for the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Emoji name"},
                    "image_url": {"type": "string", "description": "URL to emoji image"},
                    "roles": {"type": "array", "items": {"type": "string"}, "description": "Roles that can use emoji"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["server_id", "name", "image_url"]
            }
        ),

        Tool(
            name="create_webhook",
            description="Create a webhook for external integrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "name": {"type": "string", "description": "Webhook name"},
                    "avatar_url": {"type": "string", "description": "Webhook avatar URL"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["channel_id", "name"]
            }
        ),

        Tool(
            name="send_webhook_message",
            description="Send a message via webhook",
            inputSchema={
                "type": "object",
                "properties": {
                    "webhook_url": {"type": "string", "description": "Webhook URL"},
                    "content": {"type": "string", "description": "Message content"},
                    "username": {"type": "string", "description": "Override username"},
                    "avatar_url": {"type": "string", "description": "Override avatar URL"},
                    "embeds": {"type": "array", "description": "Message embeds"},
                    "thread_name": {"type": "string", "description": "Thread name for forum posts"}
                },
                "required": ["webhook_url"]
            }
        ),

        # MODERATION TOOLS
        Tool(
            name="ban_member",
            description="Ban a member from the server with options",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "user_id": {"type": "string", "description": "User ID to ban"},
                    "reason": {"type": "string", "description": "Reason for ban"},
                    "delete_message_days": {"type": "number", "description": "Days of messages to delete (0-7)"},
                    "delete_message_seconds": {"type": "number", "description": "Seconds of messages to delete"}
                },
                "required": ["server_id", "user_id"]
            }
        ),

        Tool(
            name="kick_member",
            description="Kick a member from the server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "user_id": {"type": "string", "description": "User ID to kick"},
                    "reason": {"type": "string", "description": "Reason for kick"}
                },
                "required": ["server_id", "user_id"]
            }
        ),

        Tool(
            name="timeout_member",
            description="Temporarily timeout a member",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "user_id": {"type": "string", "description": "User ID to timeout"},
                    "duration_minutes": {"type": "number", "description": "Timeout duration in minutes"},
                    "reason": {"type": "string", "description": "Reason for timeout"}
                },
                "required": ["server_id", "user_id", "duration_minutes"]
            }
        ),

        Tool(
            name="bulk_delete_messages",
            description="Bulk delete messages in a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "limit": {"type": "number", "description": "Number of messages to delete (max 100)"},
                    "reason": {"type": "string", "description": "Reason for deletion"}
                },
                "required": ["channel_id", "limit"]
            }
        ),

        # COMMUNITY FEATURES
        Tool(
            name="create_scheduled_event",
            description="Create a scheduled server event",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Event name"},
                    "description": {"type": "string", "description": "Event description"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "location": {"type": "string", "description": "Event location"},
                    "event_type": {
                        "type": "string",
                        "enum": ["stage_instance", "voice", "external"],
                        "description": "Type of event"
                    },
                    "channel_id": {"type": "string", "description": "Channel ID for voice/stage events"},
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "guild_only"],
                        "description": "Event privacy level"
                    }
                },
                "required": ["server_id", "name", "start_time", "event_type"]
            }
        ),

        Tool(
            name="create_invite",
            description="Create a custom invite link",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "max_age": {"type": "number", "description": "Max age in seconds (0 = never expires)"},
                    "max_uses": {"type": "number", "description": "Max uses (0 = unlimited)"},
                    "temporary": {"type": "boolean", "description": "Grant temporary membership"},
                    "unique": {"type": "boolean", "description": "Create unique invite"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["channel_id"]
            }
        ),

        Tool(
            name="create_thread",
            description="Create a discussion thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Channel ID"},
                    "name": {"type": "string", "description": "Thread name"},
                    "auto_archive_duration": {
                        "type": "number",
                        "enum": [60, 1440, 4320, 10080],
                        "description": "Auto archive duration in minutes"
                    },
                    "thread_type": {
                        "type": "string",
                        "enum": ["public_thread", "private_thread", "announcement_thread"],
                        "description": "Type of thread"
                    },
                    "invitable": {"type": "boolean", "description": "Whether private thread is invitable"},
                    "slowmode_delay": {"type": "number", "description": "Slowmode delay in seconds"},
                    "message_id": {"type": "string", "description": "Message ID to create thread from"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["channel_id", "name"]
            }
        ),

        # AUTOMODERATION
        Tool(
            name="create_automod_rule",
            description="Create an automoderation rule for content filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Rule name"},
                    "trigger_type": {
                        "type": "string",
                        "enum": ["keyword", "spam", "keyword_preset", "mention_spam"],
                        "description": "Type of trigger"
                    },
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords to filter"},
                    "keyword_presets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preset keyword lists"
                    },
                    "mention_total_limit": {"type": "number", "description": "Max mentions per message"},
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["block_message", "send_alert_message", "timeout"]},
                                "duration_seconds": {"type": "number"},
                                "channel_id": {"type": "string"}
                            }
                        },
                        "description": "Actions to take when rule triggers"
                    },
                    "exempt_roles": {"type": "array", "items": {"type": "string"}, "description": "Exempt role IDs"},
                    "exempt_channels": {"type": "array", "items": {"type": "string"}, "description": "Exempt channel IDs"},
                    "enabled": {"type": "boolean", "description": "Whether rule is enabled"}
                },
                "required": ["server_id", "name", "trigger_type", "actions"]
            }
        ),

        # ANALYTICS & MONITORING  
        Tool(
            name="get_server_analytics",
            description="📊 Get comprehensive server analytics and insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "time_range": {"type": "string", "enum": ["day", "week", "month"], "description": "Analytics time range"},
                    "include_members": {"type": "boolean", "description": "Include member analytics"},
                    "include_channels": {"type": "boolean", "description": "Include channel analytics"},
                    "include_roles": {"type": "boolean", "description": "Include role analytics"}
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="monitor_server_health",
            description="🏥 Monitor server health metrics and get recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "check_permissions": {"type": "boolean", "description": "Check permission issues"},
                    "check_channels": {"type": "boolean", "description": "Check channel health"},
                    "check_roles": {"type": "boolean", "description": "Check role configuration"},
                    "check_moderation": {"type": "boolean", "description": "Check moderation setup"}
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="backup_server",
            description="💾 Create a complete backup of server configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID to backup"},
                    "include_messages": {"type": "boolean", "description": "Include recent messages"},
                    "backup_name": {"type": "string", "description": "Custom backup name"},
                    "compress": {"type": "boolean", "description": "Compress backup data"}
                },
                "required": ["server_id"]
            }
        ),

        # EXISTING CORE TOOLS
        Tool(
            name="get_server_info",
            description="Get detailed information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="get_channels",
            description="Get a organized list of all channels in a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="list_members",
            description="Get a list of members in a server with roles and activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to add role to"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to add"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to remove"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),

        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Channel name"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deletion"
                    }
                },
                "required": ["channel_id"]
            }
        ),

        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),

        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)"
                        },
                        "description": "List of emojis to add as reactions"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }
        ),

        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),

        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    }
                },
                "required": ["channel_id", "content"]
            }
        ),

        Tool(
            name="read_messages",
            description="Read recent messages from a channel with reactions",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel_id"]
            }
        ),

        Tool(
            name="get_user_info",
            description="Get detailed information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),

        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),

        Tool(
            name="list_servers",
            description="Get a list of all Discord servers the bot has access to with detailed information",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle Discord tool calls with comprehensive error handling and routing."""
    
    try:
        # Validate server ID for server-specific operations
        if "server_id" in arguments and not validate_server_id(arguments["server_id"]):
            return [TextContent(
                type="text",
                text="❌ Invalid server ID format. Please provide a valid Discord server ID."
            )]

        # Route to AI-driven server setup - USE YOUR SOPHISTICATED IMPLEMENTATION
        if name == "setup_complete_server":
            logger.info(f"🤖 Starting AI-driven setup for server {arguments['server_id']}")
            
            # Use your sophisticated AIServerManager instead of basic implementation
            from .integration_complete import AIServerManager
            
            try:
                # This uses your advanced setup with pre-flight checks, backups, health scoring, etc.
                results = await AIServerManager.setup_complete_server(discord_client, arguments)
                
                # Format the comprehensive results
                success_count = len([r for r in results if r.startswith('✅')])
                error_count = len([r for r in results if r.startswith('❌')])
                warning_count = len([r for r in results if r.startswith('⚠️')])
                
                # Create a beautiful summary
                formatted_results = f"""
🚀 **AI-Powered Discord Server Setup Complete!**

**Results Summary:**
✅ Successful Operations: {success_count}
❌ Failed Operations: {error_count}  
⚠️ Warnings: {warning_count}

**Detailed Report:**
{chr(10).join(results)}

---
🎉 **Your server is ready! Check your Discord server for the new structure.**
                """.strip()
                
                return [TextContent(type="text", text=formatted_results)]
                
            except Exception as e:
                error_msg = ErrorFormatter.format_discord_error(e)
                logger.error(f"AI setup failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"❌ **AI Setup Failed**\n\nError: {error_msg}\n\nPlease check the logs and try again."
                )]

        # Route to advanced feature handlers
        advanced_tools = [
            "get_server_analytics", "monitor_server_health", "backup_server",
            "security_audit", "audit_log_analysis", "member_activity_report"
        ]
        
        if name in advanced_tools:
            results = await handle_advanced_tools(name, arguments, discord_client)
            return [TextContent(type="text", text=result["text"]) for result in results]

        # Route to advanced tool handlers
        advanced_tool_names = [
            "edit_server_settings", "create_server_template", "create_channel_category",
            "create_voice_channel", "create_stage_channel", "create_forum_channel",
            "create_announcement_channel", "edit_channel", "set_channel_permissions",
            "create_role", "edit_role", "delete_role", "create_role_hierarchy",
            "create_emoji", "create_webhook", "send_webhook_message",
            "ban_member", "kick_member", "timeout_member", "bulk_delete_messages",
            "create_scheduled_event", "create_invite", "create_thread", "create_automod_rule"
        ]
        
        if name in advanced_tool_names:
            handler_method = f"handle_{name}"
            if hasattr(AdvancedToolHandlers, handler_method):
                return await getattr(AdvancedToolHandlers, handler_method)(discord_client, arguments)

        # Route to core tool handlers
        core_tool_names = [
            "get_server_info", "list_servers", "get_channels", "list_members",
            "get_user_info", "send_message", "read_messages", "add_reaction",
            "add_multiple_reactions", "remove_reaction", "moderate_message",
            "create_text_channel", "delete_channel", "add_role", "remove_role"
        ]
        
        if name in core_tool_names:
            handler_method = f"handle_{name}"
            if hasattr(CoreToolHandlers, handler_method):
                return await getattr(CoreToolHandlers, handler_method)(discord_client, arguments)

        # If we get here, the tool wasn't found
        return [TextContent(
            type="text",
            text=f"❌ Unknown tool: {name}. Please check the available tools list."
        )]
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return [TextContent(
            type="text",
            text=f"❌ Tool execution failed: {str(e)}"
        )]
        
async def main():
    """Main entry point - start Discord bot and MCP server"""
    try:
        # Start Discord bot in the background
        logger.info("Starting Discord bot...")
        asyncio.create_task(bot.start(DISCORD_TOKEN))
        
        # Give the bot a moment to initialize
        await asyncio.sleep(2)
        
        # Run MCP server
        logger.info("Starting MCP server...")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Shutting down Discord MCP server...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
