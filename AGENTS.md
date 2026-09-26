# Repository Guide

## Purpose and boundaries

This repository builds reviewed icon packs from Icons8 content that the operator is entitled to use. It must not be described or used as an access-control bypass. Do not add cookies, account data, API keys, or private manifests to source control. Add assets only when their licence and repository visibility permit it.

Read [README.md](README.md), [SECURITY.md](SECURITY.md), and the relevant script before changing behavior. Keep source changes small and preserve unrelated work. Use bounded delegation for independent work when useful.

## Commands

Run the fixture suite for page parsing or manifest naming changes:

```bash
python3 -B -m unittest discover -s tests -v
```

Use the syntax check and targeted validation guidance in [CONTRIBUTING.md](CONTRIBUTING.md) for other changes. Complete the relevant checks and state any behavior left unverified.

Run the test command only in an environment that already has the packages declared in `requirements.txt`. Do not run authenticated download commands with someone else's credentials. Review output files before sharing them.

`scripts/icons8_pipeline.py` provides the asset workflow. `scripts/discover_swiftui_symbols.py` produces candidate queries from Swift source. Review matches visually and add overrides where needed before release use.

## Documentation and validation

Keep `LICENSE`, `license.md`, and `TRADEMARKS.md` consistent. The MIT license applies to this repository's tooling, not to Icons8 assets or marks. Keep security guidance aligned with the actual credential flow and generated-file handling.

Keep commits, pushes, deployments, installs, and live-service changes within the user's authorized scope. Use existing authorization for necessary implied steps without asking again.

For dependency-oriented work, consider [Clean Development](https://github.com/magrathean-uk/clean-development) to keep managed caches outside the checkout.
