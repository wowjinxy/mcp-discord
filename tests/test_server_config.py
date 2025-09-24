from types import SimpleNamespace

import pytest

from discord_mcp.server import ConfigSchema, DiscordToolError, _get_session_config


def _make_ctx(value):
    return SimpleNamespace(session_config=value)


_TOKEN_ENV_VARS = ("DISCORD_TOKEN", "discordToken")
_GUILD_ENV_VARS = ("DISCORD_DEFAULT_GUILD_ID", "discordDefaultGuildId", "defaultGuildId")


def _clear_token_env(monkeypatch):
    for name in _TOKEN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _clear_guild_env(monkeypatch):
    for name in _GUILD_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_config_schema_allows_missing_token():
    config = ConfigSchema.model_validate({})
    assert config.discord_token is None
    assert config.default_guild_id is None


def test_config_schema_ignores_extra_fields():
    config = ConfigSchema.model_validate({
        "discordToken": " token ",
        "defaultGuildId": 123,
        "unexpected": "value",
    })

    assert config.discord_token == " token "
    assert config.default_guild_id == 123
    assert not hasattr(config, "unexpected")


def test_initialize_allows_env_token(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("DISCORD_TOKEN", " env-token ")

    validated = ConfigSchema.model_validate({})
    resolved = _get_session_config(_make_ctx(validated))

    assert resolved.discord_token == "env-token"


def test_initialize_allows_env_token_alias(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("discordToken", " env-token ")

    validated = ConfigSchema.model_validate({})
    resolved = _get_session_config(_make_ctx(validated))

    assert resolved.discord_token == "env-token"


def test_env_token_alias_used_when_primary_blank(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("DISCORD_TOKEN", "   ")
    monkeypatch.setenv("discordToken", "env-token")

    resolved = _get_session_config(_make_ctx({}))

    assert resolved.discord_token == "env-token"


def test_get_session_config_prefers_explicit_token(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.setenv("DISCORD_DEFAULT_GUILD_ID", "987654")

    resolved = _get_session_config(
        _make_ctx({"discordToken": " session-token ", "defaultGuildId": 42})
    )

    assert resolved.discord_token == "session-token"
    assert resolved.default_guild_id == 42


def test_get_session_config_uses_env_default(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.setenv("DISCORD_DEFAULT_GUILD_ID", "12345")

    resolved = _get_session_config(_make_ctx({}))

    assert resolved.discord_token == "env-token"
    assert resolved.default_guild_id == 12345


def test_get_session_config_uses_env_default_alias(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("discordToken", "env-token")
    monkeypatch.setenv("discordDefaultGuildId", "54321")

    resolved = _get_session_config(_make_ctx({}))

    assert resolved.discord_token == "env-token"
    assert resolved.default_guild_id == 54321


def test_get_session_config_requires_token(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)

    with pytest.raises(DiscordToolError):
        _get_session_config(_make_ctx({}))


def test_get_session_config_strips_bot_prefix(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)

    resolved = _get_session_config(_make_ctx({"discordToken": " Bot session-token"}))

    assert resolved.discord_token == "session-token"


def test_get_session_config_strips_quotes(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)

    resolved = _get_session_config(
        _make_ctx({"discordToken": ' "quoted-session-token" '})
    )

    assert resolved.discord_token == "quoted-session-token"


def test_get_session_config_ignores_tokens_with_whitespace(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")

    resolved = _get_session_config(
        _make_ctx({"discordToken": " invalid token contents "})
    )

    assert resolved.discord_token == "env-token"


def test_get_session_config_rejects_invalid_tokens(monkeypatch):
    _clear_token_env(monkeypatch)
    _clear_guild_env(monkeypatch)

    with pytest.raises(DiscordToolError):
        _get_session_config(_make_ctx({"discordToken": "not a real token"}))
