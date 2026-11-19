// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_DEMO_DRIVER_HPP
#define EDI_APP_DEMO_DRIVER_HPP

#include <QDir>
#include <QHash>
#include <QElapsedTimer>
#include <QImage>
#include <QJsonArray>
#include <QJsonObject>
#include <QObject>
#include <QPointer>
#include <QString>
#include <QStringList>
#include <QTemporaryDir>
#include <QTimer>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <optional>
#include <vector>

class QQuickItem;
class QQuickWindow;

namespace edi_app {

class PatternChartController;

// Copies the CLI project docs/user/cli/<id>/project of this build's source tree into <into>/<id>/project, for a
// test project the app does not bundle. Returns the copy's path, or an empty string when it cannot be made.
QString copy_cli_project(const QString& id, const QDir& into);

// The scripted demo mode: clicks through the app with real mouse events on controls found by
// objectName, waits for each state to settle, and saves one image per state into <dir>. The UI test
// compares those images with the committed expected set. A step whose control is missing, hidden or
// disabled stops the run with exit code 1, naming the step.
class DemoDriver : public QObject {
    Q_OBJECT

   public:
    // `only`: run just the steps whose image name starts with it (each opens what it needs), else all.
    DemoDriver(QQuickWindow& window, const QString& output_dir, const QString& only = QString(),
               QObject* parent = nullptr);
    void start();
    /// Load a documentation walkthrough; see ADR-0060. Refuses invalid scripts or fixture inputs.
    bool loadDocumentationScript(const QString& path, QString* error);

   private:
    // One image and the actions that lead to it, in order. An action is an objectName to click, or:
    //   key:<name>               press a key (QKeySequence spelling, e.g. key:Escape)
    //   type:<text>              type the text, a key press per character, into what has the keyboard
    //   show:<view>:<row>        scroll a list view to a row, as a user would before clicking it
    //   choose:<text>            click the open popup's entry showing <text>
    //   load-experiments:<file>  load bundled .edi files through the view-model call the file
    //                            dialog's accept makes (the dialog itself is not driven)
    //   preference:<name>=<value>   one of edi's Preferences, as its dialog sets it (a string value)
    //   theme:<light|dark|system>   the Preferences theme (the base's Colors.theme)
    //   platform:<light|dark>       the platform appearance "system" follows (AppState's seam; a
    //                               headless runner has none)
    //   pin-time:<timestamp>        the open project's created / last-modified time, so its Text is
    //                               reproducible
    //   scroll-to:<view>:<text>     scroll the text view's Flickable so the first line holding <text> is
    //                               its top line, as a user scrolls to it
    //   wait-fit                    wait until the open project's fit has ended (at most kFitWaitMs)
    //   capture-now                 capture this step's image a fixed time after its actions, unsettled: a
    //                               running fit's moving bar never settles
    //   resize:<width>x<height>     the window's logical size
    //   type:<text>                 type the text into the focused field
    //   expand:<group>              unfold a group, whether or not it is folded
    //   save-as:<name>              save the open project into a directory of that name in the run's
    //                               scratch directory (or at an absolute path); open-project:<name> opens one
    //   timed-fit:<files>[:<stop>]  start the open scan and time it on a monotonic clock until its end is
    //                               published and nothing is calculating; then check its work (every one of
    //                               <files> datasets fitted and converged, no refusal) or fail; with <stop>,
    //                               cancel after that many files (a control that must fail)
    //   timed-reset                 time Reset fits the same way, then check the scan holds no results, the
    //                               model its pre-fit values, and Undo is available
    //   remove-scan-data            delete the open scan copy's data directory (a control whose start must fail)
    // Each timed interval is a line of timings.tsv in the output directory. EDI_DEMO_DELAY_MS, when set, adds that
    // delay at the scan's end and inside the reset, so a control can show both intervals contain it.
    // EDI_DEMO_PERF_PROJECT, when set, is the prepared scan copy the timing steps open in place.
    struct Step {
        QString image;
        QStringList actions;
        QString description{};
        QString page{};
        QString sidebar{};
        QStringList highlights{};
        bool capture = true;
        QString fit_phase{};
        QString trace{};     // the measured step's name in the UI trace (ui_probe.hpp); empty for a set-up step
        int navigation = 0;  // +1 or -1 for a next or previous dataset press, whose selection the trace names
    };

    void run_step();
    void next_action();
    bool perform(const QString& action);
    QQuickItem* find(const QString& object_name, bool must_be_usable);
    bool on_screen(QQuickItem* item) const;  // any part of it shown: inside the window and every clip
    bool click_item(QQuickItem* item);
    void park_pointer();
    QImage grab();  // window_.grabWindow(), bracketed in the UI trace as the driver's own work
    bool click(const QString& object_name);
    void settle_then(const std::function<void()>& next);
    // Waits until the fit has ended or, with `files`, until a running scan has fitted that many files.
    void wait_fit_then(const std::function<void()>& next, int waited_ms = 0, int files = -1);
    // Presses only the status bar's Next until the running tutorial's last step; fails on a step Next cannot leave.
    void tutorial_next_then(const std::function<void()>& next, int step = -1, int waited_ms = 0, int clicked_ms = -1);
    // A fit step of a tutorial replay: the free set before the fit and the fit's outcome after it, each checked
    // against the step's expectFree and expectChi2 when the manifest gives them. False after a mismatch (failed).
    bool tutorial_fit_check(QObject* panel, int step);
    int fit_free_reported_ = -1, fit_result_reported_ = -1, sites_reported_ = -1, step_checked_ = -1, shot_step_ = -1;
    bool fit_seen_running_ = false;
    void fail(const QString& message);
    void timed_fit_then(const std::function<void()>& next, int files, int stop_after);
    bool timed_reset();
    // Polls every few milliseconds until nothing is calculating, then calls `next`.
    void idle_then(const std::function<void()>& next, int waited_ms = 0);
    // Waits until a display catching up with a scan has drawn every pattern, then until nothing is calculating.
    void drawn_then(const std::function<void()>& next, int waited_ms = 0);
    QString scan_work(int files) const;
    void record_time(const QString& label, qint64 ms);
    // Waits until a scan view's model has read every dataset, then calls `next`.
    void wait_scan_then(const std::function<void()>& next, const QString& mode, int waited_ms = 0);
    void wait_online_then(const std::function<void()>& next, int waited_ms = 0);
    void wait_assistant_then(const std::function<void()>& next, int waited_ms = 0, int idle_polls = 0);
    // Applies `change` and waits for the first frame swapped after a scene synchronisation that follows it, and
    // follows `ready()` turning true when given; the milliseconds from the change to that swap, or -1 when none came.
    double frame_after(const std::function<void()>& change, const std::function<bool()>& ready = {});
    // `count` changes of one kind to a scan view (zoom, pan, restyle, select, data), each timed by frame_after; the
    // samples go to frames.tsv and their median and 95th percentile to timings.tsv.
    bool timed_frames(const QString& mode, const QString& kind, int count);
    // `count` steps of the Analysis slider, each timed from the move to the frame after its calculation ended.
    bool timed_slider(int count);
    void record_samples(const QString& label, std::vector<double> samples);
    void delay_then_record();
    std::optional<bool> documentationAction(const QString& action);
    bool saveDocumentationFrame(const QString& path, QString* error);
    bool saveDocumentationManifest(const QString& status, const QString& error = {});

    QQuickWindow& window_;
    QDir output_dir_;
    std::vector<Step> steps_;
    std::size_t current_ = 0;
    qsizetype action_ = 0;
    QImage previous_frame_;
    int settle_attempts_ = 0;
    int preparing_attempts_ = 0;
    QTemporaryDir loaded_files_;
    // The UI trace's hooks (ui_probe.hpp): no-ops, with no state, where EDI_UI_INSTRUMENTATION is off.
    void trace_step_begin(const Step& step);    // a measured step starts: the trace's begin, a wait's action, the control
    void trace_issue(const QString& action);    // a measured step's action is about to be issued
    void trace_issued(const Step& step);        // a next or previous press has been issued
    bool trace_complete(int code);              // the trace's end, when it began; true if it ends the run itself
    QString only_;
#if EDI_UI_INSTRUMENTATION
    void trace_measurement(bool enter, int id, const QString& callback);
    int tool_id_ = 0;
    bool blocked_ = false;  // EDI_UI_BLOCK_MS has blocked once
    bool trace_begun_ = false;
    QString trace_scenario_;
    int request_id_ = 0;
    // A measured step's action, open until the native state reaches what it asked for: then its state, the transition's
    // publication and the step itself are written, in that order and in the steps' order.
    struct Pending {
        int request = 0;
        QString name;              // the scenario's step
        QString page;              // a page the action shows
        int before = -1;           // the selection before a next or previous press
        int dataset = -1;          // the selection the press made
        QString direction;         // "next" or "previous"
        QString fit;               // "start", "running", "ended" or "settled"
    };
    std::deque<Pending> pending_;
    // A next or previous press's chart: its first swapped frame after the press, and the first frame swapped once the
    // chart has uploaded the selected dataset's own data (its settled frame).
    struct FrameWatch {
        int request = 0;
        int dataset = -1;
        qint64 base = 0;  // the chart's upload count before the press
        QPointer<QQuickItem> chart;
        QPointer<PatternChartController> controller;
        QString native;   // the selected dataset's data identity, read from the project once that dataset is applied
        bool first = false, presented = false, settled = false;
        QJsonObject presentation;  // request, dataset, generation, data_identity, input
    };
    void trace_watch();
    QJsonObject trace_state();
    QString trace_native_identity();
    void trace_frame();
    QString trace_input();
    QJsonObject trace_geometry(QQuickItem* chart) const;
    std::mutex trace_mutex_;            // the render thread reads what the GUI thread publishes for the next frame
    QJsonArray published_transitions_;  // published since the last frame was synchronised
    QJsonObject synced_displayed_;      // the last synchronised frame's native state, its transitions and number
    QJsonArray synced_transitions_;
    QJsonArray synced_frames_;          // the frame observations of the last synchronised frame
    QJsonArray synced_presented_;       // the presentations the last synchronised frame shows for the first time
    qint64 synced_frame_ = 0;
    QMetaObject::Connection trace_sync_, trace_swap_;
    QList<FrameWatch> frame_watches_;   // GUI thread; the render thread reads them only while the GUI thread waits
    QString input_identity_;
    std::pair<std::uint64_t, QString> native_cache_;  // the native identity, by the project's applied view
    QList<QPointer<QQuickItem>> page_tabs_, view_tabs_;
    int fit_runs_ = 0;
    bool fit_running_ = false;
    bool watching_ = false;
#endif
    QElapsedTimer nav_clock_;  // the 100 ms schedule of next and previous presses
    QHash<QString, QPointer<QQuickItem>> app_bar_tabs_;  // the settle poll's tabs, found once
    qint64 nav_base_ = -1;
    int nav_index_ = 0;
    QElapsedTimer timer_;
    std::vector<double> pre_fit_values_;
    QString loaded_cli_project_;
    bool documentation_ = false;
    bool documentation_skip_ = false;
    // A simulation's tutorial: calculated without measured data, so its Analysis and Report show no fit.
    bool documentation_simulation_ = false;
    QString documentation_script_;
    QString documentation_example_;
    QString documentation_workflow_;
    QJsonObject documentation_fixture_;
    QJsonArray documentation_dependencies_;
    QJsonArray documentation_scenes_;
    QJsonArray documentation_actions_;
    QJsonObject documentation_inputs_;
};

}  // namespace edi_app

#endif  // EDI_APP_DEMO_DRIVER_HPP
