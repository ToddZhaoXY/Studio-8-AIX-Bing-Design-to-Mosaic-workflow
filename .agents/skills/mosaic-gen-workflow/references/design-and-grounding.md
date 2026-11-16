# Design, References, and Grounding

Use this reference when selecting a concept, choosing a working Mosaic reference, grounding claims, or reviewing visual fidelity.

### Companion design workflow

Use the local companion skills when they are installed. The standalone governance below remains mandatory when they are unavailable.

1. **`serp-composition`** owns the concept: query intent, lead answer, content roles, representation choice, body structure, data-shape needs, and narrow-width reading order.
2. **`mosaic-gen-workflow`** owns feasibility and implementation: reference selection, live schema discovery, JSX, JSON Schema, `schemaData`, version compatibility, preview, and full validation.
3. **`serp-design-critique`** owns rendered judgment: hierarchy, coherence, data integrity, responsive behavior, accessibility, provenance, and interaction truth in the target host.

When the user asks only for concept creation or body-layout brainstorming, apply `serp-composition` when available or the standalone concept rules below. Stop after the concept tradeoffs and feasibility notes. Stop before any template mutation or iteration mutation; do not create a template or iteration until implementation is requested or a direction is chosen.

When implementation is requested, convert the chosen concept into this handoff before writing JSX:

```text
Target design surface and zone:
Primary intent and lead:
Chosen body structure:
Content roles and order:
Required data shape:
Primary reference template:
Verified components and props:
Wide and narrow behavior:
Visualization fallback:
Grounding and disclosure requirements:
```

Treat component roles proposed during brainstorming as hypotheses. Exact Mosaic component names, props, containment, and version support become facts only after live discovery, matching-version reference review, and saved full validation.

For deeper data-visualization guidance, use `serp-composition` when it is installed. Otherwise use the standalone matrix below. In both cases, verify that the target Mosaic contract can implement the representation. If it cannot, fall back to a supported chart, ranked rows, a compact table, or a prominent metric without changing the underlying claim.

### Standalone design coherence governance

This section makes the Mosaic skill sufficient on its own. Apply it before reference selection or JSX authoring.

#### Intent and content brief

Write one line for each item:

```text
Audience and decision:
Primary intent:
Lead answer:
Supporting questions:
Grounded evidence and freshness:
Content roles: answer | explanation | evidence | exploration | action
Body structure:
Narrow-width reading order:
Content omitted or combined:
```

If the lead cannot be stated in one sentence, do not choose a layout yet. Resolve the answer hierarchy first.

#### Concept rules

When the direction is open, generate two or three structural concepts using the same facts. Vary one primary axis such as hierarchy, grouping, sequence, comparison model, density, or disclosure. Do not create cosmetic alternatives that differ only in color, radius, or decoration.

Useful structural directions:

- **Anchor and evidence:** one lead fact, metric, or media item followed by compact proof.
- **Paired comparison:** aligned peer entities or periods using the same fields and scale.
- **Ranked scan:** ordered rows or bars when rank and magnitude matter.
- **Guided sequence:** chronological moments, steps, or causes.
- **Browsable set:** repeated peers in a verified scroll or wrap pattern.
- **Detail first:** compact facts or a table when exact values matter most.

For each concept, state its body organization, required data shape, likely component roles, narrow behavior, strength, and cost. Recommend one only when the intent, data volume, usage frequency, and target zone establish a clear winner.

#### Coherence rules

1. Give the card one clear lead through order, span, media, or ACF-supported text emphasis.
2. Give every block one job. Remove repeated summaries, metrics, images, and actions.
3. Treat peer items consistently; do not give unequal visual weight to equivalent data.
4. Make spacing between conceptual groups greater than spacing within a group, using only verified Bing tokens.
5. Align related content to shared edges and use separators only when dense content needs them.
6. Keep controls visually distinct from content and place related actions together.
7. Preserve answer, explanation, evidence, then exploration when a wide layout wraps or stacks.
8. Keep required units, dates, scope, provenance, and disclosures visible at every supported width.
9. Use the smallest verified component set that expresses the structure. Every wrapper must own layout, sizing, clipping, surface, semantics, or interaction.
10. Use one visual language: Bing ACF semantic components and tokens. Market examples may influence reasoning, never styling.

#### Standalone visualization matrix

| User question | Prefer | Avoid |
|---|---|---|
| What is the current result? | Prominent metric with unit and timestamp | Charting one useful point |
| How did it change over time? | Line chart or sparkline | Donut or unordered cards |
| Which item is larger? | Sorted bars or aligned comparison rows | Unrelated gauges |
| What is the range or target? | Labeled range rail | Decorative progress ring |
| How is a whole composed? | Stacked bar; donut only for a few stable parts | Many slices or unlabeled color blocks |
| What caused the change? | Waterfall or ordered contribution bars | Pie chart |
| What are the exact values? | Table or key-value rows | A chart that hides precision |
| What happened in sequence? | Annotated timeline | Disconnected stat cards |

Use a visualization only when the data contains enough compatible points and the result remains readable at the target width. Show the question, unit, time range, source, freshness, and key takeaway. Preserve missing observations as missing, keep parts reconciled to totals, and never encode meaning through color alone.

#### Standalone critique gate

After full validation, inspect the rendered target host at its widest and narrowest relevant widths and in both themes when supported. Check:

- The primary answer is the first visual landing point.
- Every region answers a distinct sub-intent.
- No nearby block repeats the same takeaway.
- The chosen representation is simpler than its alternatives without losing meaning.
- Charts preserve baselines, totals, ordering, intervals, labels, units, and provenance.
- Narrow layouts preserve semantic reading order without clipping critical content.
- Images load, controls work, selected state persists, and meaning survives without color or motion.
- The result looks native to the chosen Bing reference rather than to an imported design system.

Separate evidence into measured validator results, observed render behavior, and inferred design judgment. Fix data integrity, hidden answers, broken interactions, and narrow-width failures before aesthetic polish.

For the exact three-width responsive protocol, media acceptance gates, composite
action-target recipe, and fixed-height capture caveats proven by the GTX set,
use [the GTX responsive and media QA reference](./gtx-responsive-media-qa.md).

> **SDL status (verified 2026-10-09):** Mosaic's live changelog exposes schema comparisons through v1.5. Staging `bing-acf-card` template `CCbeNWTiNTU583Net4kDy`, iteration 4, saves a complete schema-bound v1.5 template, passes saved full validation with component version resolution at v1.5, and renders the verified favicon-led source treatment in the staging canvas when the source Link omits explicit `variant` and `color`. The current API preview path disagrees and reports `GENUI4001` claiming `LinkProps.onClickAction` is missing even though the JSX contains it. Production availability remains a separate gate because existing production templates are pinned to v1.3. The v1.4 release notes explicitly list `Video` as a component added in v1.4; the verified v1.4 Video template emits SDL v1.4 but remains preview-only.

> **Schema-source caveat:** Mosaic MCP `search_schema`, `describe_component`, and `list_layout_props` can expose a reduced component-oriented index that omits shared v1.4 reference props. For version-specific shared contracts, reconcile MCP discovery with the v1.4 reference gallery. Absence from MCP discovery alone does not prove that a shared SDL feature is unavailable.

---

## 3) Reference-first workflow (UPDATED in v2.12)

**CRITICAL: Never invent a layout from scratch.** Always fetch a working reference template first, study its JSX/schema/data shape, then adapt with your own data and scenario needs.

### Why this matters

LLMs that skip this step produce templates with:
- Invented props that don't exist (`minWidth`, `background="surface-secondary"`, `truncate`, `textAlign`)
- Wrong layout patterns for the zone (vertical stacks in scrollable zones, carousels in grid zones)
- Schema/data shapes that don't match proven Bing rendering patterns

### Reference workflow

```python
# 1. Fetch a working template that resembles your target
ref = mcp_call('get_template', {'id': 'REFERENCE_TEMPLATE_ID'})
ref_it = next(
  item for item in ref['iterations']
  if item['iteration'] == ref['currentIteration']
)

# 2. Study its JSX structure, schema shape, and data shape
print(ref_it['jsxTemplate'])   # ← Learn the layout pattern
print(ref_it['schema'])        # ← Learn the data shape
print(ref_it['schemaData'])    # ← Learn field naming conventions

# 3. Adapt — keep the proven JSX structure, swap in your data
# Tweak layout as needed based on YOUR data count, interaction intent, and zone
```

### Build a Mosaic fidelity brief before coding

Choose one primary visual reference with the same design surface, zone, content type, and interaction intent. Use at most one secondary reference for a component pattern the primary reference does not contain. Combining unrelated patterns usually produces a template that is valid but does not look native to Mosaic.

Inspect the matching SDL version in the reference gallery, including Overview, Gallery, and Changelog. Expand the exact component or shared-reference rows needed by the design. From the primary reference, record this compact fidelity brief in working notes:

- **Composition:** root type, major regions, ordering, and visual hierarchy
- **Geometry:** zone, tracks, fixed or flexible dimensions, aspect ratios, and wrapping thresholds
- **Rhythm:** gap, padding, margin, border, and radius tokens
- **Typography:** title/body/caption roles, sizes, weights, line limits, and color roles
- **Media:** image role, crop position, fit, framing, and loading/source constraints
- **Interaction:** pressable area, actions, controls, states, focus order, and accessibility roles
- **Responsiveness:** what resizes, wraps, scrolls, hides, or reorders at narrow and wide widths
- **Distinctive details:** the two or three choices that make the reference recognizably Mosaic rather than a generic card

Preserve this fingerprint unless the supplied data or user goal requires a deviation. State material deviations in the template notes. Copy structure and design behavior, not the reference's content or unsupported assumptions.

### Visual comparison loop

After the candidate passes full validation:

1. Render the reference and candidate at the same host width and theme.
2. Compare geometry first: outer bounds, region proportions, alignment, image crop, and whitespace.
3. Compare hierarchy second: typography, color roles, borders, radii, and control emphasis.
4. Fix the largest visible mismatch with one focused edit, then rerun validation.
5. Repeat at the narrowest and widest relevant host widths; verify wrapping, scrolling, truncation, and interaction states.

When both views are browser-accessible, use screenshots at identical viewport dimensions rather than visual memory. Do not polish minor color or icon details while the composition or responsive behavior still differs.

### When to deviate from the reference

References are starting points, not fixed rules. Adapt when:
- Your data has more/fewer items than the reference
- The interaction intent is different (browse vs compare vs scan)
- The zone size changes the available space
- The content type needs different emphasis (image-heavy vs text-heavy)

### Common clone: algorithmic site-result card

The common clone for official-site and navigational queries is the Bing algorithmic result card. The known source template is `nWT3XrQiVyLuDiSYz9J4V` (`algo card`). Template `6qGmXitka5P7mhww48nL9` follows the same structure with Nike data and tighter `maxLines` constraints.

These are legacy structural references. For new v1.5 work, preserve their hierarchy while translating the component contract: `Basic`/`Row`/`Col` become directional `Box`, `Title`/`Caption` become `Text.variant`, and `Pressable` links become `Link`.

**Visual anatomy:**

1. A zero-padding root allowed by the v1.5 surface so the result reads as native SERP content.
2. One full-size bordered vertical `Box` with medium radius, 20px padding, and 12px section gaps.
3. Site-identity row: 28px circular favicon beside site name and display URL.
4. Primary result block: large accent-colored linked title followed by a two-line tertiary description.
5. Sitelink area: three rows with two equal columns per row, producing a fixed $2 \times 3$ matrix.
6. Each sitelink uses an accent linked title and a compact two-line tertiary snippet.
7. Semantic roles mirror the visual structure: the outer sitelink group is `role="list"`; each pair is `role="listitem"`; destinations use semantic `Link`.

**Data pattern:**

```json
{
  "entities": [
    {
      "favicon": "...",
      "siteName": "...",
      "siteUrl": "...",
      "url": "...",
      "title": "...",
      "description": "...",
      "sitelinkRows": [
        {
          "left": { "title": "...", "url": "...", "snippet": "..." },
          "right": { "title": "...", "url": "...", "snippet": "..." }
        }
      ]
    }
  ]
}
```

**Design pattern:** identity first, one dominant answer second, navigation choices third. Equal columns and repeated title/snippet rhythm make the lower area easy to scan without competing with the primary result. Accent is reserved for navigation, while tertiary text carries provenance and supporting detail.

Use this clone for brand, organization, product-homepage, and other navigational queries with several strong destinations. Do not use it for comparison, image browsing, changing item counts, or tasks with one primary action; choose a grid, carousel, or utility layout instead. Treat the source as a structural reference and run current full validation before publishing.

### Inspect the live SDL contract before adapting

The current MCP exposes component-oriented discovery tools. Use them before writing or changing JSX:

```python
# Find components, icons, and color tokens.
mcp_call('search_schema', {'category': 'components', 'query': 'link'})
mcp_call('search_schema', {'category': 'icons', 'query': 'arrow'})
mcp_call('search_schema', {'category': 'colors', 'query': 'accent'})

# Get exact props, enum values, containment, and detailed guidance.
mcp_call('describe_component', {'name': 'Link'})
mcp_call('get_component_guide', {'name': 'Link'})
mcp_call('component_containment', {})
mcp_call('list_text_styles', {})
mcp_call('get_color_reference', {})
mcp_call('design_checklist', {})
```

For component-local props, live schema results supersede old examples and remembered prop rules. Props such as `inline`, `background`, `minWidth`, `flush`, `disabled`, `ariaLabel`, and accessibility `role` values can differ by SDL/component version. For shared SDL reference types such as `anchorPositioning`, apply the version-aware freshness gate and do not treat an empty MCP search result as proof of absence.

For color-sensitive work, use current semantic color tokens rather than copying rendered hex values or choosing a token by hue alone. Match the reference's semantic role, such as surface, foreground, link, status, or border, then verify the result in both light and dark themes. A token that visually matches in one theme but changes meaning or loses contrast in the other is not a valid match.

---
