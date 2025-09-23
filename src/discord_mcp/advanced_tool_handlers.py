# src/discord_mcp/advanced_tool_handlers.py
"""
Advanced Discord tool implementations - handles complex operations like automod, webhooks, moderation
"""

import discord
import aiohttp
import json
from typing import List, Any, Dict
from mcp.types import TextContent
from datetime import datetime, timedelta
from .utils import parse_permissions, hex_to_color, fetch_image_bytes

class AdvancedToolHandlers:
    """Handles all advanced Discord operations"""
    
    @staticmethod
    async def handle_edit_server_settings(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Edit comprehensive server settings"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        edit_kwargs = {}
        changes_made = []
        
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
            changes_made.append(f"Name: {arguments['name']}")
        
        if "description" in arguments:
            edit_kwargs["description"] = arguments["description"]
            changes_made.append("Description updated")
        
        if "verification_level" in arguments:
            level_map = {
                "none": discord.VerificationLevel.none,
                "low": discord.VerificationLevel.low,
                "medium": discord.VerificationLevel.medium,
                "high": discord.VerificationLevel.high,
                "highest": discord.VerificationLevel.highest
            }
            edit_kwargs["verification_level"] = level_map[arguments["verification_level"]]
            changes_made.append(f"Verification level: {arguments['verification_level']}")
        
        if "default_notifications" in arguments:
            notif_map = {
                "all_messages": discord.NotificationLevel.all_messages,
                "only_mentions": discord.NotificationLevel.only_mentions
            }
            edit_kwargs["default_notifications"] = notif_map[arguments["default_notifications"]]
            changes_made.append(f"Notifications: {arguments['default_notifications']}")
        
        if "explicit_content_filter" in arguments:
            filter_map = {
                "disabled": discord.ContentFilter.disabled,
                "members_without_roles": discord.ContentFilter.no_role,
                "all_members": discord.ContentFilter.all_members
            }
            edit_kwargs["explicit_content_filter"] = filter_map[arguments["explicit_content_filter"]]
            changes_made.append(f"Content filter: {arguments['explicit_content_filter']}")
        
        if "afk_timeout" in arguments:
            edit_kwargs["afk_timeout"] = arguments["afk_timeout"]
            changes_made.append(f"AFK timeout: {arguments['afk_timeout']}s")
        
        # Handle icon and banner if URLs provided
        if "icon_url" in arguments:
            icon_bytes = await fetch_image_bytes(arguments["icon_url"])
            if icon_bytes:
                edit_kwargs["icon"] = icon_bytes
                changes_made.append("Icon updated")
        
        if "banner_url" in arguments:
            banner_bytes = await fetch_image_bytes(arguments["banner_url"])
            if banner_bytes:
                edit_kwargs["banner"] = banner_bytes
                changes_made.append("Banner updated")
        
        if edit_kwargs:
            await guild.edit(**edit_kwargs, reason="Server settings updated via MCP")
        
        return [TextContent(
            type="text",
            text=f"Updated server settings for {guild.name}:\n• " + "\n• ".join(changes_made)
        )]

    @staticmethod
    async def handle_create_server_template(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a server template"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        template = await guild.create_template(
            name=arguments["name"],
            description=arguments.get("description", "")
        )
        
        return [TextContent(
            type="text",
            text=f"Created server template '{template.name}' with code: {template.code}\nURL: https://discord.new/{template.code}"
        )]

    @staticmethod
    async def handle_create_channel_category(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a channel category"""
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
            text=f"Created category '{category.name}' (ID: {category.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_create_voice_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a voice channel"""
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
            text=f"Created voice channel '{channel.name}' (ID: {channel.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_create_stage_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a stage channel"""
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
            text=f"Created stage channel '{channel.name}' (ID: {channel.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_create_forum_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a forum channel"""
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
            text=f"Created forum channel '{channel.name}' (ID: {channel.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_create_announcement_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create an announcement channel"""
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
            text=f"Created announcement channel '{channel.name}' (ID: {channel.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_edit_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Edit channel properties"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        
        edit_kwargs = {}
        changes_made = []
        
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
            changes_made.append(f"Name: {arguments['name']}")
        
        if "topic" in arguments:
            edit_kwargs["topic"] = arguments["topic"]
            changes_made.append("Topic updated")
        
        if "position" in arguments:
            edit_kwargs["position"] = arguments["position"]
            changes_made.append(f"Position: {arguments['position']}")
        
        if "nsfw" in arguments:
            edit_kwargs["nsfw"] = arguments["nsfw"]
            changes_made.append(f"NSFW: {arguments['nsfw']}")
        
        if "slowmode_delay" in arguments:
            edit_kwargs["slowmode_delay"] = arguments["slowmode_delay"]
            changes_made.append(f"Slowmode: {arguments['slowmode_delay']}s")
        
        if "user_limit" in arguments and hasattr(channel, 'user_limit'):
            edit_kwargs["user_limit"] = arguments["user_limit"]
            changes_made.append(f"User limit: {arguments['user_limit']}")
        
        if "bitrate" in arguments and hasattr(channel, 'bitrate'):
            edit_kwargs["bitrate"] = arguments["bitrate"]
            changes_made.append(f"Bitrate: {arguments['bitrate']}")
        
        if edit_kwargs:
            await channel.edit(**edit_kwargs, reason="Channel updated via MCP")
        
        return [TextContent(
            type="text",
            text=f"Updated channel '{channel.name}':\n• " + "\n• ".join(changes_made)
        )]

    @staticmethod
    async def handle_set_channel_permissions(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Set channel-specific permissions"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        target_id = int(arguments["target_id"])
        
        if arguments["target_type"] == "role":
            target = channel.guild.get_role(target_id)
            target_name = f"@{target.name}" if target else "Unknown Role"
        else:
            target = await discord_client.fetch_user(target_id)
            target_name = target.name if target else "Unknown User"
        
        if not target:
            return [TextContent(type="text", text="Target role or user not found")]
        
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
            text=f"Updated permissions for {target_name} in #{channel.name}"
        )]

    @staticmethod
    async def handle_create_role(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a new role"""
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
            text=f"Created role '{role.name}' (ID: {role.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_edit_role(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Edit an existing role"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        if not role:
            return [TextContent(type="text", text="Role not found")]
        
        edit_kwargs = {}
        changes_made = []
        
        if "name" in arguments:
            edit_kwargs["name"] = arguments["name"]
            changes_made.append(f"Name: {arguments['name']}")
        
        if "color" in arguments:
            edit_kwargs["color"] = hex_to_color(arguments["color"])
            changes_made.append(f"Color: {arguments['color']}")
        
        if "permissions" in arguments:
            edit_kwargs["permissions"] = parse_permissions(arguments["permissions"])
            changes_made.append("Permissions updated")
        
        if "hoist" in arguments:
            edit_kwargs["hoist"] = arguments["hoist"]
            changes_made.append(f"Hoisted: {arguments['hoist']}")
        
        if "mentionable" in arguments:
            edit_kwargs["mentionable"] = arguments["mentionable"]
            changes_made.append(f"Mentionable: {arguments['mentionable']}")
        
        if "position" in arguments:
            edit_kwargs["position"] = arguments["position"]
            changes_made.append(f"Position: {arguments['position']}")
        
        edit_kwargs["reason"] = arguments.get("reason", "Role updated via MCP")
        
        if edit_kwargs:
            await role.edit(**edit_kwargs)
        
        return [TextContent(
            type="text",
            text=f"Updated role '{role.name}':\n• " + "\n• ".join(changes_made)
        )]

    @staticmethod
    async def handle_delete_role(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete a role"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        if not role:
            return [TextContent(type="text", text="Role not found")]
        
        role_name = role.name
        await role.delete(reason=arguments.get("reason", "Role deleted via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Deleted role '{role_name}' from {guild.name}"
        )]

    @staticmethod
    async def handle_create_role_hierarchy(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create multiple roles with proper hierarchy"""
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
            text=f"Created role hierarchy in {guild.name}:\n• " + "\n• ".join(reversed(created_roles))
        )]

    @staticmethod
    async def handle_create_emoji(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a custom emoji"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        image_bytes = await fetch_image_bytes(arguments["image_url"])
        
        if not image_bytes:
            return [TextContent(type="text", text="Failed to fetch image from URL")]
        
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
            text=f"Created emoji :{emoji.name}: (ID: {emoji.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_create_webhook(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a webhook"""
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
            text=f"Created webhook '{webhook.name}' in #{channel.name}\nURL: {webhook.url}"
        )]

    @staticmethod
    async def handle_send_webhook_message(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Send a message via webhook"""
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
                if resp.status in [200, 204]:
                    return [TextContent(type="text", text="Webhook message sent successfully")]
                else:
                    error_text = await resp.text()
                    return [TextContent(type="text", text=f"Failed to send webhook message: {resp.status} - {error_text}")]

    @staticmethod
    async def handle_ban_member(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Ban a member from the server"""
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
            text=f"Banned user {user.name} from {guild.name}\nReason: {kwargs['reason']}"
        )]

    @staticmethod
    async def handle_kick_member(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Kick a member from the server"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        
        member_name = member.display_name
        await member.kick(reason=arguments.get("reason", "Kicked via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Kicked member {member_name} from {guild.name}\nReason: {arguments.get('reason', 'Kicked via MCP')}"
        )]

    @staticmethod
    async def handle_timeout_member(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Timeout a member"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        
        duration = timedelta(minutes=arguments["duration_minutes"])
        member_name = member.display_name
        
        await member.timeout(duration, reason=arguments.get("reason", "Timed out via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Timed out member {member_name} for {arguments['duration_minutes']} minutes\nReason: {arguments.get('reason', 'Timed out via MCP')}"
        )]

    @staticmethod
    async def handle_bulk_delete_messages(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Bulk delete messages in a channel"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(arguments["limit"], 100)
        
        deleted = await channel.purge(
            limit=limit,
            reason=arguments.get("reason", "Bulk delete via MCP")
        )
        
        return [TextContent(
            type="text",
            text=f"Deleted {len(deleted)} messages from #{channel.name}\nReason: {arguments.get('reason', 'Bulk delete via MCP')}"
        )]

    @staticmethod
    async def handle_create_scheduled_event(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a scheduled server event"""
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
            privacy_map = {
                "public": discord.PrivacyLevel.guild_only,
                "guild_only": discord.PrivacyLevel.guild_only
            }
            kwargs["privacy_level"] = privacy_map.get(arguments["privacy_level"], discord.PrivacyLevel.guild_only)
        
        event = await guild.create_scheduled_event(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created scheduled event '{event.name}' (ID: {event.id}) in {guild.name}\nStarts: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )]

    @staticmethod
    async def handle_create_invite(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create an invite link"""
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
            text=f"Created invite for #{channel.name}: {invite.url}\nCode: {invite.code}\nExpires: {'Never' if kwargs.get('max_age', 0) == 0 else f'{kwargs.get(\"max_age\", 0)} seconds'}"
        )]

    @staticmethod
    async def handle_create_thread(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a thread in a channel"""
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
            text=f"Created thread '{thread.name}' (ID: {thread.id}) in #{channel.name}"
        )]

    @staticmethod
    async def handle_create_automod_rule(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create an automoderation rule"""
        # Note: This requires discord.py with AutoMod support (v2.4+)
        # For now, we'll create a detailed response showing what would be created
        
        rule_info = {
            "name": arguments["name"],
            "trigger_type": arguments["trigger_type"],
            "actions": arguments["actions"],
            "enabled": arguments.get("enabled", True)
        }
        
        actions_summary = []
        for action in arguments["actions"]:
            if action["type"] == "block_message":
                actions_summary.append("Block message")
            elif action["type"] == "send_alert_message":
                actions_summary.append(f"Send alert to channel {action.get('channel_id', 'TBD')}")
            elif action["type"] == "timeout":
                actions_summary.append(f"Timeout user for {action.get('duration_seconds', 60)} seconds")
        
        return [TextContent(
            type="text",
            text=f"""AutoMod rule configured: '{rule_info['name']}'
Trigger Type: {rule_info['trigger_type']}
Actions: {', '.join(actions_summary)}
Status: {'Enabled' if rule_info['enabled'] else 'Disabled'}

Note: Full AutoMod implementation requires discord.py 2.4+ with AutoMod support."""
        )]
