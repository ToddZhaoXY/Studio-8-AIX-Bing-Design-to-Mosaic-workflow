# Copilot Agent and Mosaic Skill Setup

Use this chapter when someone asks to install or update the Mosaic workflow
skill, configure Mosaic in VS Code or GitHub Copilot, create or update a
Microsoft 365 Copilot agent, connect Remote MCP, add offline fallback, package a
pilot, or prepare an organization-wide submission.

## 1) Choose the support path

Do not assume one distribution model fits every user. Confirm:

1. **Host:** VS Code/GitHub Copilot, Microsoft 365 Copilot, or both.
2. **Scope:** one user, a repository/team, a named pilot group, or the whole
   organization.
3. **Live access:** local Mosaic CLI, approved Remote MCP, or offline guidance
   only.
4. **Mutation:** read-only guidance or confirmed template/ADO writes.
5. **Hosting:** developer workstation through a tunnel or persistent approved
   cloud hosting.
6. **Authentication:** per-user Mosaic sign-in, anonymous pilot access, or
   Entra/OAuth.
7. **Identity:** new app versus an update that must preserve an existing Teams
   App ID and display name.

Use these routes:

- **Practitioner workflow:** install this skill in VS Code/GitHub Copilot.
- **Casual M365 users:** use a declarative agent with embedded knowledge.
- **Live M365 pilot:** add a Remote MCP action and a controlled availability
  group.
- **Organization-wide release:** require persistent hosting, authentication,
  compliance artifacts, operational ownership, and complete validation.

## 2) First-time skill installation

A skill cannot bootstrap itself before Copilot can discover it. Give the user a
trusted ZIP, VibeHub package, or repository path first. Never ask for
credentials or tokens in chat.

### Personal Copilot installation

The ZIP should contain `SKILL.md`, `references/`, and `scripts/` at its root.
Extract it to:

```text
~/.copilot/skills/mosaic-gen-workflow/
```

Optional compatible personal locations:

```text
~/.agents/skills/mosaic-gen-workflow/
~/.claude/skills/mosaic-gen-workflow/
```

Reload VS Code after installation. Verify:

- Folder name and frontmatter `name` are both `mosaic-gen-workflow`.
- `description` includes the tasks users expect to trigger.
- Every relative reference and script exists.
- A prompt such as `Help me set up Mosaic Copilot on this machine` loads the
  skill.

### Repository-shared installation

For a team repository, place the same folder at:

```text
.github/skills/mosaic-gen-workflow/
```

Commit the complete folder, not only `SKILL.md`. Do not include token caches,
environment secrets, personal app IDs, personal tunnel URLs, or generated
review packages.

### Install the Mosaic CLI integration

Use the official installer and `mosaic mcp add --target vscode --scope global`
from [API and iteration workflow](./api-and-iteration-workflow.md). Then:

1. Run `mosaic status`.
2. Authenticate with `mosaic login` when required.
3. Add the MCP configuration.
4. Reload VS Code.
5. Verify tools or run a read-only template lookup.

The CLI evolves. Inspect `mosaic --help` before teaching exact commands and do
not assume a historical `mcp stdio` or tool name still works.

## 3) Skill update workflow

When asked to update:

1. Inspect the installed `SKILL.md` version and package source.
2. Obtain the trusted newer package.
3. Compare frontmatter, references, and scripts; preserve unrelated user files.
4. Replace only when the incoming version is newer or the user explicitly
   requests a reinstall.
5. Validate all relative links and script syntax.
6. Reload VS Code and run one discovery prompt plus one Mosaic read test.
7. Report old/new versions and any tool or authentication action still needed.

Do not silently overwrite a newer local skill with an older shared archive.

## 4) Microsoft 365 Copilot agent architecture

A Remote MCP declarative agent has separate layers:

```text
Microsoft 365 Copilot package
  ├─ manifest and declarative-agent instructions
  ├─ up to 10 embedded knowledge files
  └─ Remote MCP action
       └─ HTTPS endpoint
            └─ Mosaic adapter, validation, feedback, and optional ADO gateway
```

Keep these claims precise:

- Azure Dev Tunnels provides an Azure relay; it does not move a local MCP
  process into Azure compute.
- A tunnel-backed server stops working when the workstation, process, or tunnel
  stops.
- `auth: None` is an anonymous endpoint, even when the URL is difficult to
  guess.
- Embedded knowledge is fallback guidance, not proof of a live template,
  current contract, validation result, or target-host behavior.

## 5) Build or update the M365 agent

Before editing:

1. Locate the existing package and environment configuration.
2. Read the current Teams App ID, title/app IDs when available, display name,
   manifest version, MCP URL, and authentication type.
3. Decide whether this is a new dev identity or an in-place update.
4. Preserve the existing Teams App ID and production name for an in-place
   update; increase the version. Do not reuse the exact production name with a
   different ID because duplicate-looking agents confuse users.
5. Keep development and production environment files separate.

Minimum package:

- `manifest.json`
- `declarativeAgent.json`
- `ai-plugin.json` for Remote MCP
- color and outline icons
- referenced embedded knowledge

The package must keep the manifest at the ZIP root. Resolve environment
placeholders before upload. Validate the exact ZIP users will upload, not only
the source templates.

## 6) Pilot versus production hosting

### Time-limited development pilot

A Dev Tunnel can support a named pilot when the owner explicitly accepts:

- Workstation and tunnel dependency
- Anonymous access when `auth: None`
- No availability guarantee
- Restricted consequential tools
- Clear non-production labeling
- Embedded offline fallback

Keep ADO or other identity-bearing write tools hidden on an anonymous endpoint.

### Organization-wide release

Before broad publication, require:

- Persistent approved hosting such as an approved Azure service
- Entra/OAuth and tenant/audience validation
- Least-privilege downstream identities
- Approved storage and retention behavior
- Monitored team ownership and support
- Security Development Lifecycle artifact
- Privacy assessment
- Accessibility evidence
- RAI artifacts when required
- Approved source-code location
- SPACE and PowerShield records when required by the publishing portal

Do not use placeholder compliance URLs or describe a local process behind a Dev
Tunnel as an Azure-hosted application.

## 7) Offline fallback contract

Embed the durable SDL guidance needed for graceful degradation, respecting the
declarative-agent limit of 10 knowledge files. When MCP is unavailable:

1. Announce `Offline fallback mode`.
2. Do not retry the failed tool in a loop.
3. Do not claim live fetch, current iteration, current contract, validation,
   feedback logging, or ADO creation.
4. Request pasted JSX, schema, schemaData, diagnostics or emitted SDL, surface,
   viewport, and relevant visual evidence.
5. Continue learning, design critique, static review, troubleshooting, and
   copyable draft support.
6. Label embedded guidance as a versioned snapshot and require live
   verification for current support.
7. Give the smallest recovery step: restore service/tunnel/authentication or
   retry later.

Fallback improves continuity; it does not make anonymous or workstation-hosted
MCP suitable for production.

## 8) Validation and release gates

Run the smallest repository-standard commands that cover the change. For the
current Mosaic agent project, the expected sequence is:

```bash
npm run check
npm run package:agent -- <environment>
atk validate --package-file <exact-zip> --validate-method validation-rules -i false
```

Also verify:

- ZIP integrity and root layout
- Resolved version, App ID, display name, endpoint, and auth type
- No unresolved `${{...}}` placeholders
- Embedded knowledge count is within the platform limit
- Public and local health when Remote MCP is expected
- Raw ID and URL template retrieval
- Exact-version contract reads
- MCP outage fallback
- No false success claims for validation, host behavior, logging, or ADO
- Backward-compatible update behavior for the previous installed version

Treat warnings as explicit review items, not silent passes.

## 9) Installation and distribution paths

- **Personal skill:** extract to `~/.copilot/skills/mosaic-gen-workflow`.
- **Team skill:** commit to `.github/skills/mosaic-gen-workflow`.
- **Private M365 agent:** provision or upload to a controlled user group.
- **Official M365 update:** preserve identity/version continuity and complete the
  publishing portal's compliance requirements.

After installation, give users starting prompts:

```text
Set up Mosaic and verify my Copilot skill installation.
Fetch this Mosaic template by ID and explain the current iteration.
Help me package a private Mosaic Copilot pilot with offline fallback.
Audit this Mosaic Copilot package for organization-wide submission.
```

## 10) Completion report

Report separately:

- Skill installation and discovery
- Mosaic CLI authentication and connectivity
- MCP configuration and read/write boundary
- Agent package identity and version
- Embedded fallback coverage
- Package validation
- Pilot or production eligibility
- Untested outcomes and external compliance blockers

Never call a package production-ready merely because its ZIP validates.
