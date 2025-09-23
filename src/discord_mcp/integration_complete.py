# src/discord_mcp/ai_integration.py
"""
Complete AI integration for server setup - connects all the components
"""

import asyncio
import logging
from typing import Dict, List, Any
from .server_setup_templates import setup_server_from_description, execute_setup_plan, ServerType
from .advanced_discord_features import ServerAnalytics, ServerBackupManager
from .utils import ErrorFormatter

logger = logging.getLogger("discord-mcp-ai")

class AIServerManager:
    """Main AI-driven server management coordinator"""
    
    @staticmethod
    async def setup_complete_server(discord_client, arguments: Dict[str, Any]) -> List[str]:
        """Complete AI-driven server setup with comprehensive error handling"""
        
        server_id = arguments["server_id"]
        description = arguments["server_description"]
        server_type = arguments.get("server_type", "general")
        server_name = arguments.get("server_name")
        
        results = []
        
        try:
            # Step 1: Validate server access
            logger.info(f"🔍 Validating access to server {server_id}")
            guild = await discord_client.fetch_guild(int(server_id))
            results.append(f"✅ Connected to server: {guild.name}")
            
            # Step 2: Generate AI setup plan
            logger.info(f"🤖 Generating AI setup plan for {server_type} server")
            plan = setup_server_from_description(server_id, description, server_type)
            
            if server_name:
                plan.server_name = server_name
                
            results.append(f"🎯 Generated plan for '{plan.server_name or guild.name}'")
            results.append(f"📋 Template: {server_type.title()}")
            results.append(f"📊 Planned: {len(plan.categories)} categories, {len(plan.channels)} channels, {len(plan.roles)} roles")
            
            # Step 3: Create backup before changes
            logger.info("💾 Creating backup before modifications")
            try:
                backup = await ServerBackupManager.create_backup(guild, include_messages=False)
                results.append("✅ Pre-setup backup created")
            except Exception as e:
                results.append(f"⚠️ Backup creation failed: {str(e)}")
                logger.warning(f"Backup failed: {e}")
            
            # Step 4: Execute the setup plan
            logger.info("🚀 Executing AI-generated setup plan")
            setup_results = await execute_setup_plan(discord_client, server_id, plan)
            results.extend(setup_results)
            
            # Step 5: Post-setup validation and health check
            logger.info("🔍 Running post-setup health check")
            health_score = await ServerAnalytics._calculate_health_score(guild)
            results.append(f"🏥 Server health score: {health_score}/100")
            
            if health_score >= 80:
                results.append("🎉 Server setup completed successfully with excellent health!")
            elif health_score >= 60:
                results.append("✅ Server setup completed with good health.")
            else:
                results.append("⚠️ Server setup completed but may need optimization.")
            
            # Step 6: Generate summary and recommendations
            summary = AIServerManager._generate_setup_summary(plan, setup_results, health_score)
            results.extend(summary)
            
            return results
            
        except Exception as e:
            error_msg = ErrorFormatter.format_discord_error(e)
            logger.error(f"AI setup failed: {e}")
            results.append(f"❌ Setup failed: {error_msg}")
            return results
    
    @staticmethod
    def _generate_setup_summary(plan, setup_results, health_score: int) -> List[str]:
        """Generate a comprehensive setup summary"""
        
        summary = [
            "",
            "📊 **Setup Summary:**"
        ]
        
        # Count successful operations
        successful = len([r for r in setup_results if r.startswith("✅")])
        failed = len([r for r in setup_results if r.startswith("❌")])
        warnings = len([r for r in setup_results if r.startswith("⚠️")])
        
        summary.extend([
            f"✅ Successful operations: {successful}",
            f"❌ Failed operations: {failed}",
            f"⚠️ Warnings: {warnings}",
            f"🏥 Final health score: {health_score}/100"
        ])
        
        # Add recommendations based on health score
        if health_score < 70:
            summary.extend([
                "",
                "🔧 **Recommendations:**",
                "• Review failed operations above",
                "• Check bot permissions",
                "• Consider manual adjustment of settings",
                "• Run security audit for optimization"
            ])
        elif health_score < 90:
            summary.extend([
                "",
                "💡 **Optimization Tips:**",
                "• Consider adding more specific channel permissions",
                "• Review automoderation settings",
                "• Add custom server branding (icon/banner)",
                "• Set up welcome messages and rules"
            ])
        else:
            summary.extend([
                "",
                "🎯 **Next Steps:**",
                "• Invite members to your new server",
                "• Test all channels and permissions",
                "• Customize automoderation rules",
                "• Schedule events and activities"
            ])
        
        # Add feature highlights
        if plan.welcome_message:
            summary.append("📝 Welcome message configured")
        if plan.rules_channel_content:
            summary.append("📜 Rules content generated")
        if plan.automod_rules:
            summary.append(f"🛡️ {len(plan.automod_rules)} automod rules configured")
        
        return summary

class ServerTypeDetector:
    """Automatically detect server type from description"""
    
    TYPE_KEYWORDS = {
        ServerType.GAMING: [
            "gaming", "game", "esports", "competitive", "tournament", "clan", "guild",
            "valorant", "league", "cs2", "minecraft", "wow", "raid", "pvp", "fps",
            "mmorpg", "strategy", "team", "scrim", "practice"
        ],
        ServerType.BUSINESS: [
            "business", "company", "corporate", "startup", "team", "work", "office",
            "project", "client", "meeting", "sales", "marketing", "hr", "department",
            "professional", "enterprise", "productivity", "collaboration"
        ],
        ServerType.EDUCATION: [
            "education", "school", "university", "college", "class", "course", "student",
            "teacher", "professor", "study", "homework", "assignment", "lecture",
            "academic", "learning", "tutorial", "training", "workshop"
        ],
        ServerType.CREATIVE: [
            "creative", "art", "artist", "design", "music", "writing", "photography",
            "video", "streaming", "content", "creator", "portfolio", "showcase",
            "collaboration", "project", "commission", "inspiration", "gallery"
        ],
        ServerType.COMMUNITY: [
            "community", "social", "hangout", "friends", "chat", "discussion",
            "hobby", "interest", "local", "neighborhood", "support", "group",
            "club", "society", "gathering", "casual", "friendly", "welcoming"
        ]
    }
    
    @staticmethod
    def detect_server_type(description: str) -> ServerType:
        """Detect server type from description"""
        description_lower = description.lower()
        
        type_scores = {server_type: 0 for server_type in ServerType}
        
        for server_type, keywords in ServerTypeDetector.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    type_scores[server_type] += 1
        
        # Return the type with the highest score
        best_type = max(type_scores, key=type_scores.get)
        
        # If no keywords matched, default to general
        if type_scores[best_type] == 0:
            return ServerType.GENERAL
            
        return best_type

class SetupPreflightChecker:
    """Pre-flight checks before server setup"""
    
    @staticmethod
    async def run_preflight_checks(discord_client, guild) -> List[str]:
        """Run comprehensive pre-flight checks"""
        checks = []
        
        # Check bot permissions
        bot_member = guild.get_member(discord_client.user.id)
        if not bot_member:
            checks.append("❌ Bot is not a member of this server")
            return checks
        
        required_perms = [
            "manage_guild", "manage_channels", "manage_roles", 
            "send_messages", "view_channel", "create_instant_invite"
        ]
        
        missing_perms = []
        for perm in required_perms:
            if not getattr(bot_member.guild_permissions, perm, False):
                missing_perms.append(perm)
        
        if missing_perms:
            checks.append(f"❌ Missing permissions: {', '.join(missing_perms)}")
        else:
            checks.append("✅ Bot has sufficient permissions")
        
        # Check server limits
        channel_count = len(guild.channels)
        role_count = len(guild.roles)
        
        if channel_count > 450:  # Discord limit is 500
            checks.append("⚠️ Server has many channels - may hit Discord limits")
        else:
            checks.append(f"✅ Channel count OK ({channel_count}/500)")
        
        if role_count > 200:  # Discord limit is 250
            checks.append("⚠️ Server has many roles - may hit Discord limits")
        else:
            checks.append(f"✅ Role count OK ({role_count}/250)")
        
        # Check server features
        if "COMMUNITY" in guild.features:
            checks.append("✅ Community server - advanced features available")
        else:
            checks.append("ℹ️ Not a community server - some features unavailable")
        
        return checks

# Integration helper functions
async def enhanced_setup_with_ai(discord_client, arguments: Dict[str, Any]) -> List[str]:
    """Enhanced setup function with full AI capabilities"""
    
    # Step 1: Pre-flight checks
    server_id = arguments["server_id"]
    guild = await discord_client.fetch_guild(int(server_id))
    
    preflight_results = await SetupPreflightChecker.run_preflight_checks(discord_client, guild)
    
    # Check if we should proceed
    critical_errors = [r for r in preflight_results if r.startswith("❌")]
    if critical_errors:
        return ["🚨 **Pre-flight check failed:**"] + preflight_results + [
            "",
            "🔧 **Please fix the above issues before proceeding with setup.**"
        ]
    
    # Step 2: Auto-detect server type if not provided
    if "server_type" not in arguments or arguments["server_type"] == "general":
        description = arguments["server_description"]
        detected_type = ServerTypeDetector.detect_server_type(description)
        arguments["server_type"] = detected_type.value
        logger.info(f"Auto-detected server type: {detected_type.value}")
    
    # Step 3: Run AI setup
    results = ["🔍 **Pre-flight Check Results:**"] + preflight_results + [""]
    
    ai_results = await AIServerManager.setup_complete_server(discord_client, arguments)
    results.extend(ai_results)
    
    return results

# Export the main integration function
__all__ = [
    'AIServerManager', 
    'ServerTypeDetector', 
    'SetupPreflightChecker',
    'enhanced_setup_with_ai'
]
