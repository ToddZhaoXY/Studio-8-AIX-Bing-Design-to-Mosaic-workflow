# Responsive Layouts

Use this reference for layout selection, wrapping, flex geometry, zone recipes, and narrow-width reading order. Complete runtime acceptance with the GTX responsive and media QA reference.

## Two-level responsiveness model

Responsive planning has two distinct levels. Plan them in this order.

### 1) Section-level responsiveness

Section-level responsiveness changes the composition of major semantic regions.
Examples include an answer and media rail moving from side by side to stacked,
a hero separating from its supporting grid, or a wrapped gallery group filling
a new row.

For every major section, record:

| Decision | Required answer |
|---|---|
| Semantic purpose | What user intent does this section serve? |
| Preferred width | What width preserves the intended composition? |
| Minimum usable width | Below what width is the section no longer usable? |
| Growth ownership | Which section absorbs surplus width? |
| Reflow threshold | At what calculated width must major sections wrap? |
| Wide arrangement | Which sections share a row? |
| Stacked arrangement | Which sections occupy new rows and whether they fill them? |
| Narrow reading order | What semantic order must JSX preserve after reflow? |
| Expanded height | Can the host grow, scroll, or clip when sections stack? |

Use section-level reflow when keeping major regions side by side would make a
primary region narrower than its minimum usable width. Do not wait until text
technically overflows; a 169px answer rail can wrap without remaining usable.

### 2) Content-level responsiveness

Content-level responsiveness adapts the material inside one section without
changing the section's semantic role or major position. Examples include
inline wrapping, shrinkable flex children, a peer scroller, table density,
image crop, proportional media tracks, line clamping, or chart-label
adaptation.

For each section, record:

| Decision | Required answer |
|---|---|
| Natural wrapping | Which text and inline groups may wrap? |
| Shrink behavior | Which children use flex shrink or `minWidth={0}`? |
| Overflow strategy | Does a bounded peer collection wrap, scroll, or reduce columns? |
| Density strategy | Which optional details may become more compact? |
| Truncation policy | Which noncritical text may use `maxLines`? |
| Media behavior | Does media crop, clamp, preserve a ratio, or request a larger render budget? |
| Control behavior | Do actions remain visible, focusable, and in reading order? |
| Block-size behavior | Does content grow vertically, scroll, or require a larger host? |

Use this decision order:

1. Allow natural text and inline-group wrapping.
2. Let intended flexible children shrink safely.
3. Rebalance internal tracks or reduce a grid's column count.
4. Reduce optional density without hiding grounding or primary evidence.
5. Scroll only when the content is a peer collection meant for browsing.
6. Truncate only content whose omitted portion is noncritical.
7. Scale or crop media with verified subject visibility.
8. Never scale essential text below the design-system typography.

### Required planning sequence

Before JSX, write:

```text
Section-level plan:
- Major sections:
- Preferred and minimum widths:
- Growth ownership:
- First reflow threshold:
- Wide arrangement:
- Stacked arrangement:
- Narrow semantic order:
- Expanded-height behavior:

Content-level plan:
- Section name:
  - Inline wrapping:
  - Shrinkable children:
  - Scroll/wrap/density strategy:
  - Truncation policy:
  - Media behavior:
  - Control and focus behavior:
```

Section-level planning comes first because it determines the actual width
available to each section. Then plan content-level behavior for every resulting
wide, transition, and narrow state.

Do not use a content-level technique to conceal a section-level failure:

- Do not shrink a primary answer below its usable minimum merely because its
  text still wraps.
- Do not introduce a scroller for the primary answer to avoid wrapping major
  sections.
- Do not truncate required grounding, units, dates, disclosures, or actions to
  preserve an unsuitable side-by-side layout.
- Do not reduce media or text to unreadable sizes when the containing sections
  should reflow.
- Do not call a composition responsive when only its outer sections reflow but
  internal content still clips or overflows.

Mark section-level responsiveness `not-applicable` for a single fixed region
that never changes major composition. Mark content-level responsiveness
`not-applicable` only when its internal layout truly has no width-dependent
behavior.

## Layout decision framework

> **Zone size does NOT dictate layout pattern.** A 3×2 can scroll inline; a 6×4 can be a static grid. Choose layout based on data and interaction intent, then adapt to the zone.

### Decision factors

| Factor | Grid (`wrap="nowrap"`, fixed rows) | Scrollable (`scrollable={true}`) |
|--------|-------------------------------------|----------------------------------|
| **Item count** | Fixed/small (3–9), known at design time | Variable/large (5+), may grow |
| **User intent** | Compare, scan all at once | Browse, discover, explore more |
| **Data shape** | Pre-split into `row1`/`row2`/`row3` | Flat array with `.map()` |
| **Content type** | Overview facts, comparison grids | Entity cards, image galleries |
| **Zone context** | Standalone answer block | Inline section within page |

### Responsive left/right reflow pattern

Use this when a design has meaningful left and right groups that should sit side by side on wide hosts and stack vertically on narrow hosts. It scales beyond image walls to paired result groups, media/detail layouts, comparison sections, and main-content/sidebar compositions.

Pre-structure the data into explicit balanced sets such as `leftSet` and `rightSet` or `columnSet1` and `columnSet2`. Do not use `.slice()` in Mosaic JSX.

```jsx
<Box direction="row" width="100%" gap={6} justify="start" align="stretch" wrap="wrap">
  <Box direction="row" flex={1} minWidth={312} gap={6} align="stretch">
    {/* left set */}
  </Box>
  <Box direction="row" flex={1} minWidth={312} gap={6} align="stretch">
    {/* right set */}
  </Box>
</Box>
```

**Behavior:**

1. Wide: both sets share one row and `flex={1}` makes them expand equally across all available width.
2. Narrow: once `2 × minWidth + gap` no longer fits, `wrap="wrap"` moves the second set below the first; each wrapped set expands to fill its row.
3. Keep the same gap token at each sibling level when the gutters should look uniform.
4. Do not combine fixed-width sets with `justify="between"`; leftover width is added to the center gutter, making it larger than the internal gutters.
5. Verify both wide and narrow hosts: no unused right-side space, equal center/internal gutters, no squeezed columns, and a clean vertical stack after wrapping.

**Known reference:** Yellowstone Scenic Image Wall `r1xMJVPbAtGNCmQwrHGk9`, iteration 4, provides the legacy structure. Translate its row groups to directional `Box` and its image dimensions/actions to the v1.5 contract.

### Tabs inside fixed-height layouts

Keep `Tabs` natural-height. In observed stretched or fixed-height layouts,
putting `height`, `height="100%"`, or `flex={1}` on `Tabs` or its immediate
layout chain can make the renderer miscalculate the space for the tab header
and active panel.

Use this repair order:

1. Remove stretch sizing from `Tabs`.
2. Remove unnecessary `height`, `height="100%"`, or `flex={1}` from its
   immediate layout chain one variable at a time.
3. Put the desired padding, gap, and content sizing inside each `Tabs.Panel`.
4. Avoid `justify="between"` on the column that owns `Tabs`; it can distribute
   spare height around the tab region.
5. Verify every active panel in the target host, not only the initially
   selected panel.

This is observed renderer-layout behavior, not a universal SDL contract rule.
Preserve a fixed outer answer viewport only when the target surface requires
it; do not force that height onto `Tabs`.

### Zone reference recipes

These are starting points — tweak based on data and scenario:

#### 12x2 Answer/Review row

- Root: live v1.5 root, normally `Box` or `Card` as allowed by the target surface
- Layout: `<Box direction="row" scrollable={true}>` + fixed-width child cards
- Keep title + one body line + attribution compact
- Good for: entity carousels, review snippets, browseable lists

#### 6x4 Hero media card

- Root: `<Card>` or `<Box>` according to the v1.5 containment contract
- Can be: large image hero, 2-row or 3-row grid, or even scrollable if data warrants
- Explicit image dimensions and `fit="cover"`
- Good for: media-forward features, attraction grids, comparison layouts

#### 3x4 Overview/facts card

- Root: `<Card>`
- Top: title + short narrative
- Middle: fact rows (`label` + `value`) — use explicit fields for reliability
- Bottom: compact schema-bound source `Link`
- Good for: quick facts, stats, entity overviews

#### 3x2 Utility card (video/weather/inline scroll)

- Root: `<Card>` or `<Box>` according to the v1.5 containment contract
- Use compact typography such as `variant="caption-xs"` or `variant="body-md"`
- Can scroll inline if data has many items (e.g. horizontal pill strip, mini carousel)
- Good for: video thumbnails, weather forecasts, compact entity strips, maps

---
