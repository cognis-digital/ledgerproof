<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:6b46c1,100:2b6cb0&height=120&section=header&text=LEDGERPROOF&fontSize=48&fontColor=ffffff&fontAlignY=58" width="100%" alt="LEDGERPROOF"/>

# LEDGERPROOF

### Verifies double-entry ledger integrity and tamper-evidence by checking balance invariants and hash-chained journal entries.

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3500&pause=1000&color=6B46C1&center=true&vCenter=true&width=720&lines=Verifies+doubleentry+ledger+integrity+and+tamperevidence+by+;Self-hostable+%C2%B7+MCP-native+%C2%B7+CI-ready+%C2%B7+polyglot" width="720"/>

[![PyPI](https://img.shields.io/pypi/v/cognis-ledgerproof.svg?color=6b46c1)](https://pypi.org/project/cognis-ledgerproof/) [![CI](https://github.com/cognis-digital/ledgerproof/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/ledgerproof/actions) [![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

*Fintech & Payments Security — PCI, fraud, AML, and payment rails.*

</div>

```bash
pip install "git+https://github.com/cognis-digital/ledgerproof.git"
ledgerproof scan .            # → prioritized findings in seconds
```

<!-- cognis:layman:start -->
## What is this?

Ledgerproof is a command-line tool that checks whether a financial journal is accurate and untampered. It works by verifying that every transaction balances (money in equals money out) and that no past entries have been quietly edited after the fact. You point it at a ledger file, and it immediately tells you if anything looks wrong — making it useful for accountants, developers building payment systems, and anyone who needs an audit trail they can trust.
<!-- cognis:layman:end -->

## Contents

- [Why ledgerproof?](#why) · [Features](#features) · [Quick start](#quick-start) · [Example](#example) · [Architecture](#architecture) · [AI stack](#ai-stack) · [How it compares](#how-it-compares) · [Integrations](#integrations) · [Install anywhere](#install-anywhere) · [Related](#related) · [Contributing](#contributing)

<a name="why"></a>
## Why ledgerproof?

Every payments startup hand-rolls a ledger and discovers drift in an audit. A CLI that proves 'debits == credits' and detects retroactive edits via Merkle chain is an instant trust badge.

`ledgerproof` is single-purpose, scriptable, and self-hostable: point it at a target, get prioritized results in the format your workflow already speaks (table · JSON · SARIF), gate CI on it, and let agents drive it over MCP.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="features"></a>
## Features

- ✅ Load Entries
- ✅ Compute Entry Hash
- ✅ Chain Entries
- ✅ Verify Ledger
- ✅ Runs on Linux/macOS/Windows · Docker · devcontainer
- ✅ Ports in Python, JavaScript, Go, and Rust (`ports/`)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="quick-start"></a>
<!-- cognis:install:start -->
## Install

`ledgerproof` is source-available (not published to PyPI) — every method below installs
straight from GitHub. Pick whichever you prefer; the one-line scripts auto-detect
the best tool available on your machine.

**One-liner (Linux / macOS):**
```sh
curl -fsSL https://raw.githubusercontent.com/cognis-digital/ledgerproof/HEAD/install.sh | sh
```

**One-liner (Windows PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cognis-digital/ledgerproof/HEAD/install.ps1 | iex
```

**Or install manually — any one of:**
```sh
pipx install "git+https://github.com/cognis-digital/ledgerproof.git"     # isolated (recommended)
uv tool install "git+https://github.com/cognis-digital/ledgerproof.git"  # uv
pip install "git+https://github.com/cognis-digital/ledgerproof.git"      # pip
```

**From source:**
```sh
git clone https://github.com/cognis-digital/ledgerproof.git
cd ledgerproof && pip install .
```

Then run:
```sh
ledgerproof --help
```
<!-- cognis:install:end -->

## Quick start

```bash
pip install "git+https://github.com/cognis-digital/ledgerproof.git"
ledgerproof --version
ledgerproof scan .                       # scan current project
ledgerproof scan . --format json         # machine-readable
ledgerproof scan . --fail-on high        # CI gate (non-zero exit)
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="example"></a>
## Example

```text
$ ledgerproof scan .
  [HIGH    ] LED-001  example finding             (./src/app.py)
  [MEDIUM  ] LED-002  another signal              (./config.yaml)

  2 findings · risk score 5 · 38ms
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="architecture"></a>
## Architecture

```mermaid
flowchart LR
  A[Input: file / dir / API] --> B[Collectors]
  B --> C[Rules / Analyzers]
  C --> D[Scorer]
  D --> E{Reporters}
  E --> F[Table]
  E --> G[JSON / SARIF]
  E --> H[MCP tool -. drives .-> AI agents]
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="ai-stack"></a>
## Use it from any AI stack

`ledgerproof` is interoperable with every popular way of using AI:

- **MCP server** — `ledgerproof mcp` (Claude Desktop, Cursor, Cognis.Studio, [uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet))
- **OpenAI-compatible / JSON** — pipe `ledgerproof scan . --format json` into any agent or LLM
- **LangChain · CrewAI · AutoGen · LlamaIndex** — wrap the CLI/JSON as a tool in one line
- **CI / scripts** — exit codes + SARIF for non-AI pipelines

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="how-it-compares"></a>
## How it compares

| | **Cognis ledgerproof** | Formance Ledger |
|---|:---:|:---:|
| Self-hostable, no account | ✅ | varies |
| Single command, zero config | ✅ | ⚠️ |
| JSON + SARIF for CI | ✅ | varies |
| MCP-native (AI agents) | ✅ | ❌ |
| Polyglot ports (JS/Go/Rust) | ✅ | ❌ |
| Open license | ✅ COCL | varies |

*Built in the spirit of **Formance Ledger / AWS QLDB**, re-framed the Cognis way. Missing a credit? Open a PR.*

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="integrations"></a>
## Integrations

Pipes into your stack: **SARIF** for code-scanning, **JSON** for anything, an **MCP server** (`ledgerproof mcp`) for AI agents, and a webhook forwarder for SIEM/Slack/Jira. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="install-anywhere"></a>
## Install — every way, every platform

```bash
pip install "git+https://github.com/cognis-digital/ledgerproof.git"    # pip (works today)
pipx install "git+https://github.com/cognis-digital/ledgerproof.git"   # isolated CLI
uv tool install "git+https://github.com/cognis-digital/ledgerproof.git" # uv
pip install cognis-ledgerproof                                          # PyPI (when published)
docker run --rm ghcr.io/cognis-digital/ledgerproof:latest --help        # Docker
brew install cognis-digital/tap/ledgerproof                             # Homebrew tap
curl -fsSL https://raw.githubusercontent.com/cognis-digital/ledgerproof/main/install.sh | sh
```

| Linux | macOS | Windows | Docker | Cloud |
|---|---|---|---|---|
| `scripts/setup-linux.sh` | `scripts/setup-macos.sh` | `scripts/setup-windows.ps1` | `docker run ghcr.io/cognis-digital/ledgerproof` | [DEPLOY.md](docs/DEPLOY.md) (AWS/Azure/GCP/k8s) |

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="related"></a>
## Related Cognis tools

- [`panhound`](https://github.com/cognis-digital/panhound) — Scans code, logs, fixtures, and S3 buckets for leaked PANs (Luhn-validated card numbers) and CVVs before they hit prod.
- [`fraudlens`](https://github.com/cognis-digital/fraudlens) — Replays a stream of transactions against pluggable fraud rules and ML scorers, emitting precision/recall and alert volume from the terminal.
- [`obscan`](https://github.com/cognis-digital/obscan) — Conformance and security linter for Open Banking / FAPI APIs: validates OAuth flows, consent scopes, and PSD2 endpoints against the spec.
- [`iso20022`](https://github.com/cognis-digital/iso20022) — Validates, lints, and diffs ISO 20022 / pacs / camt payment messages and translates legacy MT into MX with schema-aware errors.
- [`tokenvault`](https://github.com/cognis-digital/tokenvault) — Self-hostable PCI tokenization microservice and CLI that swaps PANs for format-preserving tokens and proves no raw card data persists.
- [`sanctscan`](https://github.com/cognis-digital/sanctscan) — Screens counterparties and transactions against OFAC/EU/UN sanctions lists with fuzzy name matching and explainable hit scoring.

**Explore the suite →** [🗂️ all 170+ tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources) · [🤖 uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet) · [🧠 engram](https://github.com/cognis-digital/engram)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="contributing"></a>
## Contributing

PRs, new rules, and demo scenarios are welcome under the collaboration-pull model — see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

> ### ⭐ If `ledgerproof` saved you time, **star it** — it genuinely helps others find it.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

---

<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · one of 170+ tools in the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
