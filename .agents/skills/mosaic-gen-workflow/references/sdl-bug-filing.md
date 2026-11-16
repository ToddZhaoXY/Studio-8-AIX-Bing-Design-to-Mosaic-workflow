# SDL Partner Support, Spec Proposals, and Bug Filing

Routing snapshot verified 2026-10-22. Use this reference when the user asks where to raise an SDL question, propose a capability, or report a Mosaic/renderer defect. Prepare or submit a work item only after explicit user intent.

## Route by intent

- Partner question, usage confusion, or early flag: [SDL Partners Teams channel](https://teams.microsoft.com/l/channel/19%3Ae589e4088018413d9718b8700434962f%40thread.tacv2/SDL%20Partners?groupId=c13ea7cc-1b13-4cbf-a93d-764489ac5ea9&tenantId=72f988bf-86f1-41af-91ab-2d7cd011db47).
- New component, prop, action, contract change, or SDL capability proposal: [SDL Spec proposal User Story template](https://msasg.visualstudio.com/24a0501b-d131-45af-ae52-27db9291efd4/_workitems/create/User%20Story?templateId=1064ab67-dc7b-499e-9ac5-2f18354dd473&ownerId=05965234-1285-43fe-9c92-a809c85e322a).
- Reproduced renderer, validation, tooling, or product defect: [SDL Bug template](https://msasg.visualstudio.com/24a0501b-d131-45af-ae52-27db9291efd4/_workitems/create/Bug?templateId=a524759b-1147-4c3a-b076-450a8c9b6085&ownerId=05965234-1285-43fe-9c92-a809c85e322a).
- Legacy/general fallback: <https://aka.ms/sdl-spec-request>.

The direct links target the `msasg` Azure DevOps organization and the current project template. Open the authenticated template because required fields, owner, area, iteration, and tags can evolve. Preserve template-populated routing and verify it before submission; do not replace it with remembered defaults or assign a person manually unless current team guidance requires it.

## Required issue content

### SDL capability requests and linked proposal PRs

For a new SDL capability, follow the complete Issue-plus-proposal workflow. An Issue alone is
not a completed proposal submission.

1. Inspect the current component contract and a related existing component before proposing
   property names, types, defaults, or version support. Confirm consequential scope choices with
   the user before filing; do not present undecided behavior as approved.
2. Reconfirm the SDL Spec proposal User Story template and preserve its current owner, area,
   iteration, tags, and required fields. Do not copy routing from an unrelated work item.
3. Create or repair one User Story with the template's Proposal, Properties, and Usage examples
   (JSX) sections. Include the motivating scenario, actual schema evidence, reference template
   URL, focused screenshots when available, acceptance criteria, and the agreed target version
   (or explicitly TBD). Preserve the template-provided tags and verified area/iteration. Do not
   invent custom ADO fields or copy outcome tags such as `Rejected` from precedent.
4. In the Azure Repos `Bing_UX/Mosaic` repository, fetch current `main` using authenticated Git
   and create an isolated proposal branch/worktree. Preserve existing user edits and keep other
   proposal branches untouched.
5. Follow the current `docs/spec_proposals/_template.md`, not a remembered document format.
   Its eight sections are Proposal, Properties, Children, Actions, Prompt instructions / Tips,
   Renderer requirements, Usage examples (JSX), and SDL payload example. Every proposed change
   must appear in JSX and the combined versioned SDL payload.
6. Validate with the repository formatter, section-order checks, JSON parsing, API/example
   consistency, and `git diff --check`. These validate proposal integrity, not implementation
   support. Do not claim a new prop passes the existing released schema.
7. Commit and push the proposal before creating the PR to `main`. Check for an existing PR
   from the branch to prevent duplicates. Add reviewers according to current repository policy
   and the user's instructions; verify reviewer identities and required flags.
8. Link the User Story to the PR with an actual ADO Pull Request `ArtifactLink`, not only description
   text. Use full PR URLs in prose: `#7144086` can resolve to an unrelated work item rather
   than Mosaic PR 7144086.
9. Read back the User Story fields, proposal at the pushed commit, PR source/target and changed-file
   scope, reviewers, and work-item relation. Return both the User Story and PR URLs. Report pending
   approvals, failed checks, or missing evidence honestly.

Historical submission pattern:

- PR: <https://msasg.visualstudio.com/Bing_UX/_git/Mosaic/pullrequest/7187362>
- Work item: <https://dev.azure.com/msasg/Bing_UX/_workitems/edit/11263512>

Use these only as workflow examples. The current User Story and Bug templates above are authoritative for new intake.

### Renderer defect evidence

Include:

1. A concise component, version, and failure-oriented title.
2. Environment, design surface, SDL version, template ID, iteration, and reproduction date.
3. Minimal working and failing JSX or SDL snippets.
4. Exact reproduction steps that change one variable at a time.
5. Expected and actual behavior.
6. Separate results for schema legality, saved full validation, API preview, and target-host rendering.
7. A link to the staging or production template when access is appropriate.
8. Acceptance criteria that cover the fix, safe failure behavior, and a regression test.

Do not attach screenshots that expose unrelated chats, people, credentials, tokens, or internal content. Prefer a focused renderer screenshot or the template link.

## Authenticated Azure CLI fallback

Use this fallback when the browser is blocked at sign-in and `az` already has an authenticated corporate session.

Preflight:

```bash
az account show --query '{tenant:tenantId,subscription:name}' -o json
```

Acquire the Azure DevOps token only inside the command that uses it:

```bash
token="$(az account get-access-token \
  --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --query accessToken -o tsv)"
```

Never print, log, persist, return, or paste the token into chat. Keep it in a shell variable and send it only in the `Authorization: Bearer` header.

Create the work item with JSON Patch. Choose the work-item type that matches the current route:

```text
POST https://dev.azure.com/msasg/Bing_UX/_apis/wit/workitems/$User%20Story?api-version=7.1
POST https://dev.azure.com/msasg/Bing_UX/_apis/wit/workitems/$Bug?api-version=7.1
Content-Type: application/json-patch+json
```

Populate at least:

- `System.Title`
- `System.AreaPath`
- `System.IterationPath`
- `System.AssignedTo`
- `System.Tags`
- `System.Description`
- `Microsoft.VSTS.Common.AcceptanceCriteria`

The REST fallback does not automatically apply browser-template defaults. Reconfirm the matching User Story or Bug template and reproduce its current required routing fields explicitly.

## Resolving an explicitly requested assignee

Normally preserve the owner from the selected template. If the user or current team guidance explicitly names a different assignee, use the identities endpoint with `General` as the search-filter enum and the person's name as `filterValue`:

```text
GET https://vssps.dev.azure.com/msasg/_apis/identities
  ?searchFilter=General
  &filterValue=Person%20Name
  &queryMembership=None
  &api-version=7.1-preview.1
```

Require one active exact-name match. Use the resolved identity value for `System.AssignedTo`. Do not pass a person's name as the `searchFilter` value; ADO interprets that parameter as an enum and returns HTTP 400.

## Verification and error handling

After creation, verify and report:

- Work item ID and HTML URL
- Title and state
- Assigned person
- Tags
- Area and iteration

If creation returns success, do not retry. If the result is ambiguous, search for the exact title before attempting another POST to avoid duplicates.

- `401` or `403`: ask the user to authenticate through the browser or Azure CLI.
- Identity lookup `400`: verify `searchFilter=General` and put the name in `filterValue`.
- Field validation `400`: inspect the Issue work-item-type fields before removing data; do not silently drop assignment, tags, or acceptance criteria.

When the environment supports artifact registration, register the created ADO issue as an artifact.
