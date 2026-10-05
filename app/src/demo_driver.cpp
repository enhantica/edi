// SPDX-License-Identifier: BSD-3-Clause
#include "demo_driver.hpp"

#include <QCoreApplication>
#include <QFile>
#include <QGuiApplication>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMouseEvent>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QUrl>
#include <cstdio>

#include "session.hpp"

namespace edi_app {
namespace {

// A frame counts as settled when two grabs this far apart are identical (the base's animations run
// up to 1 s); a state that never settles within the bound fails the run.
constexpr int kSettleIntervalMs = 100;
constexpr int kSettleMaxAttempts = 30;
// A fit the demo starts ends within this, or the run fails; `capture-now` captures this long after its actions.
constexpr int kFitWaitMs = 300000;
constexpr int kUnsettledCaptureMs = 1500;

// Open a bundled example from the Project page: scroll its row into view, click it.
QStringList open_example(const QString& id) {
    const qsizetype row = ExampleListModel::bundledIds().indexOf(id);
    return {QStringLiteral("appBar.tab.project"), QStringLiteral("sideBar.tab.basic"),
            QStringLiteral("show:examples.list:%1").arg(row),
            QStringLiteral("examples.open.") + id};
}

}  // namespace

DemoDriver::DemoDriver(QQuickWindow& window, const QString& output_dir, const QString& only, QObject* parent)
    : QObject(parent), window_(window), output_dir_(output_dir) {
    const QString experiment = QStringLiteral("appBar.tab.experiment");
    const QString basic = QStringLiteral("sideBar.tab.basic");
    const QString extras = QStringLiteral("sideBar.tab.extras");
    const QString text = QStringLiteral("sideBar.tab.text");
    // The states of the owner's v0.9.9 originals, in their order, on the Co2SiO4/D20 example the
    // originals show ...
    steps_ = {
        // The platform appearance "System" follows is pinned to light first: the set is captured light on
        // every host, whatever its appearance (a dark Mac rendered every capture dark); the dark and "System"
        // captures below switch through the same seam explicitly.
        {"01-home", {"platform:light"}},
        // Every foldable group but Get started starts folded (edi ADR-0017 §3), so each capture opens what it
        // shows; Get started is open already.
        {"02-project-no-project", {"home.start"}},
        {"03-project-examples", {"group.examples"}},
        {"04-project-loaded", {"examples.open.pd-neut-cwl_cosio-d20_start-1"}},
        {"05-model-models", {"appBar.tab.structure", "group.structures"}},
        {"06-model-space-group", {"group.space_group"}},
        {"07-model-cell", {"group.cell"}},
        {"08-model-atom-site", {"group.atom_site"}},
        {"09-model-text-mode", {text}},
        {"10-experiment-experiments", {experiment, "group.experiments"}},
        {"11-experiment-profile-shape", {"group.peak"}},
        {"12-experiment-background", {"group.background"}},
        {"13-analysis-basic", {"appBar.tab.analysis"}},
        {"14-analysis-extra-minimizer", {extras, "group.minimizer"}},
        {"15-summary", {"appBar.tab.report"}},
        {"16-summary-preferences", {"appBar.button.preferences"}},
    };
    // ... then the capabilities edi has and the original had not (§1.7, §5b, §15.4) ...
    steps_.push_back({"17-experiment-profile-selector", QStringList{"choose:OK"}  // close the Preferences dialog
                                                            + open_example("pd-neut-cwl_lbco-hrpt_start-2")
                                                            + QStringList{experiment, basic, "group.peak", "peak.type"}});
    steps_.push_back({"18-experiment-tch", {"choose:cwl-thompson-cox-hastings"}});
    steps_.push_back({"19-experiment-extras", {extras}});
    steps_.push_back({"20-experiment-tof", open_example("pd-neut-tof_si-sepd_start-2")
                                               + QStringList{experiment, basic, "group.peak"}});
    steps_.push_back({"21-structure-extras", {"appBar.tab.structure", extras, "group.scattering_length"}});
    steps_.push_back({"22-analysis-fitting-mode", {"appBar.tab.analysis", extras, "group.fitting_mode"}});
    steps_.push_back({"23-experiment-text", {experiment, text}});
    steps_.push_back({"24-analysis-text", {"appBar.tab.analysis", text}});
    // The Report page's Text tab shows the project's `_metadata.created`, which a loaded example takes
    // from the clock, so it cannot be a pin: the Report page of the TOF project instead.
    steps_.push_back({"25-report-tof", {"appBar.tab.report"}});
    steps_.push_back({"26-experiment-loaded",
                      open_example("pd-neut-cwl_cosio-d20_start-1")
                          + QStringList{experiment, basic,
                                        "load-experiments:pd-neut-cwl_lbco-hrpt_start-2/project/experiments/hrpt.edi",
                                        // The offscreen software renderer draws the new experiment's
                                        // background rows unclipped until the page is drawn anew;
                                        // leaving and returning redraws it.
                                        "appBar.tab.analysis", experiment}});
    steps_.push_back({"27-experiment-xray", open_example("pd-xray-cwl_lif") + QStringList{experiment, extras,
                                                                                          "group.scattering_source"}});
    // ... then the owner's review notes, each on the page it changed (the note-to-image map is
    // docs/dev/design/app-review-captures.json): the constant-wavelength instrument, the linked structure table,
    // the Extras peak group, the Analysis sidebar with a parameter selected, and the Report's Text at a
    // pinned time; then the dark theme and "system" through the platform seam, the status bar included; then
    // the Project Text tab and the new loop tables; and back to light for the rest.
    const QString analysis = QStringLiteral("appBar.tab.analysis");
    steps_.push_back({"t2-01-instrument-cw", open_example("pd-neut-cwl_cosio-d20_start-1")
                                                 + QStringList{experiment, basic, "group.instrument"}});
    steps_.push_back({"t2-02-linked-structure", {"group.linked_structure"}});
    steps_.push_back({"t2-03-experiment-extras-peak", {extras, "group.peak"}});
    steps_.push_back({"t2-04-analysis-slider", {analysis, basic, "parameters.row.0"}});
    steps_.push_back({"t2-05-report-text",
                      {"pin-time:28 Sep 2026 12:00:00", QStringLiteral("appBar.tab.report"), text,
                       "scroll-to:text.view:_atom_site.multiplicity"}});
    steps_.push_back({"t2-06-dark-experiment", {"theme:dark", experiment, basic}});
    steps_.push_back({"t2-07-dark-analysis", {analysis, basic}});
    steps_.push_back({"t2-08-dark-structure-text", {"appBar.tab.structure", text}});
    steps_.push_back({"t2-09-system-dark-report", {"platform:dark", "theme:system", QStringLiteral("appBar.tab.report")}});
    steps_.push_back({"t2-10-system-light-report", {"platform:light"}});
    // ... the Project Text tab, and every loop table the task made visible (note 6), expanded ...
    steps_.push_back({"t2-11-project-text", {"appBar.tab.project", text}});
    // Measured data is on Extras (edi ADR-0017 §3).
    steps_.push_back({"t2-12-measured-data", {experiment, extras, "group.data"}});
    // Measured data, open, fills the tab: it is folded again (a click on its title) to reach Reflections.
    steps_.push_back({"t2-13-reflections", {extras, "group.data", "group.refln"}});
    steps_.push_back({"t2-14-joint-fit", {analysis, extras, "group.joint_fit"}});
    steps_.push_back({"t2-15-scan-extraction", open_example("pd-neut-cwl_cosio-d20_scan-324f")
                                                   + QStringList{analysis, extras, "group.sequential_fit_extract"}});
    steps_.push_back({"t2-16-fit-start", {"group.fit_parameter"}});
    // The four constant-wavelength fields, which no bundled project declares: the D20 experiment
    // loaded again with both shifts declared, as a user edits it.
    steps_.push_back({"t2-17-instrument-cw-four",
                      open_example("pd-neut-cwl_cosio-d20_start-1") + QStringList{experiment, basic, "load-experiments:pd-neut-cwl_cosio-d20_start-1/project/experiments/d20.edi"
                       "|data_d20=data_d20_shifted"
                       "|_instrument.calib_twotheta_offset 0.()=_instrument.calib_twotheta_offset 0.()\\n"
                       "_instrument.calib_sample_displacement 0.05\\n_instrument.calib_sample_transparency -0.02",
                       "group.instrument"}});
    // ... and every Example's Experiment page with its peak group open, where the types differ most.
    // The first returns to the light theme the rest are captured in.
    for (const QString& id : ExampleListModel::bundledIds()) {
        const QStringList theme = steps_.back().image.startsWith(QLatin1String("t2-")) ? QStringList{"theme:light"}
                                                                                        : QStringList{};
        steps_.push_back({QStringLiteral("ex-") + id, theme + open_example(id) + QStringList{experiment, basic, "group.peak"}});
    }
    // ... then ideas no capture above shows (edi ADR-0017): the Experiment type grid three
    // wide (§2), and Measured data's one increment where the steps are equal (§6; t2-12 shows the range) ...
    steps_.push_back({"t4-01-experiment-type", open_example("pd-neut-cwl_lbco-hrpt_start-2")
                                                   + QStringList{experiment, basic, "group.experiments"}});
    steps_.push_back({"t4-02-measured-data-uniform", {extras, "group.data"}});
    // ... and the messages (ideas 24-26; §14): the example that always has three, counted in the status bar
    // before they are viewed, listed in the dialog, and counted again after it closes; then a refused
    // calculation's error in the list, below a loader warning and over its neutral chart placeholder. No
    // bundled project is refused, so another project's experiment is loaded: its preferred orientation
    // names a structure this project does not have.
    steps_.push_back({"t4-03-messages-not-viewed", open_example("pd-neut-tof_fe_pseudo-voigt")});
    steps_.push_back({"t4-04-messages-list", {"statusBar.warnings"}});
    steps_.push_back({"t4-05-messages-viewed", {"choose:OK"}});
    steps_.push_back({"t4-06-messages-error",
                      open_example("pd-neut-cwl_cosio-d20_scan-3f")
                          + QStringList{experiment, basic,
                                        "load-experiments:pd-neut-cwl_lbco-hrpt_start-2/project/experiments/hrpt.edi",
                                        "statusBar.warnings"}});
    // ... and the About dialog, last: it stays open.
    steps_.push_back({"28-home-about", {"choose:OK",  // close the Messages dialog
                                        "appBar.tab.home", "home.about"}});
    // ... and the fit area, the fitting buttons, the block selector in the main view's tab bar, the Experiments
    // explorer with its Fit column, type selectors and Create experiment, and a searchable combo box. Each
    // opens its example from Home, so `--demo-only t16-` runs them alone.
    const QStringList start = {QStringLiteral("appBar.tab.home"), QStringLiteral("home.start")};
    steps_.push_back({"t16-01-analysis", start + open_example("pd-neut-cwl_cosio-d20_start-1") + QStringList{analysis, basic}});
    steps_.push_back({"t16-02-fit-running", {"fitting.start", "capture-now"}});
    steps_.push_back({"t16-03-fit-done", {"wait-fit"}});
    steps_.push_back({"t16-04-fit-results", {"statusBar.fit.outcome"}});
    steps_.push_back({"t16-05-experiments", {"choose:OK", experiment, basic, "group.experiments"}});
    steps_.push_back({"t16-06-structure", {"appBar.tab.structure", basic}});
    steps_.push_back({"t16-07-narrow", {"resize:900x768", experiment}});
    steps_.push_back({"t16-08-create-experiment", QStringList{"resize:1280x768"} + start + open_example("pd-xray-cwl_lif")
                                                      + QStringList{experiment, basic, "group.experiments", "experiments.create"}});
    steps_.push_back({"t16-09-create-tof", {"experimentType.beamMode", "choose:time-of-flight"}});
    steps_.push_back({"t16-10-create-undone", {"appBar.button.undo"}});
    steps_.push_back({"t16-11-alias-search", {analysis, extras, "group.alias", "aliases.append", "alias.parameter.0"}});
    steps_.push_back({"t16-12-alias-search-filtered", {"type:scale"}});
    if (!only.isEmpty()) {
        std::erase_if(steps_, [&only](const Step& step) { return !step.image.startsWith(only); });
    }
}

void DemoDriver::start() {
    if (!output_dir_.mkpath(QStringLiteral("."))) {
        fail(QStringLiteral("cannot create the output directory %1").arg(output_dir_.path()));
        return;
    }
    park_pointer();
    QTimer::singleShot(0, this, [this] { run_step(); });
}

void DemoDriver::run_step() {
    if (current_ == steps_.size()) {
        QCoreApplication::exit(0);
        return;
    }
    action_ = 0;
    next_action();
}

void DemoDriver::next_action() {
    const Step& step = steps_[current_];
    const bool unsettled = step.actions.contains(QStringLiteral("capture-now"));
    if (action_ < step.actions.size()) {
        const QString& action = step.actions.at(action_);
        ++action_;
        if (action == QLatin1String("capture-now")) {
            next_action();
            return;
        }
        if (action == QLatin1String("wait-fit")) {
            wait_fit_then([this] { settle_then([this] { next_action(); }); });
            return;
        }
        if (!perform(action)) {
            return;  // fail() has ended the run
        }
        park_pointer();
        // What the action opened is drawn before the next; a step captured unsettled does not wait for it.
        if (unsettled) {
            QTimer::singleShot(kSettleIntervalMs, this, [this] { next_action(); });
        } else {
            settle_then([this] { next_action(); });
        }
        return;
    }
    const auto save = [this] {
        const QString path = output_dir_.filePath(steps_[current_].image + QStringLiteral(".png"));
        if (!previous_frame_.save(path)) {
            fail(QStringLiteral("cannot write %1").arg(path));
            return;
        }
        ++current_;
        run_step();
    };
    if (unsettled) {
        QTimer::singleShot(kUnsettledCaptureMs, this, [this, save] {
            previous_frame_ = window_.grabWindow();
            save();
        });
        return;
    }
    settle_then(save);
}

void DemoDriver::wait_fit_then(std::function<void()> next, int waited_ms) {
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    const bool running = session != nullptr && session->project() != nullptr && session->project()->fit()->running();
    if (!running) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the fit did not end within %2 ms").arg(steps_[current_].image).arg(kFitWaitMs));
        return;
    }
    QTimer::singleShot(kSettleIntervalMs * 5, this,
                       [this, next, waited_ms] { wait_fit_then(next, waited_ms + kSettleIntervalMs * 5); });
}

bool DemoDriver::perform(const QString& action) {
    if (action.startsWith(QLatin1String("key:"))) {
        const QKeyCombination key = QKeySequence::fromString(action.mid(4))[0];
        QKeyEvent press(QEvent::KeyPress, key.key(), key.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &press);
        QKeyEvent release(QEvent::KeyRelease, key.key(), key.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &release);
        return true;
    }
    if (action.startsWith(QLatin1String("show:"))) {
        const QStringList parts = action.split(QLatin1Char(':'));
        QQuickItem* view = find(parts.value(1), false);
        if (view == nullptr || parts.value(2).toInt() < 0) {
            fail(QStringLiteral("step %1: cannot show row %2 of '%3'").arg(steps_[current_].image, parts.value(2),
                                                                          parts.value(1)));
            return false;
        }
        QMetaObject::invokeMethod(view, "positionViewAtIndex", Q_ARG(int, parts.value(2).toInt()),
                                  Q_ARG(int, 1 /* ListView.Contain */));
        return true;
    }
    if (action.startsWith(QLatin1String("choose:"))) {
        // The open popup's entry: a visible, enabled button-like item showing the text.
        const QString wanted = action.mid(7);
        QList<QQuickItem*> candidates;
        std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
            for (QQuickItem* child : parent->childItems()) {
                if (child->isVisible() && child->isEnabled() && child->property("text").toString() == wanted &&
                    child->metaObject()->indexOfSignal("clicked()") >= 0) {
                    candidates.append(child);
                }
                walk(child);
            }
        };
        walk(window_.contentItem()->parentItem() != nullptr ? window_.contentItem()->parentItem()
                                                            : window_.contentItem());
        if (candidates.isEmpty()) {
            fail(QStringLiteral("step %1: no open entry shows '%2'").arg(steps_[current_].image, wanted));
            return false;
        }
        return click_item(candidates.last());
    }
    if (action.startsWith(QLatin1String("theme:")) || action.startsWith(QLatin1String("platform:"))) {
        // The base's theme values (Colors.Themes) and Qt's colour schemes (Qt::ColorScheme).
        const QString value = action.section(QLatin1Char(':'), 1);
        const bool theme = action.startsWith(QLatin1String("theme:"));
        const int code = value == QLatin1String("light")  ? (theme ? 0 : static_cast<int>(Qt::ColorScheme::Light))
                         : value == QLatin1String("dark") ? (theme ? 1 : static_cast<int>(Qt::ColorScheme::Dark))
                         : value == QLatin1String("system") && theme ? 2
                                                                     : -1;
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* target = engine == nullptr ? nullptr
                          : theme ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Colors")
                                  : engine->singletonInstance<QObject*>("edi.app", "AppState");
        if (code < 0 || target == nullptr ||
            !target->setProperty(theme ? "theme" : "platformColorScheme", code)) {
            fail(QStringLiteral("step %1: cannot apply '%2'").arg(steps_[current_].image, action));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("scroll-to:"))) {
        const QString name = action.section(QLatin1Char(':'), 1, 1);
        const QString wanted = action.section(QLatin1Char(':'), 2);
        QQuickItem* view = find(name, false);
        const qsizetype at = view != nullptr ? view->property("text").toString().indexOf(wanted) : -1;
        QQuickItem* flickable = view != nullptr ? view->parentItem() : nullptr;
        while (flickable != nullptr && flickable->metaObject()->indexOfProperty("contentY") < 0) {
            flickable = flickable->parentItem();
        }
        QRectF line;
        if (at < 0 || flickable == nullptr ||
            !QMetaObject::invokeMethod(view, "positionToRectangle", Q_RETURN_ARG(QRectF, line),
                                       Q_ARG(int, static_cast<int>(at)))) {
            fail(QStringLiteral("step %1: cannot scroll '%2' to '%3'").arg(steps_[current_].image, name, wanted));
            return false;
        }
        auto* content = qvariant_cast<QQuickItem*>(flickable->property("contentItem"));
        flickable->setProperty("contentY", content != nullptr ? view->mapToItem(content, line.topLeft()).y() : line.y());
        return true;
    }
    if (action.startsWith(QLatin1String("type:"))) {
        for (const QChar character : action.mid(5)) {
            QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &press);
            QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &release);
        }
        return true;
    }
    if (action.startsWith(QLatin1String("resize:"))) {
        const QStringList size = action.mid(7).split(QLatin1Char('x'));
        window_.resize(size.value(0).toInt(), size.value(1).toInt());
        return true;
    }
    if (action.startsWith(QLatin1String("pin-time:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        if (session == nullptr || session->project() == nullptr) {
            fail(QStringLiteral("step %1: no project to pin the time of").arg(steps_[current_].image));
            return false;
        }
        session->project()->pinTimestamps(action.mid(9));
        return true;
    }
    if (action.startsWith(QLatin1String("load-experiments:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        QList<QUrl> files;
        if (!loaded_files_.isValid()) {  // its filePath() would be empty, naming the working directory
            fail(QStringLiteral("step %1: cannot create a directory for the loaded files: %2")
                     .arg(steps_[current_].image, loaded_files_.errorString()));
            return false;
        }
        // `<files>|<find>=<replace>|...`: each copy's text edited as a user would edit the file ("\n" in a
        // replacement is a line break), so a declared state no bundled file carries can be shown.
        const QStringList parts = action.mid(17).split(QLatin1Char('|'));
        for (const QString& resource : parts.first().split(QLatin1Char(','))) {
            const QString target = loaded_files_.filePath(resource.section(QLatin1Char('/'), -1));
            QFile source(QStringLiteral(":/edi/examples/") + resource);
            if (!source.open(QIODevice::ReadOnly)) {
                fail(QStringLiteral("step %1: no bundled file %2").arg(steps_[current_].image, resource));
                return false;
            }
            QString content = QString::fromUtf8(source.readAll());
            for (const QString& edit : parts.mid(1)) {
                const QString find = edit.section(QLatin1Char('='), 0, 0);
                if (!content.contains(find)) {
                    fail(QStringLiteral("step %1: %2 has no '%3' to edit").arg(steps_[current_].image, resource, find));
                    return false;
                }
                content.replace(find, edit.section(QLatin1Char('='), 1).replace(QLatin1String("\\n"), QLatin1String("\n")));
            }
            QFile copy(target);
            if (!copy.open(QIODevice::WriteOnly | QIODevice::Truncate) || copy.write(content.toUtf8()) < 0) {
                fail(QStringLiteral("step %1: cannot write %2").arg(steps_[current_].image, target));
                return false;
            }
            files.append(QUrl::fromLocalFile(target));
        }
        if (session == nullptr || session->project() == nullptr || !session->project()->loadExperiments(files)) {
            fail(QStringLiteral("step %1: the load was refused: %2")
                     .arg(steps_[current_].image, session ? session->lastError() : QStringLiteral("no session")));
            return false;
        }
        return true;
    }
    return click(action);
}

QQuickItem* DemoDriver::find(const QString& object_name, bool must_be_usable) {
    // Every page stays loaded, side by side in the content area's SwipeView, so a name can match on a
    // page not shown, and such an item still counts as visible: the visible, enabled one on screen
    // counts, before any other. Declared items are the window's QObject children; view delegates only
    // visual ones.
    QList<QQuickItem*> matches = window_.findChildren<QQuickItem*>(object_name);
    std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
        for (QQuickItem* child : parent->childItems()) {
            if (child->objectName() == object_name && !matches.contains(child)) {
                matches.append(child);
            }
            walk(child);
        }
    };
    walk(window_.contentItem());
    QQuickItem* off_screen = nullptr;
    for (QQuickItem* match : matches) {
        if (match->isVisible() && (!must_be_usable || match->isEnabled())) {
            if (on_screen(match)) {
                return match;
            }
            off_screen = off_screen != nullptr ? off_screen : match;
        }
    }
    if (off_screen != nullptr) {
        return off_screen;
    }
    return matches.isEmpty() ? nullptr : matches.first();  // the caller names why it is unusable
}

bool DemoDriver::on_screen(QQuickItem* item) const {
    // What is left of the item inside the window and inside every clipping ancestor: a sidebar tab not
    // shown lies within the window, beside the shown one, but its view clips it away (the Extras
    // `group.peak` beside the Basic one).
    QRectF shown = item->mapRectToScene(item->boundingRect())
                       .intersected(QRectF(QPointF(0, 0), QSizeF(window_.width(), window_.height())));
    for (QQuickItem* ancestor = item->parentItem(); ancestor != nullptr && !shown.isEmpty();
         ancestor = ancestor->parentItem()) {
        if (ancestor->clip()) {
            shown = shown.intersected(ancestor->mapRectToScene(ancestor->boundingRect()));
        }
    }
    return !shown.isEmpty();
}

bool DemoDriver::click(const QString& object_name) {
    QQuickItem* item = find(object_name, true);
    // A click at an item off screen reaches nothing, so the run stops rather than capture an unchanged page.
    if (item == nullptr || !item->isVisible() || !item->isEnabled() || !on_screen(item)) {
        fail(QStringLiteral("step %1: control '%2' is %3")
                 .arg(steps_[current_].image, object_name,
                      item == nullptr         ? QStringLiteral("missing")
                      : !item->isVisible()    ? QStringLiteral("hidden")
                      : !item->isEnabled()    ? QStringLiteral("disabled")
                                              : QStringLiteral("off screen")));
        return false;
    }
    return click_item(item);
}

bool DemoDriver::click_item(QQuickItem* item) {
    // A group box is clicked on its title bar (its centre may be its content when expanded).
    const QVariant title_area = item->property("titleArea");
    auto* target = title_area.isValid() ? qvariant_cast<QQuickItem*>(title_area) : nullptr;
    if (target == nullptr) {
        target = item;
    }
    const QPointF centre = target->mapToScene(QPointF(target->width() / 2, target->height() / 2));
    const QPointF global = window_.mapToGlobal(centre);
    QMouseEvent press(QEvent::MouseButtonPress, centre, global, Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &press);
    QMouseEvent release(QEvent::MouseButtonRelease, centre, global, Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &release);
    return true;
}

void DemoDriver::park_pointer() {
    // The pointer rests in the window's corner, where nothing reacts to it, from the start and after every
    // action: a capture then never shows the hover state of whatever lies under the host's own cursor. Without
    // it the images differed by host: a headless Linux display keeps its cursor at the window's centre, which
    // highlighted the Messages row drawn there, and a macOS runner's cursor did not (edi PR 97).
    const QPointF corner(1, 1);
    QMouseEvent move(QEvent::MouseMove, corner, window_.mapToGlobal(corner), Qt::NoButton, Qt::NoButton,
                     Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &move);
}

void DemoDriver::settle_then(std::function<void()> next) {
    settle_attempts_ = 0;
    previous_frame_ = QImage();
    auto poll = std::make_shared<std::function<void()>>();
    *poll = [this, next, poll] {
        // A calculation in flight will change the page when it is published (edi ADR-0020): the frame is
        // settled only once the project has no calculation in flight or owed.
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        const bool calculating =
            session != nullptr && session->project() != nullptr && session->project()->calculating();
        const QImage frame = window_.grabWindow();
        if (!calculating && !previous_frame_.isNull() && frame == previous_frame_) {
            next();
            return;
        }
        previous_frame_ = frame;
        if (++settle_attempts_ > kSettleMaxAttempts) {
            fail(QStringLiteral("step %1 did not settle within %2 ms")
                     .arg(steps_[current_].image)
                     .arg(kSettleIntervalMs * kSettleMaxAttempts));
            return;
        }
        QTimer::singleShot(kSettleIntervalMs, this, *poll);
    };
    QTimer::singleShot(kSettleIntervalMs, this, *poll);
}

void DemoDriver::fail(const QString& message) {
    std::fprintf(stderr, "edi_app --demo: %s\n", qPrintable(message));
    QCoreApplication::exit(1);
}

}  // namespace edi_app
