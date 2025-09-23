# server_setup_templates.py
"""
Templates and logic for AI-driven Discord server setup
"""

import re
import json
import discord
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ServerType(Enum):
    GAMING = "gaming"
    COMMUNITY = "community"
    EDUCATION = "education"
    BUSINESS = "business"
    CREATIVE = "creative"
    GENERAL = "general"

@dataclass
class ChannelConfig:
    name: str
    type: str  # text, voice, stage, forum, announcement, category
    category: Optional[str] = None
    topic: Optional[str] = None
    position: Optional[int] = None
    permissions: Optional[Dict[str, List[str]]] = None
    nsfw: bool = False
    slowmode: int = 0
    user_limit: Optional[int] = None  # for voice channels

@dataclass
class RoleConfig:
    name: str
    color: str
    permissions: List[str]
    hoist: bool = False
    mentionable: bool = False
    position: Optional[int] = None

@dataclass
class ServerSetupPlan:
    server_name: Optional[str]
    description: Optional[str]
    verification_level: str = "medium"
    categories: List[ChannelConfig]
    channels: List[ChannelConfig]
    roles: List[RoleConfig]
    automod_rules: List[Dict[str, Any]]
    welcome_message: Optional[str] = None
    rules_channel_content: Optional[str] = None

class ServerSetupAI:
    """AI-driven server setup logic"""
    
    # Predefined templates based on server types
    TEMPLATES = {
        ServerType.GAMING: {
            "categories": [
                {"name": "📋 Information", "type": "category"},
                {"name": "💬 General Chat", "type": "category"},
                {"name": "🎮 Gaming", "type": "category"},
                {"name": "🔊 Voice Channels", "type": "category"},
                {"name": "🔧 Admin", "type": "category"}
            ],
            "channels": [
                # Information Category
                {"name": "📖-rules", "type": "text", "category": "📋 Information", 
                 "topic": "Server rules and guidelines"},
                {"name": "📢-announcements", "type": "announcement", "category": "📋 Information",
                 "topic": "Important server announcements"},
                {"name": "❓-support", "type": "text", "category": "📋 Information",
                 "topic": "Get help and support here"},
                
                # General Chat
                {"name": "💬-general", "type": "text", "category": "💬 General Chat",
                 "topic": "General discussion and chat"},
                {"name": "🎯-introductions", "type": "text", "category": "💬 General Chat",
                 "topic": "Introduce yourself to the community"},
                {"name": "🌍-off-topic", "type": "text", "category": "💬 General Chat",
                 "topic": "Non-gaming related discussions"},
                
                # Gaming
                {"name": "🎮-general-gaming", "type": "text", "category": "🎮 Gaming",
                 "topic": "General gaming discussions"},
                {"name": "🎯-lfg", "type": "text", "category": "🎮 Gaming",
                 "topic": "Looking for group/teammates"},
                {"name": "📊-game-stats", "type": "text", "category": "🎮 Gaming",
                 "topic": "Share your gaming achievements"},
                {"name": "🎮-game-forum", "type": "forum", "category": "🎮 Gaming",
                 "topic": "Game-specific discussions and help"},
                
                # Voice Channels
                {"name": "🔊 General Voice", "type": "voice", "category": "🔊 Voice Channels"},
                {"name": "🎮 Gaming Voice 1", "type": "voice", "category": "🔊 Voice Channels"},
                {"name": "🎮 Gaming Voice 2", "type": "voice", "category": "🔊 Voice Channels"},
                {"name": "🎤 Stage Channel", "type": "stage", "category": "🔊 Voice Channels"},
                
                # Admin
                {"name": "🛡️-mod-chat", "type": "text", "category": "🔧 Admin",
                 "topic": "Moderator discussions", "permissions": {"view": ["Moderator", "Admin"]}},
                {"name": "📋-mod-logs", "type": "text", "category": "🔧 Admin",
                 "topic": "Moderation logs", "permissions": {"view": ["Moderator", "Admin"]}}
            ],
            "roles": [
                {"name": "👑 Server Owner", "color": "#ff0000", "permissions": ["administrator"], "hoist": True},
                {"name": "🛡️ Admin", "color": "#ff6600", "permissions": ["administrator"], "hoist": True},
                {"name": "🔨 Moderator", "color": "#3498db", "permissions": [
                    "kick_members", "ban_members", "manage_messages", "mute_members", 
                    "deafen_members", "move_members", "manage_nicknames"
                ], "hoist": True},
                {"name": "🎮 Gamer", "color": "#9b59b6", "permissions": ["send_messages", "connect"], "hoist": True},
                {"name": "✨ VIP", "color": "#f1c40f", "permissions": ["send_messages", "connect"], "hoist": True},
                {"name": "👤 Member", "color": "#95a5a6", "permissions": ["send_messages", "connect"]}
            ]
        },
        
        ServerType.COMMUNITY: {
            "categories": [
                {"name": "📋 Server Info", "type": "category"},
                {"name": "💬 Community", "type": "category"},
                {"name": "🎨 Creative", "type": "category"},
                {"name": "🔊 Voice", "type": "category"},
                {"name": "🔧 Staff", "type": "category"}
            ],
            "channels": [
                # Server Info
                {"name": "📜-rules", "type": "text", "category": "📋 Server Info"},
                {"name": "📢-announcements", "type": "announcement", "category": "📋 Server Info"},
                {"name": "🎉-events", "type": "text", "category": "📋 Server Info"},
                
                # Community
                {"name": "💬-general", "type": "text", "category": "💬 Community"},
                {"name": "👋-introductions", "type": "text", "category": "💬 Community"},
                {"name": "💭-discussions", "type": "forum", "category": "💬 Community"},
                {"name": "📸-media", "type": "text", "category": "💬 Community"},
                
                # Creative
                {"name": "🎨-showcase", "type": "text", "category": "🎨 Creative"},
                {"name": "💡-ideas", "type": "text", "category": "🎨 Creative"},
                {"name": "🤝-collaborations", "type": "text", "category": "🎨 Creative"},
                
                # Voice
                {"name": "🗣️ General Voice", "type": "voice", "category": "🔊 Voice"},
                {"name": "🎵 Music/Podcast", "type": "voice", "category": "🔊 Voice"},
                {"name": "🎤 Town Hall", "type": "stage", "category": "🔊 Voice"},
                
                # Staff
                {"name": "👮-staff-chat", "type": "text", "category": "🔧 Staff"},
                {"name": "📊-reports", "type": "text", "category": "🔧 Staff"}
            ],
            "roles": [
                {"name": "👑 Owner", "color": "#e74c3c", "permissions": ["administrator"], "hoist": True},
                {"name": "🔨 Moderator", "color": "#3498db", "permissions": [
                    "kick_members", "ban_members", "manage_messages", "mute_members"
                ], "hoist": True},
                {"name": "🌟 Active Member", "color": "#f39c12", "permissions": ["send_messages"], "hoist": True},
                {"name": "👥 Member", "color": "#95a5a6", "permissions": ["send_messages"]}
            ]
        },
        
        # Add other templates as needed...
        ServerType.GENERAL: {
            "categories": [
                {"name": "📋 Information", "type": "category"},
                {"name": "💬 General", "type": "category"},
                {"name": "🔊 Voice", "type": "category"}
            ],
            "channels": [
                {"name": "📜-rules", "type": "text", "category": "📋 Information"},
                {"name": "📢-announcements", "type": "announcement", "category": "📋 Information"},
                {"name": "💬-general", "type": "text", "category": "💬 General"},
                {"name": "🗣️ General Voice", "type": "voice", "category": "🔊 Voice"}
            ],
            "roles": [
                {"name": "👑 Owner", "color": "#e74c3c", "permissions": ["administrator"], "hoist": True},
                {"name": "🔨 Moderator", "color": "#3498db", "permissions": [
                    "kick_members", "ban_members", "manage_messages"
                ], "hoist": True},
                {"name": "👥 Member", "color": "#95a5a6", "permissions": ["send_messages"]}
            ]
        }
    }

    @classmethod
    def parse_description(cls, description: str, server_type: ServerType) -> ServerSetupPlan:
        """Parse natural language description and generate setup plan"""
        
        # Start with template based on server type
        template = cls.TEMPLATES.get(server_type, cls.TEMPLATES[ServerType.GENERAL])
        
        # Extract key information from description
        analysis = cls._analyze_description(description)
        
        # Generate setup plan
        plan = ServerSetupPlan(
            server_name=analysis.get("server_name"),
            description=analysis.get("server_description"),
            verification_level=analysis.get("verification_level", "medium"),
            categories=[ChannelConfig(**cat) for cat in template["categories"]],
            channels=[ChannelConfig(**ch) for ch in template["channels"]],
            roles=[RoleConfig(**role) for role in template["roles"]],
            automod_rules=cls._generate_automod_rules(analysis),
            welcome_message=cls._generate_welcome_message(analysis),
            rules_channel_content=cls._generate_rules_content(analysis)
        )
        
        # Customize based on analysis
        plan = cls._customize_plan(plan, analysis)
        
        return plan

    @classmethod
    def _analyze_description(cls, description: str) -> Dict[str, Any]:
        """Analyze the natural language description"""
        analysis = {}
        
        # Extract server name if mentioned
        name_patterns = [
            r"(?:server|community|guild)\s+(?:called|named)\s+['\"]([^'\"]+)['\"]",
            r"['\"]([^'\"]+)['\"](?:\s+server|\s+community|\s+guild)",
            r"call(?:ed)?\s+it\s+['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                analysis["server_name"] = match.group(1)
                break
        
        # Detect verification level preferences
        if any(word in description.lower() for word in ["strict", "secure", "verification", "verified"]):
            analysis["verification_level"] = "high"
        elif any(word in description.lower() for word in ["open", "welcoming", "easy"]):
            analysis["verification_level"] = "low"
        
        # Detect content filters needed
        analysis["content_filter"] = "medium"
        if any(word in description.lower() for word in ["family", "safe", "clean", "appropriate"]):
            analysis["content_filter"] = "high"
        elif any(word in description.lower() for word in ["adult", "mature", "18+"]):
            analysis["content_filter"] = "low"
        
        # Detect special features needed
        features = []
        if any(word in description.lower() for word in ["announcement", "news", "update"]):
            features.append("announcements")
        if any(word in description.lower() for word in ["event", "schedule", "calendar"]):
            features.append("events")
        if any(word in description.lower() for word in ["voice", "talk", "call", "meeting"]):
            features.append("voice")
        if any(word in description.lower() for word in ["stage", "presentation", "lecture"]):
            features.append("stage")
        if any(word in description.lower() for word in ["forum", "discussion", "topic"]):
            features.append("forum")
        
        analysis["features"] = features
        analysis["server_description"] = description
        
        return analysis

    @classmethod
    def _customize_plan(cls, plan: ServerSetupPlan, analysis: Dict[str, Any]) -> ServerSetupPlan:
        """Customize the plan based on analysis"""
        
        # Add additional channels based on features
        features = analysis.get("features", [])
        
        if "events" in features:
            plan.channels.append(ChannelConfig(
                name="📅-events",
                type="text",
                category="📋 Information",
                topic="Server events and activities"
            ))
        
        if "forum" in features and not any(ch.type == "forum" for ch in plan.channels):
            plan.channels.append(ChannelConfig(
                name="💭-discussions",
                type="forum",
                category="💬 General Chat",
                topic="General discussion topics"
            ))
        
        # Adjust verification level
        if analysis.get("verification_level"):
            plan.verification_level = analysis["verification_level"]
        
        return plan

    @classmethod
    def _generate_automod_rules(cls, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate automod rules based on analysis"""
        rules = []
        
        # Basic spam protection
        rules.append({
            "name": "Anti-Spam",
            "trigger_type": "spam",
            "actions": [
                {"type": "block_message"},
                {"type": "timeout", "duration_seconds": 300}
            ],
            "enabled": True
        })
        
        # Content filter based on analysis
        content_level = analysis.get("content_filter", "medium")
        if content_level == "high":
            rules.append({
                "name": "Family Friendly Filter",
                "trigger_type": "keyword_preset",
                "keyword_presets": ["profanity", "sexual_content"],
                "actions": [
                    {"type": "block_message"},
                    {"type": "send_alert_message"}
                ],
                "enabled": True
            })
        
        return rules

    @classmethod
    def _generate_welcome_message(cls, analysis: Dict[str, Any]) -> str:
        """Generate a welcome message based on analysis"""
        server_name = analysis.get("server_name", "our server")
        
        return f"""
Welcome to {server_name}! 🎉

We're excited to have you join our community. Here's how to get started:

1. 📜 Read our rules in the rules channel
2. 👋 Introduce yourself in our introductions channel
3. 🎯 Check out our various channels and find your interests
4. 🤝 Be respectful and have fun!

If you have any questions, feel free to ask our staff members.
Enjoy your stay! ✨
        """.strip()

    @classmethod
    def _generate_rules_content(cls, analysis: Dict[str, Any]) -> str:
        """Generate rules content based on analysis"""
        server_name = analysis.get("server_name", "this server")
        
        return f"""
# 📜 {server_name} Rules

Please read and follow these rules to maintain a positive environment for everyone.

## 🤝 General Conduct
1. **Be respectful** - Treat all members with kindness and respect
2. **No harassment** - Harassment, bullying, or discrimination will not be tolerated
3. **Keep it civil** - Disagreements are fine, but keep discussions constructive
4. **Use appropriate language** - Keep content appropriate for all ages

## 💬 Communication Guidelines
5. **Stay on topic** - Use appropriate channels for discussions
6. **No spam** - Avoid repetitive messages, excessive caps, or flooding
7. **No advertising** - Don't advertise other servers or products without permission
8. **English only** - Please communicate primarily in English

## 🚫 Prohibited Content
9. **No NSFW content** - Keep all content safe for work
10. **No piracy** - Don't share or discuss illegal content
11. **No doxxing** - Don't share personal information of others
12. **No hate speech** - Discriminatory language is strictly prohibited

## 🔨 Enforcement
- **First offense**: Warning
- **Second offense**: Temporary timeout
- **Third offense**: Temporary ban
- **Severe violations**: Immediate permanent ban

## 📞 Contact Staff
If you have questions or need to report an issue, please contact our staff members.

**Remember**: These rules help keep our community safe and enjoyable for everyone!
        """.strip()

# Usage functions
def setup_server_from_description(server_id: str, description: str, server_type: str = "general") -> ServerSetupPlan:
    """
    Main function to set up a server from a natural language description
    """
    
    try:
        server_type_enum = ServerType(server_type.lower())
    except ValueError:
        server_type_enum = ServerType.GENERAL
    
    return ServerSetupAI.parse_description(description, server_type_enum)

# Discord execution function
async def execute_setup_plan(discord_client, server_id: str, plan: ServerSetupPlan) -> List[str]:
    """Execute the setup plan on the Discord server"""
    results = []
    
    try:
        guild = await discord_client.fetch_guild(int(server_id))
        
        # Update server settings
        if plan.server_name or plan.description:
            try:
                edit_kwargs = {}
                if plan.server_name:
                    edit_kwargs["name"] = plan.server_name
                if plan.description:
                    edit_kwargs["description"] = plan.description
                
                await guild.edit(**edit_kwargs, reason="AI-driven server setup")
                results.append(f"✅ Updated server settings")
            except Exception as e:
                results.append(f"❌ Failed to update server settings: {str(e)}")
        
        # Create roles first (in reverse order for hierarchy)
        created_roles = {}
        for role_config in reversed(plan.roles):
            try:
                permissions = discord.Permissions.none()
                for perm in role_config.permissions:
                    if hasattr(permissions, perm.lower()):
                        setattr(permissions, perm.lower(), True)
                
                color = discord.Color.default()
                if role_config.color.startswith('#'):
                    color = discord.Color(int(role_config.color[1:], 16))
                
                role = await guild.create_role(
                    name=role_config.name,
                    permissions=permissions,
                    color=color,
                    hoist=role_config.hoist,
                    mentionable=role_config.mentionable,
                    reason="AI-driven server setup"
                )
                created_roles[role_config.name] = role
                results.append(f"✅ Created role: {role_config.name}")
                
            except Exception as e:
                results.append(f"❌ Failed to create role {role_config.name}: {str(e)}")
        
        # Create categories
        created_categories = {}
        for category_config in plan.categories:
            try:
                category = await guild.create_category(
                    name=category_config.name,
                    position=category_config.position,
                    reason="AI-driven server setup"
                )
                created_categories[category_config.name] = category
                results.append(f"✅ Created category: {category_config.name}")
                
            except Exception as e:
                results.append(f"❌ Failed to create category {category_config.name}: {str(e)}")
        
        # Create channels
        for channel_config in plan.channels:
            try:
                category = created_categories.get(channel_config.category)
                
                kwargs = {
                    "name": channel_config.name,
                    "category": category,
                    "reason": "AI-driven server setup"
                }
                
                if channel_config.topic:
                    kwargs["topic"] = channel_config.topic
                if channel_config.position is not None:
                    kwargs["position"] = channel_config.position
                if channel_config.slowmode > 0:
                    kwargs["slowmode_delay"] = channel_config.slowmode
                
                # Create appropriate channel type
                if channel_config.type == "text":
                    channel = await guild.create_text_channel(**kwargs)
                elif channel_config.type == "voice":
                    if channel_config.user_limit:
                        kwargs["user_limit"] = channel_config.user_limit
                    channel = await guild.create_voice_channel(**kwargs)
                elif channel_config.type == "stage":
                    channel = await guild.create_stage_channel(**kwargs)
                elif channel_config.type == "forum":
                    channel = await guild.create_forum(**kwargs)
                elif channel_config.type == "announcement":
                    kwargs["type"] = discord.ChannelType.news
                    channel = await guild.create_text_channel(**kwargs)
                else:
                    continue
                
                results.append(f"✅ Created {channel_config.type} channel: {channel_config.name}")
                
                # Add content to rules channel
                if "rules" in channel_config.name.lower() and plan.rules_channel_content:
                    try:
                        await channel.send(plan.rules_channel_content)
                        results.append(f"✅ Added rules content to {channel_config.name}")
                    except Exception as e:
                        results.append(f"⚠️ Created {channel_config.name} but couldn't add content: {str(e)}")
                
            except Exception as e:
                results.append(f"❌ Failed to create channel {channel_config.name}: {str(e)}")
        
        # Send welcome message to general channel
        general_channel = None
        for channel in guild.channels:
            if "general" in channel.name.lower() and hasattr(channel, 'send'):
                general_channel = channel
                break
        
        if general_channel and plan.welcome_message:
            try:
                await general_channel.send(plan.welcome_message)
                results.append(f"✅ Sent welcome message to general channel")
            except Exception as e:
                results.append(f"⚠️ Failed to send welcome message: {str(e)}")
        
        results.append(f"🎉 Server setup completed! Created {len(created_categories)} categories, {len([r for r in results if 'Created' in r and 'channel' in r])} channels, and {len(created_roles)} roles.")
        
    except Exception as e:
        results.append(f"❌ General setup error: {str(e)}")
    
    return results