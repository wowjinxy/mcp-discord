"""FastMCP server entry point for Discord MCP tools."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Sequence

import discord
from discord import Forbidden, HTTPException, NotFound
from discord.abc import Messageable
from discord.ext import commands
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, ConfigDict, Field
from smithery.decorators import smithery

logger = logging.getLogger("discord_mcp.server")


class ConfigSchema(BaseModel):
    """Session configuration for the Discord MCP server."""

    discord_token: str | None = Field(
        None,
        alias="discordToken",
        description=(
            "Discord bot token with the required privileged intents enabled. "
            "Omit this when the DISCORD_TOKEN environment variable is set."
        ),
    )
    default_guild_id: int | None = Field(
        None,
        alias="defaultGuildId",
        description="Optional default Discord server (guild) ID used when a tool call omits server_id.",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DiscordToolError(RuntimeError):
    """Raised when a Discord interaction cannot be completed."""


_MISSING_TOKEN_MESSAGE = (
    "No Discord token provided. Configure a token via Smithery session config or the DISCORD_TOKEN environment variable."
)


@dataclass(slots=True)
class _DiscordClientEntry:
    bot: commands.Bot
    task: asyncio.Task[None]
    ready: asyncio.Future[None]


def _create_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.presences = True
    intents.message_content = True
    intents.guild_messages = True
    intents.guild_reactions = True
    intents.dm_messages = True
    intents.dm_reactions = True
    intents.moderation = True
    intents.auto_moderation = True
    intents.auto_moderation_configuration = True
    intents.auto_moderation_execution = True
    return intents


class DiscordClientManager:
    """Manages Discord client lifecycles for different bot tokens."""

    def __init__(self) -> None:
        self._entries: dict[str, _DiscordClientEntry] = {}
        self._lock = asyncio.Lock()

    async def get_bot(self, token: str) -> commands.Bot:
        token = token.strip()
        if not token:
            raise DiscordToolError("A Discord bot token is required to use this server.")

        old_entry: _DiscordClientEntry | None = None
        async with self._lock:
            entry = self._entries.get(token)
            if entry is None or entry.task.done():
                if entry is not None:
                    old_entry = entry
                entry = self._start_bot(token)
                self._entries[token] = entry

        if old_entry is not None:
            await self._cleanup_entry(token, old_entry)

        try:
            await entry.ready
        except Exception:
            await self._cleanup_entry(token, entry)
            raise

        if entry.task.done():
            exc = entry.task.exception()
            if exc is not None:
                await self._cleanup_entry(token, entry)
                raise exc

        return entry.bot

    async def close_all(self) -> None:
        async with self._lock:
            entries = list(self._entries.items())
            self._entries.clear()

        for token, entry in entries:
            await self._cleanup_entry(token, entry)

    def _start_bot(self, token: str) -> _DiscordClientEntry:
        bot = commands.Bot(command_prefix="!", intents=_create_intents())
        ready: asyncio.Future[None] = asyncio.get_running_loop().create_future()

        @bot.event
        async def on_ready() -> None:  # type: ignore[override]
            if not ready.done():
                ready.set_result(None)
            logger.info("Discord bot connected as %s", bot.user)

        async def runner() -> None:
            try:
                await bot.start(token)
            except Exception as exc:  # pragma: no cover - best effort logging
                if not ready.done():
                    ready.set_exception(exc)
                logger.exception("Discord bot task stopped unexpectedly")
                raise

        task = asyncio.create_task(runner(), name="discord-mcp-bot")
        return _DiscordClientEntry(bot=bot, task=task, ready=ready)

    async def _cleanup_entry(self, token: str, entry: _DiscordClientEntry) -> None:
        if not entry.ready.done():
            entry.ready.cancel()

        try:
            await entry.bot.close()
        except Exception:  # pragma: no cover - cleanup best effort
            logger.debug("Error while closing Discord bot", exc_info=True)

        if not entry.task.done():
            entry.task.cancel()

        try:
            await entry.task
        except asyncio.CancelledError:  # pragma: no cover - expected during shutdown
            pass
        except Exception:  # pragma: no cover - cleanup best effort
            logger.debug("Discord bot task ended with error", exc_info=True)

        async with self._lock:
            if self._entries.get(token) is entry:
                self._entries.pop(token, None)


def _normalize_token(token: str | None) -> str | None:
    if token is None:
        return None
    stripped = token.strip()
    if not stripped:
        return None

    if (stripped.startswith("\"") and stripped.endswith("\"")) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        stripped = stripped[1:-1].strip()
        if not stripped:
            return None

    if stripped.lower().startswith("bot "):
        stripped = stripped[4:].strip()

    return stripped or None


def _get_env_config() -> ConfigSchema:
    token = _normalize_token(os.getenv("DISCORD_TOKEN"))
    guild_raw = os.getenv("DISCORD_DEFAULT_GUILD_ID")
    default_guild = int(guild_raw) if guild_raw else None
    return ConfigSchema(discord_token=token, default_guild_id=default_guild)


def _get_session_config(ctx: Context) -> ConfigSchema:
    config = getattr(ctx, "session_config", None)
    if isinstance(config, ConfigSchema):
        session_config = config
    elif config is not None:
        session_config = ConfigSchema.model_validate(config)
    else:
        session_config = ConfigSchema()

    env_config = _get_env_config()

    session_token = _normalize_token(session_config.discord_token)
    env_token = _normalize_token(env_config.discord_token)
    token = session_token or env_token
    if token is None:
        raise DiscordToolError(_MISSING_TOKEN_MESSAGE)

    default_guild = session_config.default_guild_id
    if default_guild is None:
        default_guild = env_config.default_guild_id

    return ConfigSchema(discord_token=token, default_guild_id=default_guild)


def _require_int(value: str | int | None, name: str) -> int:
    if value is None:
        raise DiscordToolError(f"{name} is required for this operation.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - validation guard
        raise DiscordToolError(f"{name} must be an integer identifier.") from exc


def _resolve_guild_id(config: ConfigSchema, supplied: str | int | None) -> int:
    if supplied is not None:
        return _require_int(supplied, "server_id")
    if config.default_guild_id is None:
        raise DiscordToolError("Provide a server_id or configure defaultGuildId in the session configuration.")
    return config.default_guild_id


def _format_timestamp(dt: datetime | None) -> str:
    if dt is None:
        return "Unknown"
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _describe_discord_error(action: str, exc: discord.DiscordException) -> DiscordToolError:
    if isinstance(exc, Forbidden):
        return DiscordToolError(f"{action} failed: the bot is missing required permissions.")
    if isinstance(exc, NotFound):
        return DiscordToolError(f"{action} failed because the requested resource could not be found.")
    if isinstance(exc, HTTPException):
        detail = exc.text or getattr(exc, "original", "")
        detail = f" ({detail})" if detail else ""
        return DiscordToolError(f"{action} failed with HTTP status {exc.status}{detail}.")
    return DiscordToolError(f"{action} failed: {exc}.")


async def _call_discord(action: str, coro):
    try:
        return await coro
    except discord.DiscordException as exc:
        raise _describe_discord_error(action, exc) from exc


async def _ensure_guild(bot: commands.Bot, guild_id: int) -> discord.Guild:
    guild = bot.get_guild(guild_id)
    if guild is not None:
        return guild
    return await _call_discord("fetch server", bot.fetch_guild(guild_id))


async def _ensure_channel(bot: commands.Bot, channel_id: int) -> Messageable:
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await _call_discord("fetch channel", bot.fetch_channel(channel_id))
    if not isinstance(channel, Messageable):
        raise DiscordToolError("The specified channel does not support text messages.")
    return channel


async def _fetch_message(channel: Messageable, message_id: int) -> discord.Message:
    if not hasattr(channel, "fetch_message"):
        raise DiscordToolError("Unable to fetch messages for this channel type.")
    return await _call_discord("fetch message", channel.fetch_message(message_id))


def _format_channel_summary(channels: Sequence[discord.abc.GuildChannel]) -> str:
    by_category: dict[str, list[str]] = {}
    uncategorized: list[str] = []

    for channel in channels:
        entry = f"• {channel.name} (ID: {channel.id})"
        if isinstance(channel, discord.TextChannel):
            entry += " – text"
        elif isinstance(channel, discord.VoiceChannel):
            entry += " – voice"
        elif isinstance(channel, discord.CategoryChannel):
            entry += " – category"
        elif isinstance(channel, discord.StageChannel):
            entry += " – stage"
        elif isinstance(channel, discord.ForumChannel):
            entry += " – forum"

        if isinstance(channel, discord.CategoryChannel):
            by_category.setdefault(channel.name, [])  # keep category entry for completeness
        elif channel.category:
            by_category.setdefault(channel.category.name, []).append(entry)
        else:
            uncategorized.append(entry)

    lines: list[str] = []
    for category, entries in by_category.items():
        lines.append(f"**{category}**")
        if entries:
            lines.extend(f"  {value}" for value in entries)
        else:
            lines.append("  (no channels)")
        lines.append("")

    if uncategorized:
        lines.append("**Uncategorized**")
        lines.extend(f"  {value}" for value in uncategorized)

    return "\n".join(line for line in lines if line)


def _format_member(member: discord.Member) -> str:
    roles = [role.name for role in member.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles[:3]) + ("..." if len(roles) > 3 else "") if roles else "None"
    joined = _format_timestamp(member.joined_at)
    return f"• {member.display_name} ({member.id}) – Joined {joined} – Roles: {roles_str}"


def _format_messages(messages: Sequence[discord.Message]) -> str:
    lines: list[str] = []
    for message in messages:
        timestamp = _format_timestamp(message.created_at)
        author = message.author.display_name if hasattr(message.author, "display_name") else str(message.author)
        lines.append(f"[{timestamp}] {author}: {message.content or '(no content)'}")
    return "\n".join(lines)


_client_manager = DiscordClientManager()


@smithery.server(config_schema=ConfigSchema)
def create_server() -> FastMCP:
    """Create and configure the FastMCP Discord server."""

    @asynccontextmanager
    async def lifespan(_: FastMCP):
        try:
            yield
        finally:
            await _client_manager.close_all()

    server = FastMCP(
        name="Discord Server",
        instructions=(
            "Interact with Discord using a bot token. Configure `discordToken` (or set the `DISCORD_TOKEN` environment "
            "variable) and an optional `defaultGuildId` when connecting through Smithery."
        ),
        lifespan=lifespan,
    )

    async def _acquire(ctx: Context) -> tuple[commands.Bot, ConfigSchema]:
        config = _get_session_config(ctx)
        token = _normalize_token(config.discord_token)
        if token is None:
            raise DiscordToolError(_MISSING_TOKEN_MESSAGE)
        bot = await _client_manager.get_bot(token)
        return bot, config

    @server.tool()
    async def list_servers(ctx: Context) -> str:
        """List the Discord servers the bot is currently connected to."""

        bot, config = await _acquire(ctx)
        guilds = bot.guilds
        if not guilds:
            raise DiscordToolError("The bot is not connected to any servers. Invite it to a server and try again.")

        lines = ["**Connected Servers**"]
        for guild in guilds:
            default_marker = " (default)" if config.default_guild_id == guild.id else ""
            member_count = guild.member_count if guild.member_count is not None else "unknown"
            lines.append(f"• {guild.name} (ID: {guild.id}) – Members: {member_count}{default_marker}")
        return "\n".join(lines)

    @server.tool()
    async def get_server_info(server_id: str | int | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """Retrieve detailed information about a Discord server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        owner = None
        if guild.owner_id:
            try:
                owner_user = await _call_discord("fetch server owner", bot.fetch_user(guild.owner_id))
                owner = f"{owner_user.display_name} ({owner_user.id})"
            except DiscordToolError:
                owner = str(guild.owner_id)

        created = _format_timestamp(guild.created_at)
        boost_tier = getattr(guild, "premium_tier", "unknown")
        boost_count = getattr(guild, "premium_subscription_count", "unknown")
        features = ", ".join(guild.features) if guild.features else "None"

        return (
            f"**{guild.name}** (ID: {guild.id})\n"
            f"Owner: {owner or 'Unknown'}\n"
            f"Created: {created}\n"
            f"Members: {guild.member_count or 'unknown'}\n"
            f"Boost Tier: {boost_tier} ({boost_count} boosts)\n"
            f"Verification Level: {guild.verification_level.name}\n"
            f"Explicit Content Filter: {guild.explicit_content_filter.name}\n"
            f"Features: {features}"
        )

    @server.tool()
    async def get_channels(server_id: str | int | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """List channels for a Discord server grouped by category."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)
        channels = await _call_discord("fetch channels", guild.fetch_channels())
        summary = _format_channel_summary(channels)
        if not summary:
            return f"{guild.name} has no channels."
        return f"**Channels for {guild.name}:**\n{summary}"

    @server.tool()
    async def list_members(
        server_id: str | int | None = None,
        limit: int = 25,
        include_bots: bool = True,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """List members of a Discord server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        limit = max(1, min(limit, 200))
        members: list[discord.Member] = []
        try:
            async for member in guild.fetch_members(limit=None):
                if not include_bots and member.bot:
                    continue
                members.append(member)
                if len(members) >= limit:
                    break
        except discord.DiscordException as exc:
            raise _describe_discord_error("fetch members", exc) from exc

        if not members:
            return f"No members found for {guild.name}."

        summary = "\n".join(_format_member(member) for member in members)
        total = guild.member_count or len(members)
        return f"**Members for {guild.name} (showing {len(members)} of ~{total}):**\n{summary}"

    @server.tool()
    async def get_user_info(user_id: str | int, ctx: Context) -> str:
        """Fetch information about a specific Discord user."""

        bot, _ = await _acquire(ctx)
        user = await _call_discord("fetch user", bot.fetch_user(_require_int(user_id, "user_id")))
        created = _format_timestamp(user.created_at)
        return (
            f"**{user.display_name}** (ID: {user.id})\n"
            f"Username: {user.name}\n"
            f"Bot: {'Yes' if user.bot else 'No'}\n"
            f"Created: {created}"
        )

    @server.tool()
    async def send_message(channel_id: str | int, message: str, ctx: Context) -> str:
        """Send a message to a Discord text channel or thread."""

        if not message.strip():
            raise DiscordToolError("Message content cannot be empty.")

        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        sent_message = await _call_discord("send message", channel.send(message))
        jump_url = getattr(sent_message, "jump_url", "")
        url_line = f"\nLink: {jump_url}" if jump_url else ""
        return f"Message sent to channel {channel.id}.{url_line}"

    @server.tool()
    async def read_messages(channel_id: str | int, limit: int = 20, ctx: Context = None) -> str:  # type: ignore[override]
        """Read recent messages from a channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        limit = max(1, min(limit, 100))

        history: list[discord.Message] = []
        try:
            async for message in channel.history(limit=limit, oldest_first=False):
                history.append(message)
        except discord.DiscordException as exc:
            raise _describe_discord_error("read messages", exc) from exc
        history.reverse()

        if not history:
            return "No messages found in the specified channel."

        return _format_messages(history)

    @server.tool()
    async def add_reaction(channel_id: str | int, message_id: str | int, emoji: str, ctx: Context) -> str:
        """Add a reaction to a specific message."""

        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))
        await _call_discord("add reaction", message.add_reaction(emoji))
        return f"Added reaction {emoji} to message {message.id}."

    @server.tool()
    async def add_multiple_reactions(
        channel_id: str | int,
        message_id: str | int,
        emojis: Sequence[str],
        ctx: Context,
    ) -> str:
        """Add multiple reactions to a message."""

        if not emojis:
            raise DiscordToolError("Provide at least one emoji to add.")

        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))

        for emoji in emojis:
            await _call_discord("add reaction", message.add_reaction(emoji))

        return f"Added {len(emojis)} reactions to message {message.id}."

    @server.tool()
    async def remove_reaction(channel_id: str | int, message_id: str | int, emoji: str, ctx: Context) -> str:
        """Remove the bot's reaction from a message."""

        bot, _ = await _acquire(ctx)
        if bot.user is None:
            raise DiscordToolError("Discord client is not ready yet. Try again shortly.")

        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))
        await _call_discord("remove reaction", message.remove_reaction(emoji, bot.user))
        return f"Removed reaction {emoji} from message {message.id}."

    @server.tool()
    async def create_text_channel(
        name: str,
        server_id: str | int | None = None,
        category_id: str | int | None = None,
        topic: str | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create a new text channel in the specified server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        category = None
        if category_id is not None:
            category = await _call_discord("fetch category", guild.fetch_channel(_require_int(category_id, "category_id")))
            if not isinstance(category, discord.CategoryChannel):
                raise DiscordToolError("Provided category_id does not refer to a category.")

        channel = await _call_discord(
            "create channel",
            guild.create_text_channel(name=name, category=category, topic=topic, reason=reason),
        )
        return f"Created text channel {channel.name} (ID: {channel.id})."

    @server.tool()
    async def delete_channel(channel_id: str | int, reason: str | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """Delete a Discord channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _call_discord("fetch channel", bot.fetch_channel(_require_int(channel_id, "channel_id")))
        await _call_discord("delete channel", channel.delete(reason=reason))
        return f"Deleted channel {channel_id}."

    @server.tool()
    async def add_role(
        user_id: str | int,
        role_id: str | int,
        server_id: str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Add a role to a Discord user."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        member = await _call_discord("fetch member", guild.fetch_member(_require_int(user_id, "user_id")))
        role = guild.get_role(_require_int(role_id, "role_id"))
        if role is None:
            raise DiscordToolError("Role not found in the specified server.")

        await _call_discord("add role", member.add_roles(role, reason=reason))
        return f"Added role {role.name} to {member.display_name}."

    @server.tool()
    async def remove_role(
        user_id: str | int,
        role_id: str | int,
        server_id: str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Remove a role from a Discord user."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        member = await _call_discord("fetch member", guild.fetch_member(_require_int(user_id, "user_id")))
        role = guild.get_role(_require_int(role_id, "role_id"))
        if role is None:
            raise DiscordToolError("Role not found in the specified server.")

        await _call_discord("remove role", member.remove_roles(role, reason=reason))
        return f"Removed role {role.name} from {member.display_name}."

    @server.tool()
    async def moderate_message(
        channel_id: str | int,
        message_id: str | int,
        delete_message: bool = True,
        timeout_minutes: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Moderate a message by deleting it and optionally timing out the author."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))

        results: list[str] = []
        if delete_message:
            await _call_discord("delete message", message.delete(reason=reason))
            results.append("Message deleted")

        if timeout_minutes is not None:
            if not isinstance(message.author, discord.Member):
                raise DiscordToolError("Cannot timeout the author because they are not a guild member.")
            duration = max(1, timeout_minutes)
            until = datetime.now(tz=UTC) + timedelta(minutes=duration)
            await _call_discord("timeout member", message.author.timeout(until=until, reason=reason))
            results.append(f"Author timed out for {duration} minute(s)")

        if not results:
            results.append("No moderation action was requested.")

        return "; ".join(results) + "."

    return server


def main() -> None:
    """Entry point for running the server from the command line."""

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.WARNING)

    server = create_server()
    transport = os.getenv("MCP_DISCORD_TRANSPORT", "stdio")
    server.run(transport=transport)

