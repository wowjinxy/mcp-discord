# src/discord_mcp/core_tool_handlers.py
"""
Core Discord tool implementations - handles the fundamental Discord operations
"""

import discord
from typing import List, Any, Dict
from mcp.types import TextContent
from datetime import timedelta

class CoreToolHandlers:
    """Handles all core Discord operations"""
    
    @staticmethod
    async def handle_server_info(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get server information"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        # Get additional info
        owner = await discord_client.fetch_user(guild.owner_id) if guild.owner_id else None
        
        info = f"""
**Server Information for {guild.name}**

**Basic Info:**
- ID: {guild.id}
- Owner: {owner.name if owner else "Unknown"}
- Member Count: {guild.member_count}
- Created: {guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}

**Settings:**
- Verification Level: {guild.verification_level.name}
- Content Filter: {guild.explicit_content_filter.name}
- Boost Level: {guild.premium_tier}
- Boost Count: {guild.premium_subscription_count}

**Channels & Roles:**
- Channels: {len(guild.channels)}
- Roles: {len(guild.roles)}
- Emojis: {len(guild.emojis)}

**Features:** {', '.join(guild.features) if guild.features else 'None'}
        """.strip()
        
        return [TextContent(type="text", text=info)]

    @staticmethod
    async def handle_list_servers(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """List all servers the bot has access to"""
        servers_info = []
        
        for guild in discord_client.guilds:
            servers_info.append({
                "name": guild.name,
                "id": guild.id,
                "member_count": guild.member_count,
                "created_at": guild.created_at.strftime('%Y-%m-%d'),
                "owner_id": guild.owner_id
            })
        
        if not servers_info:
            return [TextContent(type="text", text="No servers found. Make sure the bot is invited to servers.")]
        
        # Format the server list
        server_list = "\n".join([
            f"**{server['name']}**\n"
            f"  - ID: {server['id']}\n"
            f"  - Members: {server['member_count']}\n"
            f"  - Created: {server['created_at']}\n"
            for server in servers_info
        ])
        
        return [TextContent(
            type="text", 
            text=f"**Available Servers ({len(servers_info)}):**\n\n{server_list}"
        )]

    @staticmethod
    async def handle_get_channels(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get channels in a server"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        # Organize channels by category
        categories = {}
        uncategorized = []
        
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                categories[channel.name] = {
                    "id": channel.id,
                    "channels": []
                }
            elif channel.category:
                if channel.category.name not in categories:
                    categories[channel.category.name] = {
                        "id": channel.category.id,
                        "channels": []
                    }
                categories[channel.category.name]["channels"].append({
                    "name": channel.name,
                    "id": channel.id,
                    "type": str(channel.type)
                })
            else:
                uncategorized.append({
                    "name": channel.name,
                    "id": channel.id,
                    "type": str(channel.type)
                })
        
        # Format the output
        result = f"**Channels in {guild.name}:**\n\n"
        
        # Add categorized channels
        for cat_name, cat_data in categories.items():
            if cat_data["channels"]:  # Only show categories with channels
                result += f"**📁 {cat_name}** (ID: {cat_data['id']})\n"
                for channel in cat_data["channels"]:
                    emoji = "🔊" if "voice" in channel["type"] else "💬"
                    result += f"  {emoji} {channel['name']} (ID: {channel['id']}) - {channel['type']}\n"
                result += "\n"
        
        # Add uncategorized channels
        if uncategorized:
            result += "**📋 Uncategorized:**\n"
            for channel in uncategorized:
                emoji = "🔊" if "voice" in channel["type"] else "💬"
                result += f"  {emoji} {channel['name']} (ID: {channel['id']}) - {channel['type']}\n"
        
        return [TextContent(type="text", text=result)]

    @staticmethod
    async def handle_list_members(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """List server members"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        limit = min(int(arguments.get("limit", 50)), 1000)
        
        members_info = []
        count = 0
        
        async for member in guild.fetch_members(limit=limit):
            if count >= limit:
                break
                
            roles = [role.name for role in member.roles if role.name != "@everyone"]
            
            members_info.append({
                "name": member.display_name,
                "username": str(member),
                "id": member.id,
                "joined": member.joined_at.strftime('%Y-%m-%d') if member.joined_at else "Unknown",
                "roles": roles,
                "is_bot": member.bot
            })
            count += 1
        
        # Format the member list
        member_list = []
        humans = 0
        bots = 0
        
        for member in members_info:
            if member["is_bot"]:
                bots += 1
                member_type = "🤖"
            else:
                humans += 1
                member_type = "👤"
            
            roles_str = ", ".join(member["roles"][:3])  # Limit to first 3 roles
            if len(member["roles"]) > 3:
                roles_str += f" (+{len(member['roles'])-3} more)"
            
            member_list.append(
                f"{member_type} **{member['name']}** ({member['username']})\n"
                f"   Joined: {member['joined']} | Roles: {roles_str or 'None'}"
            )
        
        result = f"""**Members in {guild.name}** (Showing {len(members_info)} of {guild.member_count})

**Summary:** {humans} humans, {bots} bots

{chr(10).join(member_list)}"""
        
        return [TextContent(type="text", text=result)]

    @staticmethod
    async def handle_get_user_info(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get user information"""
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        
        info = f"""
**User Information for {user.display_name}**

**Basic Info:**
- Username: {user.name}
- Display Name: {user.display_name}
- ID: {user.id}
- Bot: {"Yes" if user.bot else "No"}
- Account Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}

**Avatar:** {user.display_avatar.url if user.display_avatar else "No avatar"}
        """.strip()
        
        return [TextContent(type="text", text=info)]

    @staticmethod
    async def handle_send_message(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Send a message to a channel"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        
        return [TextContent(
            type="text",
            text=f"Message sent successfully to #{channel.name}. Message ID: {message.id}"
        )]

    @staticmethod
    async def handle_read_messages(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Read recent messages from a channel"""
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
                "timestamp": message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "reactions": reaction_data
            })
        
        def format_reaction(r):
            return f"{r['emoji']}({r['count']})"
        
        formatted_messages = []
        for m in messages:
            reactions_str = ', '.join([format_reaction(r) for r in m['reactions']]) if m['reactions'] else 'No reactions'
            formatted_messages.append(
                f"**{m['author']}** ({m['timestamp']}): {m['content']}\n"
                f"   Reactions: {reactions_str}"
            )
        
        return [TextContent(
            type="text",
            text=f"**Recent messages from #{channel.name}** ({len(messages)} messages):\n\n" + 
                 "\n\n".join(formatted_messages)
        )]

    @staticmethod
    async def handle_add_reaction(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Add a reaction to a message"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        emoji = arguments["emoji"]
        await message.add_reaction(emoji)
        
        return [TextContent(
            type="text",
            text=f"Added reaction {emoji} to message in #{channel.name}"
        )]

    @staticmethod
    async def handle_add_multiple_reactions(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Add multiple reactions to a message"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        emojis = arguments["emojis"]
        for emoji in emojis:
            await message.add_reaction(emoji)
        
        return [TextContent(
            type="text",
            text=f"Added {len(emojis)} reactions ({', '.join(emojis)}) to message in #{channel.name}"
        )]

    @staticmethod
    async def handle_remove_reaction(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Remove a reaction from a message"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        emoji = arguments["emoji"]
        await message.remove_reaction(emoji, discord_client.user)
        
        return [TextContent(
            type="text",
            text=f"Removed reaction {emoji} from message in #{channel.name}"
        )]

    @staticmethod
    async def handle_moderate_message(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete a message and optionally timeout the user"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        
        # Get the message author before deletion
        author = message.author
        content_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
        
        # Delete the message
        await message.delete(reason=arguments["reason"])
        
        result = f"Deleted message from {author.name}: '{content_preview}'\nReason: {arguments['reason']}"
        
        # Apply timeout if specified
        if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
            if isinstance(author, discord.Member):
                timeout_duration = timedelta(minutes=arguments["timeout_minutes"])
                await author.timeout(timeout_duration, reason=arguments["reason"])
                result += f"\nApplied {arguments['timeout_minutes']} minute timeout to {author.name}"
            else:
                result += f"\nCould not timeout {author.name} (user may not be in server)"
        
        return [TextContent(type="text", text=result)]

    @staticmethod
    async def handle_create_text_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a new text channel"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        
        kwargs = {
            "name": arguments["name"],
            "reason": "Channel created via MCP"
        }
        
        if "category_id" in arguments:
            category = guild.get_channel(int(arguments["category_id"]))
            if category:
                kwargs["category"] = category
        
        if "topic" in arguments:
            kwargs["topic"] = arguments["topic"]
        
        channel = await guild.create_text_channel(**kwargs)
        
        return [TextContent(
            type="text",
            text=f"Created text channel '#{channel.name}' (ID: {channel.id}) in {guild.name}"
        )]

    @staticmethod
    async def handle_delete_channel(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete a channel"""
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        channel_name = channel.name
        guild_name = channel.guild.name
        
        await channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
        
        return [TextContent(
            type="text",
            text=f"Deleted channel '#{channel_name}' from {guild_name}"
        )]

    @staticmethod
    async def handle_add_role(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Add a role to a user"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        if not role:
            return [TextContent(type="text", text="Role not found")]
        
        await member.add_roles(role, reason="Role added via MCP")
        
        return [TextContent(
            type="text",
            text=f"Added role '{role.name}' to {member.display_name} in {guild.name}"
        )]

    @staticmethod
    async def handle_remove_role(discord_client, arguments: Dict[str, Any]) -> List[TextContent]:
        """Remove a role from a user"""
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        
        if not role:
            return [TextContent(type="text", text="Role not found")]
        
        await member.remove_roles(role, reason="Role removed via MCP")
        
        return [TextContent(
            type="text",
            text=f"Removed role '{role.name}' from {member.display_name} in {guild.name}"
        )]
