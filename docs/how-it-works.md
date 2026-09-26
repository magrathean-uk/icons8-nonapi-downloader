# How the pipeline works

The two scripts are local command-line tools. `discover_swiftui_symbols.py` reads Swift files and writes candidate CSVs. `icons8_pipeline.py` handles page manifests, search, downloads, theming, rendering, and contact sheets. See the [README](../README.md) for complete command examples.

## Page manifests

`page-manifest` normalizes input URLs to HTTPS on `icons8.com`, dropping queries and fragments. Root style pages expand to matching `/icons/set/<category>--style-<style>` links. `--no-expand-root` is useful with set-page inputs; it does not make a root page directly parseable.

Set pages are parsed from the `__NUXT_DATA__` script. The parser tries `categoryData` first, then `iconsData` if the first path raises a runtime error. It records the icons present in those structures, rather than validating the provider's entire catalogue. Website changes can break discovery or change the inventory.

Manifest columns are:

```text
source_url,category,style,subcategory_code,subcategory_name,icons8_id,name,common_name,slug,asset_key,icon_url
```

Output stems use `<category>--style-<style>__<slug>`. The slug usually comes from the icon URL, falling back to common name or ID. Duplicate `(asset_key, icons8_id)` rows are removed. Conflicting names are disambiguated using common names and, when needed, IDs; a final check rejects any remaining key owned by different IDs. Naming is repeatable for the same ordered input, not a promise that live page results stay fixed.

## Search and overrides

`download` reads `asset_key` and `icons8_query`, plus optional `sf_symbols`. Without an override, it calls `search_icons` through JSON-RPC at `https://mcp.icons8.com/mcp/`, requesting platform `liquid-glass` and five results by default.

Each result scores 10 points for the Liquid Glass platform, 2 for a colour icon, and 3 per query token found in its name, common name, category, or subcategory. The highest score wins; ties keep the first result. Scoring does not guarantee semantic correctness or strictly exclude another platform.

An override with `asset_key` and `icons8_id` bypasses search. Optional `icons8_name` and `icons8_common_name` are copied into the report. Review overrides visually rather than assuming a stable ID proves suitability.

## Downloads and reports

Both download routes send the environment key as the `token` query parameter to `https://api-img.icons8.com/`, with `format=svg`, `fromSite=true`, and a requested size. The query route requests size 512; the manifest route exposes `--size`, defaulting to 512.

Responses are accepted when their bytes contain `<svg`. This is not SVG sanitization. Files are written as `<asset_key>.svg`; input keys are not constrained to a safe directory by a dedicated path validator. Use only reviewed CSVs and trusted SVGs. See [security and data handling](security.md).

The query route runs sequentially and pauses after each row. The manifest route defaults to one worker, can run concurrently, and pauses after successful downloads. Both default pauses are 0.08 seconds; this is pacing, not rate-limit handling. There is no retry, resume, or skip-existing mechanism.

Successes and failures are recorded separately. Download failures do not roll back successful files. Both commands return status 1 if a row failed. Reports contain asset names, local output paths, and potentially unredacted error text. Manifest reports preserve the input columns; query reports include the chosen icon's ID and labels.

## Swift discovery

The scanner recursively reads `*.swift`. It looks for quoted strings on lines containing `systemName:`, `systemImage:`, or `icon:`, and in certain icon-named helper bodies. Heuristics filter strings, and a manual mapping converts known symbols into search queries. Other names are simplified by removing suffixes and replacing separators.

Symbols mapping to the same query share an `lg_` asset key. The detailed CSV contains `sf_symbol,asset_key,icons8_query,refs`, with up to eight sorted references per symbol. The grouped query CSV contains `asset_key,icons8_query,sf_symbols`. Dynamic expressions and multiline source patterns can be missed; false positives remain possible.

## Theming and rendering

`theme` processes only top-level `*.svg` files. For white gradient stops written in the recognized attribute form, `stop-opacity` selects the replacement colour:

| Opacity | Colour |
| --- | --- |
| At least 0.64 | `#F8FBFF` |
| At least 0.54, below 0.64 | `#6BD8FF` |
| At least 0.40, below 0.54 | `#20D7E8` |
| Below 0.40 | `#1A26FF` |

It also replaces selected `#999` and `#4c4c4c` fills and strokes, and changes literal 48px width/height attributes to 512px. These regex substitutions do not cover every valid SVG syntax or colour style.

`render` calls `rsvg-convert` for each top-level SVG, requesting equal width and height, default 512. Existing PNG names are overwritten. It does not create an iOS asset catalogue or multiple scale variants.

`contact-sheet` uses Pillow, with 72px thumbnails and eight columns by default. It reads the resolved CSV in order, opens a matching PNG for each asset key, and draws shortened labels on a dark background. It requires nonempty input and does not skip missing PNGs.

## Validation boundary

The five tests in `tests/test_icons8_pages.py` exercise synthetic Nuxt payloads, root-page link filtering, and filename collisions. They do not validate account access, current Icons8 service behavior, Chrome cookie compatibility, Swift discovery, or rendered appearance. Use the checks in [CONTRIBUTING.md](../CONTRIBUTING.md) for changes, and report separately what was checked locally and what was observed live.
