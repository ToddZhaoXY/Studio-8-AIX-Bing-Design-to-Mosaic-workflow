# GTX Responsive, Media, and Interaction QA

Use this reference for responsive Mosaic layouts, flex-based image galleries,
anchored controls, whole-card actions, and target-host acceptance. These rules
come from SDL v1.5 GTX Scenarios 22–25.

## ACF viewport and content-budget calculation

For the current Bing ACF grid, one cell is 88px and the gap between cells is
24px:

```text
viewport width  = columns × 88 + (columns - 1) × 24
viewport height = rows × 88 + (rows - 1) × 24
```

Common canonical viewports:

| Grid | Pixels |
|---|---:|
| 3x2 | 312x200 |
| 3x4 | 312x424 |
| 5x4 | 536x424 |
| 6x4 | 648x424 |
| 11x2 | 1208x200 |
| 11x3 | 1208x312 |
| 11x4 | 1208x424 |
| 12x2 | 1320x200 |
| 12x4 | 1320x424 |

The viewport is not the size of every child. Calculate from the outside in:

1. Start with canonical viewport pixels.
2. Subtract root horizontal and vertical padding, border contribution, and
   fixed header/footer heights.
3. Subtract the gaps between major regions.
4. Allocate fixed tracks, then divide the remaining width by the intended flex
   ratio.
5. For each region, subtract its internal padding, borders, and sibling gaps to
   get the component content box.
6. Set explicit media render budgets from the maximum effective media track,
   not from the grid label or source aspect ratio alone.
7. Compare total block demand with the canonical height. Choose deliberate
   wrapping, scrolling, truncation, content reduction, or expanded height; do
   not assume the host grows automatically.

Record this before JSX:

```text
Grid and canonical pixels:
Root padding/border:
Header/footer block budget:
Major region tracks and gaps:
Usable inline/block size per region:
Media box and requested render size:
Source pixel dimensions:
First wrap threshold:
Expanded narrow height:
```

After rendering, measure the actual target-host boxes. If measured geometry
differs from the budget, update the model rather than compensating with
unrelated fixed sizes.

## Two-level responsive evidence

Evaluate the two responsive levels separately:

1. **Section level** — major semantic regions stay side by side, wrap, stack,
   fill a new row, or change growth ownership as planned.
2. **Content level** — material inside every section wraps, shrinks, scrolls,
   changes density, truncates, crops, and exposes controls as planned.

Record before target-host testing:

```text
Section-level expectation:
- Major regions:
- Wide arrangement:
- First reflow threshold:
- Transition arrangement:
- Narrow semantic order:
- Expanded-height behavior:

Content-level expectation by region:
- Region:
  - Inline wrapping:
  - Shrink behavior:
  - Overflow strategy:
  - Truncation/density:
  - Media behavior:
  - Controls and focus:
```

At each tested width, assign `passed`, `failed`, `not-tested`, `blocked`, or
`not-applicable` to each level independently. A width does not pass overall
when sections reflow correctly but internal content clips, or when internal
content remains technically visible only because a major section was squeezed
below its usable minimum.

## Three-width responsive protocol

Test every wrapping composition at three states:

1. **Canonical** — the saved `bing-acf-card.generated-viewport`.
2. **Transition** — the first width at which major regions approach or cross
   their wrap threshold.
3. **Narrow** — the smallest relevant host width.

Record:

```text
Canonical viewport:
Expected wrap threshold:
Wide section-level behavior:
Wide content-level behavior:
Transition section-level behavior:
Transition content-level behavior:
Narrow section-level behavior:
Narrow content-level behavior:
Semantic stacking order:
Capture-height limitation:
```

The transition state is mandatory. Wide and narrow captures can both pass while
an intermediate flex track exposes blank space or clips content.

For content-only responsiveness with no major reflow, mark section-level
behavior `not-applicable` and still test canonical, stress/transition, and
narrow content behavior. For section-level wrapping, test the content inside
every resulting section; reflow alone is not a complete responsive pass.

When temporarily changing generated viewport metadata:

1. Read and retain the canonical value.
2. Set one temporary test value.
3. Capture fresh evidence.
4. Restore the canonical value even if capture fails.
5. Re-fetch and confirm the restored metadata before handoff.

## Responsive region recipe

For meaningful left and right regions:

```jsx
<Box direction="row" width="100%" gap={6} wrap="wrap">
  <Box flex={6} minWidth={312}>
    {/* answer */}
  </Box>
  <Box flex={5} minWidth={312}>
    {/* media or evidence */}
  </Box>
</Box>
```

Use the intended semantic reading order in JSX. Wrapping must not put
exploration or action before the primary answer.

## Image track sizing model

Treat these as separate values:

- Owning `Box` width.
- Flex-track width.
- Requested `Image.renderInlineSize`.
- Source pixel dimensions.
- Encoded payload size.
- Effective crop after `fit` and `position`.

`maxWidth="100%"` clamps an image down; it does not force an undersized render
request to grow and cover a larger flex track. If the track can become wider
than the normal media size, request an integer pixel budget at least as large
as the maximum expected track and clamp it:

```jsx
<Box flex={1} minWidth={0} height={200}>
  <Image
    src={imageUrl}
    alt={imageAlt}
    fit="cover"
    position="center"
    maxWidth="100%"
    renderInlineSize={{ value: 672, unit: "pixel" }}
    renderBlockSize={{ value: 200, unit: "pixel" }}
  />
</Box>
```

For a capped companion track:

```jsx
<Box flex={1} minWidth={0} maxWidth={200} height={200}>
  <Image
    src={secondaryImageUrl}
    alt={secondaryImageAlt}
    fit="cover"
    maxWidth="100%"
    renderInlineSize={{ value: 400, unit: "pixel" }}
    renderBlockSize={{ value: 200, unit: "pixel" }}
  />
</Box>
```

The budget must not exceed the source quality without review. A source smaller
than the effective display width will look soft even when layout coverage is
correct.

## Image acceptance gate

HTTP 200 is only the first check:

1. Verify the response is an image MIME type.
2. Inspect source dimensions.
3. Inspect encoded payload size.
4. Prefer a right-sized CDN or public derivative over a multi-megabyte original.
5. Render in the target host; browser or curl success is not enough.
6. Inspect the actual `fit="cover"` crop at canonical and transition widths.
7. Confirm the subject remains recognizable and important features are not cut.
8. Make alt text describe the visible crop, not unseen source-image content.

A high-resolution original can exceed the host image pipeline's practical
decode or proxy budget. If it renders as a placeholder, use a verified 960px,
1280px, or similarly appropriate derivative rather than falling back to a
low-resolution thumbnail.

## Composite action-target recipe

For a whole card or anchored control with multiple visible children:

```jsx
<Box
  background="black"
  radius="xxl"
  anchorPositioning={{ anchorPositioned: positionedConfig }}
>
  <Box direction="row" align="center" padding={{ x: 2, y: 1 }} actionTarget={true}>
    <Icon name="image" color="white" ariaHidden={true} />
    <Text value={visibleLabel} color="white" />
    <Link
      value=""
      ariaLabel={actionAriaLabel}
      expandActionTarget={true}
      onClickAction={{
        type: "link:navigate",
        payload: { url: destinationUrl },
      }}
    />
  </Box>
</Box>
```

The outer Box owns placement and surface. The inner Box owns the composite hit
area. The Link owns semantic navigation and its accessible name.

Target-host tests must confirm that the overlay receives pointer input instead
of underlying actionable media.

## Pointer and keyboard acceptance

Pointer:

- The intended visual region activates the correct action.
- An anchored overlay is not blocked by media beneath it.
- Nested actions do not compete.
- Hover behavior appears only where an action truly exists.

Keyboard:

- Tab reaches every semantic destination.
- Focus follows semantic reading order.
- Enter or Space matches the component's semantics.
- A scrollable Box does not trap focus or hide nested Links.
- Arrow-key scrolling does not replace access to nested actions.

Saved validation and emitted action counts are not interaction evidence.

## Fixed-height capture caveat

When a wide row wraps into multiple rows, a screenshot service may preserve the
original card height. In that case report separately:

- Horizontal reflow: verified or failed.
- Second-row vertical visibility: verified, clipped by capture surface, or not
  tested.
- Full expanded composition: verified or not verified.

Do not describe horizontal reflow alone as a complete responsive pass.
