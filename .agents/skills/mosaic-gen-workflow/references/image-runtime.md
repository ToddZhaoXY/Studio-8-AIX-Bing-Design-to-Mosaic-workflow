# Image and Media Runtime

Use this reference for grounded media, image-host reliability, optimized derivatives, weather imagery, render sizing, and broken-domain handling.

## 8) Data grounding rules

- Use real source data only (no fabricated metrics/ratings/counts)
- Validate every image URL with `curl -sI <url> | head -5` before publish
- If a source image fails, replace with another working image from the same real dataset
- Keep source attribution explicit: favicon(s), source count, destination URL
- Google favicon proxy: `https://www.google.com/s2/favicons?domain=DOMAIN&sz=32`
- Bing requery URLs (`bing.com/search?q=...`) are acceptable as behavioral triggers

### Image URL priority (NEW in v2.2)

For Bing SERP, image source reliability matters. Use this priority order:

| Priority | Source | Example | Notes |
|----------|--------|---------|-------|
| 1 (best) | **Bing OLC** | `bing.com/th?id=OLC.xxx480x360` | Bing-hosted, no hotlink/CORS issues, best for SERP |
| 2 | **Bing OIP** | `bing.com/th?id=OIP.xxx` | Bing image proxy, reliable |
| 3 | **CDN-hosted** | `s3-media0.fl.yelpcdn.com/...`, `media.tacdn.com/...` | Yelp, TripAdvisor CDNs — generally reliable |
| 4 | **Gov/official** | `nps.gov/common/uploads/...` | Works but may have CORS issues in iframe |
| 5 | **Optimized public derivative** | Wikimedia `thumb/.../1280px-*` | Prefer a right-sized derivative over a multi-megabyte original |
| 6 (avoid) | **Search thumbnails** | `tse1.mm.bing.net/th?q=...` | Low quality, unreliable, URL changes frequently |

> **Image render-size magnitudes must use intentional numeric values.** The SDL v1.5 manifest accepts both `pixel` and `percent`, but the verified staging `bing-acf-card` pilot did not reliably render percentage-sized Image media. Treat this as a schema-versus-runtime discrepancy. Until target-host preview proves percentage support for the template, use integer pixel render sizes matched to the known zone and keep the owning Box at `width="100%"`. Do not use decimal pixel values such as `145.5`.

Current verified 3×4 staging pattern:

```jsx
<Box width="100%" height={140}>
  <Image
    src={imageUrl}
    alt={imageAlt}
    fit="cover"
    renderInlineSize={{ value: 312, unit: "pixel" }}
    renderBlockSize={{ value: 140, unit: "pixel" }}
  />
</Box>
```

The Box owns placement and the Image owns crop behavior. Re-probe percentage sizing when the renderer changes; do not infer runtime support from the manifest or saved validation alone.

HTTP success alone does not make an image acceptable. Before handoff, verify
MIME type, source dimensions, payload size, target-host decoding, subject
visibility after `fit="cover"`, crop position, and alt-text truth. A very large
original can fail the host image pipeline even when the URL and file are valid;
prefer an optimized derivative that still exceeds the largest effective render
budget. For flex-track coverage and transition-width testing, follow
[the GTX responsive and media QA reference](./gtx-responsive-media-qa.md).

### Official Bing weather condition imagery (NEW in v2.26)

For weather cards and forecasts, use the official Bing weather assets in
[`references/weather-official-images.json`](./weather-official-images.json).
The reference contains the complete supplied day and night mapping with condition code,
display label, and canonical `https://th.bing.com/th/id/OBWA.v6-106-png-*` URL.

Apply these rules:

1. Treat the weather icon as defined upstream data, not as an agent design choice. When the
   weather record supplies `imageUrl`, bind and use that exact value; do not reinterpret the
   condition label and select a different icon.
2. Use the reference mapping only when the grounded record supplies a provider condition
   code but does not supply `imageUrl`, or when validating that a supplied URL matches the
   official code mapping.
3. Select a mapped image by the grounded provider condition code and day/night state. Do not
   select by display label alone because labels such as `Light rain showers`, `T-storms`,
   `Partly sunny`, `Rain and snow`, `Blowing dust`, and `Windy` intentionally map to
   multiple condition codes.
4. Put `conditionCode`, `conditionLabel`, `isDaytime`, `imageUrl`, and `imageAlt` in
   `schemaData`. Bind `Image.src` and `Image.alt` directly; do not construct or transform
   the URL inside Mosaic JSX.
5. Use the exact mapped URL. Do not infer a code by replacing the `d`/`n` prefix or by
   appending a suffix.
6. Every `Windy` condition code uses the one canonical asset:
   `https://th.bing.com/th/id/OBWA.v6-106-png-d0001`. Do not invent `d1001`,
   `d2001`, `d3001`, `d4001`, or `n0001` asset URLs.
7. Use the condition label as the basis for concise alt text, adding day/night context only
   when it is useful and non-redundant, for example `Partly cloudy at night`.
8. Validate every selected URL at runtime before rollout even though the host is official.
   A successful historical check does not guarantee current availability.
9. Availability check on 2026-10-09: all 75 unique canonical URLs were available.
10. Keep units, observation time, forecast period, and demo/live disclosure separate from
   the image mapping. The icon communicates conditions; it does not prove freshness.

Preferred data shape:

```json
{
  "conditionCode": "d200",
  "conditionLabel": "Partly sunny",
  "isDaytime": true,
  "imageUrl": "https://th.bing.com/th/id/OBWA.v6-106-png-d200",
  "imageAlt": "Partly sunny"
}
```

### Known broken image domains

| Domain | Status | Reason |
|--------|--------|--------|
| `acura.com` | 403 | Akamai hotlink protection |
| `s27363.pcdn.co` | 000 | Connection refused |
| `alltrails.com/mugen` | 400 | Proxy rejects direct access |

Always test image URLs from new domains before committing to templates.

---
