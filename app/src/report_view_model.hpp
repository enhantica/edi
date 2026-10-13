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

// The Report page (edi ADR-0035): the report model built from the project and the page's Contents and Export, given to
// QML as the model's JSON values, rebuilt once per coalesced change. The correlation level is the Analysis page's
// (its Correlations tab); the page reads the model only, never the project.
class ReportViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // The report model as its JSON values (report_to_json).
    Q_PROPERTY(QVariantMap model READ model NOTIFY modelChanged)
    // The Contents keys left out (the model's `contents`), each with everything under it.
    Q_PROPERTY(QStringList hidden READ hidden WRITE setHidden NOTIFY hiddenChanged)
    // Export: whether a saved report embeds its libraries (online by default; the owner, 2026-10-12).
    Q_PROPERTY(bool embedLibraries READ embedLibraries WRITE setEmbedLibraries NOTIFY embedLibrariesChanged)

   public:
    ReportViewModel(const ProjectViewModel& project, QObject* parent);

    QVariantMap model() const { return model_; }
    QStringList hidden() const;
    void setHidden(const QStringList& keys);
    bool embedLibraries() const { return embed_libraries_; }
    void setEmbedLibraries(bool on);

    // A Contents box: includes or leaves out the item of `key`.
    Q_INVOKABLE void setIncluded(const QString& key, bool included);
    // Builds the model again from the project; the project calls it once per coalesced change, and when the Analysis
    // page's correlation level changes.
    void refresh();

   signals:
    void modelChanged();
    void hiddenChanged();
    void embedLibrariesChanged();

   private:
    const ProjectViewModel& project_;
    edi::ReportOptions options_;
    bool embed_libraries_ = false;
    QVariantMap model_;
};

}  // namespace edi_app

#endif  // EDI_APP_REPORT_VIEW_MODEL_HPP
