# 0109. UTF-8 paths on Windows

- **Status:** Accepted
- **Date:** 2026-11-27
- **Implementation:** ✅ Implemented
- **Priority:** Highest
- **Forward constraint (binding on new features):** a narrow string that holds a path is UTF-8 everywhere in edi; a new
  Windows executable gets the manifest from the build without asking for it, and the Python module turns every path
  argument into the narrow text core expects through its one conversion.

## Context

edi passes paths through its core and through crysta as `std::string`. Everything that makes such a string writes
UTF-8: Qt's `QString::toStdString`, nanobind for a Python `str`, the project files. On Windows, MSVC's narrow file calls
(`std::filesystem::path(std::string)`, `path::string()`, `std::ifstream` with a narrow name, `fopen`) read and write the
process's ANSI code page instead. So a folder called "Université" was created as "UniversitÃ©" on a Western Windows,
and a name like "Łódź", or any path under a Polish or Greek user name, threw `std::system_error`, sometimes where
nothing caught it, which could close the app while it built the list of recent projects.

A count of the places that do this found about two hundred in crysta and over four hundred in edi, half of them only
building error messages.

## Decision

1. **Every executable edi builds for Windows carries `cmake/windows/utf8.manifest`**, which sets the process's
   `activeCodePage` to UTF-8 (Windows 10 1903 and later). `cmake/edi_windows_manifest.cmake` adds it to each executable
   target once the whole tree is configured and stops the configure if one lacks it. Inside edi's programs every narrow
   call, in edi, in the crysta it links and in other libraries, then reads and writes UTF-8, and the CLI's `argv` keeps
   every letter. `tools/ci/windows_manifest.py` reads the manifest embedded in the built programs, in the Windows app
   build and in the installer and CLI packaging, and also checks that Python's own executable fails the same test.
2. **The app catches what a path check or a save's last step can throw.** `Session::projectDirectoryExists` lists a
   path it cannot check as missing, `Session::publishStaged` reports a refusal, and the scope guards that remove a
   save's staging folder never throw.
3. **The Python module converts at its boundary.** It runs inside `python.exe`, whose code page is the system's. Every
   argument that names a folder or a file, `Path` or `str`, becomes a `std::filesystem::path` and reaches core as its
   `.string()`, in the process code page, so names that code page holds work; a name it cannot hold is refused with a
   `ValueError` that names the Windows setting "Use Unicode UTF-8 for worldwide language support", with which every
   name works. Path text core hands back (the save messages, the importer callback's argument, the scan's template file
   and data folder, the report files written, a download's folder) is turned back into UTF-8 for Python, and the data
   file name a single crystal's load records is taken from the UTF-8 argument.
4. On Windows builds that ignore the setting the app logs one warning at start.

## Consequences

- The fix covers every narrow call in edi's programs at once, including ones added later, without a rule to remember.
- Windows 10 before 1903 keeps the old behaviour.
- In `python.exe` without the system setting, a path outside the code page is refused rather than misnamed, and names
  core itself writes into project files (a scan's relinked data folder, a listed scan file's name) stay in the code
  page. Lifting that needs every narrow path call in core and crysta converted one by one.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Convert every narrow path call in core and crysta to and from UTF-8 explicitly | Rejected for now: over six hundred places in two repositories, kept right only by review, and inside edi's programs it changes nothing the manifest does not. It is the way to lift the Python module's limit. |
| `wmain` in the CLI and wide paths at the app's own call sites only | Rejected: core and crysta would still read narrow strings in the code page. |
| Set the C runtime's locale to UTF-8 inside the Python module | Rejected: it changes the whole Python process, not only edi. |
