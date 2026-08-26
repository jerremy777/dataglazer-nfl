"""Structural guarantees the layout depends on."""

import subprocess
import sys

from dataglazer_nfl import config


def test_proj_root_is_the_repo_root():
    assert (config.PROJ_ROOT / "pyproject.toml").is_file()
    assert (config.PROJ_ROOT / "src" / "dataglazer_nfl").is_dir()


def test_cache_lives_under_data_not_at_the_repo_root():
    assert config.CACHE_DIR is not None
    assert config.CACHE_DIR.is_relative_to(config.DATA_DIR)
    assert not (config.PROJ_ROOT / ".espn_cache").exists()


def test_stylesheet_ships_with_the_package():
    assert config.STYLE_FILE.is_file()
    assert "font.sans-serif" in config.STYLE_FILE.read_text()


def test_nested_mcp_package_does_not_shadow_the_mcp_library():
    """The whole reason the package is `dataglazer_nfl.mcp` and not `mcp`."""
    import mcp.server.fastmcp

    import dataglazer_nfl.mcp

    assert "site-packages" in mcp.__file__
    assert dataglazer_nfl.mcp.__name__ == "dataglazer_nfl.mcp"


def test_client_layer_never_imports_pandas():
    """What keeps the MCP server a two-dependency install.

    Run in a subprocess because the test session itself has pandas loaded.
    """
    code = (
        "import sys; from dataglazer_nfl.clients import espn; "
        "heavy = {'pandas', 'numpy', 'matplotlib', 'torch', 'polars'} & set(sys.modules); "
        "print(sorted(heavy))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "[]", f"client layer pulled in heavyweight deps: {out}"
