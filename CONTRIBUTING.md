# Contributing to offlickr

Thanks for your interest! This project is maintained as a small, long-lived OSS archive tool; we prefer quality and consistency over speed.

## Development setup

Install [`uv`](https://docs.astral.sh/uv/) (one-time):

```bash
brew install uv  # macOS; or: pip install uv
```

Clone and install dev dependencies:

```bash
git clone https://github.com/yaniv-golan/offlickr
cd offlickr
uv sync --all-extras --dev
```

## Running tests, lint, and type checks

```bash
uv run pytest                         # tests
uv run pytest --cov                   # tests with coverage
uv run ruff check                     # lint
uv run ruff format --check            # format check
uv run ruff format                    # auto-format
uv run mypy src tests                 # type check
```

## Test-driven development

This project is strictly test-driven for the ingest, model, render, and sanitize layers. The discipline is red-green-refactor:

1. Write a failing test that expresses the desired behavior.
2. Write the minimum implementation to make it pass.
3. Refactor with tests green.

PRs that add behavior without tests will be asked to add them. Patch coverage is enforced in CI via `diff-cover` at ≥ 80%.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org). `commitizen` enforces this in CI.

Common prefixes:

- `feat:` — user-visible feature
- `fix:` — user-visible bug fix
- `docs:` — documentation only
- `test:` — tests only
- `refactor:` — no behavior change
- `chore:` — dependencies, tooling
- `ci:` — CI config

Breaking changes use `!` (e.g. `feat!: rename --foo to --bar`) and a `BREAKING CHANGE:` footer.

## Pull request process

1. Branch from `main`. One logical change per PR.
2. Add or update tests.
3. Add a `CHANGELOG.md` entry under `[Unreleased]` for any user-visible change.
4. Open a PR. CI must pass: lint, format, mypy, tests, patch coverage, pip-audit.
5. A maintainer reviews and merges.

## Release process

Releases are cut from `main` by bumping the version, writing `docs/release-notes/v<version>.md`, dating the `CHANGELOG.md` section, and pushing a `v<version>` tag. The `release.yml` workflow handles build, PyPI publish (via OIDC trusted publishing), and GitHub Release creation. See `docs/superpowers/specs/2026-04-22-offlickr-design.md` §13.2 for the full process.
