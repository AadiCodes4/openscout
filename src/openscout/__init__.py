"""openscout: a pluggable sports analytics library and CLI.

openscout ships built-in analytics for basketball and soccer, but its core
idea is a plugin architecture: any Python package can register a new
"sport" (a bundle of named metrics computed from box-score-like input) by
declaring an ``openscout.sports`` entry point. See :mod:`openscout.plugins`
and CONTRIBUTING.md for details.
"""

from __future__ import annotations

from .plugins import (
    Sport,
    SportBase,
    SportNotFoundError,
    UnknownMetricError,
    get_sport,
    list_sports,
    register_sport,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Sport",
    "SportBase",
    "SportNotFoundError",
    "UnknownMetricError",
    "register_sport",
    "get_sport",
    "list_sports",
]
