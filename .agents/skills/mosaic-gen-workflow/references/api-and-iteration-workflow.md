# API and Iteration Workflow

Use this reference for Mosaic CLI setup, authenticated MCP operations, safe iteration mutation, viewport metadata, published export, cloning, maintenance, and distribution.

## 1) Quick setup (once per machine)

For failed saves, client updates, or contract drift, use
[API and MCP troubleshooting](./api-mcp-troubleshooting.md) before retrying.
Inspect release metadata with a GET for read-only version checks; a command
named `upgrade` may apply an update even when its help describes a check.

### Prerequisites

1. **Mosaic CLI binary** — install or update it with the official platform command (VPN required):

  macOS/Linux:

  ```bash
  curl -fsSL "https://afd-mosaic-f6e8eycvfaeffkam.b02.azurefd.net/api/cli/install" | bash
  ```

  Windows PowerShell:

  ```powershell
  irm "https://afd-mosaic-f6e8eycvfaeffkam.b02.azurefd.net/api/cli/install.ps1" | iex
  ```

  The installer updates the CLI binary and PATH. Register the MCP server with VS Code separately:

  ```bash
  mosaic mcp add --target vscode --scope global
  ```

  Reload VS Code after installing or updating. The CLI manages its bundled skill catalog; use `mosaic skills sync-local --source-dir <path>` only for explicit local skill overrides.

### Skill updates

The canonical shared package for this workflow skill is:

<https://vibehub.microsoft.com/app/anthonyleung-fp-t-a/>

**Agent update rule:** When the user asks to install, refresh, or update this workflow skill, open the VibeHub page, fetch its latest downloadable package, and inspect the packaged `SKILL.md` version before changing the local copy. Replace the installed skill only when the package is newer, preserve any unrelated local files, and report the old and new versions. VibeHub requires Microsoft corporate access and may require VPN or browser authentication; never ask the user to paste credentials into chat.

2. **Microsoft (AAD) login** — required for API auth
   - First run: `~/.mosaic/bin/mosaic` opens a browser for Microsoft corporate login
   - Tokens are cached in `~/.mosaic/token_cache.json` (access + refresh tokens)
   - Refresh tokens auto-renew silently; if expired, re-run the CLI interactively to re-auth
   - **Agent rule:** If `token_cache.json` is missing or MCP calls return auth errors, tell the user to run `~/.mosaic/bin/mosaic` in a terminal to re-authenticate

3. **Access to `mosaic.ai.microsoft.com`** — Microsoft corpnet or VPN required

### Reusable MCP helper (use this for ALL calls)

```python
import subprocess, json

def mcp_call(tool, args):
    init = json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'t','version':'1.0'}}})
    notif = json.dumps({'jsonrpc':'2.0','id':2,'method':'notifications/initialized','params':{}})
    msg = json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name': tool,'arguments': args}})
    r = subprocess.run(['/Users/anthonyleung/.mosaic/bin/mosaic','mcp','stdio'],
        input=init+'\n'+notif+'\n'+msg+'\n', capture_output=True, text=True, timeout=60)
    for line in r.stdout.strip().split('\n'):
        try:
            d = json.loads(line)
            if d.get('id') == 3:
                for c in d['result']['content']:
                    t = c.get('text','')
                    if t.startswith('{') or t.startswith('['):
                        return json.loads(t)
                    return t
        except: pass
    return None
```

### Smoke test

```python
result = mcp_call('search_schema', {'category': 'components'})
print(result)  # Should list the available GenUI components
```

### Autopilot draft workflow

The merged CLI exposes `mosaic search-card autopilot` for a checkpointed
grounding → architecture → authoring → hillclimb workflow. Use it as a draft and
stress-test path, not as a replacement for the version-aware authoring gates in
this skill.

Verified on 2026-10-13 with a 6x4, three-product specification comparison:

- Grounding and architecture completed and produced a useful equal-column table
  concept.
- Authoring persisted a template after repair cycles.
- Despite explicit SDL v1.5 instructions, template creation pinned the result to
  v1.3 and the author used removed `Col`, `Row`, `Title`, and `Caption`
  components.
- Saved full validation passed only as v1.3.
- Preview failed because legacy data action objects used `actionType`, which the
  generated action contract could not deserialize.
- Snapshot capture then returned HTTP 502 because no target card rendered.
- Hillclimb correctly refused to create a score without screenshot evidence.
- The checkpoint preserved the completed stages and failure evidence even though
  result collection later encountered a broken pipe.

Apply these rules:

1. State the target surface, card size, SDL version, content count,
   representation, grounding requirements, and action semantics explicitly.
2. Enable checkpointing for any run worth retaining.
3. After authoring, inspect the created template's immutable SDL version before
   accepting or repairing its JSX.
4. Treat a full-validation pass as version-scoped evidence. A v1.3 pass does not
   satisfy a v1.5 request.
5. Run preview and inspect the emitted SDL before allowing screenshot scoring or
   hillclimb to influence the result.
6. When preview fails, diagnose the preview error first. Do not treat a later
   capture 502 or missing-target error as the root cause.
7. Never reuse grounded product data without reconciling product identity,
   values, source disclosure, and destination URLs.
8. If autopilot creates an older immutable template, retain it only as evidence
   or a structural draft. Create a separate version-correct template rather than
   mixing removed components or legacy actions into new v1.5 work.

Current conclusion: autopilot can accelerate grounding and architecture, but one
successful Scenario 03 draft did not establish a reliable end-to-end SDL v1.5
authoring path. Continue to require formatting, saved full validation, preview,
emitted-SDL inspection, screenshot evidence, and target-host QA as independent
gates.

---

---

## 2) Mandatory direct API workflow

Treat the authenticated Mosaic MCP transport as the primary read/write API. The browser is for visual review and publishing only; it is not the default way to inspect or edit templates.

When the user provides a template ID or asks to update an existing Mosaic template:

1. Call `get_template({id})` immediately through `~/.mosaic/bin/mosaic mcp stdio`.
2. Select the iteration whose `iteration` equals `currentIteration`; do not assume `iterations[-1]` is authoritative and do not use a stale session snapshot.
3. Preserve that current iteration's JSX, schema, `schemaData`, notes, and instructions as the source of truth.
4. Call `create_iteration({templateId})` exactly once for the edit.
5. Re-fetch with `get_template({id})` and use the returned `currentIteration` as the write target. Do not guess the iteration number or rely on `currentIteration + 1`.
6. Push changed fields individually with `update_iteration`. Read JSX from `jsxTemplate`, but write it using `field: "jsx"`.
7. Run the discovered exact-pin saved-validation tool as the authoritative compatibility gate: currently `validate_iteration`; use `validate_template_full` only when the installed MCP exposes that legacy name.
8. Run `preview_template`, inspect emitted SDL and diagnostics, then capture and test the target host.
9. Repair validation, render, asset, crop, responsive, and interaction defects in that same newly created iteration.
10. Report the template ID, final iteration, validation result, preview result, and target-host result separately. Publish only when the user explicitly asks.

Do not start with browser automation, frontend-bundle inspection, broad web search, session-history search, or manual source reconstruction when `get_template` can read the ID directly. Do not create a replacement template merely because the UI is inconvenient.

### Iteration repair discipline

Treat one user-requested edit as one working iteration:

1. Re-fetch the authoritative current iteration immediately before mutation.
2. Create one new iteration for the requested change and re-fetch its number.
3. Keep all repair attempts for that change in the same new iteration, including
   image replacements, crop changes, schema fixes, responsive adjustments, and
   runtime workarounds.
4. Create another iteration only when the user begins a distinct edit after
   accepting the prior result, or a platform restriction prevents safe repair.
5. Record the source iteration, working iteration, changed fields, repair
   attempts, and final accepted state. Never use diagnostic iteration count as
   evidence of progress.

### Persist the generated viewport before snapshot QA

`capture_search_card_screenshot` uses the saved
`bing-acf-card.generated-viewport` iteration metadata. When that metadata is
absent, the capture path can fall back to 5x4 even when the intended scenario is
6x4, producing misleading clipping and density judgments.

The current MCP does not expose a general extension-metadata mutation tool. Use
the authenticated staging endpoint without printing or persisting the bearer
token:

```bash
token=$(jq -r '.AccessToken | to_entries[0].value.secret // empty' \
  "$HOME/.mosaic/token_cache.json")

[[ -n "$token" ]] && curl -fsS -X POST \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  --data '{
    "TemplateId": "TEMPLATE_ID",
    "ExtensionId": "bing-acf-card",
    "Key": "generated-viewport",
    "Value": "6x4"
  }' \
  "https://mosaic-staging.ai.microsoft.com/api/TemplateExtensionMetadata/SetIterationMetadata"
```

After the write:

1. Re-fetch the authoritative current iteration.
2. Confirm
   `extensionMetadata["bing-acf-card"]["generated-viewport"]`.
3. Capture a fresh screenshot and verify its pixel dimensions against the ACF
   formula.
4. Do not reuse a screenshot captured before the metadata correction.

Verified on 2026-10-13 with staging template
`YTpRAm1TkuPk6aHLSNRE2`, iteration 2: capture was 536x424 before metadata and
648x424 after saving `6x4`.

### Published template export fallback

Published or Featured IDs may not be owned by the current user, so `get_template` can reject them even though the account can view them. For read-only reference recovery, use the authenticated export endpoint:

```bash
token=$(jq -r '.AccessToken | to_entries[0].value.secret // empty' "$HOME/.mosaic/token_cache.json")
[[ -n "$token" ]] && curl -fsSL \
  -H "Authorization: Bearer $token" \
  "https://afd-mosaic-f6e8eycvfaeffkam.b02.azurefd.net/api/publishing/GetPublishedTemplateForExport/PUBLISHED_TEMPLATE_ID"
```

Security and mutation rules:

- Keep the bearer token inside the shell pipeline; never print, log, store, or paste it into chat.
- If the cache is missing, the token is empty, or the endpoint returns `401`, ask the user to re-authenticate by running `~/.mosaic/bin/mosaic`; do not scrape credentials from a browser.
- Export is a read-only reference path. To adapt the result, create a user-owned template and push JSX/schema/data through MCP.
- Do not call `CopyToTemplateCreator` or any publishing mutation endpoint unless the user explicitly asks to copy or publish.

---

---

## 4) Golden template workflow

### Fast path: polish an existing template

For a known template ID, take this direct route by default. Do not reopen CLI setup, enumerate every MCP tool, search session history, or broadly rediscover components that the current JSX already uses.

```python
template_id = 'EXISTING_TEMPLATE_ID'

# 1. Fetch once and select the server-declared current iteration.
template = mcp_call('get_template', {'id': template_id})
source = next(
  item for item in template['iterations']
  if item['iteration'] == template['currentIteration']
)

# 2. Create one editable iteration, then re-fetch its authoritative number.
mcp_call('create_iteration', {'templateId': template_id})
updated_template = mcp_call('get_template', {'id': template_id})
iteration = updated_template['currentIteration']

# 3. Update only the fields that changed.
mcp_call('update_iteration', {
  'templateId': template_id,
  'iteration': iteration,
  'field': 'jsx',
  'value': revised_jsx,
})
# Repeat for schema/schemaData only when their shape or content changed.

# 4. Full validation is the compatibility gate.
mcp_call('validate_iteration', {
  'templateId': template_id,
  'iteration': iteration,
})

# 5. Preview only after the saved template resolves to one SDL version.
mcp_call('preview_template', {'id': template_id, 'iteration': iteration})
```

**Fast-path rules:**

1. Use the existing iteration's JSX, schema, and data as the reference; keep changes local.
2. Call live component discovery only for a new component or prop, or when preview/full validation reports a component-contract or version-resolution error.
3. Do not update schema or `schemaData` when a layout-only JSX change leaves the data contract intact.
4. Run the discovered saved-validation tool (`validate_iteration` in the current MCP) before preview. If either gate fails, repair that same iteration and repeat from saved validation.
5. Report the new iteration number and validation result. Do not publish unless the user explicitly asks.

### Create new template

```python
r = mcp_call('create_template', {
    'name': 'my-card-name',
    'groupName': 'My Group',           # NOT 'group'
    'designSurface': 'bing-acf-card'
})
template_id = r['templateId']          # NOT 'id'

mcp_call('create_iteration', {'templateId': template_id})
created = mcp_call('get_template', {'id': template_id})
iteration = created['currentIteration']
mcp_call('update_iteration', {'templateId': template_id, 'iteration': iteration, 'field': 'jsx', 'value': jsx_string})
mcp_call('update_iteration', {'templateId': template_id, 'iteration': iteration, 'field': 'schema', 'value': schema_json_string})
mcp_call('update_iteration', {'templateId': template_id, 'iteration': iteration, 'field': 'schemaData', 'value': data_json_string})
```

### Clone existing template

```python
src = mcp_call('get_template', {'id': 'SOURCE_TEMPLATE_ID'})
it = next(
  item for item in src['iterations']
  if item['iteration'] == src['currentIteration']
)
src_jsx = it['jsxTemplate']     # NOTE: field is 'jsxTemplate' on read
src_schema = it['schema']
src_data = it['schemaData']

# Create new template, then apply the cloned content
r = mcp_call('create_template', {'name': 'cloned-name', 'groupName': 'Group', 'designSurface': 'bing-acf-card'})
new_id = r['templateId']
mcp_call('create_iteration', {'templateId': new_id})
created = mcp_call('get_template', {'id': new_id})
iteration = created['currentIteration']
mcp_call('update_iteration', {'templateId': new_id, 'iteration': iteration, 'field': 'jsx', 'value': src_jsx})
mcp_call('update_iteration', {'templateId': new_id, 'iteration': iteration, 'field': 'schema', 'value': src_schema})
mcp_call('update_iteration', {'templateId': new_id, 'iteration': iteration, 'field': 'schemaData', 'value': modified_data})
```

### Critical API details

- `create_template` uses `groupName` (NOT `group`)
- Response uses `templateId` (NOT `id`)
- `update_iteration` field names: `jsx`, `schema`, `schemaData`, `notes`, `instructions`
- `get_template` returns JSX under `jsxTemplate`, but update uses `field: "jsx"`
- `create_iteration` is REQUIRED before first `update_iteration` — skipping it will fail silently

---

---

## 13) Skill freshness maintenance

Refresh this skill when any of these triggers occurs:

- Mosaic preview emits a different `sdlVersion`
- The versioned reference gallery or Changelog adds, removes, or changes a shared contract
- MCP discovery disagrees with the matching-version reference
- Full validation rejects a previously documented prop combination
- A target host renders differently from Mosaic preview
- The Mosaic CLI or authoring workflow changes tool names or required arguments

For each verified refresh:

1. Capture the exact evidence: reference version, component or shared type, target surface, and validation result.
2. Update or remove the stale rule instead of only appending another exception.
3. Bump the workflow skill version and record time-sensitive behavior with a verification date.
4. Search the full skill for contradictory examples, stale tool names, and last-iteration assumptions.
5. Validate frontmatter, required sections, and code snippets before syncing copies.
6. Sync Copilot, Claude, and the shareable archive; report any distribution target not updated.

Keep static recipes focused on durable design patterns. Keep volatile prop names, enum values, component versions, and renderer support behind the freshness gate so the agent rechecks them at authoring time.

---

---

## 14) Copy/share workflow (Copilot + Claude + zip)

Source of truth:

- `~/.copilot/skills/mosaic-gen-workflow/SKILL.md`

Sync copies:

```bash
mkdir -p ~/.claude/skills/mosaic-gen-workflow ~/Desktop/mosaic-gen-workflow-skill && \
cp -R ~/.copilot/skills/mosaic-gen-workflow/. ~/.claude/skills/mosaic-gen-workflow/ && \
cp -R ~/.copilot/skills/mosaic-gen-workflow/. ~/Desktop/mosaic-gen-workflow-skill/ && \
cd ~/Desktop && rm -f mosaic-gen-workflow-skill.zip && \
zip -r mosaic-gen-workflow-skill.zip mosaic-gen-workflow-skill/ -x '.*' '__MACOSX/*'
```

This gives:

- Copilot-local skill
- Claude-local skill
- Shareable zip for other devices/teammates
