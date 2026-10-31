# Source checkout and local assets

[← Project overview](../README.md) · [Documentation](README.md)

VSL Clinic uses Electron, React/TypeScript, Three.js/VRM and Python/FastAPI. This standalone repository does not include Android/Flutter code or the Translator project's Git history.

## Clone

The repository is public; no GitHub login is required:

```powershell
git clone https://github.com/ntthienphuc/vsl-clinic-desktop.git
cd vsl-clinic-desktop
```

`package.json`, `src/`, `backend/`, `desktop/`, `assets/` and `tools/` are at the repository root. An Android checkout is not needed to run Clinic.

Git contains source, lockfiles, tests, build configuration, the motion bank, avatar assets, scripts and JSON evidence. Recognition/ASR weights, original videos, caches, development environments and executables remain outside Git. `local-assets-manifest.json` records paths, sizes and SHA-256 hashes for 107 local inputs; it is not a full training-corpus backup.

## Restore authorized inputs

Use Windows, Python 3.11 and Node.js 22+. From the checkout root:

```powershell
py -3.11 tools/restore_local_assets.py --from "D:\complete-copy\vsl-clinic-desktop"
./tools/setup.ps1
npm start
```

Replace the example path with an existing complete Clinic folder you are authorized to use. The tool copies only manifest-listed files, verifies hashes before and after copying, and refuses to overwrite an existing file with different content. It does not download data or infer redistribution rights from a source URL. Missing inputs are reported without replacing existing files.

To verify without copying:

```powershell
py -3.11 tools/restore_local_assets.py
```

After restoration, run `.venv/Scripts/python.exe -m pytest -q`, `npm test` and `npm run build`.

## Source versus portable distribution

The portable distribution runs independently of this checkout and includes its own runtimes and model files. Keep its complete folder together. [Package contents](PACKAGE_CONTENTS.md) distinguishes recognition labels, avatar motions, sample videos and raw research references.

Research scripts such as `prepare_assets.py`, `expand_vocabulary.py`, `build_qipedc_bank.py` and `research_qipedc.py` retain default paths to the original corpus. They are separate data-building tools, not part of setup or startup. Rebuilding the bank requires the appropriate original corpus; the tested motion bank is already in Git.

Inherited recognition code is checked against fixed hashes in `backend/legacy/provenance.json`; tests do not depend on the Android/server parent's current revision. QIPEDC source checks read restored videos from `assets/reference-source/qipedc` instead of the original workstation's absolute paths.
