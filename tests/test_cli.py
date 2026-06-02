"""CLI smoke tests — each subcommand runs and returns the right exit code."""

import json

import pytest

from dndwright.cli import main

CHAR = {
    "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                       "intelligence": 18, "wisdom": 12, "charisma": 10},
    "class_data": {"class_name": "wizard"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 5,
}


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "dndwright" in capsys.readouterr().out


def test_eval_from_file(tmp_path, capsys):
    f = tmp_path / "c.json"
    f.write_text(json.dumps(CHAR))
    assert main(["eval", str(f)]) == 0
    sheet = json.loads(capsys.readouterr().out)
    assert sheet["proficiency_bonus"] == 3


def test_eval_from_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(CHAR)))
    assert main(["eval", "-", "--compact"]) == 0
    out = capsys.readouterr().out
    assert "\n" not in out.strip()  # compact = single line
    assert json.loads(out)["proficiency_bonus"] == 3


def test_graph_mermaid(capsys):
    assert main(["graph", "--format", "mermaid"]) == 0
    assert capsys.readouterr().out.startswith("graph TD")


def test_graph_dot(capsys):
    assert main(["graph", "--format", "dot"]) == 0
    assert capsys.readouterr().out.startswith("digraph ruleset {")


def test_content_list(capsys):
    assert main(["content"]) == 0
    out = capsys.readouterr().out
    assert "magic_items" in out


def test_content_names(capsys):
    assert main(["content", "classes", "--names"]) == 0
    assert capsys.readouterr().out.strip()  # non-empty list of names


def test_content_unknown_category(capsys):
    assert main(["content", "nope"]) == 2
    assert "unknown category" in capsys.readouterr().err


def test_eval_strict_rejects_bad_input(tmp_path, capsys):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"level": 0}))
    assert main(["eval", str(f), "--strict"]) == 1
    assert "problem" in capsys.readouterr().err


def test_validate_builtin(capsys):
    assert main(["validate"]) == 0
    assert "OK" in capsys.readouterr().out


def test_bad_json_returns_error_code(tmp_path, capsys):
    f = tmp_path / "bad.json"
    f.write_text("{not json")
    assert main(["eval", str(f)]) == 2
    assert "error" in capsys.readouterr().err


def test_eval_non_dict_json_is_clean_error(tmp_path, capsys):
    # A JSON list (or number/string) must not crash with a raw AttributeError.
    f = tmp_path / "list.json"
    f.write_text("[1, 2, 3]")
    assert main(["eval", str(f)]) == 1
    err = capsys.readouterr().err
    assert "JSON object" in err
    assert "Traceback" not in err


def test_validate_invalid_ruleset_is_clean_error(tmp_path, capsys):
    # Valid JSON that isn't a well-formed Ruleset → clean error, not a pydantic traceback.
    f = tmp_path / "rs.json"
    f.write_text('{"id": "x"}')  # missing required fields (name, nodes)
    assert main(["validate", str(f)]) == 2
    err = capsys.readouterr().err
    assert "invalid ruleset" in err
    assert "Traceback" not in err
