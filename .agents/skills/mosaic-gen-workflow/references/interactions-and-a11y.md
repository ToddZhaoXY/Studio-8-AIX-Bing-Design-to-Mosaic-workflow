# Interactions and Accessibility

Use this reference for anchor positioning, native component actions, wrapper ownership, expanded targets, and accessibility-sensitive interaction decisions. Pair it with the GTX runtime QA reference for pointer and keyboard acceptance.

### SDL v1.4+ anchor positioning

Reference: <https://afd-mosaic-f6e8eycvfaeffkam.b02.azurefd.net/components/anchor-positioning>

SDL v1.4 defines a shared `anchorPositioning` prop for declaring named anchors and attaching other elements to their logical edges. This contract was verified against Mosaic's generated v1.4 `Box` manifest on 2026-09-02:

- `anchor: { anchorName }` declares the current element as an anchor. `anchorName` is a non-empty string and must be unique within the template.
- `anchorPositioned: { positionAnchor, inset, margin? }` attaches the current element to an anchor. `positionAnchor` must match an `anchorName` declared elsewhere.
- `positionAnchor` and `inset` are required when using `anchorPositioned`; `margin` is optional.
- An element may use both fields to participate in an anchor chain.
- `inset` accepts `blockStart`, `blockEnd`, `inlineStart`, and `inlineEnd`. Each edge accepts `start`, `center`, or `end`; omitted edges are unconstrained.
- `margin` accepts the same four logical edge names with spacing tokens `none`, `xxxs`, `xxs`, `xs`, `sm`, `md`, `lg`, `xl`, or `xxl`.
- The nested objects reject additional properties.

Known pattern, adapted to the v1.5 component set:

```jsx
<Box direction="col">
  <Box anchorPositioning={{ anchor: { anchorName: 'photo' } }}>
    <Image
      src={image.src}
      alt={image.alt}
      renderInlineSize={{ value: 320, unit: 'pixel' }}
      renderBlockSize={{ value: 180, unit: 'pixel' }}
    />
    <Badge
      label={badgeLabel}
      anchorPositioning={{
        anchorPositioned: {
          positionAnchor: 'photo',
          inset: { blockStart: 'start', inlineStart: 'start' },
          margin: { blockStart: 'xxs', inlineStart: 'xxs' },
        },
      }}
    />
  </Box>
</Box>
```

For repeated anchored compositions, keep the anchor name in data and make it unique per mapped item. Do not hardcode one shared anchor name inside `.map()`:

```jsx
{entities[0].items.map((item) => (
  <Box anchorPositioning={{ anchor: { anchorName: item.anchorName } }}>
    <Image
      src={item.image}
      alt={item.alt}
      renderInlineSize={{ value: 320, unit: "pixel" }}
      renderBlockSize={{ value: 180, unit: "pixel" }}
    />
    <Badge
      label={item.label}
      anchorPositioning={{
        anchorPositioned: {
          positionAnchor: item.anchorName,
          inset: { blockStart: "start", inlineStart: "start" },
          margin: { blockStart: "xxs", inlineStart: "xxs" },
        },
      }}
    />
  </Box>
))}
```

Treat anchor placement and overflow as separate concerns:

1. `anchorPositioning` places an element relative to a named anchor; it does not guarantee that ancestors allow content to render outside their bounds.
2. Check every ancestor that contributes clipping, radius, fixed dimensions, or a surface boundary. Do not invent an `overflow="visible"` prop unless the live contract exposes it.
3. If an overlay must protrude beyond its media or card, preview it at the target host widths and verify that no ancestor clips it. If clipping cannot be disabled with a validated prop, enlarge the owning container or keep the overlay inside its bounds.
4. For maintenance of an existing v1.3 template, the documented legacy negative-margin fallback remains available. For new v1.5 work, keep the v1.5 anchor contract and report the surface rollout gate rather than rewriting the design to removed v1.3 components.
5. For mapped overlays, validate that every `anchorName` is unique and every `positionAnchor` resolves to the corresponding item rather than another repeated item.

Anchor geometry best practices:

1. Put the anchor declaration on the stable Box that owns the measured visual
   surface, not on an incidental wrapper with ambiguous size.
2. Calculate and verify the anchor owner's width and height before positioning
   overlays. The positioned component follows that coordinate space.
3. Keep each anchor and positioned component in the same repeated-item branch
   so source order, clipping, and relationship ownership remain local.
4. Prefer logical `blockStart`/`blockEnd` and `inlineStart`/`inlineEnd` edges
   with supported margin tokens; do not emulate absolute CSS coordinates.
5. Budget the positioned component's own size. A badge, action, or label can
   clip or cover important media even when its anchor relationship is valid.
6. Anchor placement does not prove z-order or hit testing. Test overlap,
   pointer activation, keyboard reachability, narrow-width movement, and both
   themes in the target host.

Do not confuse this contract with `Image.position`, which controls image crop alignment only. Do not translate browser CSS Anchor Positioning properties such as `position`, `anchorName`, or `positionAnchor` directly into SDL; use the SDL `anchorPositioning` object.

The field shapes and enum values remain versioned. Recheck the expanded reference rows before authoring rather than assuming this verified snapshot still applies. Because the current Mosaic MCP discovery index may omit this shared prop, validate anchor usage in three stages:

1. Confirm the exact `anchorPositioning` and Anchor Inset shapes in the matching-version reference gallery.
2. Run saved full validation, including component version resolution.
3. Preview in the target host and design surface, especially `bing-acf-card`, to confirm renderer deployment and placement behavior.

`validate_template_inline` accepting unknown JSX attributes is not evidence of renderer support. Treat the versioned reference contract plus saved validation and target-host preview as the completion gate.

### Version-aware freshness gate

Run this lightweight gate once per authoring task before changing JSX. Record the target surface, intended zone, current date, reference template ID and authoritative iteration, emitted `sdlVersion`, and any advanced feature being considered.

No single discovery source is authoritative for every question. Use the source that owns the decision:

| Question | Primary source | Required confirmation |
|----------|----------------|-----------------------|
| Component-local props and enum values | `describe_component` and `get_component_guide` | Saved full validation |
| Color tokens, semantic roles, and theme behavior | `search_schema` with `category: "colors"` and `get_color_reference` | Same-theme visual comparison plus light/dark QA |
| Shared SDL types and versioned wire contracts | Matching-version reference gallery and changelog | Emitted SDL inspection |
| Existing template behavior | `get_template` item matching `currentIteration` | Fresh preview |
| Cross-component version compatibility | Discovered saved-validation tool (`validate_iteration` in the current MCP) | Exact-pin saved checks and component version resolution pass |
| Actual rendering and responsive behavior | Target host and design surface | Visual QA at relevant widths |

When sources disagree, do not silently choose one or infer support from an empty search result. State the discrepancy, inspect the matching-version reference, and run the smallest saved probe on the target design surface. A successful inline parse is only syntax evidence; it is not compatibility or runtime evidence.

### Native capability before wrapper components

Before wrapping a component to add one behavior, check whether that component already owns a supported prop for the behavior in the target SDL version. Prefer the native prop when the interaction applies only to that component.

```jsx
// Prefer: the image is the complete hit target.
<Image
  src={item.thumbnail}
  alt={item.alt}
  renderInlineSize={{ value: 260, unit: "pixel" }}
  renderBlockSize={{ value: 160, unit: "pixel" }}
  fit="cover"
  onClickAction={{
    type: "image:navigate",
    payload: { url: item.url },
  }}
/>

// Use a semantic Link when text owns navigation.
<Link
  value={item.title}
  onClickAction={{
    type: "link:navigate",
    payload: { url: item.url },
  }}
/>
```

Use this ownership test before adding a wrapper:

1. Does the child expose the required prop in the live contract for the target version?
2. Is the child itself the full intended hit target?
3. Does a containing `Box` or `Card` add no layout, clipping, surface treatment, hover/focus behavior, disabled state, accessibility semantics, or multi-child interaction?

If all three answers are yes, use the child's native prop and omit the wrapper. If the wrapper owns any remaining responsibility, keep it. Do not infer support from memory: confirm the native prop through live discovery and saved full validation.

### Production accessibility gate

- Give informative images concise alt text that describes the visible crop.
  Use empty alt only for truly decorative images when the exact contract and
  target host preserve that behavior without losing information.
- When an expanded action uses an empty visible `Link.value`, provide a
  non-empty, schema-bound `ariaLabel` that names the destination or action.
- Use semantic `Link` for navigation and `Button` for commands. Do not make a
  static `Box`, badge, or image appear interactive without a real reachable
  action.
- Give repeated semantic groups truthful list/listitem roles when the live
  contract supports them, and preserve source order as keyboard and narrow
  reading order.
- Do not encode status, selection, rank, or series identity through color,
  position, or motion alone. Keep a visible text or shape-independent cue.
- Test focus visibility, Tab order, Enter/Space activation as appropriate,
  scroll-container reachability, and destination correctness in the intended
  host. Record screen-reader behavior as `not-tested` unless it was actually
  exercised with the supported host and assistive technology.
