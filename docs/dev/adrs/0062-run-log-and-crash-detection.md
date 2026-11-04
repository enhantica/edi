# 0062. A log of every run, and crash detection

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** 🟡 Partially implemented — the log, its rotation and the crash detection are in; the crash popup
  comes with the Help and feedback form
- **Priority:** Medium

## Context

When something goes wrong, a user should be able to send what the app was doing. Until now the app printed Qt's
messages to the terminal only, which most users never see, and the Preferences "Logging to" choice was a disabled
placeholder from the GUI base. The base's Python apps wrote one aligned line per message with the time since the
previous one, its level, whether it came from QML or Python, and where; edi keeps that shape.

## Decision

Every Qt message of a run, from C++, from QML and from what the app reports of crysta's calculations, goes through one
message handler (`RunLog`, installed by `main` before the QML engine starts). Messages at or above the Preferences
level (Debug, Info, Error or Disabled; Info by default, and Info includes warnings) go to stderr and to this run's file.
A fatal message is always written.

**Where.** `logs/session-<yyyyMMdd>-<HHmmss>.log` in the app's data folder (`QStandardPaths::AppDataLocation`). A demo
or test run that uses fresh settings logs into that fresh folder, and `EDI_APP_DATA_DIR` names another data folder for
a test. The browser keeps no file.

**Header.** The file starts with `# EasyDiffraction run log` and `# key: value` lines, in this order: `date` (the date
and UTC offset, the only place the date appears), `app` (version and commit), `crysta` (version and SDK commit), `Qt`,
`OS` (product, kernel and CPU architecture), `graphics` (the Qt Quick graphics API) and `preferences` (logging level,
threads per calculation, parallel fits, colour scheme, sidebar side, tooltips).

**Lines.** After the header every line is one record, fields separated by two spaces:

```text
HH:MM:SS.mmm  +S.SSS  LEVEL     source  message  location
```

- `HH:MM:SS.mmm`: local time.
- `+S.SSS`: seconds since the previous record, a plus and exactly five characters, rounded to fit (`+0.091`, `+50.65`,
  `+116.2`, `+12345`).
- `LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `FATAL` (Qt's debug, info, warning, critical and fatal), padded to
  eight characters.
- `source`: `crysta` for the `crysta` category, `qml` for a message from a `.qml` or `.js` file or the `qml`/`js`
  categories, else `app`, padded to six characters. The component a message came from is in its location.
- `message`: one line of the text, trimmed, tabs as spaces, `-` when empty. A message of several lines becomes several
  records with the same time; the later ones have `+0.000`.
- `location`: `file:line` with the file's name only, never its folder, or `-`. The app builds with
  `QT_MESSAGELOGCONTEXT` so release builds keep C++ locations.

A file stops growing at 5,000,000 bytes, after one `WARNING` record saying so; the terminal keeps every line.

**Actions.** Each thing the user does with a control is one `INFO` record from `app` (`UserActionLog`, one application
event filter for every control): `click <name>` for a button or tab, `choose <name> = <choice>` for a combo box, `check
<name> = on|off` for a check box, and for a field once its value is committed and changed, `set <name> = <number>` when
the field is made for a number (a parameter's value, a field or cell accepting a number or an integer, or one with a
number validator) and `edit <name>` otherwise. A control is named by its object name, else by its type and page. What a
field is for decides, never what it holds: free text (a message, a name, a title, an e-mail) is never written, even when
it reads as a number.

**Rotation.** At start the app keeps this run's log and the two newest earlier ones and removes older `session-*.log`
files, except a crashed run's log and any log whose lock file exists when it would be removed.

**Names.** A run reserves its name by taking `session-<...>.running` first and only then creating its log, which must
not exist yet; a name that is held or already used moves to `session-<...>-2`, `-3` and so on. A run never opens an
existing log, so two instances starting in the same second never write into one file.

**Crash detection.** While it runs, a run holds `session-<...>.running` beside its log as a `QLockFile` (stale only
when its process is gone, never by age). A normal quit releases it, which removes it. At the next start a lock file
that can be taken belongs to a run that ended without quitting: its log is `RunLog.crashedLog`, offered for a problem
report through Help and feedback, and kept until `RunLog.dismissCrash()`. Two instances running at once do not see
each other as crashed. On Linux and macOS, Ctrl+C and SIGTERM quit the app as closing its window does, so
they are not reported as crashes.

## Consequences

- The log stays on the user's disk; it leaves the machine only when the user sends a report with the log included.
- Every new warning in the app also reaches the user's log file, so warnings stay rare and meaningful.
- Tests make their own `RunLog` with an injected folder and clock, or point a real run at `EDI_APP_DATA_DIR`.
