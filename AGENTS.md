# Repository context

This repository builds icon packs from Icons8 content. The MIT licence covers this repository's tooling; Icons8 assets and marks have separate licence terms.

[README.md](README.md) describes setup and usage. [SECURITY.md](.github/SECURITY.md) describes credential flow and generated-file handling. [CONTRIBUTING.md](.github/CONTRIBUTING.md) contains syntax checks and validation examples. Legal references include `LICENSE`, `NOTICE`, `docs/legal/third-party-notices.md` and `docs/legal/trademarks.md`.

## Source map

`scripts/icons8_pipeline.py` provides the asset workflow. `scripts/discover_swiftui_symbols.py` produces candidate queries from Swift source. The pipeline supports visual match review and overrides for release assets.

## Command reference

Python dependencies are declared in `requirements.txt`. The fixture suite covers page parsing and manifest naming:

```bash
python3 -B -m unittest discover -s tests -v
```
