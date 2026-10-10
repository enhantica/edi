// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_FIT_VIEW_MODEL_HPP
#define EDI_APP_FIT_VIEW_MODEL_HPP

#include <QElapsedTimer>
#include <QObject>
#include <QString>
#include <QTimer>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <optional>

#include "edi/fit_job.hpp"
#include "edi/model.hpp"
#include "edi/scan.hpp"
#include "edi/worker.hpp"
#include "row_table_model.hpp"

namespace edi_app {

class ProjectViewModel;

// How a recorded fit ended, as the outcome key the app draws (FitOutcomes.qml): "success", "maxIterations",
// "noStep", "stopped", "superseded" or "failed"; empty when the project holds no result.
QString recorded_outcome(const edi::FitResultRecord& result);

// The last fit's results, as diffraction-lib's "Least-squares fit results" table: roles
// `icon` (a font icon), `metric`, `value` and `outcome` (the outcome key on the Overall status row, else
// empty), from the fit's final result.
// What a scan's results say about the run as a whole: the files, those fitted, converged and not, the χ² range,
// the run's outcome (its own Failed or Stopped, else the worst file's) and its time (negative: not known).
struct ScanSummary {
    int files = 0;
    int fitted = 0;
    int ok = 0;
    int failed = 0;
    int skipped = 0;             // files with no intensity above zero, not fitted
    long long negative_points = 0;  // rows skipped for a negative intensity, over every file
    // Every completed file: a fitted one has a results row, a skipped one none (crysta writes no row for it).
    int processed() const { return fitted + skipped; }
    double chi_min = 0.0;
    double chi_max = 0.0;
    double seconds = -1.0;
    QString outcome;
};

class FitResultListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the fit")

   public:
    explicit FitResultListModel(QObject* parent);
    // The rows of the result the project records (`_fit_result`): after a fit and after a project that holds
    // one is opened alike.
    void setRecord(const edi::Project& project);
    // A scan's summary instead (edi ADR-0017 §19): its outcome, the files fitted, the ok and fail counts and the χ²
    // range, from `analysis/results.csv`.
    void setScan(const ScanSummary& summary);
    void clear();
};

// Start fitting (edi ADR-0020 §9): the fit of the open project runs on its worker (edi::FitJob); its
// progress, its end and its result reach the GUI here, on the GUI thread, in order.
class FitViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // A fit is running: Start fitting is Stop fitting.
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)
    // A scan project with some datasets fitted and some not: Start fitting reads Continue fitting, and fits from
    // the first unfitted one. `canReset`: Reset fits can clear the scan's fit results (one Undo step).
    Q_PROPERTY(bool continuable READ continuable NOTIFY continuableChanged)
    Q_PROPERTY(bool canReset READ canReset NOTIFY canResetChanged)
    // A scan is running: Follow is enabled. `following`: the pattern tab shows the file being fitted.
    Q_PROPERTY(bool scanning READ scanning NOTIFY scanningChanged)
    Q_PROPERTY(bool following READ following WRITE setFollowing NOTIFY followingChanged)
    // The project's fitting mode is one Start fitting runs (single, joint); otherwise `unavailableReason`.
    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    Q_PROPERTY(QString unavailableReason READ unavailableReason NOTIFY unavailableReasonChanged)
    // The model holds a fit's start state (`_fit_parameter`): the app bar's Undo restores it.
    Q_PROPERTY(bool canUndo READ canUndo NOTIFY canUndoChanged)
    // The status bar's fit area: empty before the first fit and after an undo. `elapsed` is the running
    // fit's time, then the fit's own; `status` is the outcome's word, "Running" while a fit runs; `outcome`
    // is its key (recorded_outcome), empty while a fit runs.
    Q_PROPERTY(QString iterations READ iterations NOTIFY iterationsChanged)
    Q_PROPERTY(QString elapsed READ elapsed NOTIFY elapsedChanged)
    Q_PROPERTY(QString goodnessOfFit READ goodnessOfFit NOTIFY goodnessOfFitChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)
    Q_PROPERTY(QString outcome READ outcome NOTIFY outcomeChanged)
    Q_PROPERTY(edi_app::FitResultListModel* results READ results CONSTANT)
    // A running scan (S3): the share of its files fitted, the bar's text (count, percent, the file just fitted) and
    // the time left at the pace so far.
    Q_PROPERTY(double scanProgress READ scanProgress NOTIFY scanProgressChanged)
    Q_PROPERTY(int scanFitted READ scanFitted NOTIFY scanFittedChanged)
    Q_PROPERTY(int scanTotal READ scanTotal NOTIFY scanTotalChanged)
    Q_PROPERTY(QString scanText READ scanText NOTIFY scanTextChanged)
    Q_PROPERTY(QString eta READ eta NOTIFY etaChanged)
    // The template changed after the scan results were written: they stay shown, marked out of date, until the
    // next run replaces them (edi ADR-0017 §19).
    Q_PROPERTY(bool outOfDate READ outOfDate NOTIFY outOfDateChanged)
    // A scan's summary (scan projects): `scanFiles` reads "fitted/files", then the ok and fail counts.
    Q_PROPERTY(bool scanSummary READ scanSummary NOTIFY scanSummaryChanged)
    Q_PROPERTY(QString scanFiles READ scanFiles NOTIFY scanFilesChanged)
    Q_PROPERTY(int scanOk READ scanOk NOTIFY scanOkChanged)
    Q_PROPERTY(int scanFailed READ scanFailed NOTIFY scanFailedChanged)

   public:
    FitViewModel(edi::Project& project, edi::work::Worker& worker, ProjectViewModel& owner, QObject* parent);
    ~FitViewModel() override;

    bool running() const { return running_; }
    bool continuable() const { return continuable_; }
    bool canReset() const { return can_reset_; }
    bool scanning() const { return scanning_; }
    double scanProgress() const { return scan_.files > 0 ? static_cast<double>(scan_.fitted) / scan_.files : 0.0; }
    QString scanText() const { return scan_text_; }
    QString eta() const { return eta_; }
    bool outOfDate() const { return out_of_date_; }
    // The files the scan has fitted, of all its files.
    int scanFitted() const { return scan_.fitted; }
    int scanTotal() const { return scan_.files; }
    // Follow is on only while a scan runs: off before one, after one and in the single and joint modes.
    bool following() const { return scanning_ && following_; }
    void setFollowing(bool following);
    bool available() const { return available_; }
    QString unavailableReason() const { return unavailable_reason_; }
    bool canUndo() const { return can_undo_; }
    QString iterations() const { return iterations_; }
    QString elapsed() const { return elapsed_; }
    QString goodnessOfFit() const { return goodness_of_fit_; }
    QString status() const { return status_; }
    QString outcome() const { return outcome_; }
    FitResultListModel* results() const { return results_; }
    // The last run was the scan's (a single fit on a dataset since then shows its own summary).
    bool scanSummary() const { return scan_.fitted > 0 && scan_last_; }
    QString scanFiles() const { return QStringLiteral("%1/%2").arg(scan_.fitted).arg(scan_.files); }
    int scanOk() const { return scan_.ok; }
    int scanFailed() const { return scan_.failed; }
    // A scan project's results: the status bar's summary and the results window show the run as a whole, unless
    // `scan_last` is false (a single fit on a dataset came after the run, and its own record is shown).
    void showScan(const ScanSummary& summary, bool scan_last);
    // The scan results came from another template than the one held now (the owner compares their provenance).
    void setOutOfDate(bool out_of_date);

    Q_INVOKABLE void start();
    Q_INVOKABLE void cancel();
    // Clears every dataset's fit result in a scan project (one Undo step), so the next Start fits them all.
    Q_INVOKABLE void reset();
    // Whether the fit's start state was restored (refused while a fit runs or when there is none).
    Q_INVOKABLE bool undo();
    // After every publication of the project: what the mode and the start state allow now.
    void sync();
    // The project closes: the fit stops and delivers nothing more. Before the worker goes.
    void close();

   signals:
    void runningChanged();
    void continuableChanged();
    void canResetChanged();
    void scanningChanged();
    void followingChanged();
    void availableChanged();
    void unavailableReasonChanged();
    void canUndoChanged();
    void iterationsChanged();
    void elapsedChanged();
    void goodnessOfFitChanged();
    void statusChanged();
    void outcomeChanged();
    void scanSummaryChanged();
    void scanFilesChanged();
    void scanOkChanged();
    void scanFailedChanged();
    void scanProgressChanged();
    void scanFittedChanged();
    void scanTotalChanged();
    void scanTextChanged();
    void etaChanged();
    void outOfDateChanged();
    // A scan ended with its rows on disk (finished or stopped): the pop-up.
    void scanFinished();
    // A fit ended with a result the project now holds (finished, cancelled or stopped early): the pop-up.
    void finished();
    // A fit was refused or failed; the project is unchanged.
    void refused(const QString& message);

   private:
    void started(const edi::FitPreamble& preamble);
    void iterated(const edi::IterationRecord& record);
    void frame(const edi::FitFrame& frame);
    void showFrame();
    void ended(const edi::FitReport& report);
    void scanStarted(const edi::ScanPreamble& preamble);
    void fileCompleted(const edi::ScanFileRecord& record);
    void scanEnded(const edi::FitReport& report);
    void setScanning(bool scanning);
    void setContinuable(bool continuable);
    // Continue fitting and Reset fits from the scan's fitted count and the mode.
    void syncScanState();
    void setScanCounts(const ScanSummary& counts, const QString& file);
    void setRunning(bool running);
    void setProgress(const QString& iterations, const QString& goodness, const QString& status,
                     const QString& outcome = QString());
    void setElapsed(const QString& elapsed);
    // The status bar's fit items and the results table from the result the project records (a project
    // opened with one).
    void showRecord();

    edi::Project& project_;
    ProjectViewModel& owner_;
    std::unique_ptr<edi::FitJob> job_;
    FitResultListModel* results_;
    ScanSummary scan_;
    // Frames wait here for the next frame tick, at most one at a time (the job calculates the next only
    // once this one is shown).
    std::optional<edi::FitFrame> pending_frame_;
    QTimer frame_timer_;
    // The running fit's clock, shown once a second.
    QElapsedTimer clock_;
    QTimer clock_timer_;
    bool running_ = false, available_ = false, can_undo_ = false, following_ = true;
    bool can_reset_ = false;
    bool scanning_ = false, continuable_ = false, out_of_date_ = false, scan_last_ = true;
    // The running scan: the files already fitted when it started (a continued scan), for its pace.
    int scan_resumed_ = 0;
    QString scan_text_, eta_;
    double chi_before_ = 0.0;
    QString unavailable_reason_, iterations_, elapsed_, goodness_of_fit_, status_, outcome_;
};

}  // namespace edi_app

#endif  // EDI_APP_FIT_VIEW_MODEL_HPP
