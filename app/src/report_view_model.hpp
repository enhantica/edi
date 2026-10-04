// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_REPORT_VIEW_MODEL_HPP
#define EDI_APP_REPORT_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

class ProjectViewModel;

// The Report page's text: a simple report as Qt rich text — project information, crystal data per
// structure, data collection per experiment, the fit — composed from the typed view-models
// (presentation only, ADR-0009's per-surface amendment) and re-composed once per coalesced change.
class ReportViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(QString richText READ richText NOTIFY richTextChanged)

   public:
    ReportViewModel(const ProjectViewModel& project, QObject* parent);
    QString richText() const { return rich_text_; }
    void refresh();

   signals:
    void richTextChanged();

   private:
    QString compose() const;
    const ProjectViewModel& project_;
    QString rich_text_;
};

}  // namespace edi_app

#endif  // EDI_APP_REPORT_VIEW_MODEL_HPP
