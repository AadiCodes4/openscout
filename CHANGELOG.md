# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Nothing yet.

## [0.1.0] - 2026-08-27

### Added

- Initial public release of openscout.
- Plugin architecture (`openscout.plugins`) that discovers "sport" plugins
  through the `openscout.sports` `importlib.metadata` entry_points group,
  plus a `Sport` protocol / `SportBase` ABC that plugins implement.
- Built-in **basketball** plugin (`openscout.sports.basketball`) with
  True Shooting %, Effective Field Goal %, Dean Oliver's Four Factors, and
  a simplified "PER-lite" (Game-Score-inspired) productivity composite.
- Built-in **soccer** plugin (`openscout.sports.soccer`) with a simplified
  toy Expected Goals (xG) model, pass completion %, and a simplified
  zone-based "expected threat"-lite metric.
- Synthetic, clearly-fabricated sample data generators and JSON/CSV
  loaders for user-supplied data (`openscout.data`).
- `openscout` command-line interface (`list-sports`, `analyze`, `demo`).
- Full pytest suite, including hand-computed expected values for the core
  formulas and end-to-end plugin discovery tests.
- GitHub Actions CI (lint, type-check, test across Python 3.10-3.12),
  issue/PR templates, contributing guide, and Contributor Covenant code of
  conduct.

[Unreleased]: https://github.com/AadiCodes4/openscout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AadiCodes4/openscout/releases/tag/v0.1.0
