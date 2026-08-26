"""Data-fetching clients. Each returns plain dicts and lists — never DataFrames,
so that importing one never drags a heavyweight dependency into the MCP server.
"""
