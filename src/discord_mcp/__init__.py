# Replace your src/discord_mcp/__init__.py with this:

"""Discord integration for Model Context Protocol."""

from . import integrated_server  # Changed from 'server' to 'integrated_server'
import asyncio
import warnings
import tracemalloc

__version__ = "0.1.0"

def main():
    """Main entry point for the package."""
    # Enable tracemalloc for better debugging
    tracemalloc.start()
    
    # Suppress PyNaCl warning since we don't use voice features
    warnings.filterwarnings('ignore', module='discord.client', message='PyNaCl is not installed')
    
    try:
        # Use the integrated server with all advanced features
        asyncio.run(integrated_server.main())
    except KeyboardInterrupt:
        print("\nShutting down Discord MCP server...")
    except Exception as e:
        print(f"Error running Discord MCP server: {e}")
        raise

# Expose important items at package level
__all__ = ['main', 'integrated_server']