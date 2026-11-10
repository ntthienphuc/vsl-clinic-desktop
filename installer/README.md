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

The output is `../Installer/VSL-Clinic-Setup-0.5.2.exe`. Build and inventory receipts
are under `../Organization/Installer_0.5.2`. Installation and runtime verification
are separate from successful compilation. No automatic upload or publication is
part of either command. The AV-HuBERT research license is included and displayed
by Setup; bundling does not remove its restrictions.

The Vietnamese translation is the unmodified file linked by the publisher's
[translation index](https://jrsoftware.org/files/istrans/), maintained by memecoder:
`https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/Unofficial/Vietnamese.isl`.
Downloaded 2026-11-10; SHA-256
`1ed7f5580df3a302a6955c72ddbfA8e3c3e24d5ed22ea85f55bad548859b3a19`
(case-insensitive hexadecimal). The translator attribution is retained in the file.
