---
name: mosaic-gen-workflow
description: "Concept, build, debug, publish, and update Mosaic GenUI designs and Copilot support. Use for Mosaic concepts, layouts, visualization, templates, MCP/API setup, HTTP 500 or failed saves, CLI/MCP version troubleshooting, Mosaic skill installation or updates, M365 Copilot agent setup, packaging, deployment, fallback, compliance review, create_template, update_iteration, JSX/schema/schemaData fixes, rendering problems, SDL or renderer bugs, spec requests, ADO tickets, or end-to-end workflows."
---

# Mosaic Gen Workflow (v3.6, Bing-focused)

Use this skill to design, implement, validate, debug, document, and distribute Mosaic templates for Bing ACF. New work targets SDL v1.5 unless the user explicitly requests maintenance of an older template.

## Scope router

- For Mosaic template design, authoring, validation, or debugging, follow the mandatory workflow below.
- For failed API/MCP saves, HTTP errors, client updates, or suspected tool-contract drift, use [API and MCP troubleshooting](./references/api-mcp-troubleshooting.md). Diagnose before another mutation; an updated client is not a verified save fix.
- For first-time skill installation, skill updates, M365 Copilot agent creation, Remote MCP setup, package updates, fallback, pilot distribution, or organization-wide publishing, use [Copilot agent and skill setup](./references/copilot-agent-and-skill-setup.md). Do not force the template-authoring workflow onto an installation task.
- Initial skill installation still needs a trusted package or shared repository. After installation, users can ask this skill to inspect, configure, update, validate, package, and troubleshoot the same Mosaic support stack.

## Mandatory workflow

1. **Define intent.** State the audience, primary answer, supporting evidence, action, grounding, target surface, zone, and narrow-width reading order.
2. **Choose one primary reference.** Use the same surface, version, content type, and interaction intent. Add at most one secondary component reference.
3. **Run the freshness gate.** Record the date, template ID, authoritative iteration, intended SDL version, advanced features, and any disagreement between live discovery and the matching-version reference.
4. **Plan two responsive levels.** Define section-level behavior first: major tracks, preferred and minimum widths, growth ownership, first reflow threshold, and semantic stacking order. Then define content-level behavior inside each section: wrapping, shrinking, scrolling, density, truncation, media crop, and control focus order. Do not use content compression to conceal a section that should reflow.
5. **Calculate geometry.** Convert the ACF grid to its canonical pixel viewport, then budget root padding, borders, gaps, fixed tracks, headers, footers, and media. Record every major region size, image render budget, and first wrap threshold before authoring.
6. **Fetch before editing.** Call `get_template`, select the item matching `currentIteration`, and preserve its JSX, schema, schemaData, notes, instructions, and viewport metadata.
7. **Create one working iteration.** Call `create_iteration` once for the user-requested edit, re-fetch the authoritative iteration number, and repair every defect for that edit in the same iteration.
8. **Author from the live contract.** Prefer native component capabilities, schema-bound content, constrained visual enums, explicit cross-node relationships, supported spacing tokens, and data-driven repeated composition.
9. **Validate in one order.** Format → inline validation when available → save changed fields → full saved validation → preview and emitted-SDL inspection.
10. **Test the target host.** Capture canonical, transition, and narrow widths; verify section-level reflow and content-level adaptation separately; verify image decoding and crop; test pointer behavior and keyboard reachability; distinguish capture-height clipping from complete responsive proof.
11. **Verify persistence.** Restore canonical viewport metadata, re-fetch the accepted iteration, and confirm local/server parity.
12. **Record evidence.** Update the GTX manifest and report validation, section-level responsiveness, content-level responsiveness, observed runtime behavior, design judgment, known limitations, template ID, and accepted iteration separately.
13. **Publish only on explicit request.** Keep publication eligibility separate from preview and saved-validation results.

## Completion gates

A task is complete only when all applicable gates pass:

- One root and one compatible SDL version resolve in saved full validation.
- Preview emits the intended SDL version and diagnostics are understood.
- Canonical viewport pixels, usable content area, major region dimensions, media render budgets, and wrap thresholds were calculated and then confirmed in the host.
- The target host renders at the canonical viewport.
- Section-level reflow and content-level adaptation are planned and evaluated separately; mark either level `not-applicable` rather than inventing behavior.
- Wrapping layouts pass canonical, transition, and narrow checks.
- Images pass availability, MIME, dimensions, payload, decoding, crop, subject-visibility, and alt-text checks.
- Pointer targets activate the intended action and keyboard focus reaches semantic actions in reading order.
- Grounded facts, units, dates, sources, disclosure, and neutral framing remain visible.
- Canonical viewport metadata is restored and local/server parity passes.
- Untested outcomes are reported as `not-tested`, never implied to pass.

`Production-ready` means a release candidate for one named environment and
surface, not merely valid JSX and not already published. Require saved v1.5
resolution, zero understood blocking diagnostics, intended-host rendering,
responsive and interaction evidence, bounded production data, grounding,
accessibility checks, persistence, and publication eligibility. If evidence
comes from staging, say `staging release candidate`; do not generalize it to
production until the production host and publish gate pass.

## Reference router

Load only the references needed for the task:

| Need | Reference |
|---|---|
| Concept, hierarchy, reference selection, fidelity, grounding | [Design, references, and grounding](./references/design-and-grounding.md) |
| SDL versions, components, JSON Schema, schemaData, expressions, maps | [Version contract, schema, and expressions](./references/schema-and-expressions.md) |
| Bing roots, spacing tokens, zones, legacy compatibility | [Bing ACF contract](./references/bing-contract.md) |
| CLI setup, MCP calls, iterations, viewport metadata, cloning, syncing | [API and iteration workflow](./references/api-and-iteration-workflow.md) |
| Failed saves, HTTP 500, CLI/MCP freshness, host alignment, retry safety, escalation | [API and MCP troubleshooting](./references/api-mcp-troubleshooting.md) |
| Section-level reflow, content-level adaptation, grid, scroll, flex, wrapping, responsive geometry, zone recipes | [Responsive layouts](./references/responsive-layouts.md) |
| Image sources, sizing, payloads, crops, weather assets | [Image and media runtime](./references/image-runtime.md) |
| Anchors, actions, wrapper ownership, expanded targets, accessibility | [Interactions and accessibility](./references/interactions-and-a11y.md) |
| Three-width GTX checks, media acceptance, pointer and keyboard QA | [GTX responsive and media QA](./references/gtx-responsive-media-qa.md) |
| Validation order, troubleshooting, runtime defects, handoff checklist | [Validation, troubleshooting, and QA](./references/validation-and-qa.md) |
| Scenario evidence and tracking-table generation | [GTX evidence manifest](./references/gtx-evidence-manifest.md) and [`gtx_manifest_to_table.py`](./scripts/gtx_manifest_to_table.py) |
| Asking SDL partners, proposing a capability, or filing a defect | [SDL support and filing](./references/sdl-bug-filing.md) |
| Installing/updating this skill or setting up, packaging, deploying, or troubleshooting the Mosaic Copilot agent | [Copilot agent and skill setup](./references/copilot-agent-and-skill-setup.md) |
| Official Bing weather condition images | [Weather image mapping](./references/weather-official-images.json) |

## Core authoring rules

### Do

- Use SDL v1.5 for new Bing work and preserve the recorded version of existing templates.
- Use the current live iteration as the source of truth; user edits may make local copies stale.
- Use `Box` and `Text` for new v1.5 work; verify exact props and containment live.
- Keep every visible string, URL, action label, alt text, and dynamic token schema-bound.
- Bound production arrays and text to the capacity proven by the layout; require or guard every JSX-bound field.
- Use only verified Bing spacing tokens and integer pixel image render budgets unless target-host evidence proves another form.
- Size from the outside in: grid viewport → root content box → major regions → component box → media render request → source pixels. Never guess child width or height from the grid label alone.
- Plan section-level reflow before content-level adaptation. For every major region, state how the region moves or resizes and how its internal content wraps, shrinks, scrolls, truncates, crops, or changes density.
- Prefer native `Image`, `Video`, `Link`, or `Button` actions when that component owns the complete target.
- Normalize repeated peer content into arrays and one `.map()` composition when static relationship validation permits it.
- Keep `Tabs.Panel` and other cross-node ID relationships explicit unless a saved target-surface probe proves the mapped form.
- Keep `Tabs` natural-height in fixed-height or stretched compositions. Put desired spacing inside each panel, avoid `justify="between"` on the owning column, and treat any `height`, `height="100%"`, or `flex={1}` workaround decision as target-host behavior that requires verification.
- Interpret required props with the exact-version contract, defaults, and `basicUsage`: separate minimum author inputs, defaulted/omittable props, variant-dependent props, and target-host checks.
- Inline JSX-bound object schemas when `$ref` traversal has not been proven.
- Constrain schema-bound visual tokens with exact live-contract enums.
- Fill structural whitespace only with distinct grounded evidence; never invent momentum, popularity, endorsement, sentiment, or trend.

### Don't

- Do not infer runtime support from inline parsing, preview, HTTP 200, or a manifest alone.
- Do not create extra diagnostic iterations for asset, crop, validation, or responsive repairs within one requested edit.
- Do not use removed v1.5 components, legacy actions, unsupported spacing values, `.slice()`, or `<Text>` children.
- Do not confuse JSX expressions with components, props, layout techniques, or interaction patterns.
- Do not use content-level scrolling, truncation, media shrinkage, or text compression to conceal a section-level layout that should reflow.
- Do not call a wrapping layout responsive when the transition state or vertically expanded result was not observed.
- Do not publish, copy a published template, or file an external issue without explicit user intent.

## GTX v3.4 requirements

The GTX additions are mandatory, not optional polish:

1. Two-level responsive planning: section-level reflow first, content-level adaptation second.
2. Three-width responsive matrix with separate evidence for both responsive levels.
3. Image-track sizing and quality model.
4. One canonical validation order.
5. Pointer and keyboard target-host QA.
6. `$ref` and constrained visual-enum guidance.
7. Static relationship classification for Tabs and cross-node IDs.
8. One-request/one-working-iteration repair discipline.
9. Machine-readable evidence manifest and table-row generation.
10. Grounded neutral-fill guidance.
11. Progressive disclosure through focused reference files.

## Support routing, Copilot agent, filing, and distribution

Use the Copilot setup reference when users ask how to install this skill, configure Mosaic tools, create or update the M365 agent, add MCP fallback, package a pilot, or prepare an official submission. Use the support-routing reference for partner questions, capability proposals, or renderer defects. Create or modify external resources only on explicit request. When updating this skill, validate frontmatter, all relative links, reference coverage, scripts, synchronized Copilot and Claude copies, the Desktop package, and ZIP integrity.
