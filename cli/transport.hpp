// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <string>

#include "edi/online_fetch.hpp"

namespace edi_cli {

/// Read one URL for the core's downloads: http(s) through the operating system's HTTPS (WinHTTP on Windows, the
/// system libcurl elsewhere), anything else from disk. A transport or server failure is an outage, a refusal such as a
/// 404 is an answer (edi ADR-0068).
edi::online::Reply fetch(const std::string& url);

/// Whether http(s) can be read on this system; when not, `why` says what is missing.
bool web_available(std::string& why);

}  // namespace edi_cli
