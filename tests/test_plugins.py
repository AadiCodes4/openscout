"""Tests for the plugin registry/loader itself.

These are the most important tests in the project: they prove the
plugin architecture actually works end-to-end via real
``importlib.metadata`` entry_points, not just in theory.
"""

from __future__ import annotations

from typing import Any

import pytest

from openscout.plugins import (
    PluginRegistry,
    Sport,
    SportBase,
    SportNotFoundError,
    UnknownMetricError,
    get_sport,
    list_sports,
    register_sport,
)


def test_builtin_sports_are_discovered_via_real_entry_points():
    """basketball & soccer must be found through the *actual* installed
    entry_points metadata declared in pyproject.toml -- not hardcoded."""
    names = list_sports()
    assert "basketball" in names
    assert "soccer" in names


def test_get_sport_returns_working_plugin_instances():
    basketball = get_sport("basketball")
    assert basketball.name == "basketball"
    assert "ts_pct" in basketball.list_metrics()

    soccer = get_sport("soccer")
    assert soccer.name == "soccer"
    assert "xg" in soccer.list_metrics()


def test_get_sport_unknown_name_raises_sport_not_found_error():
    with pytest.raises(SportNotFoundError):
        get_sport("cricket")


def test_fresh_registry_discovers_the_same_entry_points_independently():
    registry = PluginRegistry()
    # Nothing has been registered manually, and discover() hasn't run yet.
    assert registry._sports == {}
    registry.discover()
    assert "basketball" in registry.list_names()
    assert "soccer" in registry.list_names()


class _FakeSport(SportBase):
    """A minimal third-party-style plugin used to test manual registration."""

    name = "handball"

    def list_metrics(self) -> list[str]:
        return ["goals_per_game"]

    def compute(self, metric_name: str, data: Any) -> Any:
        if metric_name != "goals_per_game":
            raise UnknownMetricError(metric_name)
        return sum(row["goals"] for row in data) / len(data)


def test_register_sport_at_runtime_without_entry_points():
    """A plugin doesn't strictly need packaging/entry_points to be usable --
    register_sport() lets you add one programmatically too (handy for tests
    and for prototyping a plugin before publishing it)."""
    registry = PluginRegistry()
    registry.register(_FakeSport())
    # list_names()/get() also trigger entry_point discovery, so the builtin
    # sports show up alongside our manually registered one -- that's fine,
    # the point here is just that manual registration works without any
    # packaging/entry_points machinery involved.
    assert "handball" in registry.list_names()

    handball = registry.get("handball")
    assert handball.compute("goals_per_game", [{"goals": 2}, {"goals": 4}]) == pytest.approx(3.0)


def test_register_sport_accepts_a_class_and_instantiates_it():
    registry = PluginRegistry()
    registry.register(_FakeSport)
    assert registry.get("handball").name == "handball"


def test_register_sport_rejects_objects_that_do_not_satisfy_the_protocol():
    registry = PluginRegistry()
    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]


def test_register_respects_overwrite_false():
    registry = PluginRegistry()
    registry.register(_FakeSport())

    class _OtherFakeSport(SportBase):
        name = "handball"

        def list_metrics(self) -> list[str]:
            return ["different"]

        def compute(self, metric_name: str, data: Any) -> Any:
            return None

    registry.register(_OtherFakeSport(), overwrite=False)
    assert registry.get("handball").list_metrics() == ["goals_per_game"]


def test_default_registry_register_sport_module_level_helper():
    register_sport(_FakeSport())
    try:
        assert "handball" in list_sports()
        assert get_sport("handball").name == "handball"
    finally:
        from openscout.plugins import default_registry

        default_registry._sports.pop("handball", None)


def test_sport_protocol_is_runtime_checkable():
    basketball = get_sport("basketball")
    assert isinstance(basketball, Sport)
    assert isinstance(_FakeSport(), Sport)
    assert not isinstance(object(), Sport)
