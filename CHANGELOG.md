# Changelog

All notable changes to dndwright are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

**Public API** = the names exported in `dndwright.__all__` (pinned by
`tests/test_api_contract.py`). While the version is `0.x`, minor versions may make
breaking changes; these will always be noted here.

## [Unreleased]

## [0.1.0] — 2026-06-01

Initial release. The D&D 5e (2024) rules & character-computation engine, extracted
from a working application.

### Added
- `evaluate_character(data) -> dict` — one-call evaluation: character data in,
  computed sheet out (ability modifiers, proficiency, saves, spell DC/attack, HP,
  AC, initiative, …).
- The computation engine: `DND_5E_2024_RULESET` (a 135-node DAG), `evaluate`,
  `assemble_character_inputs`, `apply_modifiers`, and the `Ruleset` / `ComputationNode`
  / `FormulaSpec` / `NodeType` schema — formulas as data, not code.
- Neutral adapters: `character_data_to_inputs`, `computed_values_to_sheet`.
- Typed component models under `dndwright.rules.components`
  (`ClassMechanics`, `SpeciesMechanics`, …) and SRD-derived rules tables.

Pure (pydantic + stdlib); no application/framework coupling. Rules content derives
from the SRD 5.2 (CC-BY-4.0); see NOTICE.

[Unreleased]: https://github.com/sligara7/dndwright/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sligara7/dndwright/releases/tag/v0.1.0
