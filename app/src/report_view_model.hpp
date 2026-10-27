// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_REPORT_VIEW_MODEL_HPP
#define EDI_APP_REPORT_VIEW_MODEL_HPP

#include <QHash>
#include <QImage>
#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QUrl>
#include <QVariantMap>
#include <optional>
#include <string>
#include <QtQml/qqmlregistration.h>

#include "edi/report_html.hpp"
#include "edi/report_model.hpp"

namespace edi_app {

class ProjectViewModel;

// One report Save report wrote, for QML: its file name, its format, when it was saved (in local time) and its state,
// "current", "out of date" (the report the project would make now differs from the one written) or "missing".
struct SavedReport {
    Q_GADGET
    QML_VALUE_TYPE(savedReport)
    Q_PROPERTY(QString name MEMBER name CONSTANT)
    Q_PROPERTY(QString format MEMBER format CONSTANT)
    Q_PROPERTY(QString saved MEMBER saved CONSTANT)
    Q_PROPERTY(QString state MEMBER state CONSTANT)

   public:
    QString name;
    QString format;
    QString saved;
    QString state;
    bool operator==(const SavedReport&) const = default;
};

// The Report page (edi ADR-0036): the report model built from the project and the page's Contents and Export, given to
// QML as the model's JSON values, rebuilt once per coalesced change. Its options are the project's report settings
// (ADR-0036 §7), which the Contents boxes, the Embed checkbox and the Analysis page's correlation level and x axis
// edit; the page reads the model only, never the project.
class ReportViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // The report model as its JSON values (report_to_json), without the charts' data: the pattern presentations and
    // the structure scenes and drawings, which the chart controllers read from reportModel().
    Q_PROPERTY(QVariantMap model READ model NOTIFY modelChanged)
    // The Contents keys left out (the model's `contents`), each with everything under it: the project's
    // `_report.excluded`, or the data when it states none.
    Q_PROPERTY(QStringList hidden READ hidden WRITE setHidden NOTIFY hiddenChanged)
    // Export: whether a saved report embeds its libraries, the project's `_report.html_offline` (online by default; the
    // owner, 2026-10-12).
    Q_PROPERTY(bool embedLibraries READ embedLibraries WRITE setEmbedLibraries NOTIFY embedLibrariesChanged)
    // Export: whether Save report writes the HTML (by default), the PDF and the CIF report, the project's
    // `_report.html`, `pdf` and `cif` (ADR-0036 §7).
    Q_PROPERTY(bool writesHtml READ writesHtml WRITE setWritesHtml NOTIFY writesHtmlChanged)
    Q_PROPERTY(bool writesPdf READ writesPdf WRITE setWritesPdf NOTIFY writesPdfChanged)
    Q_PROPERTY(bool writesCif READ writesCif WRITE setWritesCif NOTIFY writesCifChanged)
    // The reports Save report wrote, one per `_report_file` row.
    Q_PROPERTY(QList<edi_app::SavedReport> savedReports READ savedReports NOTIFY savedReportsChanged)
    // The name Save report gives its files, without the format's extension: the project's short name, else "report".
    Q_PROPERTY(QString fileStem READ fileStem NOTIFY fileStemChanged)
    // The Report page is shown. Only then does a change rebuild the model at once; otherwise the next read of the
    // model rebuilds it, so a reader never sees a stale one and a hidden page costs nothing per change.
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
    // The app's palette (a token of edi::colour_scheme_from_name), whose light colours the report's charts take.
    Q_PROPERTY(QString colourScheme READ colourScheme WRITE setColourScheme NOTIFY colourSchemeChanged)
    // The project's calculation or fit is in flight or owed, so the model is not yet its outcome; a save waits for it.
    Q_PROPERTY(bool calculating READ calculating NOTIFY calculatingChanged)

   public:
    ReportViewModel(ProjectViewModel& project, QObject* parent);

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
    QString colourScheme() const { return colour_scheme_; }
    void setColourScheme(const QString& scheme);
    bool calculating() const;
    // The model's pattern of an experiment and its structure of a structure id; null when it has none.
    const edi::ReportPattern* pattern(const QString& experiment) const;
    const edi::ReportStructure* structure(const QString& id) const;
    // An experiment's reliability text in the model (edi::reliability_text); empty with none.
    Q_INVOKABLE QString reliability(const QString& experiment) const;
    QStringList hidden() const;
    void setHidden(const QStringList& keys);
    bool embedLibraries() const;
    void setEmbedLibraries(bool on);
    bool writesHtml() const { return writes("html"); }
    void setWritesHtml(bool on) { setWrites("html", on); }
    bool writesPdf() const { return writes("pdf"); }
    void setWritesPdf(bool on) { setWrites("pdf", on); }
    bool writesCif() const { return writes("cif"); }
    void setWritesCif(bool on) { setWrites("cif", on); }
    QList<SavedReport> savedReports() const;
    QString fileStem() const;

    // A Contents box: includes or leaves out the item of `key`.
    Q_INVOKABLE void setIncluded(const QString& key, bool included);
    // Save report (ADR-0036 §7): each ticked format written into the project's `reports/` as `<short name>.html` or
    // `.pdf` (the browser also downloads it), then its `_report_file` row, through crysta's writer of
    // `reports/report.edi` alone. The HTML carries the chart libraries when embedLibraries is set; the PDF's figures
    // are the images setFigure gave since the last save, and its text is in `fontFamily`. Unticked formats' files and
    // rows are left as they are. A format that cannot be written leaves its old file and stops the formats after it;
    // the files written before it keep their rows. Answers with saved, or saveFailed for each failure.
    Q_INVOKABLE void saveReport(const QString& fontFamily);
    // One of the preview's figures for the next save's PDF, by its name in the static text (structure-0, pattern-1,
    // ...); a null image is left out.
    Q_INVOKABLE void setFigure(const QString& name, const QImage& image);
    // Builds the model again from the project; the project calls it once per coalesced change, and when the Analysis
    // page's correlation level changes.
    void refresh();

   signals:
    void modelChanged();
    void hiddenChanged();
    void embedLibrariesChanged();
    void writesHtmlChanged();
    void writesPdfChanged();
    void writesCifChanged();
    void savedReportsChanged();
    void fileStemChanged();
    void activeChanged();
    void colourSchemeChanged();
    void calculatingChanged();
    void saved(const QString& location);
    void saveFailed(const QString& message);

   private:
    // Builds the model from the project; whether it changed.
    bool build() const;
    // A read while a change is pending builds the model first. A model the read changed is announced afterwards, so
    // the readers that read it before (the chart controllers) read it again.
    void ensureBuilt() const;
    // Announces a rebuilt model, and the file stem when the model's name changed it.
    void publishModel();
    // Whether Save report writes `format`, and the edit that sets it.
    bool writes(const char* format) const;
    void setWrites(const char* format, bool on);
    // The vendored chart libraries, read once; null when one cannot be read.
    const edi::ReportLibraries* libraries() const;
    // The project's `reports/` folder.
    QString reportsDirectory() const;
    // What the report is built from: a scan's stored template, else the project.
    const edi::Project& reportInput() const;
    // The model the saved reports' rows are judged by (edi::report_file_options): report_ when the page shows the
    // default scheme and the first experiment's correlations, else one built with those, on its first use after a
    // change.
    const edi::ReportModel& judged() const;
    // The digest of the CIF report the project makes now, on its first use after a change; empty when crysta cannot
    // make one.
    const std::string& cifDigest() const;

    ProjectViewModel& project_;
    // What the hidden, embedLibraries, writes and fileStem properties last announced.
    QStringList published_hidden_;
    bool published_embed_ = false;
    bool published_writes_html_ = true, published_writes_pdf_ = false, published_writes_cif_ = false;
    QString published_file_stem_;
    mutable std::optional<edi::ReportLibraries> libraries_;
    bool active_ = false;
    QString colour_scheme_ = QStringLiteral("earth");
    // The model, rebuilt on a read when a change arrived while the page was hidden (`dirty_`).
    mutable bool dirty_ = true;
    mutable edi::ReportModel report_;
    mutable std::string json_;  // report_'s JSON: a rebuild that writes the same announces nothing
    mutable QVariantMap model_;
    // The options report_ was built with, and judged()'s model when its choices are not the default ones.
    mutable edi::ReportOptions options_;
    mutable std::optional<edi::ReportModel> judged_;
    mutable std::optional<std::string> cif_digest_;
    QHash<QString, QImage> figures_;  // setFigure's images, which the next save takes
};

}  // namespace edi_app

#endif  // EDI_APP_REPORT_VIEW_MODEL_HPP
