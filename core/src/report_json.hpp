// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include "edi/report_model.hpp"

namespace edi::detail {
// HTML-only derived renderer projections. Public ReportModel JSON and PDF fingerprints stay raw.
std::string report_html_model_json(const ReportModel& model);
}  // namespace edi::detail
