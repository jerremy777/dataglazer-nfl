"""The shared FastMCP instance.

Kept in its own module so the tool modules can decorate against it without
importing `server`, which imports them.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dataglazer-nfl")
