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
    "No Discord token provided. Configure a token via Smithery session config or the DISCORD_TOKEN/discordToken environment "
    "variable."
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
        if not stripped:
            return None

    if any(ch.isspace() for ch in stripped):
        return None

    return stripped or None


def _get_env_config() -> ConfigSchema:
    token: str | None = None
    for env_name in ("DISCORD_TOKEN", "discordToken"):
        candidate = _normalize_token(os.getenv(env_name))
        if candidate is not None:
            token = candidate
            break

    guild_raw: str | None = None
    for env_name in ("DISCORD_DEFAULT_GUILD_ID", "discordDefaultGuildId", "defaultGuildId"):
        value = os.getenv(env_name)
        if value is None:
            continue
        stripped = value.strip()
        if not stripped:
            continue
        guild_raw = stripped
        break

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


async def _ensure_member(guild: discord.Guild, user_id: int) -> discord.Member:
    member = guild.get_member(user_id)
    if member is not None:
        return member
    return await _call_discord("fetch member", guild.fetch_member(user_id))


async def _ensure_role(guild: discord.Guild, role_id: int) -> discord.Role:
    role = guild.get_role(role_id)
    if role is not None:
        return role

    roles = await _call_discord("fetch roles", guild.fetch_roles())
    for role in roles:
        if role.id == role_id:
            return role
    raise DiscordToolError("Role not found in the specified server.")


async def _ensure_category(
    bot: commands.Bot, guild: discord.Guild, category_id: int
) -> discord.CategoryChannel:
    category = guild.get_channel(category_id)
    if isinstance(category, discord.CategoryChannel):
        return category

    fetched = await _call_discord("fetch category", bot.fetch_channel(category_id))
    if isinstance(fetched, discord.CategoryChannel):
        return fetched
    raise DiscordToolError("Provided category_id does not refer to a category.")


def _parse_optional_bool(value: bool | str | int | None, name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    raise DiscordToolError(f"{name} must be a boolean value.")


def _parse_colour(value: str | int | None, *, name: str = "colour") -> discord.Colour | None:
    if value is None:
        return None
    if isinstance(value, discord.Colour):
        return value
    if isinstance(value, int):
        if 0 <= value <= 0xFFFFFF:
            return discord.Colour(value)
        raise DiscordToolError(f"{name} must be between 0 and 0xFFFFFF.")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        lowered = text.lower()
        if lowered in {"default", "none"}:
            return discord.Colour.default()
        if lowered == "random":
            return discord.Colour.random()

        if lowered.startswith("#"):
            lowered = lowered[1:]
        if lowered.startswith("0x"):
            lowered = lowered[2:]

        try:
            numeric = int(lowered, 16)
        except ValueError:
            attr = getattr(discord.Colour, lowered, None)
            if callable(attr):
                try:
                    return attr()
                except TypeError:  # pragma: no cover - defensive guard
                    pass
            raise DiscordToolError(
                f"{name} must be a hex colour code (for example #FF0000) or a known colour name."
            )

        if 0 <= numeric <= 0xFFFFFF:
            return discord.Colour(numeric)
        raise DiscordToolError(f"{name} must be between 0 and 0xFFFFFF.")

    raise DiscordToolError(f"{name} must be specified as a hex string or integer value.")


def _parse_permissions(
    permissions: Sequence[str] | None,
    permissions_value: str | int | None,
) -> discord.Permissions | None:
    if permissions_value is not None:
        try:
            numeric = int(permissions_value)
        except (TypeError, ValueError) as exc:
            raise DiscordToolError("permissions_value must be an integer.") from exc
        if numeric < 0:
            raise DiscordToolError("permissions_value must be non-negative.")
        return discord.Permissions(permissions=numeric)

    if permissions is None:
        return None

    perms = discord.Permissions.none()
    for entry in permissions:
        normalized = str(entry).strip().lower()
        if not normalized:
            continue
        if not hasattr(discord.Permissions, normalized):
            raise DiscordToolError(f"Unknown permission name: {entry}.")
        setattr(perms, normalized, True)
    return perms


def _summarize_permissions(perms: discord.Permissions, *, max_entries: int = 6) -> str:
    allowed = [name.replace("_", " ") for name, value in perms if value]
    if not allowed:
        return "No permissions"
    if len(allowed) > max_entries:
        return ", ".join(allowed[:max_entries]) + ", ..."
    return ", ".join(allowed)


def _format_role(role: discord.Role) -> str:
    colour = f"#{role.colour.value:06X}" if role.colour.value else "default"
    flags: list[str] = []
    if role.managed:
        flags.append("managed")
    if role.hoist:
        flags.append("hoisted")
    if role.mentionable:
        flags.append("mentionable")
    flag_str = f" ({', '.join(flags)})" if flags else ""
    permissions = _summarize_permissions(role.permissions)
    return (
        f"• {role.name} (ID: {role.id}) – Position: {role.position} – Members: {len(role.members)} – "
        f"Colour: {colour}{flag_str}\n  Permissions: {permissions}"
    )


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
            "Interact with Discord using a bot token. Configure `discordToken` (or set the `DISCORD_TOKEN` or "
            "`discordToken` environment variable) and an optional `defaultGuildId` when connecting through Smithery."
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
    async def list_roles(server_id: str | int | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """List all roles defined in the Discord server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        roles = [role for role in guild.roles if role != guild.default_role]
        if not roles:
            return f"{guild.name} has no custom roles."

        lines = [f"**Roles for {guild.name} (excluding @everyone):**"]
        for role in sorted(roles, key=lambda item: item.position, reverse=True):
            lines.append(_format_role(role))

        return "\n".join(lines)

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
    async def pin_message(channel_id: str | int, message_id: str | int, reason: str | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """Pin a message in a text channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))
        await _call_discord("pin message", message.pin(reason=reason))
        return f"Pinned message {message.id} in channel {channel.id}."

    @server.tool()
    async def unpin_message(channel_id: str | int, message_id: str | int, reason: str | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """Unpin a message in a text channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))
        message = await _fetch_message(channel, _require_int(message_id, "message_id"))
        await _call_discord("unpin message", message.unpin(reason=reason))
        return f"Unpinned message {message.id} in channel {channel.id}."

    @server.tool()
    async def bulk_delete_messages(
        channel_id: str | int,
        message_ids: Sequence[str | int] | None = None,
        limit: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Delete multiple recent messages from a channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))

        deleted_count = 0
        if message_ids:
            for mid in message_ids:
                message = await _fetch_message(channel, _require_int(mid, "message_id"))
                await _call_discord("delete message", message.delete(reason=reason))
                deleted_count += 1
        else:
            if limit is None:
                raise DiscordToolError("Provide message_ids or a limit when using bulk_delete_messages.")
            limit = max(1, min(limit, 100))

            try:
                async for message in channel.history(limit=limit, oldest_first=False):
                    await _call_discord("delete message", message.delete(reason=reason))
                    deleted_count += 1
            except discord.DiscordException as exc:
                raise _describe_discord_error("bulk delete messages", exc) from exc

        return f"Deleted {deleted_count} message(s) from channel {channel.id}."

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
            category = await _ensure_category(
                bot, guild, _require_int(category_id, "category_id")
            )

        channel = await _call_discord(
            "create channel",
            guild.create_text_channel(name=name, category=category, topic=topic, reason=reason),
        )
        return f"Created text channel {channel.name} (ID: {channel.id})."

    @server.tool()
    async def create_voice_channel(
        name: str,
        server_id: str | int | None = None,
        category_id: str | int | None = None,
        user_limit: int | None = None,
        bitrate: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create a new voice channel in the specified server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        category = None
        if category_id is not None:
            category = await _ensure_category(
                bot, guild, _require_int(category_id, "category_id")
            )

        kwargs: dict[str, object] = {"name": name}
        if category is not None:
            kwargs["category"] = category

        if user_limit is not None:
            limit_value = max(0, min(int(user_limit), 99))
            kwargs["user_limit"] = limit_value

        if bitrate is not None:
            bitrate_value = int(bitrate)
            max_bitrate = getattr(guild, "bitrate_limit", 96000) or 96000
            bitrate_value = max(8000, min(bitrate_value, max_bitrate))
            kwargs["bitrate"] = bitrate_value

        channel = await _call_discord(
            "create channel",
            guild.create_voice_channel(reason=reason, **kwargs),
        )
        return f"Created voice channel {channel.name} (ID: {channel.id})."

    @server.tool()
    async def create_stage_channel(
        name: str,
        server_id: str | int | None = None,
        category_id: str | int | None = None,
        topic: str | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create a new stage channel for events and announcements."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        category = None
        if category_id is not None:
            category = await _ensure_category(
                bot, guild, _require_int(category_id, "category_id")
            )

        kwargs: dict[str, object] = {"name": name}
        if category is not None:
            kwargs["category"] = category
        if topic is not None:
            kwargs["topic"] = topic

        channel = await _call_discord(
            "create channel",
            guild.create_stage_channel(reason=reason, **kwargs),
        )
        return f"Created stage channel {channel.name} (ID: {channel.id})."

    @server.tool()
    async def create_category(
        name: str,
        server_id: str | int | None = None,
        position: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create a new channel category."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        kwargs: dict[str, object] = {"name": name}
        if position is not None:
            kwargs["position"] = int(position)

        category = await _call_discord(
            "create category",
            guild.create_category(reason=reason, **kwargs),
        )
        return f"Created category {category.name} (ID: {category.id})."

    @server.tool()
    async def update_channel(
        channel_id: str | int,
        name: str | None = None,
        category_id: str | int | None = None,
        position: int | None = None,
        topic: str | None = None,
        nsfw: bool | str | int | None = None,
        slowmode_delay: int | None = None,
        user_limit: int | None = None,
        bitrate: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Update channel settings such as name, topic, and category."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _call_discord(
            "fetch channel", bot.fetch_channel(_require_int(channel_id, "channel_id"))
        )

        updates: dict[str, object] = {}
        if name is not None:
            new_name = name.strip()
            if not new_name:
                raise DiscordToolError("Channel name cannot be empty.")
            updates["name"] = new_name

        if position is not None:
            updates["position"] = int(position)

        if category_id is not None:
            if not hasattr(channel, "guild") or channel.guild is None:
                raise DiscordToolError("Cannot move a channel without an associated guild.")
            category = await _ensure_category(
                bot, channel.guild, _require_int(category_id, "category_id")
            )
            updates["category"] = category

        if topic is not None:
            if isinstance(channel, (discord.TextChannel, discord.StageChannel, discord.ForumChannel)):
                updates["topic"] = topic
            else:
                raise DiscordToolError("Only text, forum, or stage channels support topics.")

        if nsfw is not None:
            nsfw_value = _parse_optional_bool(nsfw, "nsfw")
            if isinstance(channel, (discord.TextChannel, discord.StageChannel, discord.ForumChannel)):
                updates["nsfw"] = nsfw_value
            else:
                raise DiscordToolError("NSFW can only be set on text, forum, or stage channels.")

        if slowmode_delay is not None:
            if isinstance(channel, discord.TextChannel):
                updates["slowmode_delay"] = max(0, min(int(slowmode_delay), 21600))
            else:
                raise DiscordToolError("Slowmode is only supported on text channels.")

        if user_limit is not None:
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                updates["user_limit"] = max(0, min(int(user_limit), 99))
            else:
                raise DiscordToolError("User limit can only be set on voice or stage channels.")

        if bitrate is not None:
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                bitrate_value = int(bitrate)
                max_bitrate = getattr(channel.guild, "bitrate_limit", 96000) or 96000
                updates["bitrate"] = max(8000, min(bitrate_value, max_bitrate))
            else:
                raise DiscordToolError("Bitrate can only be set on voice or stage channels.")

        if not updates:
            raise DiscordToolError("Provide at least one field to update.")

        await _call_discord("update channel", channel.edit(reason=reason, **updates))
        return f"Updated channel {channel.id}."

    @server.tool()
    async def delete_channel(channel_id: str | int, reason: str | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """Delete a Discord channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _call_discord("fetch channel", bot.fetch_channel(_require_int(channel_id, "channel_id")))
        await _call_discord("delete channel", channel.delete(reason=reason))
        return f"Deleted channel {channel_id}."

    @server.tool()
    async def create_invite(
        channel_id: str | int,
        max_age_seconds: int | None = None,
        max_uses: int | None = None,
        temporary: bool | str | int | None = None,
        unique: bool | str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create an invite link for a channel."""

        assert ctx is not None
        bot, _ = await _acquire(ctx)
        channel = await _ensure_channel(bot, _require_int(channel_id, "channel_id"))

        kwargs: dict[str, object] = {}
        if max_age_seconds is not None:
            kwargs["max_age"] = max(0, int(max_age_seconds))
        if max_uses is not None:
            kwargs["max_uses"] = max(0, int(max_uses))
        if temporary is not None:
            kwargs["temporary"] = _parse_optional_bool(temporary, "temporary")
        if unique is not None:
            kwargs["unique"] = _parse_optional_bool(unique, "unique")

        invite = await _call_discord(
            "create invite", channel.create_invite(reason=reason, **kwargs)
        )
        return f"Created invite {invite.url} for channel {channel.id}."

    @server.tool()
    async def list_invites(server_id: str | int | None = None, ctx: Context = None) -> str:  # type: ignore[override]
        """List active invites for a server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        invites = await _call_discord("list invites", guild.invites())
        if not invites:
            return f"No active invites found for {guild.name}."

        lines = [f"**Active invites for {guild.name}:**"]
        for invite in invites:
            inviter = invite.inviter.display_name if invite.inviter else "Unknown"
            expires = _format_timestamp(invite.expires_at) if invite.expires_at else "No expiry"
            usage = f"{invite.uses or 0}/{invite.max_uses or '∞'} uses"
            lines.append(
                f"• {invite.code} – Channel: {getattr(invite.channel, 'name', invite.channel_id)} – "
                f"Inviter: {inviter} – Expires: {expires} – {usage}"
            )

        return "\n".join(lines)

    @server.tool()
    async def create_role(
        name: str,
        server_id: str | int | None = None,
        color: str | int | None = None,
        colour: str | int | None = None,
        hoist: bool | str | int | None = None,
        mentionable: bool | str | int | None = None,
        permissions: Sequence[str] | None = None,
        permissions_value: str | int | None = None,
        unicode_emoji: str | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Create a new role in the specified server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        colour_value = colour if colour is not None else color
        role_colour = _parse_colour(colour_value, name="color") if colour_value is not None else None
        hoist_value = _parse_optional_bool(hoist, "hoist")
        mentionable_value = _parse_optional_bool(mentionable, "mentionable")
        permission_obj = _parse_permissions(permissions, permissions_value)

        kwargs: dict[str, object] = {"name": name}
        if role_colour is not None:
            kwargs["colour"] = role_colour
        if hoist_value is not None:
            kwargs["hoist"] = hoist_value
        if mentionable_value is not None:
            kwargs["mentionable"] = mentionable_value
        if permission_obj is not None:
            kwargs["permissions"] = permission_obj
        if unicode_emoji is not None:
            kwargs["unicode_emoji"] = unicode_emoji

        role = await _call_discord(
            "create role",
            guild.create_role(reason=reason, **kwargs),
        )
        return f"Created role {role.name} (ID: {role.id})."

    @server.tool()
    async def edit_role(
        role_id: str | int,
        server_id: str | int | None = None,
        name: str | None = None,
        color: str | int | None = None,
        colour: str | int | None = None,
        hoist: bool | str | int | None = None,
        mentionable: bool | str | int | None = None,
        permissions: Sequence[str] | None = None,
        permissions_value: str | int | None = None,
        position: int | None = None,
        unicode_emoji: str | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Update the configuration of an existing role."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        role = await _ensure_role(guild, _require_int(role_id, "role_id"))

        updates: dict[str, object] = {}
        if name is not None:
            new_name = name.strip()
            if not new_name:
                raise DiscordToolError("Role name cannot be empty.")
            updates["name"] = new_name

        colour_value = colour if colour is not None else color
        if colour_value is not None:
            updates["colour"] = _parse_colour(colour_value, name="color")

        hoist_value = _parse_optional_bool(hoist, "hoist")
        if hoist_value is not None:
            updates["hoist"] = hoist_value

        mentionable_value = _parse_optional_bool(mentionable, "mentionable")
        if mentionable_value is not None:
            updates["mentionable"] = mentionable_value

        permission_obj = _parse_permissions(permissions, permissions_value)
        if permission_obj is not None:
            updates["permissions"] = permission_obj

        if position is not None:
            updates["position"] = int(position)

        if unicode_emoji is not None:
            updates["unicode_emoji"] = unicode_emoji

        if not updates:
            raise DiscordToolError("Provide at least one field to update for the role.")

        await _call_discord("update role", role.edit(reason=reason, **updates))
        return f"Updated role {role.name} (ID: {role.id})."

    @server.tool()
    async def delete_role(
        role_id: str | int,
        server_id: str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Delete a role from the server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        role = await _ensure_role(guild, _require_int(role_id, "role_id"))
        role_name = role.name
        await _call_discord("delete role", role.delete(reason=reason))
        return f"Deleted role {role_name} (ID: {role.id})."

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

        member = await _ensure_member(guild, _require_int(user_id, "user_id"))
        role = await _ensure_role(guild, _require_int(role_id, "role_id"))

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

        member = await _ensure_member(guild, _require_int(user_id, "user_id"))
        role = await _ensure_role(guild, _require_int(role_id, "role_id"))

        await _call_discord("remove role", member.remove_roles(role, reason=reason))
        return f"Removed role {role.name} from {member.display_name}."

    @server.tool()
    async def kick_member(
        user_id: str | int,
        server_id: str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Kick a member from the server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        member = await _ensure_member(guild, _require_int(user_id, "user_id"))
        display = member.display_name
        await _call_discord("kick member", member.kick(reason=reason))
        return f"Kicked {display} ({member.id}) from {guild.name}."

    @server.tool()
    async def ban_member(
        user_id: str | int,
        server_id: str | int | None = None,
        delete_message_seconds: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Ban a user from the server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        delete_seconds = None
        if delete_message_seconds is not None:
            delete_seconds = max(0, min(int(delete_message_seconds), 604800))

        try:
            member = await _ensure_member(guild, _require_int(user_id, "user_id"))
            target = member
        except DiscordToolError:
            target = await _call_discord(
                "fetch user", bot.fetch_user(_require_int(user_id, "user_id"))
            )

        await _call_discord(
            "ban member",
            guild.ban(target, reason=reason, delete_message_seconds=delete_seconds),
        )
        display = target.display_name if hasattr(target, "display_name") else str(target)
        return f"Banned {display} ({target.id}) from {guild.name}."

    @server.tool()
    async def unban_member(
        user_id: str | int,
        server_id: str | int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Remove a ban for a user."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        user = await _call_discord("fetch user", bot.fetch_user(_require_int(user_id, "user_id")))
        await _call_discord("unban member", guild.unban(user, reason=reason))
        return f"Unbanned {user.display_name} ({user.id}) from {guild.name}."

    @server.tool()
    async def list_bans(
        server_id: str | int | None = None,
        limit: int = 20,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """List banned users for the server."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        limit = max(1, min(limit, 100))
        entries: list[discord.guild.BanEntry] = []
        try:
            async for entry in guild.bans(limit=None):
                entries.append(entry)
                if len(entries) >= limit:
                    break
        except discord.DiscordException as exc:
            raise _describe_discord_error("list bans", exc) from exc

        if not entries:
            return f"No banned users found for {guild.name}."

        lines = [f"**Banned users for {guild.name} (showing {len(entries)}):**"]
        for entry in entries:
            user = entry.user
            reason_text = entry.reason or "No reason provided"
            lines.append(f"• {user.display_name} ({user.id}) – Reason: {reason_text}")

        return "\n".join(lines)

    @server.tool()
    async def timeout_member(
        user_id: str | int,
        server_id: str | int | None = None,
        duration_minutes: int | None = None,
        reason: str | None = None,
        ctx: Context = None,
    ) -> str:  # type: ignore[override]
        """Apply or clear a communication timeout for a member."""

        assert ctx is not None
        bot, config = await _acquire(ctx)
        guild_id = _resolve_guild_id(config, server_id)
        guild = await _ensure_guild(bot, guild_id)

        member = await _ensure_member(guild, _require_int(user_id, "user_id"))
        if duration_minutes is None or duration_minutes <= 0:
            until = None
            action = "Cleared timeout"
        else:
            duration = max(1, int(duration_minutes))
            until = datetime.now(tz=UTC) + timedelta(minutes=duration)
            action = f"Timed out for {duration} minute(s)"

        await _call_discord("timeout member", member.timeout(until=until, reason=reason))
        return f"{action} for {member.display_name} ({member.id})."

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

