// SPDX-License-Identifier: BSD-3-Clause
#include "fit_view_model.hpp"

#include "analysis_view_model.hpp"
#include "edi/edit.hpp"
#include "edi/selectors.hpp"
#include "project_view_model.hpp"

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

// Why the fit stopped, as the status bar names it.
QString status_text(edi::FitStatus status) {
    switch (status) {
        case edi::FitStatus::DONE: return FitViewModel::tr("Done");
        case edi::FitStatus::MAX_ITER: return FitViewModel::tr("Max iterations");
        case edi::FitStatus::NO_STEP: return FitViewModel::tr("No step");
        case edi::FitStatus::CANCELLED: return FitViewModel::tr("Cancelled");
        case edi::FitStatus::SUPERSEDED: return FitViewModel::tr("Superseded");
        case edi::FitStatus::UNAVAILABLE:
        case edi::FitStatus::ERROR: break;
    }
    return FitViewModel::tr("Failed");
}

}  // namespace

// ---- FitResultListModel --------------------------------------------------------------------------

FitResultListModel::FitResultListModel(QObject* parent) : RowTableModel({"icon", "metric", "value"}, parent) {}

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
    const auto row = [&rows, &key](const QString& icon, const QString& metric, const QString& value) {
        rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(++key)), {icon, metric, value}});
    };
    // The descent that produced the result, never the one selected since; a record written before it was kept
    // names the engine only.
    const QString descent = QString::fromStdString(result.descent);
    row(QStringLiteral("flask"), tr("Minimizer"),
        descent.isEmpty() ? QStringLiteral("crysta") : QStringLiteral("crysta (%1)").arg(descent));
    const edi::FitStatus status = status_of(result);
    row(result.success ? QStringLiteral("check-circle") : QStringLiteral("times-circle"), tr("Overall status"),
        result.success ? tr("success") : status_text(status).toLower());
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

void FitResultListModel::clear() { setTableRows({}); }

// ---- FitViewModel ---------------------------------------------------------------------------------

FitViewModel::FitViewModel(edi::Project& project, edi::work::Worker& worker, ProjectViewModel& owner, QObject* parent)
    : QObject(parent), project_(project), owner_(owner), results_(new FitResultListModel(this)) {
    // One frame per display frame at most: a frame waits for the tick, and the next is calculated only
    // once it is shown (edi::FitJob::frame_shown).
    frame_timer_.setSingleShot(true);
    frame_timer_.setInterval(16);
    connect(&frame_timer_, &QTimer::timeout, this, &FitViewModel::showFrame);
    edi::FitJob::Hooks hooks;
    hooks.started = [this](const edi::FitPreamble& preamble) { started(preamble); };
    hooks.iterated = [this](const edi::IterationRecord& record) { iterated(record); };
    hooks.frame = [this](const edi::FitFrame& shown) { frame(shown); };
    hooks.finished = [this](const edi::FitReport& report) { ended(report); };
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
    setProgress(QString::number(result.iterations), chi(result.reduced_chi_square), status_text(status_of(result)));
    results_->setRecord(project_);
}

FitViewModel::~FitViewModel() { close(); }

void FitViewModel::close() {
    frame_timer_.stop();
    pending_frame_.reset();
    job_.reset();
}

void FitViewModel::start() {
    if (!job_ || running_ || !available_) {
        return;
    }
    if (job_->start()) {
        results_->clear();
        setRunning(true);
        setProgress(QString(), QString(), tr("Running"));
    }
}

void FitViewModel::cancel() {
    if (job_ && running_) {
        job_->cancel();
    }
}

void FitViewModel::undo() {
    if (running_ || !can_undo_) {
        return;
    }
    // Through the project's one write door, as an edit: the restore, then the calculation of the pre-fit
    // state on the worker (edi::Edit::undo_fit). The fit items describe a fit the model no longer holds.
    edi::Project& project = project_;
    if (owner_.apply(edi::Edit::undo_fit(project), false).isEmpty()) {
        setProgress(QString(), QString(), QString());
        results_->clear();
    }
}

void FitViewModel::sync() {
    const QString mode = QString::fromStdString(edi::effective_fitting_mode(project_));
    const bool available = mode == QLatin1String("single") || mode == QLatin1String("joint");
    const QString reason =
        available ? QString()
                  : tr("Start fitting runs the single and joint fitting modes; this project's is %1").arg(mode);
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

void FitViewModel::ended(const edi::FitReport& report) {
    // The last delivery: a frame still waiting is older than what follows, and is dropped.
    frame_timer_.stop();
    pending_frame_.reset();
    setRunning(false);
    if (report.adopted()) {
        // The table, the χ², the chart and the texts all come from this one result, in this one step.
        owner_.publishFit();
        const edi::FitResultBase& result = *report.result;
        setProgress(QString::number(result.iterations),
                    QStringLiteral("%1 → %2").arg(chi(result.pre_fit.reduced_chi_square), chi(result.reduced_chi_square)),
                    status_text(report.status));
        results_->setRecord(project_);
        sync();
        emit finished();
        return;
    }
    // Nothing was written: the chart goes back to what the project holds.
    owner_.restorePatterns();
    setProgress(QString(), QString(), status_text(report.status));
    sync();
    if (report.status == edi::FitStatus::ERROR) {
        emit refused(QString::fromStdString(report.refusal));
    }
}

void FitViewModel::setRunning(bool running) {
    if (running != running_) {
        running_ = running;
        emit runningChanged();
        sync();
    }
}

void FitViewModel::setProgress(const QString& iterations, const QString& goodness, const QString& status) {
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
}

}  // namespace edi_app
