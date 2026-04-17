"""people — compatibility alias for pacific-solid.

    import people as ps   # equivalent to: import pacific_solid as ps

Prefer `import pacific_solid as ps` in new code. This alias re-exports
the full public API from pacific_solid and is kept for backward
compatibility.
"""

from pacific_solid import *  # noqa: F401,F403
from pacific_solid import __all__, __version__  # noqa: F401
