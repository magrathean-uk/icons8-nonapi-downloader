# Icons8 Liquid Glass Pipeline

Small utility repo for building a local icon asset pack from Icons8 Liquid Glass.

It does five things:

1. Crawls Icons8 style/category pages into a full icon manifest.
2. Maps app icon names to Icons8 search queries when you only need app-specific icons.
3. Resolves each query through the Icons8 MCP search endpoint.
4. Downloads paid SVG masters using your own Icons8 paid account key.
5. Recolors the white Liquid Glass SVG gradients into an app palette and renders PNGs.

No Icons8 assets, login cookies, paid tokens, or account data are included.

## What Was Learned

The Icons8 MCP server is useful for discovery, but it does not expose SVG download.

Available MCP tools:

- `search_icons`
- `get_icon_png_url`
- `list_categories`
- `list_platforms`

Direct public SVG URLs fail for paid formats:

```text
https://img.icons8.com/?id=<ICON_ID>&format=svg&size=512
```

returns:

```json
{"success":false,"error":"paid format requested","code":"PAID_FORMAT"}
```

The paid website download uses a different endpoint:

```text
https://api-img.icons8.com/?id=<ICON_ID>&format=svg&size=512&fromSite=true&token=<PUBLIC_API_KEY>
```

The token value is not the raw browser session cookie. It is the `publicApiKey` embedded in the Icons8 `i8token` JWT for a logged-in paid user.

## Safe Use

Preferred:

```bash
export ICONS8_PUBLIC_API_KEY="your-own-icons8-public-api-key"
```

Local convenience on macOS Chrome:

```bash
python3 scripts/icons8_pipeline.py token-from-chrome
```

That command reads only your local Chrome Icons8 cookie, extracts only the `publicApiKey`, and prints an export command. Do not commit it.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install librsvg
```

`librsvg` provides `rsvg-convert`, used for PNG rendering.

## Workflow

For full style/category pages, start from Icons8 URLs:

```text
https://icons8.com/icons/glassmorphism
https://icons8.com/icons/set/business--style-glassmorphism
https://icons8.com/icons/set/science--style-glassmorphism
```

Build a manifest from the page payloads:

```bash
python3 scripts/icons8_pipeline.py page-manifest \
  --urls-file work/icons8-pages.txt \
  --out work/page-manifest.csv \
  --json-out work/page-manifest.json
```

The root style page, such as `/icons/glassmorphism`, expands to linked set pages. Category pages are parsed from Icons8 `__NUXT_DATA__`, not search results or JSON-LD snippets, so the manifest includes the full page inventory.

Download every manifest SVG:

```bash
python3 scripts/icons8_pipeline.py download-manifest \
  --manifest work/page-manifest.csv \
  --out work/svg-original \
  --resolved work/resolved-page-icons.csv \
  --failed work/failed-page-icons.csv \
  --workers 2
```

For app-specific packs, start from a CSV:

```csv
asset_key,icons8_query,sf_symbols
lg_car,car,car.fill;car.circle
lg_battery_full,battery full,battery.100percent
```

Download SVG masters:

```bash
python3 scripts/icons8_pipeline.py download \
  --queries examples/asset-queries.example.csv \
  --overrides examples/overrides.example.csv \
  --out work/svg-original \
  --resolved work/resolved-icons.csv \
  --failed work/failed-icons.csv
```

Theme SVGs:

```bash
python3 scripts/icons8_pipeline.py theme \
  --in-dir work/svg-original \
  --out-dir work/svg-themed
```

Render PNGs:

```bash
python3 scripts/icons8_pipeline.py render \
  --in-dir work/svg-themed \
  --out-dir work/png-themed \
  --size 512
```

Generate review contact sheet:

```bash
python3 scripts/icons8_pipeline.py contact-sheet \
  --png-dir work/png-themed \
  --resolved work/resolved-icons.csv \
  --out work/contact-sheet.png
```

## SwiftUI Discovery

For a SwiftUI app that uses SF Symbols:

```bash
python3 scripts/discover_swiftui_symbols.py \
  --source /path/to/AppSource \
  --out work/symbols.csv \
  --queries work/asset-queries.csv
```

The generated queries are only a starting point. Review them and add overrides for weak matches before downloading the final pack.

Override CSV format:

```csv
asset_key,icons8_id,icons8_name,icons8_common_name
lg_car,2GEdGXRMcSaj,Car,car
```

## Notes

This is not a bypass. It requires an Icons8 account that is entitled to SVG downloads.

The scripts intentionally avoid storing credentials. Generated SVGs/PNGs are ignored by git by default because Icons8 assets are licensed content.
