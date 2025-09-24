import pytest

from discord_mcp.server import (
    DiscordToolError,
    _parse_colour,
    _parse_optional_bool,
    _parse_permissions,
)
from discord_mcp.utils import parse_permissions


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        ("true", True),
        ("NO", False),
        (1, True),
        (0, False),
        (None, None),
    ],
)
def test_parse_optional_bool_valid(value, expected):
    assert _parse_optional_bool(value, "test") == expected


@pytest.mark.parametrize("value", ["maybe", 2, object()])
def test_parse_optional_bool_invalid(value):
    with pytest.raises(DiscordToolError):
        _parse_optional_bool(value, "test")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("#FF0000", 0xFF0000),
        ("0x00ff00", 0x00FF00),
        ("default", 0x000000),
        (16711935, 0xFF00FF),
    ],
)
def test_parse_colour_valid(value, expected):
    colour = _parse_colour(value, name="color")
    assert colour is not None
    assert colour.value == expected


def test_parse_colour_named():
    colour = _parse_colour("blurple", name="color")
    assert colour is not None
    # discord.py's blurple constant is 0x5865F2
    assert colour.value == 0x5865F2


@pytest.mark.parametrize("value", ["not-a-colour", -1])
def test_parse_colour_invalid(value):
    with pytest.raises(DiscordToolError):
        _parse_colour(value, name="color")


def test_parse_permissions_from_list():
    perms = _parse_permissions(["manage_roles", "kick_members"], None)
    assert perms is not None
    assert perms.manage_roles and perms.kick_members
    assert not perms.administrator


def test_parse_permissions_accepts_common_aliases():
    perms = _parse_permissions(["Admin", "Manage Channels", "manage-roles"], None)
    assert perms is not None
    assert perms.administrator
    assert perms.manage_channels
    assert perms.manage_roles


def test_parse_permissions_from_value():
    perms = _parse_permissions(None, "1049600")
    assert perms is not None
    assert isinstance(perms.value, int)


def test_parse_permissions_unknown_name():
    with pytest.raises(DiscordToolError):
        _parse_permissions(["not_a_permission"], None)


def test_parse_permissions_none():
    assert _parse_permissions(None, None) is None


def test_utils_parse_permissions_alias():
    perms = parse_permissions(["Admin"])
    assert perms.administrator
