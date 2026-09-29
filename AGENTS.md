# Repository Guide

## Purpose and boundaries

This repository builds reviewed icon packs from Icons8 content that the operator is entitled to use. It must not be described or used as an access-control bypass. Do not add cookies, account data, API keys, or private manifests to source control. Add assets only when their licence and repository visibility permit it.

Read [README.md](README.md), [SECURITY.md](.github/SECURITY.md), and the relevant script before changing behavior. Keep source changes small and preserve unrelated work. Use bounded delegation for independent work when useful.

## Commands

Run the fixture suite for page parsing or manifest naming changes:

```bash
clean-development run --session session-only -- python3 -B -m unittest discover -s tests -v
```

Use the syntax check and targeted validation guidance in [CONTRIBUTING.md](.github/CONTRIBUTING.md) for other changes. Complete the relevant checks and state any behavior left unverified.

Run the test command only in an environment that already has the packages declared in `requirements.txt`. Do not run authenticated download commands with someone else's credentials. Review output files before sharing them.

`scripts/icons8_pipeline.py` provides the asset workflow. `scripts/discover_swiftui_symbols.py` produces candidate queries from Swift source. Review matches visually and add overrides where needed before release use.

<!-- clean-development-policy:v1 (canonical text: ~/dev/source/dev-bootstrap/snippets/clean-development-policy.md) -->
## Clean development (mandatory)

This project follows [Clean Development](https://github.com/magrathean-uk/clean-development) and the machine rule that nothing creates tool state under `~` (only the allow-listed agent homes).

- The shell environment comes from `~/.zshenv`, which loads `~/dev/env.zsh`. It routes every tool home and cache (`CARGO_HOME`, `RUSTUP_HOME`, `XDG_*`, `BUNDLE_USER_HOME`, `npm_config_cache`, `XCODE_DERIVED_DATA_PATH`, ...) and switches telemetry off. Never unset, override or bypass those variables. If a script needs a scrubbed environment, re-export them with `source ~/dev/env.zsh`.
- Run builds, tests, installs and anything else that writes caches or build output through Clean Development: `clean-development run --session session-only -- <command>`. Follow its docs and keep its receipts.
- Do not add installers or scripts that default into `~` (`~/.cargo`, `~/.rustup`, `~/.cache`, `~/.npm`, `~/.swiftpm`, `~/.gradle`, ...) and do not hardcode `$HOME` paths for caches; use the routed variables.
- Before finishing, run `dev-env-check` (must pass) and `dev-audit` (no new entries in `~`). If your work caused a violation, fix the cause in the repo and say so.

## Documentation and validation

Keep `LICENSE`, `NOTICE`, `docs/legal/third-party-notices.md`, and `docs/legal/trademarks.md` consistent. The MIT license applies to this repository's tooling, not to Icons8 assets or marks. Keep security guidance aligned with the actual credential flow and generated-file handling.

Legal files (`LICENSE`, `NOTICE`, `docs/legal/`, contributor terms, copyright and attribution strings) are owner-controlled: change them only on the owner's explicit instruction.

Keep commits, pushes, deployments, installs, and live-service changes within the user's authorized scope. Use existing authorization for necessary implied steps without asking again.
