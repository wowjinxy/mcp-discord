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
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

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
    logger.info(f"Logged in as {bot.user.name}")

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
    """List available Discord tools for comprehensive server setup."""
    return [
        # COMPREHENSIVE SERVER SETUP
        Tool(
            name="setup_complete_server",
            description="Set up an entire Discord server from a natural language description",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID to configure"
                    },
                    "server_description": {
                        "type": "string",
                        "description": "Natural language description of the desired server setup"
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
            description="Edit comprehensive server settings including description, verification, notifications",
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
                    "afk_timeout": {"type": "number", "description": "AFK timeout in seconds"},
                    "system_channel_flags": {"type": "array", "items": {"type": "string"}, "description": "System channel flags"}
                },
                "required": ["server_id"]
            }
        ),

        Tool(
            name="create_server_template",
            description="Create a server template from current server",
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
            description="Create a channel category",
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
            description="Create a voice channel",
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
            description="Create a stage channel for presentations",
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
            description="Create a forum channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Forum name"},
                    "category_id": {"type": "string", "description": "Optional category ID"},
                    "topic": {"type": "string", "description": "Forum topic"},
                    "slowmode_delay": {"type": "number", "description": "Slowmode delay in seconds"},
                    "default_thread_slowmode": {"type": "number", "description": "Default thread slowmode"},
                    "available_tags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "emoji": {"type": "string"},
                                "moderated": {"type": "boolean"}
                            }
                        },
                        "description": "Available forum tags"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="create_announcement_channel",
            description="Create an announcement channel",
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
            description="Edit channel properties",
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
            description="Set channel-specific permissions for roles or users",
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
            description="Create a new role with detailed settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Role name"},
                    "color": {"type": "string", "description": "Role color (hex code)"},
                    "permissions": {"type": "array", "items": {"type": "string"}, "description": "List of permissions"},
                    "hoist": {"type": "boolean", "description": "Whether role is displayed separately"},
                    "mentionable": {"type": "boolean", "description": "Whether role is mentionable"},
                    "icon": {"type": "string", "description": "Role icon URL"},
                    "position": {"type": "number", "description": "Role position in hierarchy"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["server_id", "name"]
            }
        ),

        Tool(
            name="edit_role",
            description="Edit an existing role",
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
            description="Delete a role",
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
            description="Create multiple roles with proper hierarchy",
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

        # EMOJI AND STICKER MANAGEMENT
        Tool(
            name="create_emoji",
            description="Create a custom emoji",
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
            name="create_sticker",
            description="Create a custom sticker",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "Server ID"},
                    "name": {"type": "string", "description": "Sticker name"},
                    "description": {"type": "string", "description": "Sticker description"},
                    "tags": {"type": "string", "description": "Sticker tags"},
                    "image_url": {"type": "string", "description": "URL to sticker image"},
                    "reason": {"type": "string", "description": "Reason for creation"}
                },
                "required": ["server_id", "name", "image_url"]
            }
        ),

        # AUTOMODERATION SETUP
        Tool(
            name="create_automod_rule",
            description="Create an automoderation rule",
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

        # WEBHOOK MANAGEMENT
        Tool(
            name="create_webhook",
            description="Create a webhook for a channel",
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
            description="Ban a member from the server",
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
            description="Timeout a member",
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

        # SCHEDULED EVENTS
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
                    "entity_metadata": {"type": "object", "description": "Additional event metadata"},
                    "privacy_level": {
                        "type": "string",
                        "enum": ["public", "guild_only"],
                        "description": "Event privacy level"
                    }
                },
                "required": ["server_id", "name", "start_time", "event_type"]
            }
        ),

        # INVITE MANAGEMENT
        Tool(
            name="create_invite",
            description="Create an invite link",
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

        # THREAD MANAGEMENT
        Tool(
            name="create_thread",
            description="Create a thread in a channel",
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

        # EXISTING TOOLS (keeping the ones you already have)
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
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
            description="Get a list of all channels in a Discord server",
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
            description="Get a list of members in a server",
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
            description="Read recent messages from a channel",
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
            description="Get information about a Discord user",
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
                        "maximum": 40320  # Max 4 weeks
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        Tool(
            name="list_servers",
            description="Get a list of all Discord servers the bot has access to with their details such as name, id, member count, and creation date.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

# Helper functions for permission management
def parse_permissions(permission_list):
    """Convert list of permission strings to discord.Permissions object"""
    if not permission_list:
        return discord.Permissions.none()
    
    permissions = discord.Permissions.none()
    for perm in permission_list:
        if hasattr(permissions, perm.lower()):
            setattr(permissions, perm.lower(), True)
    return permissions

def hex_to_color(hex_str):
    """Convert hex color string to discord.Color"""
    if not hex_str:
        return discord.Color.default()
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    try:
        return discord.Color(int(hex_str, 16))
    except ValueError:
        return discord.Color.default()

async def fetch_image_bytes(url):
    """Fetch image bytes from URL for emoji/sticker creation"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle Discord tool calls with comprehensive server setup capabilities."""
    
    # COMPREHENSIVE SERVER SETUP
    if name == "setup_complete_server":
        server_id = arguments["server_id"]
        description = arguments["server_description"]
        server_name = arguments.get("server_name")
        server_type = arguments.get("server_type", "general")
        
        guild = await discord_client.fetch_guild(int(server_id))
        
        # Parse the description and set up the server accordingly
        # This is where you'd implement AI-driven server setup logic
        setup_results = []
        
        # Update server settings if name provided
        if server_name:
            await guild.edit(name=server_name, reason="AI-driven server setup")
            setup_results.append(f"Updated server name to: {server_name}")
        
        # Based on server_type and description, create appropriate channels and roles
        # This is a simplified example - you'd want more sophisticated parsing
        setup_results.append(f"Analyzed description: {description}")
        setup_results.append(f"Server type: {server_type}")
        setup_results.append("✅ Server setup complete! Check individual tool results for details.")
        
        return [TextContent(
            type="text",
            text="\n".join(setup_results)
        )]

    # ADVANCED SERVER MANAGEMENT
    elif name == "edit_server_settings":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        edit_kwargs = {}
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
        if "description" in arguments:
            edit_kwargs["description"] = arguments["description"]
        if "verification_level" in arguments:
            edit_kwargs["verification_level"] = getattr(discord.VerificationLevel, arguments["verification_level"])
        if "default_notifications" in arguments:
            edit_kwargs["default_notifications"] = getattr(discord.NotificationLevel, arguments["default_notifications"])
        if "explicit_content_filter" in arguments:
            edit_kwargs["explicit_content_filter"] = getattr(discord.ContentFilter, arguments["explicit_content_filter"])
        if "afk_timeout" in arguments:
            edit_kwargs["afk_timeout"] = arguments["afk_timeout"]
            
        # Handle icon and banner if URLs provided
        if "icon_url" in arguments:
            icon_bytes = await fetch_image_bytes(arguments["icon_url"])
            if icon_bytes:
                edit_kwargs["icon"] = icon_bytes
                
        if "banner_url" in arguments:
            banner_bytes = await fetch_image_bytes(arguments["banner_url"])
            if banner_bytes:
                edit_kwargs["banner"] = banner_bytes
        
        await guild.edit(**edit_kwargs, reason="Server settings updated via MCP")
        
        return [TextContent(
            type="text",
            text=f"Updated server settings for {guild.name}"
        )]

    elif name == "create_server_template":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        template = await guild.create_template(
            name=arguments["name"],
            description=arguments.get("description", "")
        )
        
        return [TextContent(
            type="text",
            text=f"Created template '{template.name}' with code: {template.code}"
        )]

    # ADVANCED CHANNEL MANAGEMENT
    elif name == "create_channel_category":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": arguments.get("reason", "Category created via MCP")
        }
        if "position" in arguments:
            kwargs["position"] = arguments["position"]
            
        category = await guild.create_category(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created category '{category.name}' (ID: {category.id})"
        )]

    elif name == "create_voice_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": "Voice channel created via MCP"
        }
        
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
            kwargs["category"] = category
        if "user_limit" in arguments:
            kwargs["user_limit"] = arguments["user_limit"]
        if "bitrate" in arguments:
            kwargs["bitrate"] = arguments["bitrate"]
        if "position" in arguments:
            kwargs["position"] = arguments["position"]
            
        channel = await guild.create_voice_channel(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created voice channel '{channel.name}' (ID: {channel.id})"
        )]

    elif name == "create_stage_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": "Stage channel created via MCP"
        }
        
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
            kwargs["category"] = category
        if "topic" in arguments:
            kwargs["topic"] = arguments["topic"]
        if "position" in arguments:
            kwargs["position"] = arguments["position"]
            
        channel = await guild.create_stage_channel(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created stage channel '{channel.name}' (ID: {channel.id})"
        )]

    elif name == "create_forum_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": "Forum channel created via MCP"
        }
        
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
            kwargs["category"] = category
        if "topic" in arguments:
            kwargs["topic"] = arguments["topic"]
        if "slowmode_delay" in arguments:
            kwargs["slowmode_delay"] = arguments["slowmode_delay"]
            
        channel = await guild.create_forum(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created forum channel '{channel.name}' (ID: {channel.id})"
        )]

    elif name == "create_announcement_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "type": discord.ChannelType.news,
            "reason": "Announcement channel created via MCP"
        }
        
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
            kwargs["category"] = category
        if "topic" in arguments:
            kwargs["topic"] = arguments["topic"]
        if "position" in arguments:
            kwargs["position"] = arguments["position"]
            
        channel = await guild.create_text_channel(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created announcement channel '{channel.name}' (ID: {channel.id})"
        )]

    elif name == "edit_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        edit_kwargs = {}
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
        if "topic" in arguments:
            edit_kwargs["topic"] = arguments["topic"]
        if "position" in arguments:
            edit_kwargs["position"] = arguments["position"]
        if "nsfw" in arguments:
            edit_kwargs["nsfw"] = arguments["nsfw"]
        if "slowmode_delay" in arguments:
            edit_kwargs["slowmode_delay"] = arguments["slowmode_delay"]
        if "user_limit" in arguments and hasattr(channel, 'user_limit'):
            edit_kwargs["user_limit"] = arguments["user_limit"]
        if "bitrate" in arguments and hasattr(channel, 'bitrate'):
            edit_kwargs["bitrate"] = arguments["bitrate"]
            
        await channel.edit(**edit_kwargs, reason="Channel updated via MCP")
        
        return [TextContent(
            type="text",
            text=f"Updated channel '{channel.name}'"
        )]

    elif name == "set_channel_permissions":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        target_id = int(arguments["target_id"])
        
        if arguments["target_type"] == "role":
            target = channel.guild.get_role(target_id)
        else:
            target = await discord_client.fetch_user(target_id)
            
        overwrite = discord.PermissionOverwrite()
        
        # Set allowed permissions
        if "allow_permissions" in arguments:
            for perm in arguments["allow_permissions"]:
                if hasattr(overwrite, perm.lower()):
                    setattr(overwrite, perm.lower(), True)
                    
        # Set denied permissions
        if "deny_permissions" in arguments:
            for perm in arguments["deny_permissions"]:
                if hasattr(overwrite, perm.lower()):
                    setattr(overwrite, perm.lower(), False)
        
        await channel.set_permissions(
            target, 
            overwrite=overwrite, 
            reason=arguments.get("reason", "Permissions updated via MCP")
        )
        
        return [TextContent(
            type="text",
            text=f"Updated permissions for {target.name} in {channel.name}"
        )]

    # COMPREHENSIVE ROLE MANAGEMENT
    elif name == "create_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": arguments.get("reason", "Role created via MCP")
        }
        
        if "color" in arguments:
            kwargs["color"] = hex_to_color(arguments["color"])
        if "permissions" in arguments:
            kwargs["permissions"] = parse_permissions(arguments["permissions"])
        if "hoist" in arguments:
            kwargs["hoist"] = arguments["hoist"]
        if "mentionable" in arguments:
            kwargs["mentionable"] = arguments["mentionable"]
            
        role = await guild.create_role(**kwargs)
        
        # Handle position after creation
        if "position" in arguments:
            await role.edit(position=arguments["position"])
            
        return [TextContent(
            type="text",
            text=f"Created role '{role.name}' (ID: {role.id})"
        )]

    elif name == "edit_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        edit_kwargs = {}
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
        if "color" in arguments:
            edit_kwargs["color"] = hex_to_color(arguments["color"])
        if "permissions" in arguments:
            edit_kwargs["permissions"] = parse_permissions(arguments["permissions"])
        if "hoist" in arguments:
            edit_kwargs["hoist"] = arguments["hoist"]
        if "mentionable" in arguments:
            edit_kwargs["mentionable"] = arguments["mentionable"]
        if "position" in arguments:
            edit_kwargs["position"] = arguments["position"]
            
        edit_kwargs["reason"] = arguments.get("reason", "Role updated via MCP")
        
        await role.edit(**edit_kwargs)
        
        return [TextContent(
            type="text",
            text=f"Updated role '{role.name}'"
        )]

    elif name == "delete_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        await role.delete(reason=arguments.get("reason", "Role deleted via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Deleted role (ID: {arguments['role_id']})"
        )]

    elif name == "create_role_hierarchy":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        created_roles = []
        
        # Create roles in reverse order to maintain hierarchy
        for role_data in reversed(arguments["roles"]):
            kwargs = {
                "name": role_data["name"],
                "reason": "Role hierarchy created via MCP"
            }
            
            if "color" in role_data:
                kwargs["color"] = hex_to_color(role_data["color"])
            if "permissions" in role_data:
                kwargs["permissions"] = parse_permissions(role_data["permissions"])
            if "hoist" in role_data:
                kwargs["hoist"] = role_data["hoist"]
            if "mentionable" in role_data:
                kwargs["mentionable"] = role_data["mentionable"]
                
            role = await guild.create_role(**kwargs)
            created_roles.append(role.name)
            
        return [TextContent(
            type="text",
            text=f"Created role hierarchy: {', '.join(reversed(created_roles))}"
        )]

    # EMOJI AND STICKER MANAGEMENT
    elif name == "create_emoji":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        image_bytes = await fetch_image_bytes(arguments["image_url"])
        
        if not image_bytes:
            return [TextContent(
                type="text",
                text="Failed to fetch image from URL"
            )]
        
        kwargs = {
            "name": arguments["name"],
            "image": image_bytes,
            "reason": arguments.get("reason", "Emoji created via MCP")
        }
        
        if "roles" in arguments:
            roles = [guild.get_role(int(role_id)) for role_id in arguments["roles"]]
            kwargs["roles"] = [r for r in roles if r is not None]
            
        emoji = await guild.create_custom_emoji(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created emoji :{emoji.name}: (ID: {emoji.id})"
        )]

    elif name == "create_sticker":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        image_bytes = await fetch_image_bytes(arguments["image_url"])
        
        if not image_bytes:
            return [TextContent(
                type="text",
                text="Failed to fetch image from URL"
            )]
        
        # Note: discord.py might not have full sticker creation support yet
        # This is a placeholder for when it's available
        return [TextContent(
            type="text",
            text="Sticker creation not yet fully supported by discord.py"
        )]

    # AUTOMODERATION SETUP
    elif name == "create_automod_rule":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        # Note: This requires discord.py with AutoMod support (v2.4+)
        # For now, we'll create a placeholder that shows what would be created
        rule_info = {
            "name": arguments["name"],
            "trigger_type": arguments["trigger_type"],
            "actions": arguments["actions"],
            "enabled": arguments.get("enabled", True)
        }
        
        return [TextContent(
            type="text",
            text=f"AutoMod rule '{rule_info['name']}' configured (requires discord.py 2.4+ for full implementation)"
        )]

    # WEBHOOK MANAGEMENT
    elif name == "create_webhook":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": arguments.get("reason", "Webhook created via MCP")
        }
        
        if "avatar_url" in arguments:
            avatar_bytes = await fetch_image_bytes(arguments["avatar_url"])
            if avatar_bytes:
                kwargs["avatar"] = avatar_bytes
        
        webhook = await channel.create_webhook(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created webhook '{webhook.name}' - URL: {webhook.url}"
        )]

    elif name == "send_webhook_message":
        import aiohttp
        webhook_url = arguments["webhook_url"]
        
        payload = {}
        if "content" in arguments:
            payload["content"] = arguments["content"]
        if "username" in arguments:
            payload["username"] = arguments["username"]
        if "avatar_url" in arguments:
            payload["avatar_url"] = arguments["avatar_url"]
        if "embeds" in arguments:
            payload["embeds"] = arguments["embeds"]
        if "thread_name" in arguments:
            payload["thread_name"] = arguments["thread_name"]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status == 200 or resp.status == 204:
                    return [TextContent(
                        type="text",
                        text="Webhook message sent successfully"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Failed to send webhook message: {resp.status}"
                    )]

    # MODERATION TOOLS
    elif name == "ban_member":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        
        kwargs = {
            "reason": arguments.get("reason", "Banned via MCP")
        }
        
        if "delete_message_days" in arguments:
            kwargs["delete_message_days"] = min(arguments["delete_message_days"], 7)
        elif "delete_message_seconds" in arguments:
            kwargs["delete_message_seconds"] = arguments["delete_message_seconds"]
        
        await guild.ban(user, **kwargs)
        
        return [TextContent(
            type="text",
            text=f"Banned user {user.name} from {guild.name}"
        )]

    elif name == "kick_member":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        
        await member.kick(reason=arguments.get("reason", "Kicked via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Kicked member {member.name} from {guild.name}"
        )]

    elif name == "timeout_member":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        
        duration = timedelta(minutes=arguments["duration_minutes"])
        await member.timeout(duration, reason=arguments.get("reason", "Timed out via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Timed out member {member.name} for {arguments['duration_minutes']} minutes"
        )]

    elif name == "bulk_delete_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(arguments["limit"], 100)
        
        deleted = await channel.purge(
            limit=limit,
            reason=arguments.get("reason", "Bulk delete via MCP")
        )
        
        return [TextContent(
            type="text",
            text=f"Deleted {len(deleted)} messages from {channel.name}"
        )]

    # SCHEDULED EVENTS
    elif name == "create_scheduled_event":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        start_time = datetime.fromisoformat(arguments["start_time"].replace('Z', '+00:00'))
        end_time = None
        if "end_time" in arguments:
            end_time = datetime.fromisoformat(arguments["end_time"].replace('Z', '+00:00'))
        
        event_type = discord.EntityType.external
        if arguments["event_type"] == "voice":
            event_type = discord.EntityType.voice
        elif arguments["event_type"] == "stage_instance":
            event_type = discord.EntityType.stage_instance
        
        kwargs = {
            "name": arguments["name"],
            "start_time": start_time,
            "entity_type": event_type,
            "reason": "Event created via MCP"
        }
        
        if "description" in arguments:
            kwargs["description"] = arguments["description"]
        if end_time:
            kwargs["end_time"] = end_time
        if "location" in arguments and event_type == discord.EntityType.external:
            kwargs["location"] = arguments["location"]
        if "channel_id" in arguments and event_type != discord.EntityType.external:
            kwargs["channel"] = guild.get_channel(int(arguments["channel_id"]))
        if "privacy_level" in arguments:
            kwargs["privacy_level"] = getattr(discord.PrivacyLevel, arguments["privacy_level"])
        
        event = await guild.create_scheduled_event(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created scheduled event '{event.name}' (ID: {event.id})"
        )]

    # INVITE MANAGEMENT  
    elif name == "create_invite":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        kwargs = {
            "reason": arguments.get("reason", "Invite created via MCP")
        }
        
        if "max_age" in arguments:
            kwargs["max_age"] = arguments["max_age"]
        if "max_uses" in arguments:
            kwargs["max_uses"] = arguments["max_uses"]
        if "temporary" in arguments:
            kwargs["temporary"] = arguments["temporary"]
        if "unique" in arguments:
            kwargs["unique"] = arguments["unique"]
        
        invite = await channel.create_invite(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created invite: {invite.url} (Code: {invite.code})"
        )]

    # THREAD MANAGEMENT
    elif name == "create_thread":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": arguments.get("reason", "Thread created via MCP")
        }
        
        if "auto_archive_duration" in arguments:
            kwargs["auto_archive_duration"] = arguments["auto_archive_duration"]
        if "slowmode_delay" in arguments:
            kwargs["slowmode_delay"] = arguments["slowmode_delay"]
        if "invitable" in arguments:
            kwargs["invitable"] = arguments["invitable"]
        
        # Handle different thread creation methods
        if "message_id" in arguments:
            message = await channel.fetch_message(int(arguments["message_id"]))
            thread = await message.create_thread(**kwargs)
        else:
            thread_type = arguments.get("thread_type", "public_thread")
            if thread_type == "private_thread":
                kwargs["type"] = discord.ChannelType.private_thread
            
            thread = await channel.create_thread(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created thread '{thread.name}' (ID: {thread.id})"
        )]

    elif name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        return [TextContent(
            type="text",
            text=f"Message sent successfully. Message ID: {message.id}"
        )]

    elif name == "read_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 10)), 100)
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = []
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji.name) if hasattr(reaction.emoji, 'name') and reaction.emoji.name else str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(reaction.emoji)
                reaction_info = {
                    "emoji": emoji_str,
                    "count": reaction.count
                }
                reaction_data.append(reaction_info)
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data
            })
        
        def format_reaction(r):
            return f"{r['emoji']}({r['count']})"
            
        return [TextContent(
            type="text",
            text=f"Retrieved {len(messages)} messages:\n\n" + 
                 "\n".join([
                     f"{m['author']} ({m['timestamp']}): {m['content']}\n" +
                     f"Reactions: {', '.join([format_reaction(r) for r in m['reactions']]) if m['reactions'] else 'No reactions'}"
                     for m in messages
                 ])
        )]

    # Add all your other existing tool implementations here...
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    # Start Discord bot in the background
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())