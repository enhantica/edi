// SPDX-License-Identifier: BSD-3-Clause
#pragma once

namespace edi_cli {

/// Run a download command (list-data, download-data, list-tutorials, download-tutorial or
/// download-all-tutorials) and answer its exit code, or -1 when `argv[1]` names none of them.
int run_downloads(int argc, char** argv);

/// The download commands' usage lines.
const char* download_usage();

}  // namespace edi_cli
