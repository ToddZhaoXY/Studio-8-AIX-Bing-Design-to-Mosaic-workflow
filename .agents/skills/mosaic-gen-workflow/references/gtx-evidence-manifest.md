# GTX Evidence Manifest

Use one manifest per Mosaic stress-test scenario. The manifest separates facts
that are often confused in tracking tables and makes local/server parity
auditable.

## Recommended shape

```json
{
  "scenario": "22",
  "name": "Giant Pacific octopus lifespan",
  "templateId": "YuLBX4ow6iKxwAMwQFBng",
  "sourceIteration": 7,
  "acceptedIteration": 8,
  "designSurface": "bing-acf-card",
  "viewport": "11x2",
  "sdlVersion": "1.5",
  "root": "Box",
  "components": ["Box", "Text", "Image", "Icon", "Link"],
  "jsxExpressions": [],
  "layoutTechniques": ["wrap", "flex", "minWidth", "maxWidth"],
  "responsiveEvidence": {
    "sectionLevel": {
      "status": "passed",
      "canonical": "passed",
      "transition": "passed",
      "narrow": "passed",
      "wideBehavior": "answer and media share one row",
      "transitionBehavior": "media wraps when answer reaches its usable minimum",
      "narrowBehavior": "answer precedes full-width media",
      "semanticOrder": ["answer", "media", "source"]
    },
    "contentLevel": {
      "status": "passed",
      "canonical": "passed",
      "transition": "passed",
      "narrow": "passed",
      "regions": [
        {
          "name": "media",
          "behavior": "3:2 tracks shrink with minWidth 0; images retain cover crop"
        }
      ]
    },
    "canonical": "passed",
    "transition": "passed",
    "narrow": "passed",
    "captureHeightLimitation": null
  },
  "validation": {
    "inline": "passed",
    "savedFull": "passed",
    "componentVersionResolution": "1.5",
    "previewDiagnostics": 0
  },
  "runtime": {
    "targetHostRender": "passed",
    "images": "passed",
    "pointer": "passed",
    "keyboard": "not-tested"
  },
  "changedFields": ["jsx", "schemaData"],
  "localServerParity": "passed",
  "grounding": ["source URL or document reference"],
  "knownLimitations": []
}
```

## Classification rules

`jsxExpressions` contains only expression forms:

- `.map()`
- `Nested .map()`
- `A && B`
- `A ? B : C`

Do not put these in `jsxExpressions`:

- Components such as `Box`, `Tabs`, or `Image`.
- Props such as `wrap`, `scrollable`, `actionTarget`, or
  `anchorPositioning`.
- Layout descriptions such as hero grid or waterfall wall.
- Interaction descriptions such as whole-card click.

Track those separately under `components`, `layoutTechniques`, or runtime notes.

`responsiveEvidence.sectionLevel` and `responsiveEvidence.contentLevel` are
independent. Use `not-applicable` for a level that the composition genuinely
does not exercise. Do not mark the overall canonical, transition, or narrow
state `passed` unless every applicable responsive level passes at that state.
The generator accepts older manifests without these two fields, but validates
their overall and per-width statuses whenever they are present.

## Update sequence

1. Fetch the live template and authoritative current iteration.
2. Record the source iteration and canonical viewport.
3. Create one working iteration for the edit.
4. Update the manifest after saved validation, preview, and target-host QA.
5. Mark untested outcomes as `not-tested`; never convert missing evidence into
   `passed`.
6. Confirm local JSX, schema, and schema data match the accepted live iteration.
7. Update the central scenario register from the manifest rather than memory.

## Generate the tracking-table row

Validate the manifest and emit one Markdown row:

```bash
python scripts/gtx_manifest_to_table.py path/to/manifest.json
```

Include the table header when starting a new table:

```bash
python scripts/gtx_manifest_to_table.py --header path/to/manifest.json
```

The utility rejects missing required fields, unsupported evidence statuses,
negative diagnostic counts, and values in `jsxExpressions` that are actually
components, props, or layout techniques. It reports combined interaction QA as
passed only when both pointer and keyboard evidence pass.

## Evidence vocabulary

Use:

- `passed`
- `failed`
- `not-tested`
- `blocked`
- `not-applicable`

Avoid ambiguous values such as `works`, `looks good`, or `probably supported`.

Record validation, observed rendering, and design judgment independently:

```text
Measured: saved full validation resolved all components to SDL v1.5.
Observed: target host displayed both image tracks without blank space.
Judgment: the centered crop keeps the octopus recognizable.
```

## Neutral evidence fill

When a hero or large region has unused space, add content only when it answers a
distinct question with grounded evidence. Do not invent momentum, popularity,
sentiment, endorsement, or trend claims to fill geometry. Record the source,
scope, and calculation for any added evidence.
