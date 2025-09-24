# Discord MCP Server

[![smithery badge](https://smithery.ai/badge/@wowjinxy/mcp-discord-manager)](https://smithery.ai/server/@wowjinxy/mcp-discord-manager)
A Model Context Protocol (MCP) server that provides Discord integration capabilities to MCP clients like Claude Desktop.

<a href="https://glama.ai/mcp/servers/wvwjgcnppa"><img width="380" height="200" src="https://glama.ai/mcp/servers/wvwjgcnppa/badge" alt="mcp-discord MCP server" /></a>

## Available Tools

### Server Information
- `list_servers`: List available servers
- `get_server_info`: Get detailed server information
- `get_channels`: List channels in a server
- `list_roles`: View all roles in a server
- `list_members`: List server members and their roles
- `list_invites`: Display active invite links
- `list_bans`: Show banned users
- `get_user_info`: Get detailed information about a user

### Message Management
- `send_message`: Send a message to a channel
- `read_messages`: Read recent message history
- `add_reaction`: Add a reaction to a message
- `add_multiple_reactions`: Add multiple reactions to a message
- `remove_reaction`: Remove a reaction from a message
- `pin_message`: Pin a message in a channel
- `unpin_message`: Unpin a pinned message
- `bulk_delete_messages`: Remove batches of recent messages
- `moderate_message`: Delete messages and timeout users

### Channel Management
- `create_text_channel`: Create a new text channel
- `create_voice_channel`: Create a new voice channel
- `create_stage_channel`: Create a stage channel for events
- `create_category`: Create a channel category
- `update_channel`: Modify channel settings
- `delete_channel`: Delete an existing channel
- `create_invite`: Generate invite links for channels

### Role Management
- `create_role`: Create new roles
- `edit_role`: Update existing roles
- `delete_role`: Remove roles
- `add_role`: Add a role to a user
- `remove_role`: Remove a role from a user

### Member Management
- `kick_member`: Remove a member from the server
- `ban_member`: Ban a member and optionally delete recent messages
- `unban_member`: Lift a ban for a user
- `timeout_member`: Apply or clear communication timeouts

## Installation

1. Set up your Discord bot:
   - Create a new application at [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a bot and copy the token
   - Enable required privileged intents:
     - MESSAGE CONTENT INTENT
     - PRESENCE INTENT
     - SERVER MEMBERS INTENT
   - Invite the bot to your server using OAuth2 URL Generator

2. Clone and install the package:
```bash
# Clone the repository
git clone https://github.com/wowjinxy/mcp-discord.git
cd mcp-discord

# Create and activate virtual environment
uv venv
.venv\Scripts\activate # On macOS/Linux, use: source .venv/bin/activate

### If using Python 3.13+ - install audioop library: `uv pip install audioop-lts`

# Install the package
uv pip install -e .
```

3. Configure Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS) so it runs the installed entry point via `uv`. Provide your Discord token using either the MCP session configuration or the `DISCORD_TOKEN`/`discordToken` environment variable:
```json
    "discord": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\PATH\\TO\\mcp-discord",
        "run",
        "mcp-discord"
      ],
      "session_config": {
        "discordToken": "your_bot_token"
      }
    }
```

   Alternatively, export the token before starting Claude Desktop and omit the `session_config` block:

```bash
export DISCORD_TOKEN=your_bot_token
## or use the camelCase environment name supported by some clients
export discordToken=your_bot_token
```

### Installing via Smithery

To install Discord Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@wowjinxy/mcp-discord-manager), ensure you supply the Discord token through your MCP client configuration (for example by setting `discordToken` in the session config) or by exporting `DISCORD_TOKEN`/`discordToken` before starting the client:

```bash
npx -y @smithery/cli install @wowjinxy/mcp-discord-manager --client claude
```

## License

MIT License - see LICENSE file for details.
