# 0091. Code signing and notarisation on macOS and Windows

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** ⬜ Not implemented
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

The ids change together with signing, because signing gives the app a new identity on macOS anyway. The
first signed release reads settings from the old location when the new one is empty, and its installer
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
| `CODESIGN_WIN_KEYLOCKER_HOST` | secret | `https://clientauth.one.digicert.com` |
| `CODESIGN_WIN_KEYLOCKER_API_KEY` | secret | the KeyLocker API key |
| `CODESIGN_WIN_KEYLOCKER_KEYPAIR_ALIAS` | secret | the key pair alias, `key_…` |

The team id and identity are variables, not secrets, because every signed app shows them.

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
4. From DigiCert ONE, store the API key in `CODESIGN_WIN_KEYLOCKER_API_KEY` and the key pair alias in
   `CODESIGN_WIN_KEYLOCKER_KEYPAIR_ALIAS`; `CODESIGN_WIN_KEYLOCKER_HOST` is
   `https://clientauth.one.digicert.com`.
5. Delete `cert.p12` and `cert.b64` from the disk.

The workflow `.github/workflows/codesign-check.yml` checks the macOS entries without building anything:
it imports the certificate, signs a test file and logs in to the notary service.

**macOS steps**, in the installer job:

1. Import the `.p12` into a temporary keychain that the job deletes at the end.
2. Sign every executable and library inside the app bundle, then the bundle, with
   `codesign --options runtime --timestamp`; the hardened runtime is required for notarisation.
3. Build the installer app with Qt Installer Framework and sign it the same way, then build and sign the
   `.dmg`.
4. Notarise with `xcrun notarytool submit --wait`, using the Apple ID, app-specific password and team id.
5. Staple the ticket with `xcrun stapler staple`, then check with `spctl --assess` and `codesign --verify`.

**Windows steps**, in the installer job:

1. Install DigiCert's tools with the `digicert/ssm-code-signing` action, pinned to a release.
2. Decode the client `.p12` and set `SM_HOST`, `SM_API_KEY`, `SM_CLIENT_CERT_FILE` and
   `SM_CLIENT_CERT_PASSWORD` for the job.
3. Sign every shipped `.exe` (the app, the maintenance tool and the installer) with
   `smctl sign --keypair-alias`, using the configuration file the action installs.
4. Check with `signtool verify /pa`.

**When signing runs.** Only on release builds and pushes to `main`, never on pull requests, so a pull
request from a fork can never reach the credentials. A pull request build stays unsigned and still runs every
installer check. Linux installers are not signed.

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
