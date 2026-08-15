"""Executable checks for the packaging rules this project has adopted.

Two rules were stated in the README and in pyproject commentary and enforced by
nothing at all. They are now recorded as DesignRules in the project's reflow2
design, marked gate-blocking, and detected here:

  * dependency-light  - pydantic + pyyaml + the standard library, explicitly no NumPy.
  * the lint gate states its own rule set - an explicit ruff `select`, and ruff pinned
    on BOTH sides. This rule exists because of a real incident: ruff 0.16.0 widened the
    DEFAULT rule set and 40 pre-existing findings appeared in files nobody had touched.

These assert the DECLARATION, which is what the rules are about. They are cheap and they
fail loudly when someone adds a dependency or loosens the lint gate.
"""

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # 3.10 - the floor we claim to support, so the check must work here too
    import tomli as tomllib

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

#: Every distribution this package may import at RUNTIME. Dev/test tooling is not
#: covered by the rule and lives in the `dev` extra.
ALLOWED_RUNTIME = {"pydantic", "pyyaml"}

#: Called out by name because the README advertises its absence on the production-RNG
#: path. A generic "not in the allow-list" failure would not say why this one matters.
FORBIDDEN_RUNTIME = {"numpy"}


def _config() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _dist_name(requirement: str) -> str:
    """'pydantic>=2.5' -> 'pydantic'; normalised per PEP 503."""
    head = re.split(r"[\s\[<>=!~;(]", requirement.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", head).lower()


class TestDependencyLight:
    def test_runtime_dependencies_are_exactly_the_allowed_set(self):
        declared = {_dist_name(r) for r in _config()["project"]["dependencies"]}
        assert declared == ALLOWED_RUNTIME, (
            f"runtime dependencies drifted: {sorted(declared)!r}. dndwright is "
            f"dependency-light on purpose - a host embeds it. Adding one is a "
            f"deliberate change to that rule, not a side effect of an import."
        )

    @pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_RUNTIME))
    def test_forbidden_runtime_dependency_absent(self, forbidden):
        declared = {_dist_name(r) for r in _config()["project"]["dependencies"]}
        assert forbidden not in declared, (
            f"{forbidden!r} is a runtime dependency. The README advertises its "
            f"absence; the dice engine is deterministic via the stdlib RNG."
        )

    def test_optional_extras_do_not_smuggle_a_runtime_dependency(self):
        """An extra is fine; an extra that the package imports unconditionally is not."""
        extras = _config()["project"].get("optional-dependencies", {})
        for name, reqs in extras.items():
            for forbidden in FORBIDDEN_RUNTIME:
                if forbidden in {_dist_name(r) for r in reqs}:
                    pytest.fail(
                        f"extra {name!r} pulls in {forbidden!r}. That is only "
                        f"acceptable if nothing outside that extra imports it."
                    )


class TestLintGateStatesItsOwnRules:
    def test_ruleset_is_stated_explicitly(self):
        select = _config().get("tool", {}).get("ruff", {}).get("lint", {}).get("select")
        assert select, (
            "[tool.ruff.lint] select is missing or empty, so the gate inherits ruff's "
            "DEFAULTS. That is what broke main: 0.16.0 widened them and 40 findings "
            "appeared in untouched files. State the rule set explicitly."
        )

    def test_ruff_is_pinned_on_both_sides(self):
        dev = _config()["project"]["optional-dependencies"]["dev"]
        ruff = next((r for r in dev if _dist_name(r) == "ruff"), None)
        assert ruff is not None, "ruff is not declared in the dev extra"
        assert "<" in ruff, (
            f"ruff is not bounded above ({ruff!r}). CI installs this extra fresh on "
            f"every run, so an open-ended spec adopts whatever ruff shipped that "
            f"morning and the gate's meaning changes without a commit."
        )
        assert ">" in ruff or "==" in ruff, (
            f"ruff has no lower bound ({ruff!r}); the explicit rule set needs the "
            f"[tool.ruff.lint] table, which older ruff does not read."
        )
