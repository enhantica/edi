// SPDX-License-Identifier: BSD-3-Clause
#include "report_view_model.hpp"

#include <QLocale>

#include "project_view_model.hpp"

namespace edi_app {
namespace {

// A number as the shortest text that reads back to the same double (so the report shows what the
// model holds: 8.0953, 0.10021171489061398).
QString number(double value) { return QString::number(value, 'g', QLocale::FloatingPointShortest); }

QString escaped(const QString& text) { return text.toHtmlEscaped(); }

QString row(const QString& label, const QString& value) {
    return QStringLiteral("<tr><td>%1</td><td>%2</td></tr>").arg(escaped(label), value);
}

QString section(const QString& title, const QString& rows) {
    return QStringLiteral("<h2>%1</h2><table cellspacing=\"0\" cellpadding=\"4\">%2</table>").arg(escaped(title), rows);
}

}  // namespace

ReportViewModel::ReportViewModel(const ProjectViewModel& project, QObject* parent)
    : QObject(parent), project_(project), rich_text_(compose()) {}

void ReportViewModel::refresh() {
    const QString text = compose();
    if (text != rich_text_) {
        rich_text_ = text;
        emit richTextChanged();
    }
}

QString ReportViewModel::compose() const {
    QString html = QStringLiteral("<h1>%1</h1>").arg(escaped(project_.title()));
    html += section(tr("Project information"),
                    row(tr("Title"), escaped(project_.title())) +
                        row(tr("Description"), escaped(project_.description())) +
                        row(tr("Structures"), QString::number(project_.structureModels().size())) +
                        row(tr("Experiments"), QString::number(project_.experimentModels().size())));
    for (const StructureViewModel* structure : project_.structureModels()) {
        const CellViewModel* cell = structure->cell();
        const auto value = [](const ParameterItem* item) { return item != nullptr ? number(item->value()) : QString(); };
        html += section(tr("Crystal data"),
                        row(tr("Datablock"), escaped(structure->name())) +
                            row(tr("Crystal system"), escaped(structure->spaceGroup()->crystalSystem())) +
                            row(tr("Space group"), escaped(structure->spaceGroup()->nameHM())) +
                            row(tr("Cell lengths a, b, c (Å)"), QStringLiteral("%1, %2, %3")
                                                                  .arg(value(cell->lengthA()), value(cell->lengthB()),
                                                                       value(cell->lengthC()))) +
                            row(tr("Cell angles α, β, γ (°)"), QStringLiteral("%1, %2, %3")
                                                                .arg(value(cell->angleAlpha()), value(cell->angleBeta()),
                                                                     value(cell->angleGamma()))));
    }
    for (const ExperimentViewModel* experiment : project_.experimentModels()) {
        const RangeViewModel* range = experiment->measuredRange();
        const QString unit = experiment->beamMode() == ExperimentViewModel::ConstantWavelength ? QStringLiteral("°")
                                                                                              : QStringLiteral("μs");
        const QString axis = experiment->beamMode() == ExperimentViewModel::ConstantWavelength ? tr("2θ") : tr("TOF");
        html += section(tr("Data collection"),
                        row(tr("Datablock"), escaped(experiment->name())) +
                            row(tr("Radiation probe"), escaped(experiment->radiationProbeToken())) +
                            row(tr("Beam mode"), escaped(experiment->beamModeToken())) +
                            row(tr("Measured range: min, max, inc (%1, %2)").arg(axis, unit),
                                QStringLiteral("%1, %2, %3")
                                    .arg(number(range->minimum()), number(range->maximum()), number(range->step()))) +
                            row(tr("Number of points"), QString::number(range->points())));
    }
    const AnalysisViewModel* analysis = project_.analysis();
    const ParameterTableModel* parameters = project_.parameters();
    html += section(tr("Fit"),
                    row(tr("Calculation engine"), QStringLiteral("crysta")) +
                        row(tr("Minimization engine"), escaped(analysis->minimizerType())) +
                        row(tr("Descent"), escaped(analysis->descent())) +
                        row(tr("Parameters"), tr("%1 (free %2, fixed %3)")
                                                  .arg(parameters->count())
                                                  .arg(parameters->freeCount())
                                                  .arg(parameters->fixedCount())) +
                        row(tr("Goodness of fit"), QString()));
    return html;
}

}  // namespace edi_app
