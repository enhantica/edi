// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_FIT_VIEW_MODEL_HPP
#define EDI_APP_FIT_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QTimer>
#include <QtQml/qqmlregistration.h>
#include <memory>
#include <optional>

#include "edi/fit_job.hpp"
#include "edi/model.hpp"
#include "edi/worker.hpp"
#include "row_table_model.hpp"

namespace edi_app {

class ProjectViewModel;

// The last fit's results, as diffraction-lib's "Least-squares fit results" table: roles
// `icon` (a font icon), `metric` and `value`, from the fit's final result.
class FitResultListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the fit")

   public:
    explicit FitResultListModel(QObject* parent);
    // The rows of the result the project records (`_fit_result`): after a fit and after a project that holds
    // one is opened alike.
    void setRecord(const edi::Project& project);
    void clear();
};

// Start fitting (edi ADR-0020 §9): the fit of the open project runs on its worker (edi::FitJob); its
// progress, its end and its result reach the GUI here, on the GUI thread, in order.
class FitViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // A fit is running: Start fitting is Cancel fitting.
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)
    // The project's fitting mode is one Start fitting runs (single, joint); otherwise `unavailableReason`.
    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    Q_PROPERTY(QString unavailableReason READ unavailableReason NOTIFY unavailableReasonChanged)
    // The model holds a fit's start state (`_fit_parameter`): the app bar's Undo restores it.
    Q_PROPERTY(bool canUndo READ canUndo NOTIFY canUndoChanged)
    // The status bar's fit items: empty before the first fit and after an undo.
    Q_PROPERTY(QString iterations READ iterations NOTIFY iterationsChanged)
    Q_PROPERTY(QString goodnessOfFit READ goodnessOfFit NOTIFY goodnessOfFitChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)
    Q_PROPERTY(edi_app::FitResultListModel* results READ results CONSTANT)

   public:
    FitViewModel(edi::Project& project, edi::work::Worker& worker, ProjectViewModel& owner, QObject* parent);
    ~FitViewModel() override;

    bool running() const { return running_; }
    bool available() const { return available_; }
    QString unavailableReason() const { return unavailable_reason_; }
    bool canUndo() const { return can_undo_; }
    QString iterations() const { return iterations_; }
    QString goodnessOfFit() const { return goodness_of_fit_; }
    QString status() const { return status_; }
    FitResultListModel* results() const { return results_; }

    Q_INVOKABLE void start();
    Q_INVOKABLE void cancel();
    // Whether the fit's start state was restored (refused while a fit runs or when there is none).
    Q_INVOKABLE bool undo();
    // After every publication of the project: what the mode and the start state allow now.
    void sync();
    // The project closes: the fit stops and delivers nothing more. Before the worker goes.
    void close();

   signals:
    void runningChanged();
    void availableChanged();
    void unavailableReasonChanged();
    void canUndoChanged();
    void iterationsChanged();
    void goodnessOfFitChanged();
    void statusChanged();
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
    void setRunning(bool running);
    void setProgress(const QString& iterations, const QString& goodness, const QString& status);
    // The status bar's fit items and the results table from the result the project records (a project
    // opened with one).
    void showRecord();

    edi::Project& project_;
    ProjectViewModel& owner_;
    std::unique_ptr<edi::FitJob> job_;
    FitResultListModel* results_;
    // Frames wait here for the next frame tick, at most one at a time (the job calculates the next only
    // once this one is shown).
    std::optional<edi::FitFrame> pending_frame_;
    QTimer frame_timer_;
    bool running_ = false, available_ = false, can_undo_ = false;
    double chi_before_ = 0.0;
    QString unavailable_reason_, iterations_, goodness_of_fit_, status_;
};

}  // namespace edi_app

#endif  // EDI_APP_FIT_VIEW_MODEL_HPP
