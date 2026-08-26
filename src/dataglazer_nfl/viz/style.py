"""The @dataglazer chart theme.

`apply_style()` replaces the fragile `plt.style.use("../templates/...")` that
notebooks used to carry: it resolves the stylesheet from the installed package
rather than from the caller's working directory, so a notebook runs the same
from any cwd.

Fonts are expected to be installed on the system. The stylesheet names a
fallback chain (`Baloo 2, Poppins, DejaVu Sans, Arial`), so a missing face
degrades quietly rather than erroring — use `is_font_active()` when that
matters.
"""

from __future__ import annotations

from dataglazer_nfl.config import STYLE_FILE


def apply_style() -> None:
    """Apply the dataglazer stylesheet globally."""
    import matplotlib.pyplot as plt

    plt.style.use(STYLE_FILE)


def is_font_active() -> bool:
    """True when matplotlib resolved the preferred font rather than a fallback.

    Worth asserting before exporting: matplotlib substitutes silently, and
    DejaVu Sans is close enough to miss in a thumbnail.
    """
    from matplotlib import font_manager
    from matplotlib import pyplot as plt

    wanted = plt.rcParams["font.sans-serif"][0]
    return font_manager.FontProperties(family=wanted).get_name() == wanted
