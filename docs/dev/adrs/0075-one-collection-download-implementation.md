# 0075. One collection download implementation

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a new interface or feature that reads EasyDiffraction's collection
  supplies only a transport and its presentation; choosing the location, falling back, resolving an id or a listing
  number, checking size and digest, choosing where a file goes and unpacking an archive happen once, in the core.

## Context

ADR-0068 gave every interface one collection index, read by the core's parser. Fetching was left to each interface,
and it now exists twice: in Qt for the app and the web app (`app/src/online_fetch.cpp`: location order, the outage
rule, size and digest checks) and in plain Python (`lib/edi/_collection.py`: the same rules again). The standalone CLI
has none. The Python package and the CLI should also offer diffraction-lib's download surface (`list_data`,
`download_data`, `list_tutorials`, `download_tutorial`, `download_all_tutorials` and the matching `python -m`
commands, with listing numbers and archive extraction), and tutorial notebooks should get their files that way. A
third and fourth copy of the rules would drift, which ADR-0009 (a C++ product core with thin bindings) exists to
prevent.

## Decision

- **The rules live in the core, in `edi::online`, beside the index parser.** It owns:
  - resolving what a user names, an entry id or a 1-based number from a listing (a number is a row on screen, never
    stored), with one listing order for every interface: entries with a learning `order` (tutorials) first by it, then the rest by id,
    as diffraction-lib lists them;
  - the order of locations for a request and the fallback rule of ADR-0068: the next location only after an outage (a
    transport, proxy or server failure or a 5xx answer), never after an answer such as a 404;
  - checking received bytes against the size and SHA-256 the index records, with a SHA-256 in the core;
  - where a downloaded file goes: `<destination>/<file name>`, the last component of its path in the collection. A
    raw copy of an entry's file (`Collection.fetch`) goes the same way, replacing what is there and never unpacked;
  - unpacking a project archive into `<destination>/<entry id>-<first 12 digest characters>/`, through the existing
    archive reader with its path checks, so a replaced archive never reuses an old folder;
  - turning names into paths in one place. An index is untrusted input, since anyone can point `source` at one, and a
    valid digest vouches for the bytes, not for the names. An entry id, a collection file name and an archive member
    become a path only through `edi::safe_relative_path` (`core/include/edi/safe_names.hpp`), which admits a grammar
    and refuses everything else. Collection names and the archives a collection serves use the closed collection
    grammar: segments of ASCII letters, digits, `.`, `_` and `-` that start and end with a letter, digit, `_` or `-`,
    at most 128 bytes each. An entry id is at most 115 bytes, so the project folder `<id>-<12 digest characters>` is
    itself an admitted name. A project archive the user saves or opens uses the project grammar of the same function,
    so their own file names (accents, spaces, a leading dot) survive a save and reopen: Unicode scalar values in UTF-8
    (no overlong form, surrogate or value above U+10FFFF) except control characters and `/ \ : * ? " < > |`, at most
    255 bytes a segment. Every rule refuses an empty, `.` or `..` segment, a trailing dot or space, a Windows device
    name (CON, PRN, AUX, NUL, COM0-9, LPT0-9, and COM or LPT with a superscript 1-3) in any case, with any extension or
    trailing spaces before it, and a name over 1024 bytes. Each placement is a direct child of the destination by
    construction, and edi never writes an archive it would refuse to open;
  - stage, check, then publish. A file goes to a staging file created exclusively for that call and is renamed over
    the final name. A project archive is unpacked into a folder created for that call beside its final place, with
    every member read checked by the reader's own status (an empty member included), every directory, open, write,
    flush and close checked, and published by one rename only when all of them succeeded. The staging folder and
    every folder in it are created owner-only; just before the rename the tree's folders get the owner's full access
    plus the group and other bits of the destination folder, each change checked, so the owner can always traverse and
    remove the tree; any failure removes the staging folder and reports it;
  - a cached project counts only when complete: its marker, a hidden `.<folder>.complete` file beside it holding the
    archive's SHA-256, is written last after the rename, and a later download reuses the folder only when that marker
    is a plain file naming the index's digest and the folder and its `project.edi` are plain entries. Anything else is
    replaced by a fresh download.
- **The transport boundary.** The core never opens a network connection. It works as a small state machine that an
  interface drives: it names the next URL to read; the interface reads it and reports the bytes, or a failure marked as
  an outage or an answer; the core then names the next URL, or finishes with verified bytes or with the reason it
  stopped. The same machine serves a blocking transport (Python's `urllib`, the standalone CLI) and an asynchronous
  one (Qt networking in the app and in the web app, where a request cannot block). Interfaces keep only reading bytes,
  progress and their own messages.
- **The app's behaviour does not change.** `app/src/online_fetch.cpp` keeps its Qt transport, proxy, timeouts,
  progress and messages and calls the core for order, fallback and checks; `lib/edi/_collection.py` becomes a thin
  binding. Existing app fixtures for the popup, the Examples list and the online-source probe stay as they are and
  must pass unchanged.
- **Downloads follow the collection's `main`, as the app does; they do not pin a data commit.** diffraction-lib pins
  its data repository to one commit per package version. Here the app has always read `main`, and gate 13 requires an
  entry found by id to equal the app's. Pinning Python alone would split the two. Integrity comes from the index: every
  file has a size and SHA-256 and a mismatch refuses. A changed file must take a new id, so a published id keeps meaning
  the same bytes. `EDI_COLLECTION` still selects another collection.
- **Tutorials are indexed by the documentation site, not by the data collection.** The docs build writes
  `tutorials/index.json` in the collection's format: one `tutorial` entry per tutorial, with its learning `order`, with
  its notebook and Python source as files with their sizes and SHA-256, published beside them. A tutorial is
  documentation versioned with the code that runs it. Its data stays in `enhantica/edi-data`, and its notebook fetches
  the data with `download_data`.
- **The standalone CLI uses the operating system's HTTPS.** It stays Qt-free and Python-free (ADR-0007): WinHTTP on
  Windows, and on macOS and Linux the system libcurl, loaded only when a download needs it. A Linux system without
  libcurl still fits projects; its download commands say that libcurl is missing, and a local folder given with
  `--source` still works. Nothing is added to the download. Bundling libcurl and OpenSSL, or Qt Network, was rejected
  for the size and the security updates it would bring (decision of 2026-11-07).

## Consequences

- One place to change fallback, checking or layout, and one set of tests for them. The app, Python and the CLI cannot
  disagree on what an id, a number or a destination means.
- The core gains a SHA-256 and a little state; interfaces lose code.
- Following `main` means a tutorial run today and next month can receive different entries under new ids, never
  different bytes under one id. Reproducing an old run means naming the ids it used.
- A data change that keeps an id but changes its bytes is refused by every interface until the index is corrected.

## Alternatives considered

- **Extend `lib/edi/_collection.py` and mirror it in the CLI.** Rejected: a third copy of rules the app already has.
- **A blocking `fetch(url)` callback in the core.** Rejected: the web app cannot block on a request, and the app's
  requests are asynchronous; a state machine serves both.
- **Pin the data commit, as diffraction-lib does.** Rejected for now: it splits Python from the app, and every data
  fix would need a package release. It can be added later as an optional pin, recorded in the index, without changing
  this boundary.
- **Index tutorials in `edi-data`.** Rejected: notebooks change with the code and the docs; the data collection is
  versioned separately.


The passive tutorial input observer covers both whole-project downloads and the
existing model-building tutorials that consume collection CIFs and measurements.
It validates adjacent download/consumer assignments and literal temperature maps,
with the same guarded-install syntax handling. Declared native input files determine
the required asset identities; unused downloads, changed variables, duplicate map
keys, indirect paths and unreachable download calls refuse. Execution exclusions
remain governed by their explicit shared declaration rather than obsolete embedded
warnings in portable notebooks.
