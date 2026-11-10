# VSL Clinic documentation

[← Project overview](../README.md)

A local Windows desktop demo with simultaneous doctor and patient windows. The current usage guide and 0.5.2 handoff are in Vietnamese; technical setup and historical notes retain their original language.

## Run and present

| Guide | Contents |
| --- | --- |
| [Source setup](GIT_SETUP.md) | Clone, restore authorized local assets/runtime, setup and checksum verification. |
| [Offline installer](../installer/README.md) | Build one setup file with all models, runtimes and Desktop shortcut. |
| [Usage guide](USAGE.md) | Two modes, camera/video, pauses and unsupported sentences. |
| [0.5.2 modes and clinic UX](CLINIC_0.5.2.md) | Current Ký hiệu + khẩu hình / Chỉ ký hiệu, minimal UI, quick clinical phrases, silence handling and fixture checks. |
| [0.5.1 multimodal](MULTIMODAL100_0.5.1.md) | Preserved SL-GCN + AV-HuBERT integration and original verification status. |
| [Fusion selection](FUSION_SELECTION_0.5.1.md) | VSL100 method comparison, fixed checkpoint, encoder parity and device measurements. |
| [0.5.0 multimodal](MULTIMODAL100_0.5.0.md) | Preserved SPOTER + VLR integration and historical measurements. |
| [0.4.1 avatar voice](AVATAR_VOICE_0.4.1.md) | Preserved baseline: offline male narration, mouth animation and patient handover. |
| [0.3.7 workspace](WORKSPACE_0.3.7.md) | Avatar progress, compact speech review, clearing both screens and optional temporary history. |
| [Windows package contents](PACKAGE_CONTENTS.md) | Bundled runtimes, models, avatar bank, videos and excluded research sources. |
| [0.3.4 handoff — Vietnamese](DEMO_0.3.4.md) | Runtime changes, inventory, test conditions and limitations. |

## Understand the system

| Reference | Contents |
| --- | --- |
| [Natural conversation research — 2026-11-02](NATURAL_CONVERSATION_RESEARCH_2026-11-02.md) | Source audit, ASR repair, sign/non-sign rejection, incremental commitment and pilot evaluation; proposed work, not released features. |
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

The [0.3.1 speech fix](SPEECH_FIX_0.3.1.md) and [earlier handoff](DEMO_HANDOFF.md) remain as Vietnamese technical history. Prefer the current [usage guide](USAGE.md) and [0.5.2 status](CLINIC_0.5.2.md).
