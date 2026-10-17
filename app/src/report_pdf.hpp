// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_REPORT_PDF_HPP
#define EDI_APP_REPORT_PDF_HPP

#include <QByteArray>
#include <QHash>
#include <QImage>
#include <QString>

#include "edi/report_model.hpp"

namespace edi_app {

// The static PDF report (edi ADR-0036): the core's static HTML of `model` laid out on A4 pages with the HTML report's
// 2.5 cm margins, in `fontFamily` at its 10.04 pt, the page number centred under each page. `figures` holds each figure's image under its name in the static HTML (structure-0, pattern-1, ...); a
// figure without one is left empty. Empty when the PDF could not be written.
QByteArray reportPdf(const edi::ReportModel& model, const QHash<QString, QImage>& figures, const QString& fontFamily);

}  // namespace edi_app

#endif  // EDI_APP_REPORT_PDF_HPP
