# Contributing to openscout

Thanks for considering a contribution! This document covers how to get set
up locally, how to run the checks CI will run on your PR, and -- the thing
most people show up here to do -- how to add a brand new sport as a plugin.

## Development setup

```bash
git clone https://github.com/AadiCodes4/openscout.git
cd openscout
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

That installs openscout in editable mode plus the dev dependencies
(`pytest`, `mypy`, `ruff`). Because it's editable, the `openscout` command
and `import openscout` both immediately reflect any source changes you
make -- no reinstall needed.

Sanity-check the install:

```bash
openscout list-sports
# basketball: efg_pct, four_factors, per_lite, ts_pct
# soccer: xg, pass_pct, xt_added
```

## Running the checks

Every PR is checked by the same three commands CI runs (`.github/workflows/ci.yml`):

```bash
ruff check .      # lint
mypy src          # static type-check
pytest -q         # test suite
```

Run all three locally before opening a PR. If `ruff` finds something
auto-fixable, `ruff check . --fix` will apply the fix for you.

### Test expectations

- New metrics need at least one test with a **hand-computed expected
  value** -- work the formula out by hand (or with a throwaway script) and
  assert the function returns that exact number, not just "some plausible
  number." See `tests/test_basketball.py::test_true_shooting_pct_hand_computed`
  for the pattern.
- New plugins need a test proving they're actually discoverable through
  `openscout.plugins.list_sports()` / `get_sport()`, not just directly
  importable.

## Project layout

```
src/openscout/
  __init__.py       # public API surface + __version__
  plugins.py         # the plugin registry/loader -- the Sport protocol lives here
  data.py            # synthetic sample data + JSON/CSV loaders
  cli.py             # argparse-based CLI
  sports/
    basketball.py     # built-in basketball plugin
    soccer.py          # built-in soccer plugin
tests/                # pytest suite, one file per module above
```

## Adding a new sport plugin

This is the part openscout cares most about getting right, so here's a full
worked example: adding a toy **tennis** plugin that computes first-serve
percentage.

### 1. Decide on your plugin's shape

A plugin is any object satisfying the `openscout.plugins.Sport` protocol:

- a `name: str` attribute (a short, unique, lowercase id)
- a `list_metrics() -> list[str]` method
- a `compute(metric_name: str, data: Any) -> float | dict` method

The easiest way to satisfy this is to subclass `openscout.plugins.SportBase`,
which is an `ABC` with those same three members declared abstract. You don't
have to subclass it -- a plain class or even a module-level object with
matching attributes works too, because the check is structural (a
`Protocol`), not nominal -- but `SportBase` is the path of least resistance.

### 2. Write the plugin

This can live in your **own separate package** -- it does not need to be
added to the openscout repository at all. Say you're building
`openscout-tennis`:

```
openscout-tennis/
  pyproject.toml
  src/openscout_tennis/
    __init__.py
    plugin.py
```

`src/openscout_tennis/plugin.py`:

```python
from openscout.plugins import SportBase


class TennisSport(SportBase):
    name = "tennis"

    def list_metrics(self) -> list[str]:
        return ["first_serve_pct"]

    def compute(self, metric_name, data):
        if metric_name != "first_serve_pct":
            raise ValueError(f"tennis plugin has no metric {metric_name!r}")
        made = sum(1 for serve in data if serve["in"])
        return 100.0 * made / len(data)
```

### 3. Register it via entry_points

In `openscout-tennis`'s `pyproject.toml`, declare an entry point in the
`openscout.sports` group, pointing at your plugin class:

```toml
[project.entry-points."openscout.sports"]
tennis = "openscout_tennis.plugin:TennisSport"
```

This is the exact same mechanism openscout's own built-in plugins use --
see this repository's `pyproject.toml`:

```toml
[project.entry-points."openscout.sports"]
basketball = "openscout.sports.basketball:BasketballSport"
soccer = "openscout.sports.soccer:SoccerSport"
```

There is nothing special about being "built in." If you deleted those two
lines and instead shipped `openscout-basketball` and `openscout-soccer` as
separate PyPI packages, openscout's plugin loader would not need a single
line changed to keep finding them.

### 4. Install it and confirm discovery

```bash
pip install -e ./openscout-tennis   # or `pip install openscout-tennis` once published
openscout list-sports
# basketball: efg_pct, four_factors, per_lite, ts_pct
# soccer: xg, pass_pct, xt_added
# tennis: first_serve_pct
```

`openscout.plugins.list_sports()` and `get_sport()` scan the
`openscout.sports` entry_points group at call time via
`importlib.metadata`, so any package installed in the same environment
that declares that group is picked up automatically -- no registration
call, no import, no changes to openscout's source required.

### 5. If you're contributing a plugin *into this repo* instead

Occasionally a sport is common enough that it makes sense to live in
`openscout` itself (as basketball and soccer do). If that's your case:

1. Add `src/openscout/sports/<your_sport>.py` following the pattern in
   `basketball.py` / `soccer.py`, including a module docstring explaining
   each metric's formula and its source/justification.
2. Add the entry point to this repo's `pyproject.toml` under
   `[project.entry-points."openscout.sports"]`.
3. Add `tests/test_<your_sport>.py` with hand-computed expected values for
   every formula.
4. Update `README.md`'s metrics table and `CHANGELOG.md`'s `[Unreleased]`
   section.

## Formula honesty

If you're adding or changing a metric, get the formula right and cite where
it comes from in a docstring or comment. If a metric is a simplification or
a toy version of something with a "real," more rigorous industry
equivalent (as with this project's xG model), say so explicitly in the
docstring and don't imply more precision or calibration than actually
exists.

## Submitting a change

1. Fork the repo and create a branch off `main`.
2. Make your change, with tests.
3. Run `ruff check .`, `mypy src`, and `pytest -q` locally.
4. Open a PR using the template in `.github/PULL_REQUEST_TEMPLATE.md`.

By contributing, you agree your contributions are licensed under this
project's MIT license (see `LICENSE`), and you agree to abide by the
`CODE_OF_CONDUCT.md`.
