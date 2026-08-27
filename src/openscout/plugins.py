"""Plugin registry and loading machinery for openscout.

openscout's notion of a "sport" is a plugin: an object that implements the
:class:`Sport` protocol and is advertised through the standard Python
``importlib.metadata`` entry_points mechanism under the group name
``"openscout.sports"``.

This is exactly how openscout's own built-in basketball and soccer support
is wired up (see ``pyproject.toml``'s ``[project.entry-points."openscout.sports"]``
table) -- there is no special-casing of the built-ins anywhere in this
module. A third-party package can add a brand new sport to openscout simply
by declaring the same entry point group in its own packaging metadata and
installing it alongside openscout. No changes to openscout's source are
required.

Typical usage
-------------

    from openscout.plugins import get_sport, list_sports

    list_sports()                       # -> ["basketball", "soccer", ...]
    sport = get_sport("basketball")
    sport.list_metrics()                # -> ["ts_pct", "efg_pct", ...]
    sport.compute("ts_pct", box_score)  # -> 0.612

See CONTRIBUTING.md for a full walkthrough of writing and registering a new
sport plugin.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import metadata as importlib_metadata
from typing import Any, Protocol, runtime_checkable

#: The entry_points group that openscout sport plugins must register under.
ENTRY_POINT_GROUP = "openscout.sports"


@runtime_checkable
class Sport(Protocol):
    """The interface every openscout sport plugin must satisfy.

    A plugin can be implemented either by subclassing :class:`SportBase`
    (recommended -- it gives you a working ``__init__`` and repr for free)
    or by writing a plain class/module that happens to expose the same
    three members. Both are valid because this is a :class:`typing.Protocol`
    rather than a required base class.
    """

    #: A short, unique, lowercase identifier, e.g. "basketball".
    name: str

    def list_metrics(self) -> list[str]:
        """Return the list of metric names this plugin knows how to compute."""
        ...

    def compute(self, metric_name: str, data: Any) -> Any:
        """Compute ``metric_name`` from ``data`` and return a float or dict."""
        ...


class SportBase(ABC):
    """Convenience abstract base class for building a :class:`Sport` plugin.

    Subclassing this is optional -- anything satisfying the ``Sport``
    protocol works -- but it is the easiest way to get a well-behaved
    plugin with minimal boilerplate.
    """

    name: str = ""

    @abstractmethod
    def list_metrics(self) -> list[str]:
        """Return the list of metric names this plugin can compute."""
        raise NotImplementedError

    @abstractmethod
    def compute(self, metric_name: str, data: Any) -> Any:
        """Compute ``metric_name`` from ``data``."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r}>"


class SportNotFoundError(KeyError):
    """Raised when a requested sport plugin cannot be located."""


class UnknownMetricError(ValueError):
    """Raised when a plugin is asked to compute a metric it does not know."""


class PluginRegistry:
    """Holds a mapping of sport name -> instantiated :class:`Sport` plugin.

    Plugins can be added two ways:

    1. Automatically, via :meth:`discover`, which reads the
       ``"openscout.sports"`` entry_points group from every installed
       package (this is how ``pip install``-ed plugins are found).
    2. Manually, via :meth:`register`, which is handy for tests or for
       registering a plugin instance at runtime without packaging it.
    """

    def __init__(self) -> None:
        self._sports: dict[str, Sport] = {}
        self._discovered = False

    def register(self, sport: Sport, *, overwrite: bool = True) -> None:
        """Register a plugin instance (or class) under ``sport.name``.

        If ``sport`` is a class rather than an instance, it is instantiated
        with no arguments first.
        """
        if isinstance(sport, type):
            sport = sport()
        if not isinstance(sport, Sport):
            raise TypeError(
                f"{sport!r} does not implement the openscout Sport protocol "
                "(needs .name, .list_metrics(), .compute())"
            )
        if not overwrite and sport.name in self._sports:
            return
        self._sports[sport.name] = sport

    def discover(self, *, force: bool = False) -> None:
        """Populate the registry from installed entry_points.

        Safe to call multiple times; subsequent calls are no-ops unless
        ``force=True``, which re-scans and re-registers everything.
        """
        if self._discovered and not force:
            return

        selected = importlib_metadata.entry_points(group=ENTRY_POINT_GROUP)

        for entry_point in selected:
            plugin_cls = entry_point.load()
            plugin = plugin_cls() if isinstance(plugin_cls, type) else plugin_cls
            self.register(plugin, overwrite=False)

        self._discovered = True

    def get(self, name: str) -> Sport:
        """Look up a registered plugin by name, discovering entry_points first."""
        self.discover()
        try:
            return self._sports[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._sports)) or "(none registered)"
            raise SportNotFoundError(
                f"No sport plugin named {name!r} is registered. "
                f"Available sports: {available}"
            ) from exc

    def list_names(self) -> list[str]:
        """Return the sorted names of all currently registered plugins."""
        self.discover()
        return sorted(self._sports)

    def clear(self) -> None:
        """Remove all registered plugins and reset discovery state.

        Primarily useful in tests that want a clean registry.
        """
        self._sports.clear()
        self._discovered = False


#: The process-wide default registry used by the module-level convenience
#: functions below and by the CLI.
default_registry = PluginRegistry()


def register_sport(sport: Sport, *, overwrite: bool = True) -> None:
    """Register a sport plugin instance/class with the default registry."""
    default_registry.register(sport, overwrite=overwrite)


def get_sport(name: str) -> Sport:
    """Fetch a registered sport plugin by name from the default registry."""
    return default_registry.get(name)


def list_sports() -> list[str]:
    """List the names of all sport plugins visible to the default registry."""
    return default_registry.list_names()
