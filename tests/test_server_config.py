from types import SimpleNamespace

import pytest

from discord_mcp.server import ConfigSchema, DiscordToolError, _get_session_config


def _make_ctx(value):
    return SimpleNamespace(session_config=value)


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
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_DEFAULT_GUILD_ID", raising=False)
    monkeypatch.setenv("DISCORD_TOKEN", " env-token ")

    validated = ConfigSchema.model_validate({})
    resolved = _get_session_config(_make_ctx(validated))

    assert resolved.discord_token == "env-token"


def test_get_session_config_prefers_explicit_token(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.setenv("DISCORD_DEFAULT_GUILD_ID", "987654")

    resolved = _get_session_config(
        _make_ctx({"discordToken": " session-token ", "defaultGuildId": 42})
    )

    assert resolved.discord_token == "session-token"
    assert resolved.default_guild_id == 42


def test_get_session_config_uses_env_default(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.setenv("DISCORD_DEFAULT_GUILD_ID", "12345")

    resolved = _get_session_config(_make_ctx({}))

    assert resolved.discord_token == "env-token"
    assert resolved.default_guild_id == 12345


def test_get_session_config_requires_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_DEFAULT_GUILD_ID", raising=False)

    with pytest.raises(DiscordToolError):
        _get_session_config(_make_ctx({}))
