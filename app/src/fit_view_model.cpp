// SPDX-License-Identifier: BSD-3-Clause
#include "fit_view_model.hpp"

#include <QFileInfo>
#include <algorithm>
#include <cmath>

#include "analysis_view_model.hpp"
#include "edi/edit.hpp"
#include "edi/selectors.hpp"
#include "project_view_model.hpp"
#include "scan_session.hpp"

namespace edi_app {
namespace {

// The goodness-of-fit and the fit-results table show χ² as diffraction-lib's table does.
QString chi(double value) { return QString::number(value, 'f', 2); }

// The status a recorded result names (its exit reason, crysta's status label).
edi::FitStatus status_of(const edi::FitResultRecord& result) {
    if (result.exit_reason == "done") return edi::FitStatus::DONE;
    if (result.exit_reason == "max_iter") return edi::FitStatus::MAX_ITER;
    if (result.exit_reason == "no_step") return edi::FitStatus::NO_STEP;
    if (result.exit_reason == "cancelled") return edi::FitStatus::CANCELLED;
    return result.success ? edi::FitStatus::DONE : edi::FitStatus::ERROR;
}

// How the fit ended: the outcome key (FitOutcomes.qml draws its icon and colour) and its word, the same in the
// status bar and the results window.
QString outcome_key(edi::FitStatus status) {
    switch (status) {
        case edi::FitStatus::DONE: return QStringLiteral("success");
        case edi::FitStatus::MAX_ITER: return QStringLiteral("maxIterations");
        case edi::FitStatus::NO_STEP: return QStringLiteral("noStep");
        case edi::FitStatus::CANCELLED: return QStringLiteral("stopped");
        case edi::FitStatus::SUPERSEDED: return QStringLiteral("superseded");
        case edi::FitStatus::UNAVAILABLE:
        case edi::FitStatus::ERROR: break;
    }
    return QStringLiteral("failed");
}

QString status_text(edi::FitStatus status) {
    switch (status) {
        case edi::FitStatus::DONE: return FitViewModel::tr("Success");
        case edi::FitStatus::MAX_ITER: return FitViewModel::tr("Max iterations");
        case edi::FitStatus::NO_STEP: return FitViewModel::tr("No step");
        case edi::FitStatus::CANCELLED: return FitViewModel::tr("Stopped");
        case edi::FitStatus::SUPERSEDED: return FitViewModel::tr("Superseded");
        case edi::FitStatus::UNAVAILABLE:
        case edi::FitStatus::ERROR: break;
    }
    return FitViewModel::tr("Failed");
}

// A fit's time as the status bar shows it: tenths under a second, whole seconds under a minute, then
// minutes and seconds.
QString duration(double seconds) {
    if (seconds < 1.0) {
        return QStringLiteral("%1s").arg(seconds, 0, 'f', 1);
    }
    const auto whole = static_cast<qint64>(seconds + 0.5);
    if (whole < 60) {
        return QStringLiteral("%1s").arg(whole);
    }
    return QStringLiteral("%1m %2s").arg(whole / 60).arg(whole % 60, 2, 10, QLatin1Char('0'));
}

}  // namespace

QString recorded_outcome(const edi::FitResultRecord& result) {
    return result.held() ? outcome_key(status_of(result)) : QString();
}

// ---- FitResultListModel --------------------------------------------------------------------------

FitResultListModel::FitResultListModel(QObject* parent) : RowTableModel({"icon", "metric", "value", "outcome"}, parent) {}

void FitResultListModel::setRecord(const edi::Project& project) {
    // diffraction-lib's rows (analysis/fit_helpers/reporting.py, _build_fit_results_rows), from the result the
    // project records: crysta computes χ² and Rwp, so its R-factors are those.
    const edi::FitResultRecord& result = project.fit_result;
    if (!result.held()) {
        clear();
        return;
    }
    QList<Row> rows;
    int key = 0;
    const auto row = [&rows, &key](const QString& icon, const QString& metric, const QString& value,
                                   const QString& outcome = QString()) {
        rows.append(
            {reinterpret_cast<const void*>(static_cast<std::uintptr_t>(++key)), {icon, metric, value, outcome}});
    };
    // The descent that produced the result, never the one selected since; a record written before it was kept
    // names the engine only.
    const QString descent = QString::fromStdString(result.descent);
    row(QStringLiteral("flask"), tr("Minimizer"),
        descent.isEmpty() ? QStringLiteral("crysta") : QStringLiteral("crysta (%1)").arg(descent));
    const edi::FitStatus status = status_of(result);
    row(QString(), tr("Overall status"), status_text(status), outcome_key(status));
    row(QStringLiteral("stopwatch"), tr("Fitting time (seconds)"), QString::number(result.fitting_time, 'f', 2));
    row(QStringLiteral("redo"), tr("Iterations"), QString::number(result.iterations));
    row(QStringLiteral("ruler"), tr("Goodness-of-fit (reduced χ²)"), chi(result.reduced_chi_square));
    // crysta's Rwp is a fraction; diffraction-lib's table shows its R-factors in per cent.
    row(QStringLiteral("ruler"), tr("Weighted profile R-factor (Rwp, %)"),
        QString::number(result.prof_wr_factor * 100.0, 'f', 2));
    for (const auto& experiment : project.experiments) {
        if (experiment->fit_prof_wr_factor.has_value()) {
            row(QStringLiteral("ruler"), tr("Rwp, %1 (%)").arg(QString::fromStdString(experiment->name)),
                QString::number(*experiment->fit_prof_wr_factor * 100.0, 'f', 2));
        }
    }
    setTableRows(rows);
}

namespace {

QString chi_range(const ScanSummary& summary) {
    return summary.chi_min == summary.chi_max ? chi(summary.chi_min)
                                              : QStringLiteral("%1–%2").arg(chi(summary.chi_min), chi(summary.chi_max));
}

QString outcome_word(const QString& key) {
    if (key == QLatin1String("success")) return FitViewModel::tr("Success");
    if (key == QLatin1String("maxIterations")) return FitViewModel::tr("Max iterations");
    if (key == QLatin1String("noStep")) return FitViewModel::tr("No step");
    if (key == QLatin1String("notConverged")) return FitViewModel::tr("Not converged");
    if (key == QLatin1String("stopped")) return FitViewModel::tr("Stopped");
    if (key == QLatin1String("skipped")) return FitViewModel::tr("Skipped");
    if (key == QLatin1String("refused")) return FitViewModel::tr("Refused");
    return FitViewModel::tr("Failed");
}

}  // namespace

void FitResultListModel::setScan(const ScanSummary& summary) {
    if (summary.processed() == 0 && summary.outcome.isEmpty()) {
        clear();
        return;
    }
    QList<Row> rows;
    int key = 0;
    const auto row = [&rows, &key](const QString& icon, const QString& metric, const QString& value,
                                   const QString& outcome = QString()) {
        rows.append(
            {reinterpret_cast<const void*>(static_cast<std::uintptr_t>(++key)), {icon, metric, value, outcome}});
    };
    row(QStringLiteral("flask"), tr("Minimizer"), QStringLiteral("crysta"));
    row(QString(), tr("Overall status"), outcome_word(summary.outcome), summary.outcome);
    // The run's time when this app ran it; the driver's results record none.
    if (summary.seconds >= 0.0) {
        row(QStringLiteral("stopwatch"), tr("Fitting time (seconds)"), QString::number(summary.seconds, 'f', 2));
    }
    row(QStringLiteral("copy"), tr("Files fitted"), QStringLiteral("%1/%2").arg(summary.fitted).arg(summary.files));
    row(QStringLiteral("check-circle"), tr("Converged"), QString::number(summary.ok));
    row(QStringLiteral("times-circle"), tr("Failed"), QString::number(summary.failed));
    if (summary.skipped > 0) {
        row(QStringLiteral("minus-circle"), tr("Skipped (no intensity above zero)"), QString::number(summary.skipped));
    }
    if (summary.negative_points > 0) {
        row(QStringLiteral("minus-circle"), tr("Points skipped (negative intensity)"),
            QString::number(summary.negative_points));
    }
    if (summary.fitted > 0) {
        row(QStringLiteral("ruler"), tr("Goodness-of-fit range (reduced χ²)"), chi_range(summary));
    }
    setTableRows(rows);
}

void FitResultListModel::clear() { setTableRows({}); }

// ---- FitViewModel ---------------------------------------------------------------------------------

FitViewModel::FitViewModel(edi::Project& project, edi::work::Worker& worker, ProjectViewModel& owner, QObject* parent)
    : QObject(parent), project_(project), owner_(owner), results_(new FitResultListModel(this)) {
    // One frame per display frame at most: a frame waits for the tick, and the next is calculated only
    // once it is shown (edi::FitJob::frame_shown).
    frame_timer_.setSingleShot(true);
    frame_timer_.setInterval(16);
    connect(&frame_timer_, &QTimer::timeout, this, &FitViewModel::showFrame);
    clock_timer_.setInterval(1000);
    connect(&clock_timer_, &QTimer::timeout, this,
            [this] { setElapsed(duration(static_cast<double>(clock_.elapsed()) / 1000.0)); });
    edi::FitJob::Hooks hooks;
    hooks.started = [this](const edi::FitPreamble& preamble) { started(preamble); };
    hooks.iterated = [this](const edi::IterationRecord& record) { iterated(record); };
    hooks.frame = [this](const edi::FitFrame& shown) { frame(shown); };
    hooks.finished = [this](const edi::FitReport& report) { ended(report); };
    hooks.scan_started = [this](const edi::ScanPreamble& preamble) { scanStarted(preamble); };
    hooks.file_completed = [this](const edi::ScanFileRecord& record) { fileCompleted(record); };
    hooks.file_frame = [this](const std::string& file, const edi::FitFrame& shown) {
        if (following_) {
            owner_.showScanFrame(file, shown);
        }
        if (job_) {
            job_->frame_shown();
        }
    };
    job_ = std::make_unique<edi::FitJob>(project_, worker, std::move(hooks));
    showRecord();
    sync();
}

void FitViewModel::showRecord() {
    const edi::FitResultRecord& result = project_.fit_result;
    if (!result.held()) {
        return;
    }
    // A reopened project knows its last fit's χ², not the one before it.
    setProgress(QString::number(result.iterations), chi(result.reduced_chi_square), status_text(status_of(result)),
                recorded_outcome(result));
    setElapsed(duration(result.fitting_time));
    results_->setRecord(project_);
}

void FitViewModel::showScan(const ScanSummary& summary, bool scan_last) {
    scan_ = summary;
    scan_last_ = scan_last;
    scan_refused_ = false;
    sync();
    emit scanSummaryChanged();
    emit scanFilesChanged();
    emit scanOkChanged();
    emit scanFailedChanged();
    emit scanProgressChanged();
    emit scanFittedChanged();
    emit scanTotalChanged();
    // After a single fit on a dataset the status bar and the results window show that fit's own record (also when
    // an Undo or a reopen brings it back).
    if (!scan_last_) {
        showRecord();
        return;
    }
    if (scan_.fitted == 0) {
        // A run that failed or was stopped before its first file still says so, here and in the results window;
        // so does one that skipped every file it reached (no χ² to show).
        setProgress(QString(), QString(), scan_.outcome.isEmpty() ? QString() : outcome_word(scan_.outcome),
                    scan_.outcome);
        setElapsed(scan_.seconds >= 0.0 ? duration(scan_.seconds) : QString());
        results_->setScan(scan_);
        return;
    }
    setProgress(QString(), chi_range(scan_), outcome_word(scan_.outcome), scan_.outcome);
    setElapsed(scan_.seconds >= 0.0 ? duration(scan_.seconds) : QString());
    results_->setScan(scan_);
}

void FitViewModel::showScanRefused(const QString& error, const QString& run_outcome, double seconds) {
    scan_.outcome = run_outcome.isEmpty() ? QStringLiteral("refused") : run_outcome;
    scan_.seconds = seconds;
    scan_last_ = true;
    scan_refused_ = true;
    sync();
    emit scanSummaryChanged();
    setProgress(QString(), QString(), outcome_word(scan_.outcome), scan_.outcome);
    setElapsed(seconds >= 0.0 ? duration(seconds) : QString());
    results_->setScan(scan_);
    if (!scan_index_refused_) {
        scan_index_refused_ = true;
        emit refused(error);
    }
}

FitViewModel::~FitViewModel() { close(); }

void FitViewModel::close() {
    frame_timer_.stop();
    clock_timer_.stop();
    pending_frame_.reset();
    job_.reset();
}

void FitViewModel::start() {
    if (!job_ || running_ || !available_) {
        return;
    }
    // A chosen dataset still being read: the model still shows the one before, which is not the one to fit. A scan
    // runs from the template, whatever is shown.
    if (const QString pending = owner_.pendingRefusal();
        !pending.isEmpty() && !edi::is_scan_fitting_mode(edi::effective_fitting_mode(project_))) {
        emit refused(pending);
        return;
    }
    // A scan runs from the template. With no dataset fitted it starts afresh (the previous result files, if any, go
    // to Undo); otherwise it continues from the first dataset without a row (edi ADR-0017 §17).
    const bool scan = edi::is_scan_fitting_mode(edi::effective_fitting_mode(project_));
    if (scan) {
        const QString error = owner_.prepareScan(scan_.processed() == 0);
        if (!error.isEmpty()) {
            emit refused(error);
            return;
        }
        setFollowing(true);
        job_->follow(true);
    }
    if (job_->start(scan ? owner_.scanTemplate() : nullptr)) {
        if (scan_last_ != scan) {
            scan_last_ = scan;
            emit scanSummaryChanged();
        }
        if (scan) {
            scan_resumed_ = 0;
            scan_index_refused_ = false;
            scan_refused_ = false;
            setScanning(true);
            setScanCounts(scan_, QString());
        }
        results_->clear();
        clock_.start();
        clock_timer_.start();
        setElapsed(duration(0.0));
        setRunning(true);
        setProgress(QString(), QString(), tr("Running"));
    }
}

void FitViewModel::cancel() {
    if (job_ && running_) {
        job_->cancel();
    }
}

bool FitViewModel::undo() {
    if (running_ || !can_undo_) {
        return false;
    }
    // Through the project's one write door, as an edit: the restore, then the calculation of the pre-fit
    // state on the worker (edi::Edit::undo_fit). The fit items describe a fit the model no longer holds.
    edi::Project& project = project_;
    if (owner_.apply(edi::Edit::undo_fit(project), false).isEmpty()) {
        setProgress(QString(), QString(), QString());
        setElapsed(QString());
        results_->clear();
        return true;
    }
    return false;
}

void FitViewModel::sync() {
    syncScanState();
    // A scan mode runs only in a project whose scan resolves to datasets of one template experiment; a declared
    // scan is never fitted jointly, whatever mode the project was saved with.
    const QString mode = QString::fromStdString(edi::effective_fitting_mode(project_));
    const bool scan = edi::is_scan_fitting_mode(mode.toStdString());
    const bool declared = project_.sequential_fit.declared();
    QString reason;
    if (scan) {
        reason = owner_.scanRefusal();
        if (reason.isEmpty() && !running_ && scan_.files > 0 && scan_.processed() >= scan_.files) {
            reason = tr("Every dataset is fitted or skipped: Reset fits to fit them again");
        }
    } else if (mode == QLatin1String("joint") && declared) {
        reason = tr("This project declares a scan (_sequential_fit): its datasets are fitted in the sequential or "
                    "independent mode, not jointly");
    } else if (mode != QLatin1String("single") && mode != QLatin1String("joint")) {
        reason = tr("Start fitting runs the single, joint, sequential and independent fitting modes; this project's "
                    "is %1")
                     .arg(mode);
    }
    const bool available = reason.isEmpty();
    if (available != available_) {
        available_ = available;
        emit availableChanged();
    }
    if (reason != unavailable_reason_) {
        unavailable_reason_ = reason;
        emit unavailableReasonChanged();
    }
    const AnalysisViewModel* analysis = owner_.analysis();
    const bool can_undo = !running_ && analysis != nullptr && analysis->fitStart()->count() > 0;
    if (can_undo != can_undo_) {
        can_undo_ = can_undo;
        emit canUndoChanged();
    }
}

void FitViewModel::started(const edi::FitPreamble& preamble) {
    chi_before_ = preamble.pre_fit.reduced_chi_square;
    setProgress(QStringLiteral("0"), chi(chi_before_), tr("Running"));
}

void FitViewModel::iterated(const edi::IterationRecord& record) {
    setProgress(QString::number(record.iteration),
                QStringLiteral("%1 → %2").arg(chi(chi_before_), chi(record.reduced_chi_square)), tr("Running"));
}

void FitViewModel::frame(const edi::FitFrame& shown) {
    pending_frame_ = shown;
    if (!frame_timer_.isActive()) {
        frame_timer_.start();
    }
}

void FitViewModel::showFrame() {
    if (!pending_frame_.has_value() || !running_) {
        return;
    }
    owner_.showFitFrame(*pending_frame_);
    pending_frame_.reset();
    if (job_) {
        job_->frame_shown();
    }
}

void FitViewModel::scanStarted(const edi::ScanPreamble& preamble) {
    ScanSummary counts;
    counts.files = preamble.total_files;
    counts.fitted = static_cast<int>(preamble.completed_rows.size());
    for (const edi::ScanFileRecord& row : preamble.completed_rows) {
        ++(row.converged ? counts.ok : counts.failed);
    }
    // Files an earlier run skipped are done too: the notes it kept say which.
    if (const ScanSession* session = owner_.scanSession(); session != nullptr && session->index().error.empty()) {
        counts.skipped = static_cast<int>(session->index().skipped);
    }
    scan_resumed_ = counts.processed();
    setScanCounts(counts, preamble.completed_rows.empty()
                              ? QString()
                              : QString::fromStdString(preamble.completed_rows.back().file_name));
    if (!preamble.completed_rows.empty()) {
        setProgress(QString(), chi(preamble.completed_rows.back().reduced_chi_square), tr("Running"));
    }
}

void FitViewModel::fileCompleted(const edi::ScanFileRecord& record) {
    // The index holds this file's row and the notes of the files skipped before it (a skipped file sends no event
    // of its own), retained rows of an earlier run included: fitted and skipped are its counts.
    const int dataset = owner_.scanFileFitted(record);
    const ScanSession* session = owner_.scanSession();
    if (session != nullptr && (dataset < 0 || !session->index().error.empty())) {
        // The index refused what the run wrote: nothing more is published until a full read succeeds (the settle
        // when the run returns), and the refusal is shown once.
        if (!scan_index_refused_) {
            scan_index_refused_ = true;
            emit refused(session->index().error.empty() ? tr("The row just written could not be indexed")
                                                         : QString::fromStdString(session->index().error));
        }
        return;
    }
    ScanSummary counts = scan_;
    ++(record.converged ? counts.ok : counts.failed);
    if (session != nullptr) {
        counts.fitted = static_cast<int>(session->index().fitted);
        counts.skipped = static_cast<int>(session->index().skipped);
    } else {
        ++counts.fitted;
    }
    setScanCounts(counts, QString::fromStdString(record.file_name));
    setProgress(QString(), chi(record.reduced_chi_square), tr("Running"));
    if (following()) {
        owner_.followScanFile(record.file_name);
    }
}

void FitViewModel::setScanCounts(const ScanSummary& counts, const QString& file) {
    scan_.files = counts.files;
    scan_.fitted = counts.fitted;
    scan_.skipped = counts.skipped;
    scan_.ok = counts.ok;
    scan_.failed = counts.failed;
    sync();
    emit scanSummaryChanged();
    emit scanFilesChanged();
    emit scanOkChanged();
    emit scanFailedChanged();
    emit scanProgressChanged();
    emit scanFittedChanged();
    emit scanTotalChanged();
    const int percent = scan_.files > 0 ? static_cast<int>(100.0 * scan_.processed() / scan_.files) : 0;
    QStringList parts{QStringLiteral("%1/%2").arg(scan_.processed()).arg(scan_.files),
                      QStringLiteral("%1%").arg(percent)};
    if (!file.isEmpty()) {
        parts.append(QFileInfo(file).completeBaseName());
    }
    const QString text = parts.join(QStringLiteral(" · "));
    if (text != scan_text_) {
        scan_text_ = text;
        emit scanTextChanged();
    }
    // The time left at this run's pace: the files it fitted so far over the time they took.
    const int done = scan_.processed() - scan_resumed_;
    QString eta;
    if (scanning_ && done > 0 && scan_.files > scan_.processed()) {
        const double seconds = static_cast<double>(clock_.elapsed()) / 1000.0;
        eta = duration(seconds / done * (scan_.files - scan_.processed()));
    }
    if (eta != eta_) {
        eta_ = eta;
        emit etaChanged();
    }
}

void FitViewModel::setScanning(bool scanning) {
    if (scanning != scanning_) {
        scanning_ = scanning;
        emit scanningChanged();
        emit followingChanged();
    }
}

void FitViewModel::setContinuable(bool continuable) {
    if (continuable != continuable_) {
        continuable_ = continuable;
        emit continuableChanged();
    }
}

void FitViewModel::reset() {
    if (running_ || !can_reset_) {
        return;
    }
    if (const QString error = owner_.resetScan(); !error.isEmpty()) {
        emit refused(error);
    }
}

void FitViewModel::syncScanState() {
    // In a scan project the fit button follows the datasets' fits (owner, 2026-10-06): Start fitting while none is
    // fitted, Continue fitting while some are not, unavailable once all are; Reset fits clears them.
    const bool scan = edi::is_scan_fitting_mode(edi::effective_fitting_mode(project_)) && owner_.scan();
    setContinuable(scan && scan_.processed() > 0 && scan_.processed() < scan_.files);
    const ScanSession* session = owner_.scanSession();
    const bool unreadable = session != nullptr && (!session->index().error.empty() || session->run().invalid);
    const bool can_reset = scan && !running_ && (scan_.processed() > 0 || unreadable);
    if (can_reset != can_reset_) {
        can_reset_ = can_reset;
        emit canResetChanged();
    }
}

void FitViewModel::setOutOfDate(bool out_of_date) {
    if (out_of_date != out_of_date_) {
        out_of_date_ = out_of_date;
        emit outOfDateChanged();
    }
}

void FitViewModel::settleScanCounts() {
    owner_.settleScan();
    const ScanSession* session = owner_.scanSession();
    if (session == nullptr || !session->index().error.empty()) {
        return;
    }
    // Every count from the full read, converged and failed included: events the live index refused are counted
    // here, once the files read whole.
    ScanSummary counts = scan_;
    counts.fitted = static_cast<int>(session->index().fitted);
    counts.skipped = static_cast<int>(session->index().skipped);
    counts.ok = 0;
    counts.failed = 0;
    for (const edi::ScanResultIndex::Row& row : session->index().rows) {
        if (row.offset >= 0) {
            ++(row.converged ? counts.ok : counts.failed);
        }
    }
    setScanCounts(counts, QString());
}

void FitViewModel::scanEnded(const edi::FitReport& report) {
    setScanning(false);
    const double seconds = static_cast<double>(clock_.elapsed()) / 1000.0;
    // The owner reads the rows on disk again and shows the run's summary, its own end and time included.
    owner_.scanEnded(report.status, seconds);
    if (report.status == edi::FitStatus::ERROR) {
        emit refused(QString::fromStdString(report.refusal));
        return;
    }
    emit scanFinished();
}

void FitViewModel::ended(const edi::FitReport& report) {
    // The last delivery: a frame still waiting is older than what follows, and is dropped.
    frame_timer_.stop();
    clock_timer_.stop();
    pending_frame_.reset();
    if (scanning_) {
        // Files skipped after the last row have sent no event: the counts are settled first, so the running bar
        // closes on every file the run processed, whatever it ended as.
        settleScanCounts();
        setRunning(false);
        scanEnded(report);
        return;
    }
    setRunning(false);
    if (report.adopted()) {
        // The table, the χ², the chart and the texts all come from this one result, in this one step.
        owner_.publishFit();
        const edi::FitResultBase& result = *report.result;
        setProgress(QString::number(result.iterations),
                    QStringLiteral("%1 → %2").arg(chi(result.pre_fit.reduced_chi_square), chi(result.reduced_chi_square)),
                    status_text(report.status), outcome_key(report.status));
        setElapsed(duration(project_.fit_result.fitting_time));
        results_->setRecord(project_);
        sync();
        emit finished();
        return;
    }
    // Nothing was written: the chart goes back to what the project holds.
    owner_.restorePatterns();
    setProgress(QString(), QString(), status_text(report.status), outcome_key(report.status));
    setElapsed(duration(static_cast<double>(clock_.elapsed()) / 1000.0));
    sync();
    if (report.status == edi::FitStatus::ERROR) {
        emit refused(QString::fromStdString(report.refusal));
    }
}

void FitViewModel::setRunning(bool running) {
    if (running != running_) {
        running_ = running;
        // canUndo is settled before the change is announced, so a listener reading both sees one state:
        // when a fit ends, the start state it can undo is already back.
        sync();
        emit runningChanged();
    }
}

void FitViewModel::setFollowing(bool following) {
    if (job_) {
        job_->follow(following);
    }
    if (following != following_) {
        following_ = following;
        emit followingChanged();
    }
}

void FitViewModel::setElapsed(const QString& elapsed) {
    if (elapsed != elapsed_) {
        elapsed_ = elapsed;
        emit elapsedChanged();
    }
}

void FitViewModel::setProgress(const QString& iterations, const QString& goodness, const QString& status,
                               const QString& outcome) {
    if (iterations != iterations_) {
        iterations_ = iterations;
        emit iterationsChanged();
    }
    if (goodness != goodness_of_fit_) {
        goodness_of_fit_ = goodness;
        emit goodnessOfFitChanged();
    }
    if (status != status_) {
        status_ = status;
        emit statusChanged();
    }
    if (outcome != outcome_) {
        outcome_ = outcome;
        emit outcomeChanged();
    }
}

}  // namespace edi_app
