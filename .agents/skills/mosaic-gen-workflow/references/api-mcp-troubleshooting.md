# API and MCP Troubleshooting

Use this playbook when a Mosaic read, iteration creation, or save fails, or when
the installed CLI and live tool contract may disagree. It supplements the
[API workflow](./api-and-iteration-workflow.md); it does not authorize publishing,
replacement templates, destructive recovery, or repeated diagnostic iterations.

## 1) Freeze writes and establish the boundary

1. Record the date, operation, exact API host, template ID, current iteration,
   SDL pin, CLI version, and MCP `initialize` server version. Redact personal
   information and credentials from shareable evidence.
2. Read the template with `get_template` and select the iteration matching
   `currentIteration`. Preserve JSX, schema, schemaData, notes, instructions,
   partition key, and viewport metadata before any authorized write.
3. If a failed or timed-out write preceded the read, compare against the
   pre-write snapshot. An error response does not prove that nothing persisted.
   If the current iteration advanced, inspect it before any retry; do not
   assume it is yours or overwrite concurrent user edits.
4. Separate the failing gate: transport/authentication, read, inline validation,
   creation/save, saved validation, preview, or target-host rendering. Do not
   troubleshoot a save HTTP 500 by rewriting already-valid layout content.

## 2) Check versions and the actual host, read-only first

Use the installed executable path. The default CLI host may differ from the
host containing the requested template.

```bash
mosaic --version
MOSAIC_API_URL="https://YOUR-MOSAIC-HOST" mosaic status
MOSAIC_API_URL="https://YOUR-MOSAIC-HOST" mosaic health
curl -fsSL "https://YOUR-MOSAIC-HOST/api/cli/version"
```

- Treat the distribution endpoint as release metadata, not proof of the
  deployed backend's version. Record its environment/channel and platform
  checksum when supplied. Compare like channels; staging and production
  version differences are not automatically incompatibilities.
- Check the help/catalog before using unfamiliar commands, but do not assume
  that help accurately describes their side effects. On 2026-11-02,
  `mosaic upgrade` advertised an update check yet actually replaced the binary.
  Use the release-metadata GET for a non-mutating freshness check.
- Apply an official client update only within the requested update scope or
  with authorization. Do not change global host/profile settings merely to
  diagnose one destination; use a process-local environment override.
- After an update, start a fresh MCP connection and verify its `initialize`
  server version. Existing VS Code MCP processes may still run the old binary;
  restart/reload that connection as needed. A CLI version check alone is not
  evidence that the active MCP server changed.

## 3) Discover the contract instead of guessing

1. On the fresh MCP connection, request `tools/list` and inspect only the
   relevant tools' input schemas and descriptions. Record required fields,
   version-pin behavior, partition keys, and concurrency guards.
2. Use the discovered saved-validation tool. On 2026-11-02 this was
   `validate_iteration({templateId, iteration, partitionKey?})`; older recipes
   name `validate_template_full`. Use the legacy name only if discovery exposes
   it. Keep exact-pin saved validation mandatory regardless of the tool name.
3. If creation/save fails, independently check reads and saved validation of
   the existing iteration. Passing health, reads, and saved validation narrows
   the failure boundary; none proves that writes work.
4. Check official API documentation when available. Require a JSON content
   type and a valid OpenAPI document; HTTP 200 containing the SPA's HTML is not
   API documentation. Do not repeatedly parse it as JSON or invent V2 routes.
5. If tool discovery and documentation do not explain the failure, narrowly
   compare the official UI/client request for that operation. Do not begin
   with broad bundle inspection or rebuild an undocumented API client.

Observed save routes on 2026-11-02:

| Operation | Route | Important boundary |
|---|---|---|
| MCP `create_iteration` | `POST /api/mosaic/CreateIteration` | The exposed tool accepted only `templateId`; do not invent extra tool arguments. |
| MCP `upsert_draft` / CLI validated save | `POST /api/validatediteration/Save` | These are two clients of the same endpoint, not independent backend fallbacks. |

These are dated observations, not permanent contracts. Recheck discovery.
When available, preserve the saved partition key and exact schema pin rather
than inferring them from a ticker, workspace, or default profile.

## 4) Classify and recover safely

| Evidence | Next action |
|---|---|
| 401 or missing/expired authentication | Use the official interactive sign-in path; never request pasted tokens or scrape browser credentials. |
| 403 | Check destination and access; do not try alternate identities or credential workarounds. |
| Structured schema/data/JSX rejection | Repair only the reported artifact, then repeat validation in the same working iteration. |
| 409 or unexpected current iteration | Re-fetch and reconcile concurrent changes before writing. |
| 429 or transient transport/5xx | Re-fetch authoritative state first; honor retry guidance and require a bounded, justified retry. |
| Repeatable create/save 500 with reads passing | Preserve evidence and seek backend diagnostics; do not declare a specific cause without logs or a reproducer. |
| HTML returned from an API-document URL | Mark documentation unavailable; stop treating the response as OpenAPI. |

- No blind retry loops. A new client version, an explicit recovery signal, or a
  documented payload correction can justify one controlled retry of the
  original authorized edit after a fresh read. Repeated failure without new
  evidence is a blocker, not a reason to keep creating iterations.
- For a discovered save tool supporting `createNewIteration`,
  `expectedBaseIteration`, and `operationId`, supply its required guards and
  reuse the same operation ID when retrying that logical save. Do not assume
  client-side guards provide backend atomicity or idempotency.
- A successful creation establishes the one working iteration for this edit.
  Repair and verify there; do not create extra iterations for diagnostics.
- Do not overwrite the accepted iteration, recreate the template under a new
  ID, restore/delete history, switch environments, or publish to bypass a
  failed save without explicit user intent.
- Keep secrets in the supported auth flow. Never print token caches, bearer
  headers, or signed URLs into logs or diagnostic packages.

## 5) Verify the fix, then capture reusable evidence

If a write is in scope, re-fetch immediately before the controlled attempt.
Afterward, independently confirm the authoritative iteration/content, exact-pin
saved validation, emitted SDL, target-host behavior, canonical metadata, and
local/server parity using the normal authoring gates.

If this is a read-only investigation or skill update, do not write a template
as a diagnostic proxy. Report post-update save behavior as `not-tested`.

Record separately:

- **Observed:** versions before/after, destination/channel, failing operation,
  status and redacted response, passing gates, state before/after.
- **Hypothesis:** possible causes and the evidence still needed to test them.
- **Resolution:** the specific change and independently verified outcome.
- **Remaining:** blocked or untested gates, including an unattempted save.

An updated CLI/MCP is a verified client update, not a verified server fix.
Inline validation success plus a failed save is not a completed Mosaic design.

For escalation, collect UTC timestamp, route/method, client and MCP versions,
SDL pin, authoritative iteration, sanitized request shape, status/diagnostics,
response correlation IDs if provided, and state comparison. Backend logs are
needed when the service returns an unexplained 500. Follow
[SDL support and filing](./sdl-bug-filing.md) and its official template when the
user explicitly requests an external issue; do not file one automatically.
