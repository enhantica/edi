# 0091. Code signing and notarisation on macOS and Windows

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** ✅ Implemented
- **Priority:** High

## Context

The installers from [ADR-0071](0071-desktop-installers.md) are unsigned. macOS refuses to open them until the
user allows them in System Settings, and Windows SmartScreen warns about an unknown publisher. Both put off
new users. EasyDiffractionBeta signed its macOS installer with the European Spallation Source Developer ID
and had a Windows step prepared but disabled. easyscience keeps its signing credentials as organisation
secrets with `CODESIGN_<OS>_` names, listed in its organisation discussion on GitHub secrets.

## Decision

**Identity.** The app is signed as the European Spallation Source:

| | Value |
|---|---|
| Apple team | `W2AG9MPZ43` |
| Apple signing identity | `Developer ID Application: European Spallation Source Eric (W2AG9MPZ43)` |
| Windows | the DigiCert KeyLocker key pair, reached by its alias |

**Bundle and component ids.** The project now owns easydiffraction.org, so the ids use that domain:

| Where | Before | After |
|---|---|---|
| macOS bundle id (`app/CMakeLists.txt`) | `org.easyscience.easydiffraction` | `org.easydiffraction.app` |
| Installer component, app (`tools/installer/package.py`) | `org.easyscience.edi` | `org.easydiffraction.app` |
| Installer component, AI assistant | `org.easyscience.edi.assistant` | `org.easydiffraction.app.assistant` |
| Settings organisation (`app/main.cpp`) | `EasyScience` | `EasyDiffraction` |

The ids change in their own change, together with the settings migration, not with the signing steps. The
first release with the new ids reads settings from the old location when the new one is empty, and its installer
replaces the old components, so existing users keep their preferences and update in place.

**Secrets and variables** (GitHub Actions, repository level on edi). The names follow easyscience's:

| Name | Kind | Content |
|---|---|---|
| `CODESIGN_MAC_CERT_P12_BASE64` | secret | base64 of the `.p12` holding the Developer ID Application certificate and its private key |
| `CODESIGN_MAC_CERT_P12_PASSWORD` | secret | the `.p12` password |
| `CODESIGN_MAC_NOTARY_APPLE_ID` | secret | the Apple ID used for notarisation, a member of the team above |
| `CODESIGN_MAC_NOTARY_PASSWORD` | secret | an app-specific password for that Apple ID |
| `CODESIGN_MAC_TEAM_ID` | variable | `W2AG9MPZ43` |
| `CODESIGN_MAC_IDENTITY` | variable | the signing identity above |
| `CODESIGN_WIN_CERT_P12_BASE64` | secret | base64 of the KeyLocker client authentication `.p12` (not the signing key, which stays in KeyLocker) |
| `CODESIGN_WIN_CERT_P12_PASSWORD` | secret | its password |
| `CODESIGN_WIN_KEYLOCKER_HOST` | variable | `https://clientauth.one.digicert.com` |
| `CODESIGN_WIN_KEYLOCKER_API_KEY` | secret | the KeyLocker API key |
| `CODESIGN_WIN_KEYLOCKER_KEYPAIR_ALIAS` | variable | the key pair alias, `key_…` |

The team id, identity, KeyLocker host and key pair alias are variables, not secrets: the first two are shown
by every signed app, and the last two are useless without the client certificate and API key.

**Preparing the secrets.** Done once per certificate, and again when one expires.

macOS, on a Mac with the Developer ID Application certificate in Keychain Access:

1. In Keychain Access, open **My Certificates**, right-click "Developer ID Application: European Spallation
   Source Eric (W2AG9MPZ43)" and choose **Export**. Save it as `cert.p12` with a password. Exporting from My
   Certificates includes the private key.
2. Check the file: `openssl pkcs12 -in cert.p12 -nokeys -legacy | grep subject` shows the identity, and
   `openssl pkcs12 -in cert.p12 -nocerts -nodes -legacy | head -1` prints a private key line.
3. Encode it: `base64 -i cert.p12 -o cert.b64` (or `base64 -i cert.p12 | pbcopy` to copy it). The output has
   no header lines and no line breaks.
4. Paste `cert.b64` into `CODESIGN_MAC_CERT_P12_BASE64` and the export password into
   `CODESIGN_MAC_CERT_P12_PASSWORD`.
5. At account.apple.com, under **Sign-In and Security → App-Specific Passwords**, create a password for the
   notarising Apple ID and store it in `CODESIGN_MAC_NOTARY_PASSWORD`, with the Apple ID email in
   `CODESIGN_MAC_NOTARY_APPLE_ID`.
6. Delete `cert.p12` and `cert.b64` from the disk.

Windows, with the DigiCert ONE account:

1. In DigiCert ONE, download the client authentication certificate as `cert.p12` and note its password.
2. Encode it in a Command Prompt: `certutil -encode cert.p12 cert.b64`. Remove the
   `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----` lines before pasting. In PowerShell,
   `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.p12")) | Set-Content cert.b64` writes it without
   them; on macOS or Linux, `base64 -i cert.p12 -o cert.b64` does the same.
3. Store the result in `CODESIGN_WIN_CERT_P12_BASE64` and the password in `CODESIGN_WIN_CERT_P12_PASSWORD`.
4. From DigiCert ONE, store the API key in the secret `CODESIGN_WIN_KEYLOCKER_API_KEY` and the key pair alias
   in the variable `CODESIGN_WIN_KEYLOCKER_KEYPAIR_ALIAS`; the variable `CODESIGN_WIN_KEYLOCKER_HOST` is
   `https://clientauth.one.digicert.com`.
5. Delete `cert.p12` and `cert.b64` from the disk.

To check new credentials before a release, do it by hand. A public workflow must not hold the signing secrets
outside the guarded installer job, so there is no separate check workflow.

- macOS, with the `.p12` imported into a keychain: `security find-identity -v -p codesigning` lists the
  identity; `codesign --force --options runtime --timestamp --sign "<identity>" <copy of a small binary>` then
  `codesign --verify --strict` signs and checks a test file; `xcrun notarytool history --apple-id <id>
  --password <app-specific password> --team-id W2AG9MPZ43` proves the notary login.
- Windows, with DigiCert's `smctl` and the four `SM_` variables set: `smctl sign --simple --keypair-alias
  <alias> --input <copy of a small .exe>` then `signtool verify /pa` signs and checks a test file.

**What is signed.** macOS and Windows check only files marked as downloaded (Gatekeeper and quarantine on
macOS, SmartScreen and the Mark of the Web on Windows); files an installer writes are not checked. So the
downloads are signed: the installers on both systems, the command-line `edi.exe` on Windows (its ZIP passes
the mark to the extracted files) and the command-line `edi` on macOS. The EasyDiffraction app is signed too, on
both systems, so it shows its publisher and passes institutional policies and antivirus checks more easily.
The assistant runtime's helper executables and the Windows maintenance tool are not signed yet; the Windows
tool runs unsigned, and signing it would take the same component as the macOS tool below, with a signed
`installerbase.exe`.

**macOS steps**, in the installer job of `.github/workflows/installers.yml`:

1. `apple-actions/import-codesign-certs` imports the `.p12` into a temporary keychain.
2. `tools/installer/build.py` signs every executable and library inside the app bundle, then the bundle, with
   the identity and `--timestamp`, without the hardened runtime. The app is not notarised: the installer
   writes it to disk, so it is never quarantined, as with EasyDiffractionBeta.
3. `tools/installer/standalone_cli.py` signs the command-line `edi` and the libraries in its `.runtime` folder
   with `codesign --options runtime --timestamp` before archiving them, then sends the ZIP to
   `xcrun notarytool submit --wait` and requires the status `Accepted`. A bare executable cannot be stapled, so
   Gatekeeper looks the ticket up online.
4. **The maintenance tool.** Qt Installer Framework normally writes `MaintenanceTool.app` on the user's Mac
   from the running installer's binary. Once the installer carries a real signature, that copy no longer
   matches it and macOS kills the tool, so users could not update or uninstall (the first signed release run
   showed it). So `package.py maintenance-tool` builds the tool on its own with `binarycreator --mt`, the
   Framework's way of making a maintenance tool for separate signing, and signs, notarises and staples it like
   the installer. Both installers carry it in a hidden, always-installed component
   (`org.easyscience.edi.maintenancetool`, carrying the app version like the other components, so the
   release, preview and Pages repository checks hold), whose script calls `installer.setInstallerBaseBinary`
   on the bundle; for a bundle the Framework moves it to the installation root unchanged instead of writing
   its own. An update lists the component but unpacks nothing and keeps the installed tool. Packaging refuses an unsigned tool when signing is on, and each
   test installation checks the installed tool with `codesign --verify --strict`, its Developer ID authority
   on release builds, and its checksum against the shipped one, before running it to uninstall. Unsigned
   builds sign the tool ad hoc and take the same path. EasyDiffractionBeta shipped a separately built tool
   the same way on Windows.
5. Qt Installer Framework builds the installer app. `tools/installer/package.py seal` signs it with
   `codesign --options runtime --timestamp`, notarises it the same way, staples the ticket with
   `xcrun stapler staple`, checks it with `codesign --verify` and `spctl --assess`, and archives it again. This
   runs for the offline and the online installer.

**Windows steps**, in the same job:

1. Decode the client `.p12` and set `SM_CLIENT_CERT_FILE`. `digicert/code-signing-software-trust-action@v1` in
   simple-signing mode, without an input, installs `smctl`. `SM_HOST`, `SM_API_KEY` and
   `SM_CLIENT_CERT_PASSWORD` are set only on the steps that sign.
2. With `smctl sign --simple`, `tools/installer/build.py` signs the app, `standalone_cli.py` signs `edi.exe`
   before archiving the command-line download, and `package.py seal` signs each installer before archiving it
   again.
3. `signtool verify /pa` checks each signed file and the installed app of each test installation.

**When signing runs.** Only for release builds of the installer workflow on `main` in this repository: a manual
run with a release plan or a preview-release preparation. `EDI_CODESIGN` is set for those runs and every signing
step depends on it, so a push to `main`, a pull request, a fork, another branch or any other manual run builds
unsigned and never reaches the credentials. Signing runs also take the GitHub environment `codesign`, which only
`main` may deploy to; every other run keeps `crysta-sdk`. An unsigned build signs the app ad hoc
as before and still runs every installer check. When signing is on, a missing credential, a refused signature
or a rejected notarisation fails the job, and nothing is uploaded or published. Linux installers are not
signed. Every installer check runs on the signed installers.

## Consequences

macOS opens the installer and the app without warnings, and Windows shows the European Spallation Source as
publisher. Every release depends on Apple's notary service and on DigiCert KeyLocker being available; when
either is down, the release waits. The credentials expire: the Developer ID certificate after five years,
the app-specific password when the Apple ID's password changes, the KeyLocker key when its certificate
lapses. A release that fails to sign stops rather than shipping unsigned.

## Alternatives considered

- **App Store Connect API key for notarisation** instead of an Apple ID and app-specific password. It belongs
  to the team rather than a person and keeps working when that person's account changes. It needs an admin
  of the Apple team to create it; it can replace the two `NOTARY` secrets later without other changes.
- **Keep the `org.easyscience` ids.** Rejected: the project has its own domain, and changing ids later
  would cost the same migration again.
- **Sign on pull requests too.** Rejected: fork pull requests cannot have secrets, and the signing checks are
  the same on `main`.
