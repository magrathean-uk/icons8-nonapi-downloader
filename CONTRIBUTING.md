# Contributing

Keep changes focused on the local CLI workflow. Explain the affected command, the behavior before and after the change, and how you checked it. Use [issues](https://github.com/magrathean-uk/icons8-nonapi-downloader/issues) for reproducible bugs or feature proposals. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

Contribute only material you have the right to share under this repository's MIT licence. Follow the [organization contribution policy](https://github.com/magrathean-uk/.github/blob/main/CONTRIBUTING.md) for provenance and DCO sign-off, and the [code of conduct](https://github.com/magrathean-uk/.github/blob/main/CODE_OF_CONDUCT.md). Discuss substantial behavior or dependency changes in an issue before implementation.

## Local checks

Follow the [README setup](README.md#setup). From the repository root, the fixture suite is:

```bash
python3 -B -m unittest discover -s tests -v
```

It covers page parsing and manifest naming without using an account or making network requests. `cryptography` is needed because the pipeline imports it at module load. For syntax checks without writing bytecode:

```bash
python3 - <<'PY'
import ast
from pathlib import Path
for folder in ('scripts', 'tests'):
    for path in Path(folder).glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
PY
```

For parser changes, add a small synthetic fixture that reproduces the changed page structure or naming case. For download, discovery, theming, or rendering changes, use a focused check for that behavior and state any live-service or visual checks that remain untested. Do not use real credentials or paid artwork as fixtures.

Documentation changes need command, link, and consistency checks; a documentation edit alone does not justify an account download. The existing `.github/workflows/dependency-audit.yml` runs `pip-audit`, but its shell fallback allows scan failures to pass. It does not run tests or audit licences, despite its display name.

## Review before sharing

Use synthetic CSVs and redact private paths and error text. Keep generated packs in `work/`. Check the actual diff: `.gitignore` does not exclude every SVG, PNG, CSV, or virtual environment location. Preserve the [MIT licence](LICENSE), existing attribution, and [third-party notices](license.md).

Agent-specific boundaries and commands are in [AGENTS.md](AGENTS.md).
