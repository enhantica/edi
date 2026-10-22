// SPDX-License-Identifier: BSD-3-Clause
#include "fit_view_model.hpp"

#include <QFileInfo>
#include <QPointer>
#include <QScopeGuard>
#include <exception>
#include <algorithm>
#include <cmath>
#include <optional>

#include "analysis_view_model.hpp"
#include "edi/duration_text.hpp"
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

// A fit's time as the status bar shows it: two significant digits, never fewer than the whole seconds (0.41s, 3.2s,
// 127s; edi::duration_text).
QString duration(double seconds) { return QString::fromStdString(edi::duration_text(seconds)) + QStringLiteral("s"); }

}  // namespace

QString recorded_outcome(const edi::FitResultRecord& result) {
    return result.held() ? outcome_key(status_of(result)) : QString();
}

// ---- FitResultListModel --------------------------------------------------------------------------

FitResultListModel::FitResultListModel(QObject* parent) : RowTableModel({"icon", "metric", "value", "outcome"}, parent) {}

void FitResultListModel::setRecord(const edi::Project& project) {
    // diffraction-lib's rows (analysis/fit_helpers/reporting.py, _build_fit_results_rows), from the result the
    // project records: crysta computes χ² and the R factors, the powder ones in place of diffraction-lib's.
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
    row(QStringLiteral("stopwatch"), tr("Fitting time (seconds)"), QString::fromStdString(edi::duration_text(result.fitting_time)));
    row(QStringLiteral("redo"), tr("Iterations"), QString::number(result.iterations));
    row(QStringLiteral("ruler"), tr("Goodness-of-fit (reduced χ²)"), chi(result.reduced_chi_square));
    // crysta's R factors are fractions; diffraction-lib's table shows its R-factors in per cent. Rwp comes first; a
    // factor a result written before it does not hold has no row.
    const auto percent = [&row](const QString& metric, const std::optional<double>& value) {
        if (value.has_value()) {
            row(QStringLiteral("ruler"), metric, QString::number(*value * 100.0, 'f', 2));
        }
    };
    percent(tr("Weighted profile R-factor (Rwp, %)"), result.prof_wr_factor);
    percent(tr("Profile R-factor (Rp, %)"), result.prof_r_factor);
    percent(tr("Expected R-factor (Rexp, %)"), result.prof_wr_expected);
    percent(tr("Background-corrected Rwp (cRwp, %)"), result.prof_cwr_factor);
    percent(tr("Background-corrected Rp (cRp, %)"), result.prof_cr_factor);
    // Each experiment's own factors when the fit covered several; one experiment's are the ones above.
    const auto fitted =
        std::count_if(project.experiments.begin(), project.experiments.end(),
                      [](const auto& experiment) { return experiment->fit_prof_wr_factor.has_value(); });
    for (const auto& experiment : project.experiments) {
        const QString name = QString::fromStdString(experiment->name);
        if (fitted > 1) {
            percent(tr("Rwp, %1 (%)").arg(name), experiment->fit_prof_wr_factor);
            percent(tr("Rp, %1 (%)").arg(name), experiment->fit_prof_r_factor);
            percent(tr("Rexp, %1 (%)").arg(name), experiment->fit_prof_wr_expected);
            percent(tr("cRwp, %1 (%)").arg(name), experiment->fit_prof_cwr_factor);
            percent(tr("cRp, %1 (%)").arg(name), experiment->fit_prof_cr_factor);
            if (experiment->fit_chi_square.has_value()) {  // its own χ², dimensionless, beside the global reduced one
                row(QStringLiteral("ruler"), tr("χ², %1").arg(name), chi(*experiment->fit_chi_square));
            }
        }
        // Each phase's, named by its structure (and its experiment when there are several).
        for (const auto& link : experiment->linked_structures) {
            const std::string& linked = link->structure_id.value();
            const QString phase = QString::fromStdString(
                linked.empty() && !project.structures.empty() ? project.structures.front()->name.value() : linked);
            const QString label = fitted > 1 ? QStringLiteral("%1 / %2").arg(name, phase) : phase;
            percent(tr("Bragg R-factor (R_Bragg), %1 (%)").arg(label), link->fit_bragg_r_factor);
            percent(tr("Structure-factor R-factor (R_F), %1 (%)").arg(label), link->fit_f_r_factor);
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
        row(QStringLiteral("stopwatch"), tr("Fitting time (seconds)"), QString::fromStdString(edi::duration_text(summary.seconds)));
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

namespace {
// The shortest time between two files a followed scan shows (edi ADR-0029): fast fits show the latest file about
// twice a second, slow ones every file. "About once a second" doubles it.
constexpr int kFollowIntervalMs = 500;
constexpr int kOncePerSecondMs = 1000;
// The pattern-update modes (FitViewModel::patternUpdates).
constexpr int kEveryPattern = 0;
constexpr int kOncePerSecond = 1;
constexpr int kAdaptive = 2;
constexpr int kAtEnd = 3;
}  // namespace

FitViewModel::FitViewModel(edi::Project& project, edi::work::Worker& worker, ProjectViewModel& owner, QObject* parent)
    : QObject(parent), project_(project), owner_(owner), results_(new FitResultListModel(this)) {
    // One frame per display frame at most: a frame waits for the tick, and the next is calculated only
    // once it is shown (edi::FitJob::frame_shown).
    frame_timer_.setSingleShot(true);
    frame_timer_.setInterval(16);
    connect(&frame_timer_, &QTimer::timeout, this, &FitViewModel::showFrame);
    follow_timer_.setSingleShot(true);
    connect(&follow_timer_, &QTimer::timeout, this, &FitViewModel::followLatest);
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
    hooks.file_frame = [this](const std::string& file, const edi::FitFrame& shown) { scanFrame(file, shown); };
    job_ = std::make_unique<edi::FitJob>(project_, worker, std::move(hooks));
    job_->wait_for_patterns(pattern_updates_ == kEveryPattern && owner_.patternShown());
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
    setScanRefused(false);
    sync();
    emit scanSummaryChanged();
    emit scanFilesChanged();
    emit scanOkChanged();
    emit scanFailedChanged();
    emit scanProgressChanged();
    emit scanProcessedChanged();
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
    setScanRefused(true);
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
    invalidateFitUndo();
    latest_attempt_ = submitted_attempt_ = finished_attempt_ = native_attempt_ = 0;
    frame_timer_.stop();
    follow_timer_.stop();
    clock_timer_.stop();
    pending_frame_.reset();
    job_.reset();
}

std::uint64_t FitViewModel::beginAttempt() noexcept {
    undo_attempt_ = 0;
    latest_attempt_ = !owner_.retired_ && attempt_serial_ != UINT64_MAX ? ++attempt_serial_ : 0;
    return latest_attempt_;
}
std::uint64_t FitViewModel::prepareNativeCompletion(std::function<void(const edi::FitReport&, bool)> completion, std::uint64_t attempt) {
    if (!attempt || attempt != latest_attempt_) throw std::runtime_error("The original fit attempt is no longer current");
    if (nativeRunning() || native_completion_ || native_completion_serial_ == UINT64_MAX)
        throw std::runtime_error("A native fit is already owned or its completion identity is exhausted");
    native_attempt_ = attempt;
    native_completion_ = std::move(completion); // Callback ownership precedes either real start entrance.
    return ++native_completion_serial_;
}
void FitViewModel::discardNativePreparation(std::uint64_t token) noexcept {
    if (native_completion_serial_ == token && !nativeRunning()) native_completion_ = {};
}
void FitViewModel::startNative(std::function<void(const edi::FitReport&, bool)> completion, std::uint64_t attempt) {
    if (!attempt) attempt = beginAttempt();
    const auto token = prepareNativeCompletion(std::move(completion), attempt);
    const QPointer<FitViewModel> self(this);
    try { startImpl(attempt); }
    catch (...) { if (self) self->discardNativePreparation(token); throw; }
    if (self) self->discardNativePreparation(token); // A submitted worker keeps its actual completion.
}

void FitViewModel::start() {
    const QPointer<FitViewModel> self(this);
    const auto attempt = native_completion_ ? native_attempt_ : beginAttempt();
    try { startImpl(attempt); }
    catch (...) {
        if (!self) return;
        // Cancellation can throw from Worker tracing after setting its actual
        // flag. Neither that nor a diagnostic observer may escape this QML door.
        try { if (nativeRunning()) cancel(); } catch (...) {}
        if (self) try { emit refused(tr("Fitting could not be started or presented; any admitted worker is being stopped")); } catch (...) {}
        // An admitted worker still owns its original real FitReport callback.
    }
}
void FitViewModel::startImpl(std::uint64_t attempt) {
    const ProjectViewModel::PublicationScope publication(owner_);
    if (const QString critical = owner_.criticalEditRefusal(); !critical.isEmpty()) { emit refused(critical); return; }
    if (!attempt || attempt != latest_attempt_ || !job_ || job_->running() || !available_) {
        return;
    }
    // A chosen dataset still being read: the model still shows the one before, which is not the one to fit. A scan
    // runs from the template, whatever is shown.
    if (const QString pending = owner_.pendingRefusal();
        !pending.isEmpty() && !edi::is_scan_fitting_mode(edi::effective_fitting_mode(project_))) {
        emit refused(pending);
        if (owner_.retired_) return;
        return;
    }
    // A scan runs from the template. With no dataset fitted it starts afresh (the previous result files, if any, go
    // to Undo); otherwise it continues from the first dataset without a row (edi ADR-0017 §17).
    const bool scan = edi::is_scan_fitting_mode(edi::effective_fitting_mode(project_));
    if (scan) {
        const QString error = owner_.prepareScan(scan_.processed() == 0);
        if (!error.isEmpty()) {
            emit refused(error);
            if (owner_.retired_) return;
            return;
        }
        setFollowing(true);
        if (owner_.retired_) return;
        if (owner_.retired_) return;
        job_->follow(true);
        if (owner_.retired_) return;
    }
    submitted_single_joint_ = !scan;
    submitted_attempt_ = attempt; // The real submitted job owns this identity even if a later attempt refuses.
    const bool admitted = job_->start(scan ? owner_.scanTemplate() : nullptr);
    if (!admitted && submitted_attempt_ == attempt) submitted_attempt_ = 0;
    if (owner_.retired_) return;
    if (admitted) {
        if (scan_last_ != scan) {
            scan_last_ = scan;
            emit scanSummaryChanged();
            if (owner_.retired_) return;
        }
        if (scan) {
            scan_resumed_ = 0;
            scan_index_refused_ = false;
            // The job sends the first file's pattern unasked.
            frame_requested_ = true;
            frame_shown_ = true;
            dropHandedFile();
            setScanRefused(false);
            if (owner_.retired_) return;
            setScanning(true);
            if (owner_.retired_) return;
            setScanCounts(scan_, QString());
            if (owner_.retired_) return;
        }
        results_->clear();
        if (owner_.retired_) return;
        clock_.start();
        clock_timer_.start();
        setElapsed(duration(0.0));
        if (owner_.retired_) return;
        setRunning(true);
        if (owner_.retired_) return;
        setProgress(QString(), QString(), tr("Running"));
        if (owner_.retired_) return;
    }
}

void FitViewModel::cancel() {
    if (job_ && job_->running()) {
        job_->cancel();
    }
}

bool FitViewModel::undo() {
    const ProjectViewModel::PublicationScope publication(owner_);
    const auto input = owner_.fit_undo_input_;
    if (owner_.fit_undo_invoking_ && !input) return false;
    if (input && (!owner_.fit_undo_invoking_ || !input->consumed || input->started ||
                  input->attempt != undo_attempt_ || !owner_.fitUndoAvailable())) return false;
    if (running_ || !can_undo_) {
        return false;
    }
    // Through the project's one write door, as an edit: the restore, then the calculation of the pre-fit
    // state on the worker (edi::Edit::undo_fit). The fit items describe a fit the model no longer holds.
    edi::Project& project = project_;
    if (owner_.applyUndo(edi::Edit::undo_fit(project), false).isEmpty()) {
        if (owner_.retired_) return true;
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
    latest_file_.clear();
    followed_file_.clear();
    follow_clock_.invalidate();
    scan_pattern_updates_ = 0;
    emit scanPatternUpdatesChanged();
    emit scanShownFileChanged();
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
    latest_file_ = record.file_name;
    if (following()) {
        // The cheap indicators follow every finished file; only the pattern waits for the view (edi ADR-0029).
        owner_.markScanFile(latest_file_);
    }
    followLatest();
}

void FitViewModel::scanFrame(const std::string& file, const edi::FitFrame& frame) {
    frame_requested_ = false;
    // Only at the end: the first file's pattern, which the job sends unasked, is not drawn either.
    if (!following() || pattern_updates_ == kAtEnd) {
        return;
    }
    frame_shown_ = false;
    follow_clock_.start();
    owner_.followScanFrame(file, frame, handOver(file));
}

std::uint64_t FitViewModel::handOver(const std::string& file) {
    handed_file_ = file;
    handed_token_ = ++last_token_;
    return handed_token_;
}

void FitViewModel::dropHandedFile() {
    // A receipt still on its way for the file handed over last no longer counts.
    if (handed_token_ != 0) {
        handed_token_ = 0;
        handed_file_.clear();
        owner_.releaseFollow();
    }
}

void FitViewModel::patternDrawn(const std::string& file) {
    followed_file_ = file;
    ++scan_pattern_updates_;
    emit scanPatternUpdatesChanged();
    emit scanShownFileChanged();
}

void FitViewModel::followLatest() {
    if (!following() || frame_requested_ || !frame_shown_ || !job_ || !owner_.followReady() ||
        pattern_updates_ == kAtEnd) {
        return;
    }
    const int interval = pattern_updates_ == kEveryPattern    ? 0
                         : pattern_updates_ == kOncePerSecond ? kOncePerSecondMs
                                                              : kFollowIntervalMs;
    if (follow_clock_.isValid() && follow_clock_.elapsed() < interval) {
        if (!follow_timer_.isActive()) {
            follow_timer_.start(static_cast<int>(interval - follow_clock_.elapsed()));
        }
        return;
    }
    // The job sends the pattern of the next file it fits; a file finished before that is not drawn.
    frame_requested_ = true;
    job_->frame_shown();
}

void FitViewModel::patternShownChanged() {
    // Every pattern: the worker waits for a drawing only while a chart can draw one.
    if (job_) {
        job_->wait_for_patterns(pattern_updates_ == kEveryPattern && owner_.patternShown());
    }
    followShown();
}

void FitViewModel::followShown() {
    if (following() && !follow_timer_.isActive()) {
        followLatest();
    }
}

void FitViewModel::followRendered(std::uint64_t token, const std::string& file, bool drawn) {
    if (token == 0 || token != handed_token_) {
        return;  // a receipt for a file handed over before the one awaited, or one already dropped
    }
    handed_token_ = 0;
    handed_file_.clear();
    if (drawn) {
        // The interval runs from the drawing, so no two drawn patterns are closer than it.
        follow_clock_.start();
        patternDrawn(file);
    }
    frame_shown_ = true;
    followShown();
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
    emit scanProcessedChanged();
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

void FitViewModel::setScanRefused(bool refused) {
    if (refused != scan_refused_) {
        scan_refused_ = refused;
        emit scanRefusedChanged();
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

void FitViewModel::scanEnded(const edi::FitReport& report, bool automatic_results) {
    setScanning(false);
    if (owner_.retired_) return;
    const double seconds = static_cast<double>(clock_.elapsed()) / 1000.0;
    // The owner reads the rows on disk again and shows the run's summary, its own end and time included.
    owner_.scanEnded(report.status, seconds);
    if (report.status == edi::FitStatus::ERROR) {
        emit refused(QString::fromStdString(report.refusal));
        if (owner_.retired_) return;
        return;
    }
    emit scanFinished();
    if (owner_.retired_) return;
    if (automatic_results) emit automaticResultsRequested();
}

void FitViewModel::ended(const edi::FitReport& report) {
    const ProjectViewModel::PublicationScope publication(owner_);
    const auto attempt = submitted_attempt_;
    submitted_attempt_ = 0;
    const bool previous_presentation = presenting_;
    presenting_ = true;
    // Latch actual adoption before the first Qt notification. A later failed attempt
    // cannot borrow an older fit start; an edit during presentation retires both facts.
    const bool adopted = attempt && report.adopted() && submitted_single_joint_;
    if (adopted) history_attempt_ = attempt;
    if (attempt == latest_attempt_) undo_attempt_ = adopted ? attempt : 0;
    // Take the callback before any presentation/receiver can throw or replace the
    // model. FitJob owns this report through the entire completion invocation.
    auto completion = std::move(native_completion_);
    // This completed fit owns its origin even if presentation starts another fit.
    const bool automatic_results = !completion;
    std::exception_ptr failure;
    const bool visible = !owner_.retired_;
    try { if (visible) presentEnded(report, automatic_results, attempt); } catch (...) { failure = std::current_exception(); }
    presenting_ = previous_presentation;
    // Even a presentation failure has a real completed optimizer/publication
    // report. Contain the internal callback independently of ordinary Qt signals.
    if (completion) try { completion(report, visible && !owner_.retired_ && !failure); } catch (...) {}
    if (failure) std::rethrow_exception(failure); // Existing FitJob retains its report; no fake UI success.
}

void FitViewModel::presentEnded(const edi::FitReport& report, bool automatic_results, std::uint64_t attempt) {
    // The last delivery: a frame still waiting is older than what follows, and is dropped.
    frame_timer_.stop();
    follow_timer_.stop();
    clock_timer_.stop();
    pending_frame_.reset();
    frame_requested_ = false;
    frame_shown_ = true;
    if (scanning_) {
        // A followed scan always ends on its last file, whatever the interval skipped.
        if (following() && !latest_file_.empty() && latest_file_ != followed_file_ && latest_file_ != handed_file_) {
            owner_.followScanFile(latest_file_, handOver(latest_file_));
            if (owner_.retired_) return;
        }
        // Files skipped after the last row have sent no event: the counts are settled first, so the running bar
        // closes on every file the run processed, whatever it ended as.
        settleScanCounts();
        if (owner_.retired_) return;
        setRunning(false);
        if (owner_.retired_) return;
        scanEnded(report, automatic_results);
        if (owner_.retired_) return;
        return;
    }
    setRunning(false);
    if (owner_.retired_) return;
    if (report.adopted()) {
        // The table, the χ², the chart and the texts all come from this one result, in this one step.
        owner_.publishFit();
        if (owner_.retired_) return;
        const edi::FitResultBase& result = *report.result;
        setProgress(QString::number(result.iterations),
                    QStringLiteral("%1 → %2").arg(chi(result.pre_fit.reduced_chi_square), chi(result.reduced_chi_square)),
                    status_text(report.status), outcome_key(report.status));
        if (owner_.retired_) return;
        setElapsed(duration(project_.fit_result.fitting_time));
        if (owner_.retired_) return;
        results_->setRecord(project_);
        if (owner_.retired_) return;
        sync();
        if (owner_.retired_) return;
        finished_attempt_ = attempt;
        const auto finish_identity = qScopeGuard([this, attempt] { if (finished_attempt_ == attempt) finished_attempt_ = 0; });
        emit finished();
        if (owner_.retired_) return;
        if (automatic_results) emit automaticResultsRequested();
        if (owner_.retired_) return;
        return;
    }
    // Nothing was written: the chart goes back to what the project holds.
    owner_.restorePatterns();
    if (owner_.retired_) return;
    setProgress(QString(), QString(), status_text(report.status), outcome_key(report.status));
    if (owner_.retired_) return;
    setElapsed(duration(static_cast<double>(clock_.elapsed()) / 1000.0));
    if (owner_.retired_) return;
    sync();
    if (owner_.retired_) return;
    if (report.status == edi::FitStatus::ERROR) {
        emit refused(QString::fromStdString(report.refusal));
        if (owner_.retired_) return;
    }
}

void FitViewModel::setRunning(bool running) {
    const ProjectViewModel::PublicationScope publication(owner_);
    if (owner_.retired_) return;
    if (running != running_) {
        running_ = running;
        // canUndo is settled before the change is announced, so a listener reading both sees one state:
        // when a fit ends, the start state it can undo is already back.
        sync();
        if (owner_.retired_) return;
        emit runningChanged();
        if (owner_.retired_) return;
    }
}

void FitViewModel::setFollowing(bool following) {
    const ProjectViewModel::PublicationScope publication(owner_);
    if (owner_.retired_) return;
    if (job_) {
        job_->follow(following);
    }
    if (following != following_) {
        following_ = following;
        emit followingChanged();
        if (owner_.retired_) return;
        // Follow turned on again: the newest finished file is shown now, calculated beside the scan, and the next
        // ones as they come.
        if (this->following() && !latest_file_.empty() && latest_file_ != followed_file_ &&
            pattern_updates_ != kAtEnd) {
            frame_shown_ = false;
            follow_clock_.start();
            owner_.followScanFile(latest_file_, handOver(latest_file_));
            if (owner_.retired_) return;
        }
        // Follow turned off: a file still waiting to be drawn is not counted.
        if (!this->following()) {
            dropHandedFile();
            frame_shown_ = true;
        }
    }
    followLatest();
}

void FitViewModel::setPatternUpdates(int mode) {
    mode = mode >= kEveryPattern && mode <= kAtEnd ? mode : kAdaptive;
    if (job_) {
        job_->wait_for_patterns(mode == kEveryPattern && owner_.patternShown());
    }
    if (mode != pattern_updates_) {
        pattern_updates_ = mode;
        emit patternUpdatesChanged();
        followLatest();
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
    const ProjectViewModel::PublicationScope publication(owner_);
    if (owner_.retired_) return;
    if (iterations != iterations_) {
        iterations_ = iterations;
        emit iterationsChanged();
        if (owner_.retired_) return;
    }
    if (goodness != goodness_of_fit_) {
        goodness_of_fit_ = goodness;
        emit goodnessOfFitChanged();
        if (owner_.retired_) return;
    }
    if (status != status_) {
        status_ = status;
        emit statusChanged();
        if (owner_.retired_) return;
    }
    if (outcome != outcome_) {
        outcome_ = outcome;
        emit outcomeChanged();
        if (owner_.retired_) return;
    }
}

}  // namespace edi_app
