# Shared Library → Mosaic workflow

- Read `.agents/skills/mosaic-gen-workflow/SKILL.md` first for Mosaic authoring, validation, debugging, skill setup and distribution. The bundled snapshot is v3.6; preserve it as supplied and load only relevant references.
- The user-facing entry is `tools/mosaic-workbench/server.py`. New work uses `codex_engine.py` and controlled CLI/MCP primitives; do not re-enable the historical Mosaic autopilot path in `engine.py` as the default.
- Work from the selected Library source, then verify the exact live Mosaic version and native component contract. Source-library SDL mapping is not the target contract.
- New Bing templates target v1.5 when the active backend/profile supports it. Preserve versions of existing templates unless migration is requested.
- Always use the current user's CLI and access. Do not copy credentials, hardcode an author's home path, or assume access to another person's workspace. Explicit local config and environment variables take precedence; static sample paths in the skill must be adapted to this machine.
- Before generating, require an explicit destination. Only create authorized new templates; do not publish or edit existing templates without the user's request. Repairs stay in one working iteration.
- Report save status, full validation, screenshot capture, model visual judgment and user acceptance separately. Do not label untested interaction or responsive behavior as passing.
- For environment checks run `python3 tools/mosaic-workbench/doctor.py` first. Use `--live` only when real connection checks are intended; it can execute a small read-only model probe.
- Keep `workbench.local.json`, `outputs/`, `state/`, secrets and machine-specific logs out of commits. Never export another user's account or provider configuration.
- Run the relevant stdlib tests and `python3 scripts/smoke_test.py` before sharing a runtime change. Smoke and CI must not create real Mosaic templates.
