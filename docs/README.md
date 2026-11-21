# VSL Clinic documentation

[← Project overview](../README.md)

A local Windows desktop demo with simultaneous doctor and patient windows. The current usage guide is for 0.7.2 and is in Vietnamese; technical setup and historical notes retain their original language.

Current: [0.7.2 polish and evidence](../UI_UX_POLISH_REPORT.md), [project state](../PROJECT_STATE.md), [usage](USAGE.md). Versioned documents below are historical; their counts/controls may differ.

## Run and present

| Guide | Contents |
| --- | --- |
| [0.6.3 bilingual interface](BILINGUAL_UI_0.6.3.md) | Vietnamese / English UI, shared persistent preference; Vietnamese content and speech. |
| [0.6.2 quieter readout](REALTIME_COMFORT_0.6.2.md) | Adjusted fusion thresholds, grouped warning cues and retained fixture limits. |
| [0.6.0 natural dialogue and automatic runtime](NATURAL_DIALOGUE_0.6.0.md) | Natural clauses, controlled local LLM, five motions, CPU/GPU installer and limits. |
| [Source setup](GIT_SETUP.md) | Clone, restore authorized local assets/runtime, setup and checksum verification. |
| [Offline installer](../installer/README.md) | Build one setup file with all models, runtimes and Desktop shortcut. |
| [Usage guide](USAGE.md) | Two modes, camera/video, pauses and unsupported sentences. |
| [0.5.5 CPU realtime candidate](CPU_REALTIME_0.5.5.md) | Bounded 25-fps capture, sampling provenance, rejected attempts and acceptance/rollback status. |
| [0.5.3 voice, preview and CPU experiment](VOICE_PREVIEW_CPU_0.5.3.md) | Per-sign narration, yellow beep and three choices, immediate readout, independent preview and measured INT8 comparison. |
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

The [0.3.1 speech fix](SPEECH_FIX_0.3.1.md) and [earlier handoff](DEMO_HANDOFF.md) remain as Vietnamese technical history. Prefer the current [usage guide](USAGE.md) and [current project state](../PROJECT_STATE.md).

- [0.6.4: màn hình bệnh nhân chỉ hiển thị, từ mới và tối ưu](PASSIVE_PATIENT_0.6.4.md)
