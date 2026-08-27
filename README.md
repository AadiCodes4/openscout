# openscout

[![CI](https://github.com/AadiCodes4/openscout/actions/workflows/ci.yml/badge.svg)](https://github.com/AadiCodes4/openscout/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A sports analytics library and CLI for Python. Basketball and soccer are built in, but the point of the project is really the plugin system underneath them: both sports are registered through the same `importlib.metadata` entry-points mechanism a third-party package would use to add a new one. There's no `if sport == "basketball"` chain hiding in the loader.

Sample data is generated on the fly with generic names ("Player A", "Team X") — no real players, teams, or historical stats anywhere in here. The soccer `xg` metric is a hand-tuned toy model, not anything calibrated against real shot data.

## Install

```bash
git clone https://github.com/AadiCodes4/openscout.git
cd openscout
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

No runtime dependencies — the CLI is plain `argparse` on purpose, to keep install friction low. For linting/type-checking/tests, install the dev extra instead:

```bash
pip install -e ".[dev]"
```

## CLI

```bash
openscout list-sports

openscout demo --sport basketball
openscout demo --sport basketball --metric four_factors
openscout demo --sport soccer --metric xg

openscout analyze --sport basketball --metric ts_pct --input box_score.json
openscout analyze --sport soccer --metric pass_pct --input passes.csv
```

`--input` takes either a `.json` file (single object or array of objects) or a `.csv` file — numeric-looking fields get coerced automatically.

## Library

```python
from openscout.plugins import get_sport

basketball = get_sport("basketball")
basketball.compute("ts_pct", {"pts": 25, "fga": 18, "fta": 6})
# 0.6056201550387597

soccer = get_sport("soccer")
soccer.compute("xg", {"distance": 11.0, "angle": 40.0, "body_part": "foot", "situation": "open_play"})
# 0.3295988401911314
```

## Metrics

**Basketball** (`openscout.sports.basketball`)

| metric | formula | notes |
| --- | --- | --- |
| `ts_pct` | `PTS / (2 * (FGA + 0.44 * FTA))` | True Shooting % |
| `efg_pct` | `(FG + 0.5 * FG3) / FGA` | Effective FG% |
| `four_factors` | eFG%, TOV%, ORB%, FT rate | Dean Oliver's Four Factors. ORB% needs an `opp_drb` field |
| `per_lite` | Game-Score-style composite | not real pace/league-adjusted PER, just inspired by it |

**Soccer** (`openscout.sports.soccer`)

| metric | notes |
| --- | --- |
| `xg` | logistic curve over distance/angle/body part/situation — a teaching toy, not a real calibrated xG model |
| `pass_pct` | completed / attempted |
| `xt_added` | end-zone value minus start-zone value on a fixed 12x8 pitch grid, loosely inspired by expected-threat models |

All metrics accept a single box-score/shot dict or a list of them (summed field-by-field first).

## Adding a sport

You don't fork or touch openscout's source. Implement the `Sport` protocol in your own package:

```python
# my_package/plugin.py
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

```toml
# my_package's pyproject.toml
[project.entry-points."openscout.sports"]
tennis = "my_package.plugin:TennisSport"
```

Install your package alongside openscout and it just shows up:

```bash
$ openscout list-sports
basketball: efg_pct, four_factors, per_lite, ts_pct
soccer: xg, pass_pct, xt_added
tennis: first_serve_pct
```

`openscout.plugins.register_sport()` also lets you register a plugin instance programmatically, without any packaging at all — useful for quick prototyping. See `CONTRIBUTING.md` for the full walkthrough.

## Output

Captured from an actual run in this repo's dev environment:

```
$ openscout demo --sport basketball
{
  "player": "Player A", "pts": 7.0, "fg": 3.0, "fga": 18.0, "fg3": 0.0,
  "fg3a": 0.0, "ft": 1.0, "fta": 3.0, "orb": 1.0, "drb": 1.0, "ast": 10.0,
  "stl": 4.0, "blk": 0.0, "tov": 4.0, "pf": 3.0, "min": 16.0, "opp_drb": 10.0
}
ts_pct result: 0.18115942028985507

$ pytest -q
44 passed in 0.11s
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
mypy src
pytest -q
```

## Contributing

New metrics, new sport plugins (usually better as their own package, see above), bug fixes, docs — all welcome. Read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` first.

## License

MIT — see [LICENSE](LICENSE).
