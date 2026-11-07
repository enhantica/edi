# 0075. One collection download implementation

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** 🟡 Partially implemented — the core (`edi/online_fetch.hpp`), the app's transport, the Python
  functions, the `python -m edi` commands and the docs' tutorials index; the standalone CLI's transport is pending
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
  - where a downloaded file goes: `<destination>/<file name>`;
  - unpacking a project archive into `<destination>/<entry id>-<first 12 digest characters>/`, through the existing
    archive reader with its path checks, so a replaced archive never reuses an old folder.
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
- **The standalone CLI's transport is decided separately.** It is Qt-free and Python-free (ADR-0007), so HTTPS there
  needs a new dependency. The cost goes to the owner before it is added; until then the standalone CLI offers no
  download commands, and `python -m edi` does.

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
