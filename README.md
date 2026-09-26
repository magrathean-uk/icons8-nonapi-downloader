# Icons8 Licensed Asset Pipeline

Build a local, reviewed icon pack from Icons8 Liquid Glass assets: discover icons, download SVG masters, apply a fixed blue palette, render PNGs, and inspect a contact sheet. An optional scanner turns SF Symbol references in Swift source into candidate search queries.

This repository contains tooling and example CSVs, not Icons8 artwork or account credentials. It is independent of Icons8. Despite the repository name, the downloader makes network requests to Icons8's MCP search service and website image endpoint.

## Before you start

Use an account you control and download only assets your account and the applicable Icons8 terms permit. The software's MIT licence does not license downloaded artwork. Prefer official export or API tooling when it meets your needs; review asset attribution, modification, redistribution, and download limits separately. See [licensing and third-party notices](license.md).

The page parser depends on Icons8's website data format, and search matches need human review. It cannot guarantee a complete current catalogue or continued endpoint compatibility.

## Setup

Run commands from the repository root. Python 3.11 is the version configured in the existing dependency workflow. The Python dependencies are `cryptography` and `Pillow`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Rendering also needs `rsvg-convert` on `PATH`. On macOS with Homebrew:

```bash
brew install librsvg
```

Keep the virtual environment out of commits; `.venv/` is not currently listed in this repository's `.gitignore`.

## Authentication

Downloads read an account-holder key from the environment. Supply your own value locally:

```bash
export ICONS8_PUBLIC_API_KEY="your-own-icons8-public-api-key"
```

The script does not load `.env` files. Treat the key as a secret, including in shell history and terminal output.

An optional `token-from-chrome` command reads the current macOS user's Chrome Default profile and Keychain to extract the account's `publicApiKey`. It prints a shell export containing the key. Use it only when you intend to access your own browser credentials, after reading the [data-handling details](docs/security.md). It is not required when the environment variable is already set.

## Download by application query

Review [the query example](examples/asset-queries.example.csv), then run:

```bash
python3 scripts/icons8_pipeline.py download \
  --queries examples/asset-queries.example.csv \
  --out work/svg-original \
  --resolved work/resolved-icons.csv \
  --failed work/failed-icons.csv
```

Each row needs `asset_key` and `icons8_query`; `sf_symbols` is optional. Use simple, unique filename stems for asset keys. CSV paths and values are trusted input, not sandboxed input.

The downloader ranks up to five search results by default. A reviewed override bypasses search for its asset key:

```text
--overrides examples/overrides.example.csv
```

[Override rows](examples/overrides.example.csv) require `asset_key` and `icons8_id`; `icons8_name` and `icons8_common_name` supply labels. The included IDs illustrate the format, not an approved pack for your application.

## Download by category or style page

Create a manifest before downloading:

```bash
python3 scripts/icons8_pipeline.py page-manifest \
  --url https://icons8.com/icons/set/business--style-glassmorphism \
  --out work/page-manifest.csv \
  --json-out work/page-manifest.json

python3 scripts/icons8_pipeline.py download-manifest \
  --manifest work/page-manifest.csv \
  --out work/svg-original \
  --resolved work/resolved-icons.csv \
  --failed work/failed-icons.csv \
  --workers 1
```

Repeat `--url` for multiple pages, or use `--urls-file` with one URL per nonblank line. A root style URL such as [Glassmorphism](https://icons8.com/icons/glassmorphism) expands to linked set pages of that style. Review manifest names and counts before downloading. Use a separate output folder for each pack so old files do not enter a later render.

Both download commands write resolved and failed CSVs and exit with status 1 if any rows fail. They overwrite matching output filenames and do not resume or retry automatically. Inspect failures before rerunning; rerunning the original input downloads successful rows again. Keep concurrency low and respect provider limits.

## Theme, render, and review

After either download route, use the matching resolved CSV:

```bash
python3 scripts/icons8_pipeline.py theme \
  --in-dir work/svg-original \
  --out-dir work/svg-themed

python3 scripts/icons8_pipeline.py render \
  --in-dir work/svg-themed \
  --out-dir work/png-themed \
  --size 512

python3 scripts/icons8_pipeline.py contact-sheet \
  --png-dir work/png-themed \
  --resolved work/resolved-icons.csv \
  --out work/contact-sheet.png
```

The theme is a fixed set of colour substitutions, not a configurable palette. Keep original SVGs for comparison. The contact sheet needs at least one resolved row and a matching PNG for every row. Inspect the actual images and licences before putting a pack into an application.

## Discover SF Symbols in Swift source

```bash
python3 scripts/discover_swiftui_symbols.py \
  --source /path/to/AppSource \
  --out work/symbols.csv \
  --queries work/asset-queries.csv
```

This is a regex scan, not a Swift parser. It can miss dynamic symbols and include unrelated strings. Review the generated queries, then pass `work/asset-queries.csv` to `download`. The detailed symbol report includes source paths and line references; keep private project details local.

## Development and help

See [how it works](docs/how-it-works.md), [contribution and validation guidance](CONTRIBUTING.md), and [troubleshooting](SUPPORT.md). The existing tests cover page parsing and manifest naming with synthetic fixtures; they do not prove live downloads or visual quality.

Keep generated content under `work/`, which Git ignores. SVGs and PNGs elsewhere are not globally ignored. Review reports and error output before sharing them. Follow [SECURITY.md](SECURITY.md) for vulnerability reports and [secret hygiene](docs/security.md) for local use.

## Licence and trademarks

The tooling is licensed under the [MIT License](LICENSE), copyright (c) 2026 Magrathean UK Ltd. [Third-party notices](license.md) distinguish software dependencies from downloaded artwork. See [TRADEMARKS.md](TRADEMARKS.md) for the existing trademark notice.

This project is not affiliated with, endorsed by, sponsored by, or supported by Icons8.
