# Validation, Troubleshooting, and QA

Use this reference after authoring for the canonical validation order, runtime troubleshooting, target-host acceptance, and handoff checks.

## 9) Troubleshooting playbook

For API/MCP failures, HTTP 500, outdated clients, or changed tool names, follow
[API and MCP troubleshooting](./api-mcp-troubleshooting.md) before another
mutation. Discover the current saved-validation tool: `validate_iteration` was
verified on 2026-11-02; `validate_template_full` below remains the historical
name in dated evidence, not an assumed alias in every MCP installation.

### Mandatory validation sequence

```python
# 1. Format before validation.
formatted = mcp_call('format_template', {'jsx': jsx_string})

# 2. Validate JSX + data without saving.
mcp_call('validate_template_inline', {
  'jsx': formatted,
  'schemaData': data_json_string
})

# 3. Save only after inline validation passes.
# 4. Validate the saved iteration and resolve one complete SDL version.
mcp_call('validate_iteration', {'templateId': template_id, 'iteration': iteration})

# 5. Preview and inspect emitted SDL only after full validation passes.
mcp_call('preview_template', {'id': template_id, 'iteration': iteration})

# 6. Capture the target host at canonical, transition, and narrow widths.
# 7. Test pointer targets, keyboard reachability, media decoding, and local/server parity.
```

`preview_template` success is not publish validation. It can return an SDL tree with no diagnostics while saved validation rejects the same iteration because no single component schema version supports the complete prop combination.

**Known SDL v1.4 example:** Template `6qGmXitka5P7mhww48nL9` demonstrates the versioned envelope, nested `props`, per-node `sdlVersion`, `Pressable inline`, layout accessibility roles, percentage sizing, and a size-only border object. Its preview succeeds as SDL v1.4. On 2026-08-18, full validation still failed component-version resolution (`No schema version fits this template; closest is v1.3`). Treat it as output-shape and syntax evidence, not a publish-valid reference, until full validation passes.

**Known Mosaic-usable SDL v1.4 Video example:** Template `j9T1FNdaHb4mqVED1yAww`, iteration 1 (`QnA with Video`), demonstrates a schema-bound Mosaic `<Video>` inside a text-and-media card. Verified on 2026-10-08:

- The official Mosaic changelog lists `Video` as a component added in v1.4. The v1.4 release also introduced per-template version pinning and a stricter publish gate.
- The template was created in Mosaic, and `preview_template` succeeds on `bing-acf-card`, emits SDL v1.4, and returns zero diagnostics. This is sufficient evidence that the component can be authored, reused, and rendered in Mosaic preview workflows.
- `validate_template_full` fails component-version resolution with `Preview versions cannot be published`.
- The validation failure limits the publish-ready claim; it does not make the component unusable. Use this template as the current Mosaic reference when a requested design needs native video, while labeling its v1.4 preview-version status. Do not present it as a fully publish-validated Bing golden template or as proof of behavior in every downstream host.

The previewed `Video` node demonstrates these v1.4 fields:

```jsx
<Video
  title={entities[0].videoTitle}
  thumbnailUrl={entities[0].videoThumbnailUrl}
  metadata={{ timeLength: entities[0].videoTimeLength }}
  originalInlineSize={{ value: 1920, unit: "pixel" }}
  originalBlockSize={{ value: 1080, unit: "pixel" }}
  renderInlineSize={{ value: 320, unit: "pixel" }}
  renderBlockSize={{ value: 180, unit: "pixel" }}
  showPlayIcon={true}
  onHoverAction={{
    type: "video-inlinePreview",
    handler: "client",
    payload: {
      videoUrl: entities[0].videoHoverUrl,
      enableVolumeControl: true,
    },
  }}
  onClickAction={{
    type: "video-openInOverlay",
    handler: "client",
    payload: {
      mediaUrl: entities[0].videoClickMediaUrl,
      uniqueId: entities[0].videoClickUniqueId,
      thumbnailUrl: entities[0].videoClickThumbnailUrl,
      embedInfo: {
        allowEmbed: true,
        allowHttpsEmbed: true,
        allowMobileEmbed: true,
      },
    },
  }}
/>
```

Keep every URL, identifier, title, and metadata value schema-bound. This example preserves v1.4 evidence only. For new v1.5 work, translate its actions to the namespaced v1.5 contract documented above and omit the legacy `handler` field. For a production or publishing handoff, run saved full validation on the target design surface and visually test hover preview and overlay playback in the target host.

### A) Card does not render (blank)

1. Verify the root is `Card` or `Box` as allowed by the v1.5 target-surface contract
2. Validate JSON schema is well-formed and matches `schemaData` keys
3. Confirm every JSX variable reference exists in data
4. Check padding/gap values are valid tokens (see section 0)
5. Remove advanced props one by one to isolate the bad prop
6. Re-apply known-good base card, then layer changes back incrementally

### B) Image not rendering

1. `curl -sI <url> | head -5` — check for 200 OK
2. Replace blocked domains with verified alternatives
3. Set explicit `renderInlineSize` and `renderBlockSize` using the v1.5 size object

### C) Link or Button layout incorrect (fills instead of hugs)

1. Put the `Link` or `Button` in a directional `Box` that does not force full width
2. Avoid parent `width="100%"` around pills/chips
3. Use minimal padding on the inner `Box` for tight fit
4. Keep source attribution and destination navigation as a semantic `Link`; use a `Button` for a distinct command or handoff action
5. For a primary external destination, prefer a verified `iconEndName="external-link"` and keep the Link in a compact row so the icon remains adjacent to the label. Omit the glyph for low-emphasis source attribution when the favicon already identifies the source.
6. For single-source attribution, use a compact row with a schema-bound 16px favicon and a semantic Link. On staging `bing-acf-card` template `CCbeNWTiNTU583Net4kDy`, iteration 4, the verified working source Link omits both explicit `variant` and `color` and relies on the manifest defaults `body-md` and `brand`.
7. Treat Link style combinations as runtime-sensitive on the current v1.5 staging renderer. Several explicit `variant` and `color` combinations blanked the canvas even though preview and saved full validation passed. The final successful edit removed both props together, so the evidence does not isolate either prop as the independent cause. Preserve the last rendered iteration, change one Link prop at a time, and require target-host confirmation.
8. Do not treat API preview as authoritative for this defect. On the working default-Link iteration, preview reports a missing `onClickAction` although the action is present, full validation passes, and the editor canvas renders. Record all three outcomes separately and escalate the mismatch as a platform bug.

Verified on 2026-10-09 with staging `bing-acf-card` template `CCbeNWTiNTU583Net4kDy`, iteration 6: a `Link` with `iconEndName` rendered as a 272px-wide child when placed directly inside a vertical `Box`, pushing the end icon to the far edge. Wrapping the Link in a start-justified row made the Link hug its content and restored the expected label-to-icon spacing:

```jsx
<Box direction="row" justify="start">
  <Link
    value={continueReadingLabel}
    underline="hover"
    iconEndName="arrow-forward"
    onClickAction={{
      type: "link:navigate",
      payload: { url: sourceUrl },
    }}
  />
</Box>
```

Use this compact row wrapper whenever a Link or Button inside a vertical layout stretches across the cross-axis, especially when it has `iconStartName` or `iconEndName`. The wrapper owns intrinsic-width layout; keep the semantic action on the Link or Button itself.

For a confirmed renderer bug, preserve the disabled design intent with verified lexical comments inside the component's opening tag. This keeps the exact prop where it belongs and makes restoration mechanical. Do not leave the crashing prop active.

```jsx
<Link
  value={sourceLabel}
  underline="hover"
  /* TODO(renderer bug ADO #11321789): Restore after the v1.5 renderer fix. */
  /* color="tertiary" */
  variant="caption-xs"
  onClickAction={{ type: "link:navigate", payload: { url: sourceUrl } }}
/>
```

This exact isolation keeps `variant="caption-xs"` active and comments only `color`, proving the Link typography variant can render while the explicit color triggers the blank canvas. Mosaic `format_template` was verified to accept and preserve both `// color="tertiary"` and raw `/* color="tertiary" */` comments in the opening tag. Do not use the JSX-expression form `{/* color="tertiary" */}` between props; the formatter rejects it as invalid syntax.

Use this workaround only when one prop or small block is confirmed to trigger the runtime defect. Keep the TODO and disabled prop together, link them to the filed bug, and state the restoration condition. After the platform fix reaches the target host, uncomment the prop, rerun saved validation and host QA, then remove the TODO. If a later formatter strips lexical comments, record the same disabled prop and bug ID in the iteration notes instead.

Known-good single-source pattern:

```jsx
<Box direction="row" align="center" gap={1}>
  <Image
    src={sourceIconUrl}
    alt={sourceIconAlt}
    fit="cover"
    renderInlineSize={{ value: 16, unit: "pixel" }}
    renderBlockSize={{ value: 16, unit: "pixel" }}
  />
  <Link
    value={sourceLabel}
    underline="hover"
    onClickAction={{ type: "link:navigate", payload: { url: sourceUrl } }}
  />
</Box>
```

Do not add `radius="full"` to the favicon `Image`; the exact v1.5 save gate rejects that Image radius value. Use the source asset's native shape or a radius value verified in the live Image contract.

### D) Scroll not working

1. Use `<Box direction="row" scrollable={true}>`
2. Ensure children have concrete `width` values so overflow triggers

### E) Schema vs data mismatch

1. Keep schema/data keys identical to JSX references
2. Types must be stable (`string`, `array`, `object`)
3. When cloning, remap ALL field names — partial renames break rendering
4. Both schema and data must be valid JSON strings in `update_iteration`

### F) Tabs header or panel space is incorrect

1. Keep `Tabs` natural-height.
2. Remove `height`, `height="100%"`, or `flex={1}` from `Tabs` and its
   immediate layout chain one variable at a time.
3. Move intended padding, gap, and content sizing inside each `Tabs.Panel`.
4. Remove `justify="between"` from the column that owns `Tabs`.
5. Preview every active panel and verify the result in the target host.
6. Report this as an observed renderer-layout workaround unless a current
   matching-version contract explicitly defines the behavior.

---

---

## 10) Proven do/don't

### Do

- **Fetch a reference template first** — study its JSX/schema/data before building
- **Write a Mosaic fidelity brief** from one primary same-surface reference before coding
- **Search the live schema first** and describe every component whose props you change
- **Check the matching-version reference and changelog** for shared SDL contracts and recent changes
- **Use `get_color_reference` for color-sensitive work** and preserve semantic roles across themes
- Start from known-good templates and clone patterns
- **Adapt references** based on data count, interaction intent, and scenario
- Test every image URL host before finalize
- **Prefer Bing OLC/OIP image URLs** over third-party hosts
- **Use the official Bing condition-image mapping for weather designs** and select by code plus day/night state
- **Preserve a weather icon URL supplied by grounded upstream data** instead of reselecting it from the label
- Keep JSX simple and data-driven
- Run incremental updates (JSX → schema → data), then preview
- Include source attribution where applicable
- Use only valid SMTC token values for gap/padding
- **Use explicit fields (label1/value1)** for small fixed-count lists — more reliable than `.map()` in SERP
- **Use integer pixel magnitudes for Image render sizes until target-host preview verifies percentage rendering for that template**
- **Use a component's native action prop** when that component is the complete hit target and the target version validates it
- **Normalize repeated numbered fields into an items array** and render one mapped branch when sibling compositions are semantically identical
- **Keep repeated content and per-item anchor names in schemaData** while keeping shared dimensions and spacing in the single mapped JSX composition
- **Audit wrappers by responsibility** and remove only wrappers that contribute no layout, styling, semantics, accessibility, or interaction behavior
- **Compare emitted SDL before and after simplification** to prove content, actions, dimensions, ordering, and responsive behavior are preserved
- Run inline validation before saving and full validation before preview/publish
- Compare reference and candidate at identical host widths after full validation

### Don't

- **Don't invent layouts from scratch** — always reference a working template first
- **Don't rely on a static prop blacklist or whitelist** — component contracts are live and versioned
- Don't combine several unrelated gallery examples into one visually incoherent template
- Don't infer feature absence from an empty MCP schema search or feature support from inline parsing alone
- Don't hardcode a rendered hex value or substitute a token based only on visual hue when a semantic token exists
- Don't treat a successful SDL preview as proof that a template is publish-valid
- Don't fabricate ratings, counts, or source facts
- Don't use `1.5`, `7`, `10`, or other non-token gap/padding values
- Don't use `.slice()` on data arrays in JSX
- Don't use children text in `<Text>` — always use `value=` prop
- Don't introduce removed `Pressable` into new v1.5 work; use `Link`, `Button`, or a native media action
- Don't use full-width wrappers when a chip/pill should hug content
- Don't wrap `Image` solely to add navigation when the v1.5 `Image.onClickAction` contract covers the intended image-only hit target
- Don't keep duplicated JSX branches that differ only by numbered data fields; normalize the data and map one branch
- Don't hardcode repeated titles, URLs, images, labels, alt text, badges, or anchor names in JSX
- Don't reuse one hardcoded `anchorName` inside a mapped composition; each repeated anchor must be unique and paired with its own `positionAnchor`
- Don't remove a wrapper that owns flex sizing, alignment, clipping, radius, surface treatment, scrolling, semantics, or a composite hit area
- Don't mix incompatible field names between cloned templates
- Don't assume `group` works in create API — use `groupName`
- Don't skip `create_iteration` before `update_iteration`
- **Don't use `tse1.mm.bing.net/th?q=` search thumbnails** as image sources — use OLC/OIP instead
- **Don't synthesize weather image URLs from labels or day/night prefixes** — use the exact official mapping
- **Don't replace a defined weather `imageUrl` with an agent-selected alternative**
- **Don't assume zone size dictates layout** — 3×2 can scroll, 6×4 can be a grid. Let data and interaction drive layout

---

---

## 11) Reusable QA checklist before handoff

For scenario catalogs and stress-test sets, also create or update the
[GTX evidence manifest](./gtx-evidence-manifest.md). Keep JSX
expressions separate from component props and layout techniques.

- [ ] SDL consumers read `sdl.component`, `node.props`, and per-node `sdlVersion` rather than the old flattened shape
- [ ] Target surface, zone, emitted SDL version, reference ID, and authoritative iteration were recorded
- [ ] One primary same-surface reference was converted into a Mosaic fidelity brief
- [ ] Components, icons, colors, and text styles were checked against MCP discovery
- [ ] Color-sensitive work used the current color reference and semantic tokens rather than copied hex values
- [ ] Foreground, surface, border, link, and status colors retain their meaning and contrast in light and dark themes
- [ ] Shared/versioned contracts were checked against the matching reference gallery and changelog
- [ ] JSX was formatted with `format_template`
- [ ] `validate_template_inline` passes before save
- [ ] The discovered saved-validation tool passes for the saved iteration at its exact SDL pin
- [ ] Template opens and renders in Mosaic preview
- [ ] Root parent is valid for the v1.5 Bing contract (`Box` or `Card` in the shipped manifest; confirm target-surface containment)
- [ ] All gap/padding values are valid SMTC tokens
- [ ] No empty/undefined text fields
- [ ] Every unguarded JSX-bound field is required by the schema; guarded optional fields have tested missing-value behavior
- [ ] Repeated arrays and long strings are bounded to the largest canonical/transition/narrow payload actually proven by the layout
- [ ] Minimum, typical, maximum, and one invalid or missing production payload were exercised
- [ ] All links navigate correctly
- [ ] All images load (tested with curl)
- [ ] Weather designs use the official condition-code mapping, preserve day/night state, and do not synthesize missing URLs
- [ ] A weather `imageUrl` supplied by upstream data is preserved exactly and remains schema-bound
- [ ] Layout matches requested zone size behavior
- [ ] Grid dimensions were converted to canonical pixels and the usable content box was calculated after padding, borders, gaps, headers, and footers
- [ ] Every major region and media box has an intentional inline/block budget; requested media sizes cover the maximum effective track without exceeding source quality
- [ ] Total block demand was compared with canonical height, and any wrap, scroll, truncation, reduction, or expanded-height decision is explicit
- [ ] Reference and candidate were visually compared at the same host width and theme
- [ ] Canonical, wrap-transition, and narrow widths were checked for wrap, scroll, truncation, reordering, and empty flex tracks
- [ ] Any fixed-height capture limitation is reported separately from horizontal reflow evidence
- [ ] Advanced shared props were verified on the target host, not inferred from inline parsing
- [ ] Pointer testing confirms overlays and composite targets activate the intended action instead of underlying media
- [ ] Keyboard testing confirms Tab reaches nested semantic actions in reading order and scroll containers do not trap focus
- [ ] Informative images have crop-truthful alt text; empty-value expanded Links have non-empty schema-bound aria labels
- [ ] Status, selection, rank, and series meaning survives without color, position, or motion alone
- [ ] Screen-reader evidence names the tested host and assistive technology, or remains explicitly `not-tested`
- [ ] Image MIME type, dimensions, payload, target-host decoding, crop, subject visibility, and alt text were verified
- [ ] Native component props were preferred over wrappers when the component is the complete behavior or hit target
- [ ] Repeated sibling compositions use a normalized items array and one mapped branch where the target host supports it
- [ ] Repeated content and per-item anchor names come from schemaData rather than hardcoded JSX
- [ ] Every mapped `anchorName` is unique and resolves only its corresponding `positionAnchor`
- [ ] Every anchor owner has measured geometry; positioned content is budgeted for clipping/coverage and target-host overlap/hit testing passed
- [ ] Anchored or negative-margin overlays were checked for ancestor clipping and unintended overflow at target widths
- [ ] Every remaining wrapper has a concrete layout, visual, semantic, accessibility, or interaction responsibility
- [ ] Simplified JSX was compared with the prior emitted SDL for visible strings, actions, media, ordering, and responsive behavior
- [ ] Data is fully grounded in real sources
- [ ] Schema matches data shape exactly
- [ ] JSX-bound object schemas avoid unproven `$ref` paths and dynamic visual tokens use constrained enums
- [ ] Tabs and other cross-node ID relationships are explicit unless the mapped form has a saved target-surface proof
- [ ] Tabs in fixed-height or stretched layouts remain natural-height; panel spacing is internal, the owning column does not use `justify="between"`, and every active panel was target-host tested
- [ ] Source attribution is present when needed

### Production release-candidate decision

Record one of these outcomes:

- `production-ready`: every applicable checklist item passed in the intended
  production environment and publication eligibility passed.
- `staging release candidate`: implementation and intended-host staging gates
  passed, but production deployment or publication remains unverified.
- `preview-valid only`: formatting, saved validation, or preview passed without
  complete target-host evidence.
- `blocked`: name the failed gate, evidence, owner, and next verification step.

Never collapse saved validation, preview, staging render, production render,
and publication into one generic `passed` claim.

---
