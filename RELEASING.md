# Releasing dndwright

How a new version of dndwright is cut and published to [PyPI](https://pypi.org/project/dndwright/).

## How publishing works

- **Build backend:** hatchling. **Distribution:** [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token or password is stored anywhere; PyPI verifies the repo + workflow + environment.
- **Workflow:** [`.github/workflows/publish.yml`](.github/workflows/publish.yml). It builds the sdist + wheel and uploads them. It triggers on:
  - `release: published` — i.e. **publishing a GitHub Release** (the normal path), **or**
  - `workflow_dispatch` — a manual run that publishes whatever version is in `pyproject.toml` on `main`.
- A plain `git push` of a commit or a tag does **not** publish. Publishing only happens when a GitHub Release is published (or you manually dispatch the workflow). This gives a safe runway: you can bump, tag, and push, and nothing reaches PyPI until you create the Release.

> ⚠️ **PyPI uploads are immutable.** A version number (e.g. `0.4.0`) can be uploaded exactly once and can never be re-uploaded or overwritten — only yanked. Get the version and the build right before creating the Release.

## The version lives in two places (keep them in lockstep)

1. `pyproject.toml` → `version = "X.Y.Z"`
2. `src/dndwright/__init__.py` → `__version__ = "X.Y.Z"`

`tests/test_api_contract.py::test_version_matches_package_metadata` asserts `__version__` equals the **installed** package metadata (which comes from `pyproject.toml`). This catches the classic "bumped one but not the other" mistake — but it **only runs against an installed package**; it `skip`s when run from a bare source tree. So after bumping you must `pip install -e .` before running the tests, or the guard is silently skipped.

## Versioning policy

[SemVer](https://semver.org/). While at `0.x`, minor versions may make breaking changes (noted in the CHANGELOG). Tags are `vX.Y.Z`. You can't skip a number — the next release after `0.3.0` is `0.4.0`, even if it bundles several features.

## Step-by-step

Assume the work to release is already committed/merged on `main` and accumulated under `## [Unreleased]` in `CHANGELOG.md`.

1. **Pick the version** `X.Y.Z` (next SemVer bump from the last tag — see `git tag`).

2. **Bump both version locations:**
   - `pyproject.toml`: `version = "X.Y.Z"`
   - `src/dndwright/__init__.py`: `__version__ = "X.Y.Z"`

3. **Update `CHANGELOG.md`:**
   - Rename `## [Unreleased]` → add a new empty `## [Unreleased]` above, and title the existing block `## [X.Y.Z] — YYYY-MM-DD`.
   - Update the compare links at the bottom:
     ```
     [Unreleased]: https://github.com/sligara7/dndwright/compare/vX.Y.Z...HEAD
     [X.Y.Z]: https://github.com/sligara7/dndwright/compare/v<prev>...vX.Y.Z
     ```

4. **Reinstall + verify** (the reinstall is what makes the version guard actually run):
   ```bash
   pip install -e ".[dev]"           # use --break-system-packages on this machine
   pytest -q                         # incl. the version-metadata guard
   ruff check src tests examples
   python -m build                   # builds dist/*-X.Y.Z.{whl,tar.gz}
   python -m twine check dist/*      # README/metadata render correctly for PyPI
   rm -rf dist build                 # CI rebuilds; don't commit artifacts
   ```
   Confirm `python -c "import dndwright, importlib.metadata as m; print(dndwright.__version__, m.version('dndwright'))"` prints the same version twice.

5. **Commit, tag, push:**
   ```bash
   git add -A
   git commit -m "Release X.Y.Z"
   git tag -a vX.Y.Z -m "dndwright X.Y.Z"
   git push origin main
   git push origin vX.Y.Z
   ```
   (Nothing has been published yet.)

6. **Publish the GitHub Release** — this is the step that triggers the PyPI upload:
   ```bash
   # Release notes = the CHANGELOG section for this version:
   awk '/^## \[X.Y.Z\]/{f=1} /^## \[<prev>\]/{f=0} f' CHANGELOG.md > /tmp/relnotes.md
   gh release create vX.Y.Z --title "dndwright X.Y.Z" --notes-file /tmp/relnotes.md
   ```
   (`gh` must be authenticated: `gh auth status`. `--generate-notes` is an alternative to the curated CHANGELOG notes.)

7. **Watch the publish workflow:**
   ```bash
   gh run list --workflow=publish.yml --limit 1
   gh run watch <run-id> --exit-status
   ```

8. **Verify on PyPI** (the JSON root + simple index are CDN-cached and can lag a minute; the versioned endpoint is authoritative):
   ```bash
   curl -s https://pypi.org/pypi/dndwright/X.Y.Z/json \
     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['info']['version'], [f['filename'] for f in d['urls']])"
   pip install -U dndwright          # eventually resolves to X.Y.Z
   ```

## The README version badge lags — that's expected, not a bug

After a release you'll often see the **PyPI version badge in the README still showing an
older version** (e.g. the project page header says `dndwright 0.5.0` but the
shields.io badge says `v0.3.0`). This is **CDN caching of the badge image**, not a broken
release:

- The badge is a live image from `img.shields.io/pypi/v/dndwright.svg`, which shields.io
  (and GitHub's camo image proxy) cache for a while. It trails the real version by minutes
  to hours, then catches up on its own. **You can't reliably force it; just wait.**
- The **source of truth** is the PyPI project page header (`dndwright X.Y.Z`) and the
  JSON API (`pypi.org/pypi/dndwright/json` → `info.version`) — both update immediately.
  `pip install -U dndwright` always resolves to the real latest regardless of the badge.
- So: confirm a release with step 8 (the versioned JSON), **not** the README badge. The
  badge catching up is cosmetic and needs no action.

To sanity-check what the badge currently renders (vs. the real version):
```bash
curl -s https://img.shields.io/pypi/v/dndwright.svg | grep -o '<title>[^<]*</title>'   # cached badge text
curl -s https://pypi.org/pypi/dndwright/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"  # real
```

## The PyPI page README is frozen per-version

PyPI renders the **README that was packaged with the latest *released* version** — it does
**not** re-read `README.md` from `main`. So editing the README, adding images to `assets/`,
or fixing typos does **not** change the PyPI project page until you **publish a new version**
(there's no way to refresh the description for an already-released version; you can't re-upload
the same number). Images are referenced by absolute `raw.githubusercontent.com/...@main` URLs,
so once pushed they render on GitHub immediately and on PyPI from the next release onward.

Practical rule: **if a change is meant to improve the PyPI page (README copy, screenshots,
diagrams), it only goes live with the next release.** A docs-only patch bump (e.g. `X.Y.(Z+1)`)
is a fine way to push README/graphics to PyPI without code changes.

## If something goes wrong

- **Workflow fails before upload** (build/twine error): fix on `main`, delete the Release + tag (`gh release delete vX.Y.Z --cleanup-tag`), and redo from step 5. Nothing reached PyPI.
- **Bad artifact already uploaded to PyPI:** you cannot overwrite it. Yank it (`pip`/web UI) and release a new patch version with the fix — never reuse a number.
- **Forgot to bump `pyproject.toml`:** the installed-metadata guard fails in CI (that's exactly the regression it was added for). Bump it and re-tag.

## Checklist

- [ ] `pyproject.toml` and `__init__.__version__` both = `X.Y.Z`
- [ ] CHANGELOG `[X.Y.Z]` section dated + compare links updated
- [ ] `pip install -e .` then `pytest` / `ruff` / `build` / `twine check` all pass
- [ ] commit `Release X.Y.Z`, tag `vX.Y.Z`, both pushed
- [ ] GitHub Release published → publish workflow green
- [ ] PyPI versioned JSON shows `X.Y.Z` (wheel + sdist) — the README badge lags; don't trust it
