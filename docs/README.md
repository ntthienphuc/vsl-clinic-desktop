# VSL Clinic documentation

[← Project overview](../README.md)

A local Windows desktop demo with simultaneous doctor and patient windows. Main guides are in English; existing research notes and exact Vietnamese rehearsal scripts retain their original language, labeled below.

## Run and present

| Guide | Contents |
| --- | --- |
| [Source setup](GIT_SETUP.md) | Clone, restore 107 authorized local inputs, setup and checksum verification. |
| [Usage guide](USAGE.md) | Two modes, camera/video, pauses and unsupported sentences. |
| [Windows package contents](PACKAGE_CONTENTS.md) | Bundled runtimes, models, avatar bank, videos and excluded research sources. |
| [Two demo scenarios — Vietnamese](../demo/HAI_KICH_BAN_2026-10-31/README.md) | Ten dialogue turns, practice videos and rehearsal clips. |
| [0.3.4 handoff — Vietnamese](DEMO_0.3.4.md) | Runtime changes, inventory, test conditions and limitations. |
| [Original script — Vietnamese](../demo/KICH_BAN_DEMO.md) | An additional eight-turn rehearsal. |

## Understand the system

| Reference | Contents |
| --- | --- |
| [Semantic routing and bank — Vietnamese](SEMANTIC_AND_BANK_PLAN.md) | Controlled aliases, coverage and QIPEDC; avatar entries versus recognition classes. |
| [Voice and language — Vietnamese](VOICE_LANGUAGE.md) | Local ASR, n-best and constrained wording. |
| [Motion quality — Vietnamese](MOTION_QUALITY.md) | Synchronization, retargeting, joint constraints and rig audits. |
| [Initial design — Vietnamese](DESIGN.md) | Architecture decisions; historical inventory may differ from 0.3.4. |

## Evidence and provenance

| Record | Scope |
| --- | --- |
| [Independent checkout · 2026-11-01](evidence/standalone-source-check-2026-11-01.json) | 303 Python tests, 6 JavaScript tests, build and input restoration. |
| [Portable inventory · 2026-11-01](evidence/portable-inventory-2026-11-01.json) | Package hashes, model assets, motion coverage and video counts. |
| [Relocated runtime · 2026-11-01](evidence/portable-runtime-2026-11-01.json) | Frozen engine with isolated cache and no development-runtime paths. |
| [Rehearsal retest · 2026-10-31](evidence/idle-retest-summary-2026-10-31.json) | Two repeated video rounds on the same EXE after reducing machine load. |
| [Evidence directory](evidence) | Versioned checks and provenance; each report has its own scope. |
| [Third-party notices](../THIRD_PARTY_NOTICES.md) | Sources and distribution boundaries. |
| [Local-assets manifest](../local-assets-manifest.json) | Paths, sizes and SHA-256 hashes; no model/video payloads. |
| [Image provenance](media/README.md) | Actual 0.3.4 screenshots and the repository banner. |

The [0.3.1 speech fix](SPEECH_FIX_0.3.1.md) and [earlier handoff](DEMO_HANDOFF.md) remain as Vietnamese technical history. Prefer the 0.3.4 guide for current rehearsals.
