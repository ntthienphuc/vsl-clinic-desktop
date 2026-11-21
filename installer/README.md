# Offline Windows installer

`vsl-clinic.iss` creates one installer containing the complete verified portable
payload. It installs for the current Windows user, creates **VSL Clinic** on the
Desktop and Start Menu, and registers an uninstaller. Profiles live separately
in `%LOCALAPPDATA%\VSL Clinic\UserData`; uninstalling does not erase that profile
or the historical portable baseline.

Build with Inno Setup 7 from [the publisher](https://jrsoftware.org/isdl.php):

```powershell
npm.cmd run package
.venv\Scripts\python.exe tools\release_receipt.py
npm.cmd run installer -- --compiler "C:\path\to\Inno Setup 7\ISCC.exe"
```

The output is `../Installer/VSL-Clinic-Setup-0.7.5.exe` (installer revision R3). Build and inventory receipts
are under `../Organization/Installer_0.7.5`. Installation and runtime verification
are separate from successful compilation. No automatic upload or publication is
part of either command. Setup R3 has no license acceptance page and no information-only
page. The original component licenses remain in the payload. The separate Word document
`Giay_phep_VSL_Clinic.docx` is provided beside Setup and installed at
`Tai_lieu/Giay_phep_VSL_Clinic.docx`; changing presentation does not alter its terms.

The Vietnamese translation is the unmodified file linked by the publisher's
[translation index](https://jrsoftware.org/files/istrans/), maintained by memecoder:
`https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/Unofficial/Vietnamese.isl`.
Downloaded 2026-11-10; SHA-256
`1ed7f5580df3a302a6955c72ddbfA8e3c3e24d5ed22ea85f55bad548859b3a19`
(case-insensitive hexadecimal). The translator attribution is retained in the file.

The payload supports Windows 10/11 x64 and AVX2, with bundled Python/runtime/models/voice. Setup checks the CPU requirement and rejects source/portable destinations. The runtime selects actual working NVIDIA CUDA or CPU INT8; no Python/CUDA Toolkit download is needed. Driver installation and ARM/Jetson are outside this release. See `INSTALL_INFO.txt`.

Setup offers GPU NVIDIA (with CPU fallback) or CPU only. EnumDisplayDevices detects NVIDIA hardware for the initial selection; the application probes actual CUDA separately. `/COMPUTE=cpu` and `/COMPUTE=gpu` select an explicit mode for unattended QA. CPU excludes the full `resources/multimodal-runtime` tree. `runtime-preference.json` records the choice outside user profiles; reinstalling to switch GPU→CPU removes obsolete GPU files. Uninstall removes this generated preference, not UserData.

Verify selected installation with `tools/verify_installation.py --compute cpu` or `--compute gpu`. A GPU package audit expects both runtimes; a CPU installed parity check expects only the CPU runtime. Final acceptance is under `../Organization/ProductPolish_2026-11-15/ACCEPTANCE.json`.
