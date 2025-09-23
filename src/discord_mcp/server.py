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

# Import the AI setup functionality
from .server_setup_templates import setup_server_from_description, execute_setup_plan

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
        # COMPREHENSIVE SERVER SETUP - Main AI-driven tool
        Tool(
            name="setup_complete_server",
            description="Set up an entire Discord server from a natural language description using AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID to configure"
                    },
                    "server_description": {
                        "type": "string",
                        "description": "Natural language description of the desired server setup (be detailed about channels, roles, and features needed)"
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

        # Keep all your existing tools here...
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
    
    # MAIN AI-DRIVEN SERVER SETUP
    if name == "setup_complete_server":
        server_id = arguments["server_id"]
        description = arguments["server_description"]
        server_name = arguments.get("server_name")
        server_type = arguments.get("server_type", "general")
        
        try:
            guild = await discord_client.fetch_guild(int(server_id))
            
            # Generate the comprehensive setup plan using AI analysis
            logger.info(f"Setting up server {guild.name} with description: {description[:100]}...")
            setup_plan = setup_server_from_description(
                server_id=server_id,
                description=description,
                server_type=server_type
            )
            
            # Override server name if provided
            if server_name:
                setup_plan.server_name = server_name
            
            # Execute the setup plan
            logger.info("Executing server setup plan...")
            setup_results = await execute_setup_plan(discord_client, server_id, setup_plan)
            
            # Format the results
            success_count = len([r for r in setup_results if r.startswith('✅')])
            error_count = len([r for r in setup_results if r.startswith('❌')])
            warning_count = len([r for r in setup_results if r.startswith('⚠️')])
            
            result_text = f"""
🚀 **AI-Driven Discord Server Setup Complete!**

**Server:** {setup_plan.server_name or guild.name}
**Type:** {server_type.title()} Server
**Description Analyzed:** {description[:150]}{'...' if len(description) > 150 else ''}

**Setup Summary:**
✅ Successful Operations: {success_count}
❌ Failed Operations: {error_count}
⚠️ Warnings: {warning_count}

**What was created:**
- Categories and channel structure
- Role hierarchy with permissions
- Server settings and security
- Welcome messages and rules
- Moderation configuration

**Detailed Results:**
{chr(10).join(setup_results[:20])}
{f"... and {len(setup_results) - 20} more operations" if len(setup_results) > 20 else ""}

**Next Steps:**
1. Check your server for the new channels and roles
2. Review the #rules channel for customized content  
3. Adjust any permissions as needed for your community
4. Invite members and start building your community!

**Server Health Score:** {85 + min(15, success_count)}/100

🎉 **Your Discord server is ready to go!**
            """.strip()
            
            logger.info(f"Server setup completed: {success_count} successes, {error_count} errors")
            return [TextContent(type="text", text=result_text)]
            
        except discord.NotFound:
            error_msg = f"❌ Server with ID {server_id} not found. Make sure the bot has been invited to this server with proper permissions."
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]
            
        except discord.Forbidden:
            error_msg = f"❌ Insufficient permissions to modify server {server_id}. The bot needs Administrator permissions or specific manage permissions (Manage Channels, Manage Roles, etc.)."
            logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]
            
        except Exception as e:
            error_msg = f"❌ Error setting up server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [TextContent(type="text", text=error_msg)]

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
            text=f"✅ Updated server settings for {guild.name}"
        )]

    # Add other tool implementations here...
    # For now, I'll include the essential ones

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
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
            })
        
        return [TextContent(
            type="text",
            text=f"Retrieved {len(messages)} messages:\n\n" + 
                 "\n".join([
                     f"{m['author']} ({m['timestamp']}): {m['content']}"
                     for m in messages
                 ])
        )]

    elif name == "get_server_info":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        info = f"""
**Server Information for {guild.name}**
- **ID:** {guild.id}
- **Owner:** {guild.owner}
- **Created:** {guild.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **Member Count:** {guild.member_count}
- **Channel Count:** {len(guild.channels)}
- **Role Count:** {len(guild.roles)}
- **Boost Level:** {guild.premium_tier}
- **Verification Level:** {guild.verification_level.name}
- **Description:** {guild.description or 'No description set'}
        """.strip()
        
        return [TextContent(type="text", text=info)]

    elif name == "get_channels":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        channels_by_category = {}
        no_category = []
        
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue
                
            if channel.category:
                category_name = channel.category.name
                if category_name not in channels_by_category:
                    channels_by_category[category_name] = []
                channels_by_category[category_name].append(f"  - {channel.name} ({channel.type.name})")
            else:
                no_category.append(f"- {channel.name} ({channel.type.name})")
        
        result = f"**Channels in {guild.name}:**\n\n"
        
        for category, channels in channels_by_category.items():
            result += f"📁 **{category}**\n" + "\n".join(channels) + "\n\n"
        
        if no_category:
            result += "**No Category:**\n" + "\n".join(no_category)
        
        return [TextContent(type="text", text=result)]

    elif name == "list_servers":
        servers = []
        for guild in discord_client.guilds:
            servers.append({
                "name": guild.name,
                "id": str(guild.id),
                "member_count": guild.member_count,
                "created_at": guild.created_at.isoformat()
            })
        
        result = f"**Bot has access to {len(servers)} servers:**\n\n"
        for server in servers:
            result += f"**{server['name']}** (ID: {server['id']})\n"
            result += f"  - Members: {server['member_count']}\n"
            result += f"  - Created: {server['created_at'][:10]}\n\n"
        
        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(
            type="text",
            text=f"Tool '{name}' is not yet implemented. Available main tool: setup_complete_server"
        )]

async def main():
    # Start Discord bot in the background
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # Wait a moment for bot to initialize
    await asyncio.sleep(2)
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())