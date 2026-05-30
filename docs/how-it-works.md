# How It Works

## Discovery

The app is scanned for SwiftUI/SF Symbol entry points:

- `Image(systemName:)`
- `Label(..., systemImage:)`
- `Tab(..., systemImage:)`
- `ContentUnavailableView(..., systemImage:)`
- wrapper calls that pass `systemImage`
- simple icon helper functions returning SF Symbol strings

Symbols are collapsed into semantic asset keys. For example:

- `car.fill`, `car.circle` -> `lg_car`
- `map`, `map.fill` -> `lg_map`
- `bolt`, `bolt.fill`, `bolt.circle.fill` -> `lg_lightning_bolt`

This avoids downloading multiple nearly identical Icons8 files for one app concept.

## Icons8 Page Manifests

Full style/category packs should be discovered from the Icons8 pages themselves.
The page command fetches each URL, expands a root style page such as
`/icons/glassmorphism` into its linked `/icons/set/*--style-glassmorphism`
pages, and parses the category page `__NUXT_DATA__` payload.

This matters because Icons8 JSON-LD only lists the first visible page slice, and
search results can return repeated or unrelated icons. The Nuxt payload contains
the real category/subcategory icon inventory, including icon IDs and canonical
icon URLs. Output filenames are generated as:

```text
<category>--style-<style>__<slug>.svg
```

The manifest command checks that two different Icons8 IDs do not map to the same
output filename before any download begins.

## Icons8 Search

Search uses Icons8 MCP over JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_icons",
    "arguments": {
      "query": "car",
      "platform": "liquid-glass",
      "amount": 5
    }
  }
}
```

The first result is not always right. The script scores results by:

- exact Liquid Glass platform
- color icon
- query tokens appearing in name/common name/category/subcategory

For production use, keep an override map for known weak matches.

## Paid SVG Download

Public PNG preview works with MCP:

```text
https://img.icons8.com/?id=<ICON_ID>&format=png&size=512
```

Paid SVG needs the website download endpoint:

```text
https://api-img.icons8.com/?id=<ICON_ID>&format=svg&size=512&fromSite=true&token=<PUBLIC_API_KEY>
```

The `PUBLIC_API_KEY` comes from the signed-in Icons8 account. The script supports:

- `ICONS8_PUBLIC_API_KEY` environment variable
- macOS Chrome local extraction with `token-from-chrome`

The Chrome helper:

1. Reads Chrome's encrypted Cookies database.
2. Uses macOS Keychain item `Chrome Safe Storage`.
3. Decrypts only Icons8 cookies.
4. Extracts `publicApiKey` from the `i8token` JWT payload.
5. Prints only an `export ICONS8_PUBLIC_API_KEY=...` command.

No raw session cookie is stored.

## Theming

Icons8 Liquid Glass SVGs are often white-only gradient icons:

```xml
<stop stop-color="#fff" stop-opacity=".7"/>
<stop stop-color="#fff" stop-opacity=".45"/>
```

The theme step maps opacity bands to palette colors:

- high opacity -> near-white highlight
- medium opacity -> ice blue
- lower opacity -> cyan
- very low opacity -> primary blue

This preserves the glass structure while making icons match the app theme.

## Rendering

SVGs are kept as source masters.

PNGs are generated with `rsvg-convert` for runtime reliability:

```bash
rsvg-convert -w 512 -h 512 input.svg > output.png
```

For iOS asset catalogs, generate `@1x`, `@2x`, and `@3x` from the themed SVG masters.
