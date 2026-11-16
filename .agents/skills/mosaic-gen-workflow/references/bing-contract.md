# Bing ACF Contract

Use this reference before authoring for Bing root, spacing, zone, and compatibility constraints.

## 0) Bing-specific hard rules (READ FIRST)

For all Bing card work on `designSurface: "bing-acf-card"`:

> **Target version policy (effective 2026-10-08):** New Bing ACF work targets SDL v1.5. Existing v1.3/v1.4 templates remain valid historical references but are not the contract authority for new work. Use the live v1.5 manifest and matching-version references, then report preview and publication validation separately. The verified v1.4 `Video` example remains a useful structural reference, but adapt it through the v1.5 contract rather than copying it unchanged.

### Root parent

Every JSX template must have exactly one root node. For new work, use a root allowed by the live v1.5 `bing-acf-card` containment contract; do not assume the legacy root list still applies.

Historical v1.3/v1.4 templates commonly use:

- `<Card ...>` for card surfaces such as magazine, weather, overview, video, and compact cards
- `<Basic ...>` for non-card surfaces such as carousel strips, answer blocks, and horizontal scroll rows

The v1.4 to v1.5 changelog reports `Basic` removed, so never introduce it into new v1.5 JSX. If render is blank, verify the version-appropriate root and containment first.

### Spacing tokens (CRITICAL — Bing will not render unsupported values)

Only these values are valid for `gap` and `padding`. Any other value (e.g. `1.5`, `7`, `10`) will cause Bing to NOT render:

| Value | Pixels | SMTC Gap Token | SMTC Padding Token |
|-------|--------|----------------|---------------------|
| 0 | 0px | none | none |
| 0.5 | 2px | xx-small | xx-small |
| 1 | 4px | xx-small | xx-small |
| 2 | 8px | x-small | x-small |
| 3 | 12px | small | small |
| 4 | 16px | medium | medium |
| 5 | 20px | large | large |
| 6 | 24px | x-large | x-large |
| 9 | 36px | xx-large | — |
| 12 | 48px | — | xx-large |
| 20 | 80px | — | xxx-large |

**Examples:**

```jsx
// ✅ GOOD — uses valid token values
<Box direction="col" gap={2} padding={4}>
<Box direction="row" gap={1} padding={{x:2, y:3}}>

// ❌ BAD — 1.5 is NOT a valid token, Bing will not render
<Box direction="row" gap={1.5} padding={{x:2, y:1.5}}>

// ❌ BAD — 7, 10 are NOT valid tokens
<Box direction="col" gap={7} padding={10}>
```

### Zone sizes

- `12x2`: horizontal content, scannable, often scrollable row
- `6x4`: media-forward cards and hero layouts
- `3x4`: fact/overview dense cards
- `3x2`: compact utility cards (video/weather/snack content)

### Bing v1.3 media overlay fallback

Until `bing-acf-card` supports v1.4 anchor positioning, create a row container, render the image first, then pull a later badge wrapper back over the image with a negative percentage margin. Rendering the badge after the image preserves its visual stacking order.

```jsx
<Box width={286} height={162} radius="xs" direction="row" align="start">
  <Image src={item.thumbnail} alt={item.title} width={286} height={162} fit="cover" radius="xs" />
  <Box margin={{ left: "-100%", top: "0" }} padding={2}>
    <Badge label={item.duration} size="sm" color="secondary" variant="solid" />
  </Box>
</Box>
```

In the horizontal row, the badge wrapper begins after the image. `left: "-100%"` moves it back by the current container width to the image origin, so the overlap follows the media width when that width changes. `padding={2}` then supplies a stable token-based inset from the image edges; keep `top: "0"` so margin and padding do not create competing vertical offsets. This separates responsive overlap from visual inset and avoids recalculating a fixed negative pixel value for each thumbnail width.

Use a measured pixel margin only when target-host preview proves that the percentage basis differs from the rendered media width because of nested padding or another containing-block constraint. Keep the image and overlay wrapper as direct siblings in the same row, ensure every displayed badge has a non-empty grounded label, and inspect long labels for overflow. Run saved full validation and target-host visual QA because percentage-margin behavior is host-dependent. This is a compatibility fallback, not a replacement for `anchorPositioning` on surfaces whose saved full validation supports v1.4.

---
