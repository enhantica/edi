// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_REPORT_VIEW_MODEL_HPP
#define EDI_APP_REPORT_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantMap>
#include <QtQml/qqmlregistration.h>

#include "edi/report_model.hpp"

namespace edi_app {

class ProjectViewModel;

// The Report page (edi ADR-0035): the report options its sidebar sets, and the report model built from them, given to
// QML as the model's JSON values, rebuilt once per coalesced change of the project or the options. The page reads the
// model only, never the project.
class ReportViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // The report model as its JSON values (report_to_json).
    Q_PROPERTY(QVariantMap model READ model NOTIFY modelChanged)
    // Contents: the sections shown (report_section_name), the parameters (all, or the free ones only) and the
    // correlation level (`automaticLevel`: the five most correlated parameters, as the Correlations tab).
    Q_PROPERTY(QStringList sections READ sections WRITE setSections NOTIFY sectionsChanged)
    Q_PROPERTY(bool freeParametersOnly READ freeParametersOnly WRITE setFreeParametersOnly NOTIFY freeParametersOnlyChanged)
    Q_PROPERTY(bool automaticLevel READ automaticLevel WRITE setAutomaticLevel NOTIFY automaticLevelChanged)
    Q_PROPERTY(double correlationLevel READ correlationLevel WRITE setCorrelationLevel NOTIFY correlationLevelChanged)
    // Charts: the experiments drawn (empty: all), the x axis on d, the residual and the Bragg ticks.
    Q_PROPERTY(QStringList experiments READ experiments WRITE setExperiments NOTIFY experimentsChanged)
    Q_PROPERTY(bool dSpacing READ dSpacing WRITE setDSpacing NOTIFY dSpacingChanged)
    Q_PROPERTY(bool residual READ residual WRITE setResidual NOTIFY residualChanged)
    Q_PROPERTY(bool braggTicks READ braggTicks WRITE setBraggTicks NOTIFY braggTicksChanged)
    // Export: whether a saved report embeds its libraries (online by default; the owner, 2026-10-12).
    Q_PROPERTY(bool embedLibraries READ embedLibraries WRITE setEmbedLibraries NOTIFY embedLibrariesChanged)

   public:
    ReportViewModel(const ProjectViewModel& project, QObject* parent);

    QVariantMap model() const { return model_; }
    QStringList sections() const;
    void setSections(const QStringList& names);
    bool freeParametersOnly() const { return options_.free_parameters_only; }
    void setFreeParametersOnly(bool only);
    bool automaticLevel() const { return !options_.correlation_level.has_value(); }
    void setAutomaticLevel(bool automatic);
    double correlationLevel() const { return level_; }
    void setCorrelationLevel(double level);
    QStringList experiments() const;
    void setExperiments(const QStringList& ids);
    bool dSpacing() const { return options_.d_spacing; }
    void setDSpacing(bool on);
    bool residual() const { return options_.residual; }
    void setResidual(bool on);
    bool braggTicks() const { return options_.bragg_ticks; }
    void setBraggTicks(bool on);
    bool embedLibraries() const { return embed_libraries_; }
    void setEmbedLibraries(bool on);

    // Builds the model again from the project; the project calls it once per coalesced change.
    void refresh();

   signals:
    void modelChanged();
    void sectionsChanged();
    void freeParametersOnlyChanged();
    void automaticLevelChanged();
    void correlationLevelChanged();
    void experimentsChanged();
    void dSpacingChanged();
    void residualChanged();
    void braggTicksChanged();
    void embedLibrariesChanged();

   private:
    void changed(void (ReportViewModel::*signal)());

    const ProjectViewModel& project_;
    edi::ReportOptions options_;
    double level_ = 0.5;  // the level the Contents box holds, used when the level is not automatic
    bool embed_libraries_ = false;
    QVariantMap model_;
};

}  // namespace edi_app

#endif  // EDI_APP_REPORT_VIEW_MODEL_HPP
