# Version Contract, Schema, and Expressions

Use this reference for SDL version policy, wire shape, component inventory, JSON Schema, schemaData, JSX expressions, and data-driven simplification.

### New-work version policy

> **Agent handoff — effective 2026-10-08:** Use SDL v1.5 for all new Bing ACF prompts and templates. Leave existing v1.3 and v1.4 templates on their recorded versions unless the user explicitly requests migration.

For new work:

1. Select v1.5 in the matching reference gallery and changelog.
2. Discover the current v1.5 component, containment, root, shared-prop, and action contracts before authoring.
3. Do not carry forward a v1.3 `Basic` root, numeric image-sizing rule, removed component, or old prop solely because an existing golden template uses it.
4. Create and preview the v1.5 template even if the version is still behind a publication gate.
5. Record these outcomes separately: template creation, preview diagnostics, emitted SDL version, saved full validation, publication eligibility, and target-host behavior.
6. Count the result as a publish-ready v1.5 pass only when saved full validation resolves the complete template to v1.5. Until then, report `v1.5 preview passed; publication pending` when that is the observed state; do not silently downgrade new work to v1.3.

This policy changes the default for new authoring, not the historical meaning of existing v1.3/v1.4 test results.

### v1.5 readiness snapshot

The shipped v1.5 manifests were captured and tested on 2026-10-08:

- 20 components are present: `Badge`, `Box`, `Button`, `Card`, `Chart`, `Divider`, `Icon`, `Image`, `Link`, `Map`, `Markdown`, `ProgressBar`, `Spacer`, `Table`, `Table.Cell`, `Table.Row`, `Tabs`, `Tabs.Panel`, `Text`, and `Video`.
- The isolated v1.4 to v1.5 diff has 61 official changes: 23 breaking and 38 non-breaking.
- `Link` and `ProgressBar` are added.
- `Basic`, `Caption`, `Checkbox`, `Col`, `Form`, `Label`, `ListView`, `ListViewItem`, `Pressable`, `Row`, and `Title` are removed.
- All 20 schema-bound component probes format successfully.
- The first complete staging pilot on `bing-acf-card` passes saved full validation at v1.5 and previews as SDL 1.5 with zero diagnostics.
- This single pilot establishes the staging v1.5 creation and validation path, not pass status for all 20 component fixtures or production support.

Use this migration map:

| Removed or changed | v1.5 direction |
|---|---|
| `Basic`, `Row`, `Col` | `Box` with `direction="row"` or `direction="col"` |
| `Title`, `Caption` | `Text.variant` |
| `Pressable` | Semantic `Link` or `Button`, native media actions, or verified action-target props |
| `ListView`, `ListViewItem` | Data-driven `Box` composition with list/listitem roles |
| `Label` | `Text` with an appropriate semantic variant |
| `Card.cancel`, `Card.confirm` | Explicit `Button` children |
| `Text.size`, `Text.weight` | One semantic `Text.variant` |
| `Text.width` | Parent `Box` sizing |
| `Text.editable` | No native v1.5 replacement |
| `Checkbox`, `Form` | No native v1.5 replacement; use a truthful external action/static status or an explicitly requested older version |

Namespaced v1.5 action types replace legacy action names and omit the old `handler` field:

```jsx
<Link
  value={linkLabel}
  onClickAction={{ type: "link:navigate", payload: { url: destinationUrl } }}
/>
<Button
  label={buttonLabel}
  onClickAction={{ type: "button:navigate", payload: { url: destinationUrl } }}
/>
<Image
  src={imageUrl}
  alt={imageAlt}
  renderInlineSize={{ value: 320, unit: "pixel" }}
  renderBlockSize={{ value: 180, unit: "pixel" }}
  onClickAction={{ type: "image:navigate", payload: { url: destinationUrl } }}
/>
<Video
  title={videoTitle}
  thumbnailUrl={videoThumbnailUrl}
  renderInlineSize={{ value: 320, unit: "pixel" }}
  renderBlockSize={{ value: 180, unit: "pixel" }}
  onClickAction={{
    type: "video:open-in-overlay",
    payload: { mediaUrl: videoMediaUrl, uniqueId: videoUniqueId },
  }}
  onHoverAction={{
    type: "video:inline-preview",
    payload: { videoUrl: videoPreviewUrl, enableVolumeControl: true },
  }}
/>
```

Other v1.5 action discriminators are `image:open-in-overlay`, `video:navigate`, and `video:popup-preview`.

Report version support per environment and saved template. A staging v1.5 pass must not be generalized to production, and a production v1.3 failure must not be generalized to staging. Continue authoring against the shipped v1.5 contract, record the template ID, environment, creation pin, saved full-validation result, emitted SDL version, diagnostics, and target-host behavior separately.

### SDL v1.4 output shape (BREAKING)

Older output used a flattened component tree. Component props such as `padding`, `gap`, and `width` lived beside `type` and `children`:

```json
{
  "type": "Basic",
  "padding": 0,
  "children": [
    { "type": "Col", "gap": 3, "width": "100%", "children": [] }
  ]
}
```

SDL v1.4 wraps the root node in `component`, declares `sdlVersion` at the document and component levels, and moves component props into a `props` object:

```json
{
  "sdlVersion": "1.4",
  "component": {
    "type": "Basic",
    "sdlVersion": "1.4",
    "props": { "padding": 0 },
    "children": [
      {
        "type": "Col",
        "sdlVersion": "1.4",
        "props": { "gap": 3, "width": "100%" },
        "children": []
      }
    ]
  }
}
```

**Consumer migration rules:**

1. Read the root from `result.sdl.component`, not directly from `result.sdl`.
2. Read component properties from `node.props`, not from `node[propName]`.
3. Preserve and validate `sdlVersion` on the document and every component node.
4. Keep `type` and `children` outside `props`.
5. Leaf components may include `children: []`; consumers must accept this.
6. Do not manually convert JSX into SDL. Use `preview_template` or `validate_template_inline` and consume the returned versioned tree.

---

### Data-driven JSX simplification gate

In this skill, **simplify JSX** means replacing repeated hardcoded item markup and numbered fields with data-driven composition, usually an array plus one `.map()` block. It does not mean changing the visual design, hierarchy, content, spacing, or interaction model unless the user explicitly asks for a redesign.

Run this gate after a template works and before final polish. The goal is reusable JSX with one source of truth for repeated composition, not merely fewer lines.

1. **Write invariants first.** Record the item count, content, actions, component roles, media dimensions, spacing, responsive behavior, and accessibility behavior that must not change.
2. **Move repeated content into data.** Titles, URLs, images, labels, alt text, badges, and per-item anchor names belong in `schemaData`, not repeated inline JSX.
3. **Consolidate repeated branches.** When sibling blocks differ only by numbered fields such as `item1Title` and `item2Title`, normalize them into an `items` array and render one `.map()` branch.
4. **Keep one shared composition.** Write the card, row, tile, or media-overlay JSX once inside `.map()`; do not retain separate hardcoded branches for each item.
5. **Audit each wrapper by responsibility.** Remove a single-child wrapper only when it contributes no sizing, flex behavior, alignment, padding, gap, clipping, radius, border, surface, scrolling, semantic role, or interaction state.
6. **Move props to their owner.** Put media actions on `Image` or `Video`, layout props on `Box`, anchored-overlay props on the anchor and positioned component, and semantic navigation/actions on `Link` or `Button`.
7. **Validate parity, not only syntax.** Compare old and new emitted SDL at the same data and viewport. Check component counts, visible strings, URLs/actions, image sources and dimensions, source attribution, ordering, anchor resolution, and diagnostics before judging the simplification complete.

Preferred repeated-item data shape:

```json
{
  "entities": [
    {
      "sourceIcon": "https://example.com/favicon.ico",
      "items": [
        { "title": "First", "url": "https://example.com/1" },
        { "title": "Second", "url": "https://example.com/2" }
      ]
    }
  ]
}
```

```jsx
{entities[0].items.map((item) => (
  <Box>{/* one shared item composition */}</Box>
))}
```

Keep explicit fields when the items have genuinely different semantic roles or the target host fails the mapped form. Do not use `.slice()` to simulate groups; pre-structure those groups in data.

Hardcoded design constants such as a validated thumbnail size or spacing token may remain in JSX when every repeated item shares them. The content and per-item behavior should be data-driven; the shared design recipe should stay in the single mapped composition.

---

---

## 5) Schema and data configuration (CRITICAL for rendering)

A template will NOT render if schema and data are misconfigured. Common causes:

### Schema must be valid JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "title": { "type": "string" },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "image": { "type": "string" },
          "url": { "type": "string" }
        }
      }
    }
  }
}
```

### Data must exactly match schema shape

```json
{
  "title": "My Title",
  "entities": [
    { "name": "Item 1", "image": "https://...", "url": "https://..." }
  ]
}
```

### Schema/data rules

1. Every key referenced in JSX (`{title}`, `{item.name}`) MUST exist in both schema AND data
2. Types must match: if schema says `"type": "array"`, data must be an array
3. When cloning templates, remap ALL field names — partial renames break rendering
4. Schema and data are both JSON strings when passed to `update_iteration`
5. Nested objects need nested schema definitions — flat schema with nested data will fail
6. Bing SERP typically expects data wrapped in `entities: [{ ... }]` — reference fields as `entities[0].fieldName` in JSX
7. Add null guards in JSX for arrays: `{entities[0].items && entities[0].items.map(...)}`
8. Prefer inlined property definitions for objects referenced directly by JSX.
   Mosaic expression resolution may fail to traverse otherwise valid JSON Schema
   `$ref` definitions. Reuse `$ref` only after the saved template proves the
   complete expression path.
9. When schema data drives a visual enum prop such as `background`, `color`,
   `radius`, or another token-valued property, constrain the schema with the
   exact live-contract enum. Do not expose an unconstrained string as a renderer
   token.

### Production data boundary

Design the schema for the largest data shape the target layout has actually
passed, not an unbounded demo payload.

1. Put every unguarded JSX-bound property in the appropriate JSON Schema
   `required` array. Otherwise add a supported explicit guard and test the
   missing-value branch.
2. Add `maxItems` to repeated collections based on the proven canonical,
   transition, and narrow capacity. Use `minItems` when the composition requires
   at least one item.
3. Add realistic string limits when the current validator supports them, and
   pair them with rendered `maxLines` or an explicit overflow treatment.
4. Keep URL, identifier, numeric-unit, date, and disclosure fields typed and
   separate. Do not concatenate trusted renderer tokens or action types from
   unconstrained data.
5. Test minimum, typical, and maximum valid payloads plus one missing/invalid
   payload. Validation success with one ideal fixture is not production data
   readiness.
6. If the upstream system can exceed the visual budget, reduce or summarize
   upstream with a visible truthful continuation treatment. Do not hide
   answer-bearing content merely to preserve the canonical height.

### Data shape patterns (NEW in v2.2)

Three proven patterns — choose based on your template's needs:

**Pattern A: Flat array** — best for scrollable carousels, simple lists

```json
{ "entities": [{ "title": "...", "image": "...", "url": "..." }, ...] }
```
```jsx
{entities.map((item) => ( <Box>...</Box> ))}
```

**Pattern B: Nested wrapper** — best for single-entity cards with sub-items

```json
{ "entities": [{ "sectionTitle": "...", "items": [{ "name": "...", ... }] }] }
```
```jsx
<Text value={entities[0].sectionTitle} variant="title-lg-strong" />
{entities[0].items.map((item) => ( <Box>...</Box> ))}
```

**Pattern C: Row-split** — best for fixed grids (avoids `.slice()` which is NOT supported)

```json
{ "row1": [{ "title": "..." }, ...], "row2": [{ "title": "..." }, ...] }
```
```jsx
<Box direction="row">{row1.map((item) => ( <Box>...</Box> ))}</Box>
<Box direction="row">{row2.map((item) => ( <Box>...</Box> ))}</Box>
```

**Pattern D: Explicit fields** — best for small fixed lists (most reliable in Bing SERP)

```json
{ "entities": [{ "label1": "Area", "value1": "2M acres", "label2": "Elevation", "value2": "5,282 ft" }] }
```
```jsx
<Box direction="row"><Text value={entities[0].label1} /><Text value={entities[0].value1} /></Box>
<Box direction="row"><Text value={entities[0].label2} /><Text value={entities[0].value2} /></Box>
```

> **`.map()` reliability note:** `.map()` works in Mosaic preview but may fail in Bing SERP for certain card types (especially `<Card>` root with nested maps). For small fixed-count lists (e.g. 6 fact rows), use explicit fields (Pattern D) — it's the most reliable. Use `.map()` for variable-length data like entity carousels.

### Static relationship exception

Do not generate versioned relationships with `.map()` when the validator must
prove the relationship statically. GTX Scenario 23 required explicit
`Tabs.Panel` declarations so every `Tabs` item, panel `id`, and `tabId` could be
resolved during validation. Map ordinary repeated rows, cards, images, and
badges; keep panels and other cross-node ID relationships explicit unless a
saved target-surface probe proves the mapped form.

### Required-prop interpretation

Do not equate every normalized contract field marked `required` with a value
the author must write. Some runtime-required fields have contract defaults and
are omitted by the exact-version `basicUsage`.

When answering or authoring, separate:

1. Minimum author inputs from the exact-version `basicUsage`.
2. Defaulted props that can be omitted by authors.
3. Variant-, action-, or child-dependent props.
4. Saved-validation and target-host requirements.

For SDL v1.5 `Image`, the established minimum author inputs are `src`,
`renderInlineSize`, and `renderBlockSize`. Supply truthful `alt` for informative
images. Recheck the live contract before relying on remembered defaults such as
`fit`, `position`, `frame`, `flush`, or `expandActionTarget`.

---

---

## 6) Component inventory

> **LIVE CONTRACT REQUIRED:** The default inventory below is the shipped v1.5 contract. The current MCP component index can still report v1.3, so reconcile it with the matching v1.5 manifest/reference before authoring. A prop can parse and preview yet still fail surface version resolution.

### Layout

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `Card` | Card surface and general container | `background`, `border`, `size`, `status`, `padding`, `actionTarget`, `actionTargetHoverBehavior` |
| `Box` | General row/column layout and grouping | `direction`, `align`, `justify`, `wrap`, `gap`, sizing, scrolling, roles, `anchorPositioning`, action-target props |

`Basic`, `Row`, and `Col` are removed in v1.5. Use `Box` and its `direction` prop for all new work.

### Content

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `Text` | All text roles | `value`, `variant`, `color`, alignment, truncation, `textIndent`; `Title` and `Caption` are removed |
| `Image` | Image display and image-native action | `src`, `alt`, render/source sizes, `fit`, `radius`, `onClickAction`, `expandActionTarget` |
| `Video` | Native video thumbnail, preview, and playback | `title`, `thumbnailUrl`, metadata, original/render sizes, namespaced click/hover actions |
| `Icon` | Icon glyph | `name` (e.g. `"play-filled"`, `"star-filled"`), `size`, `color` |
| `Markdown` | Schema-bound rich text | `value`, `streaming` |
| `Badge` | Compact status or category | `label`, `size`, `color`, `variant`, `ariaLabel` |

### Actions and structured content

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `Link` | Semantic navigation text | `value`, `variant`, `underline`, `onClickAction`, icons, `expandActionTarget` |
| `Button` | Explicit action control | `label`, `variant`, `color`, `size`, `onClickAction`, `expandActionTarget` |
| `Tabs` / `Tabs.Panel` | Related views with selected state | `label`, `tabItems`, `selectedTabIndex`; panel `id` and `tabId` |
| `ProgressBar` | Progress or meter | `role`, `currentValue`, `minValue`, `maxValue`, shape and track props |
| `Table` / `Table.Row` / `Table.Cell` | Exact structured values | `title`, `density`; row `header`; cell alignment, spans, and `inlineSize` |
| `Chart` | Data visualization | `data`, `series`, `xAxis`, display and sizing props |
| `Map` | Map with pins (leaf) | `markers` (array), `initialViewState` (object), `width`, `height` |
| `Divider` / `Spacer` | Visual or spatial separation | Divider styling and spacing; Spacer `minSize` |

`Pressable`, `Form`, `Checkbox`, `ListView`, and `ListViewItem` are removed in v1.5. Do not recreate form controls or inline editing with misleading static components.

#### v1.5 Table runtime guidance

Keep header cells structurally simple. On staging `bing-acf-card` template
`YTpRAm1TkuPk6aHLSNRE2`, iteration 2, a header `Table.Cell` containing a vertical
`Box` with product name, price, and intended use passed saved full validation and
previewed without diagnostics, but the rendered snapshot displayed only the
first child. The reliable composition uses one product-name `Text` per header
cell and moves price and intended use into aligned body rows.

For comparison tables:

1. Use one concise `Text` in each header cell.
2. Put secondary product metadata in the first body rows so all products remain
   aligned.
3. Set `Table.density` deliberately. Compact density is appropriate for tight
   zones; normal density used the 6x4 height more effectively in the verified
   comparison.
4. Give the feature and product columns explicit `inlineSize` values.
5. Require a target-size screenshot even after saved validation and preview pass.

The current `check_card_budget` estimator can model sibling `Table.Cell`
children as vertically stacked full-width blocks and report a large false
overflow. Record the discrepancy, but do not waive the visual gate: confirm the
saved viewport metadata and inspect a real target-size snapshot. The verified
6x4 comparison rendered all six body rows, disclosure, and action without
clipping despite the estimator overflow result.

#### v1.5 circular ProgressBar runtime guidance

Treat full circular progress as a cross-layer contract mismatch until the target
renderer is fixed.

Verified on 2026-10-14 with staging `bing-acf-card` template
`Vtr7SerwarDMcSgXdxMbt`, iteration 2:

- Saved full validation passes at SDL v1.5.
- API preview emits `full`, `half`, and `three-quarter` circular ProgressBars
  with identical `role`, thickness, dimensions, and 5-of-8 values.
- The target host renders `half` and `three-quarter` but leaves `full` blank.
- The hook test reports:

  ```text
  [Violation][ACF_]
  callerFileName: Sdl_v1dot5_ProgressBar
  callerMemberName: RenderView
  validation failed: ArcGapPosition is missing or unknown
  ArcSweep: full
  ArcGapPosition: null
  ```

The two layers currently require incompatible inputs:

1. SDL v1.5 allows `arcGapPosition` only for open `half` and
   `three-quarter` tracks. A full circle must omit it.
2. The target `Sdl_v1dot5_ProgressBar` implementation rejects the resulting
   null `ArcGapPosition` for `ArcSweep=full`.
3. Adding `arcGapPosition` to the full node is not a valid workaround because
   the saved SDL v1.5 gate rejects that configuration.

Use explicit nodes when comparing the three sweeps so the full node can omit
the open-track-only prop:

```jsx
<ProgressBar
  role="progressbar"
  shape="circular"
  arcSweep="full"
  currentValue={currentValue}
  minValue={minValue}
  maxValue={maxValue}
/>
<ProgressBar
  role="progressbar"
  shape="circular"
  arcSweep="half"
  arcGapPosition="block-end"
  currentValue={currentValue}
  minValue={minValue}
  maxValue={maxValue}
/>
<ProgressBar
  role="progressbar"
  shape="circular"
  arcSweep="three-quarter"
  arcGapPosition="block-end"
  currentValue={currentValue}
  minValue={minValue}
  maxValue={maxValue}
/>
```

For diagnosis:

- Do not attribute this failure to progress reaching 100%; the verified fixture
  fails at 5 of 8.
- Prefer one side-by-side target capture over separate captures so every other
  variable remains constant.
- In hook output, prioritize the component-specific `[Violation][ACF_]` entry.
  Unrelated page-level Model and Ranking messages do not explain the isolated
  ProgressBar failure unless separate evidence links them to the component.
- Keep exact progress text visible as the accessibility and renderer fallback.
- Track the renderer defect in ADO
  [#11347610](https://dev.azure.com/msasg/24a0501b-d131-45af-ae52-27db9291efd4/_workitems/edit/11347610).

#### v1.5 Map runtime guidance

For a bounded nearby-place answer, keep the map contextual and the list
semantics truthful:

1. Give `Map` an explicit numeric height and full parent width.
2. Bind `markers` and `initialViewState` directly from schema data.
3. Connect static rows to markers with matching short labels such as A–C.
4. Do not add row actions or selected styling unless row activation really
   changes the map state in the target host.
5. Keep place names, coordinates, distances, freshness, and demo status
   schema-bound.
6. Remember that provider-rendered background labels can show real businesses
   even when the overlaid markers are fictional. Make the fixture disclosure
   explicit.

Verified on 2026-10-13 with staging `bing-acf-card` template
`bNzkRyEJza5dVYodvpjhM`, iteration 2: a 156px map plus three static place rows,
disclosure, and link rendered without clipping at 4x4 and passed saved full
validation at v1.5.

The current `check_card_budget` estimator counted that explicit 156px `Map` as a
26px leaf. Treat the budget result as incomplete for Map compositions and use
the saved target-size snapshot as the fit authority.

### Important v1.5 prop rules

```jsx
// Text uses one semantic variant instead of Title/Caption or size + weight.
<Text value={title} variant="title-lg-strong" />
<Text value={source} variant="caption-xs" color="tertiary" />

// textIndent uses a size object, not a bare number.
<Text
  value={quote}
  variant="body-md-strong"
  textIndent={{ value: 22, unit: "pixel" }}
/>

// Box replaces Basic, Row, and Col.
<Box direction="row" gap={2}>
  <Text value={leftValue} variant="body-md" />
  <Text value={rightValue} variant="body-md-strong" />
</Box>

// Use semantic, namespaced actions without handler.
<Link
  value={linkLabel}
  onClickAction={{ type: "link:navigate", payload: { url: linkUrl } }}
/>
<Button
  label={buttonLabel}
  onClickAction={{ type: "button:navigate", payload: { url: buttonUrl } }}
/>
<Image
  src={imageUrl}
  alt={imageAlt}
  renderInlineSize={{ value: 320, unit: "pixel" }}
  renderBlockSize={{ value: 180, unit: "pixel" }}
  onClickAction={{ type: "image:navigate", payload: { url: imageUrl } }}
/>

// Text still uses value, never JSX children.
<Text value={title} variant="body-md" />
<Text>{title}</Text> // invalid

// Pre-structure groups in data; do not use unsupported array slicing.
entities[0].row1.map((item) => <Text value={item.title} variant="body-md" />)
```

For maintenance of existing v1.3/v1.4 templates, retain their original component and action contracts. Do not mix legacy `Pressable`, `handler: "client"`, `Image.width`/`height`, or non-namespaced actions into new v1.5 JSX.

#### v1.5 Text.textIndent contract correction

Use a size object for first-line indentation:

```jsx
<Text
  value={quote}
  variant="body-md-strong"
  textIndent={{ value: 22, unit: "pixel" }}
/>
```

Verified on 2026-10-15 with staging `bing-acf-card` template
`yTH5dhEVWrC2S682mV7fA`, iteration 9:

- Saved full validation passes with component version resolution at v1.5.
- Preview emits SDL 1.5 with zero diagnostics.
- A 312x424 target capture shows that the 22px first-line indent clears an
  anchored 20px quote icon without shifting subsequent lines.

The captured readiness manifest described `textIndent` as `type: "number"`,
but bare numeric forms such as `textIndent={24}` fail saved validation with
`Number value for 'Text.textIndent' is not valid in v1.5`. Treat this as a
discovery-manifest mismatch: use the verified size-object form and require
saved validation plus target-host confirmation.

---
