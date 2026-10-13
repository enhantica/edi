// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_REPORT_VIEW_MODEL_HPP
#define EDI_APP_REPORT_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantMap>
#include <string>
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
    // The report model as its JSON values (report_to_json), without the charts' data: the pattern presentations and
    // the structure scenes and drawings, which the chart controllers read from reportModel().
    Q_PROPERTY(QVariantMap model READ model NOTIFY modelChanged)
    // The Contents keys left out (the model's `contents`), each with everything under it.
    Q_PROPERTY(QStringList hidden READ hidden WRITE setHidden NOTIFY hiddenChanged)
    // Export: whether a saved report embeds its libraries (online by default; the owner, 2026-10-12).
    Q_PROPERTY(bool embedLibraries READ embedLibraries WRITE setEmbedLibraries NOTIFY embedLibrariesChanged)
    // The Report page is shown. Only then does a change rebuild the model at once; otherwise the next read of the
    // model rebuilds it, so a reader never sees a stale one and a hidden page costs nothing per change.
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)

   public:
    ReportViewModel(const ProjectViewModel& project, QObject* parent);

    QVariantMap model() const {
        ensureBuilt();
        return model_;
    }
    const edi::ReportModel& reportModel() const {
        ensureBuilt();
        return report_;
    }
    bool active() const { return active_; }
    void setActive(bool active);
    // The model's pattern of an experiment and its structure of a structure id; null when it has none.
    const edi::ReportPattern* pattern(const QString& experiment) const;
    const edi::ReportStructure* structure(const QString& id) const;
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
    void activeChanged();

   private:
    // Builds the model from the project; whether it changed.
    bool build() const;
    // A read while a change is pending builds the model first. A model the read changed is announced afterwards, so
    // the readers that read it before (the chart controllers) read it again.
    void ensureBuilt() const;

    const ProjectViewModel& project_;
    edi::ReportOptions options_;
    bool embed_libraries_ = false;
    bool active_ = false;
    // The model, rebuilt on a read when a change arrived while the page was hidden (`dirty_`).
    mutable bool dirty_ = true;
    mutable edi::ReportModel report_;
    mutable std::string json_;  // report_'s JSON: a rebuild that writes the same announces nothing
    mutable QVariantMap model_;
};

}  // namespace edi_app

#endif  // EDI_APP_REPORT_VIEW_MODEL_HPP
