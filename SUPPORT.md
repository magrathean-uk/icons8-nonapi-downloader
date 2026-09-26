# Help and troubleshooting

For a reproducible tooling problem, open an [issue](https://github.com/magrathean-uk/icons8-nonapi-downloader/issues) with the command, commit, Python and OS versions, expected result, and a minimal synthetic input. Redact credentials, private source paths, and provider response bodies. Use [SECURITY.md](SECURITY.md) for vulnerabilities. This repository cannot resolve Icons8 billing, account entitlement, or artwork licensing questions.

| Symptom | What to check |
| --- | --- |
| Missing `cryptography` or `PIL` | Activate the environment used for the README installation steps. Pillow provides `PIL`. |
| Missing `ICONS8_PUBLIC_API_KEY` | Set it in the shell that runs the download. `.env` is not loaded automatically. |
| `token-from-chrome` fails | The optional helper assumes macOS, Chrome's Default profile, and a particular cookie format. Supply your own environment key instead of sharing a cookie database. |
| No icons found or a Nuxt parsing error | Confirm the set-page URL. The website data structure may have changed; report a redacted, minimal example. |
| Wrong icon selected | Review the query and use an explicit override for that asset key. |
| Download exits with status 1 | Read the failed CSV and retain successful files. Correct the cause before retrying; the original input downloads all rows again. |
| Provider rejects or limits downloads | Check entitlement and provider limits. Reduce concurrency or stop; there is no automatic retry/backoff. |
| `rsvg-convert missing` | Install `librsvg` as described in the README and ensure the executable is on `PATH`. |
| Contact sheet fails | Check that the resolved CSV is nonempty and every row has a matching PNG in `--png-dir`. |
| Old icons appear in rendered output | Theme and render scan the whole input folder. Use a fresh folder for each pack. |

Read [how it works](docs/how-it-works.md) for file formats and limitations. Download success does not establish that an icon is the right match, visually correct, or licensed for your intended use.
