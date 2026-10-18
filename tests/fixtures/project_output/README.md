# Project output boundary

The contract names the project output sources and the exact shared-helper allow-list.
Every write, append, removal, rename and copy in those sources uses that helper. New
native or Python production sources under the declared roots are scanned as well.
The source inventory is a regression pin for the existing non-output source set.
It carries no scientific reference values.

The native helper is `crysta::output` in `include/crysta/project_output.hpp` and
`src/core/project_output.cpp`. Edi C++ calls it directly. Edi Python delegates its
project writes to `lib/edi/_project_output.py`.

The CLI's two user-selected JSON result writers, standard output and diagnostics are
outside this project boundary. Logs, browser files and temporary scratch directories
outside the named output sources keep their existing owners.

The small consumer and failure library exercise real core scans and Python callers.
Failures occur at the actual removal, replacement or source-read boundary. A read is
armed by an iteration callback after retained rows have already been admitted. Outside
bytes and complete earlier CSV rows supply the expectations; fitted numerical values
are never used as an accuracy reference.
