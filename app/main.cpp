// SPDX-License-Identifier: BSD-3-Clause
#include <QGuiApplication>
#include <QIcon>
#include <QDir>
#include <QFile>
#include <QUrl>
#include <QQmlApplicationEngine>
#include <QScreen>
#include <QSettings>
#include <QQuickWindow>
#include <QStyleHints>
#include <QSurfaceFormat>
#include <QThreadPool>
#include <QtQml/qqmlextensionplugin.h>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <memory>
#if defined(Q_OS_UNIX)
#include <unistd.h>
#endif

#include "app_info.hpp"
#include "demo_driver.hpp"
#include "web_page_hooks.hpp"
#include "engine_setup.hpp"
#include "run_log.hpp"
#include "stall_probe.hpp"
#include "ui_probe.hpp"
#include "test_observer.hpp"
#ifndef __EMSCRIPTEN__
void start_installer_smoke(QQuickWindow&, const QString&);
#ifdef Q_OS_MACOS
double merge_mac_title_bar(QWindow* window);
#endif
#endif

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
// A failure in one event's handler is logged and that event dropped; it never reaches the event loop, which would end
// the app (a model call refusing a project it cannot take, say one without an experiment). The user sees it in the
// error popup (edi ADR-0062).
class GuardedApplication final : public QGuiApplication {
   public:
    using QGuiApplication::QGuiApplication;
    bool notify(QObject* receiver, QEvent* event) override {
        try {
            return QGuiApplication::notify(receiver, event);
        } catch (const std::exception& error) {
            qCritical("edi: an event handler failed and was skipped: %s", error.what());
            edi_app::RunLog::reportCaught(QString::fromUtf8(error.what()));
        } catch (...) {
            qCritical("edi: an event handler failed and was skipped");
            edi_app::RunLog::reportCaught(QStringLiteral("an unknown error"));
        }
        return false;
    }
};
}  // namespace

// Thin QML host (ADR-0009): it hosts the QML tree and wires the product core through the app-layer
// view-models. No product logic here. One host, two build targets — desktop and WASM — from this one
// source tree (ADR-0006).
int main(int argc, char* argv[]) {
    // An exception nothing caught is written to the run log before the abort, so the next start can say what it was.
    std::set_terminate([] {
        if (const auto current = std::current_exception()) {
            try {
                std::rethrow_exception(current);
            } catch (const std::exception& error) {
                qCritical("terminated by an uncaught exception: %s", error.what());
            } catch (...) {
                qCritical("terminated by an uncaught exception");
            }
        }
        std::abort();
    });
    if (const auto code = edi_app::refuse_test_observer(argc, argv)) {
        return *code;  // before the platform checks, so the refusal names the observer request
    }
    edi_app::select_freetype_engine(argc, argv);  // before the QGuiApplication reads the platform
    GuardedApplication app(argc, argv);
#if !defined(__EMSCRIPTEN__) && !defined(Q_OS_MACOS)
    app.setWindowIcon(QIcon(QStringLiteral(":/qt/qml/edi/app/resources/logo/App.svg")));
#endif
    QGuiApplication::setOrganizationName(edi_app::settings_organisation());
    QGuiApplication::setApplicationName(QStringLiteral("EasyDiffraction"));
    edi_app::use_design_font();
    edi_app::require_freetype_engine();
    const QStringList arguments = QGuiApplication::arguments();
#ifndef __EMSCRIPTEN__
    const auto smoke_flag = arguments.indexOf(QStringLiteral("--testmode"));
    if (smoke_flag >= 0) {
        if (smoke_flag + 1 >= arguments.size() || arguments.at(smoke_flag + 1).startsWith("--")) {
            std::fprintf(stderr, "usage: edi_app --testmode <output-directory>\n");
            return 2;
        }
        if (arguments.contains(QStringLiteral("--online-source")) ||
            arguments.filter(QStringLiteral("--online-source=")).size() > 0) return 2;
        edi_app::use_fresh_settings();
        const auto catalogue = edi_app::fresh_settings_dir() + QStringLiteral("/catalogue");
        if (!QDir().mkpath(catalogue)) return 2;
        QFile index(catalogue + QStringLiteral("/index.json"));
        const QByteArray content = R"({"schema":"edi-data-index/1","entries":[]})";
        if (!index.open(QIODevice::WriteOnly) || index.write(content) != content.size()) return 2;
        index.close();
        const auto local = QUrl::fromLocalFile(catalogue + "/").toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + local + ";easydiffraction=" + local).toUtf8());
    }
#endif
    // `--test-observer <action> ...`: a system test's observation of this app (test_observer.hpp).
    const qsizetype observer_flag = arguments.indexOf(QStringLiteral("--test-observer"));
    if (observer_flag >= 0) {
        if (const auto code = edi_app::start_test_observer(arguments.mid(observer_flag + 1))) {
            return *code;
        }
    }
    // `--demo <dir>`: the scripted click-through that saves one image per page state; `--demo-only <prefix>`
    // runs just the steps whose image name starts with the prefix.
    const qsizetype demo_flag = arguments.indexOf(QStringLiteral("--demo"));
    const qsizetype docs_flag = arguments.indexOf(QStringLiteral("--docs-capture"));
    const qsizetype script_flag = arguments.indexOf(QStringLiteral("--docs-script"));
    const bool documentation = docs_flag >= 0;
    const bool demo = demo_flag >= 0 || documentation;
    const qsizetype capture_flag = documentation ? docs_flag : demo_flag;
    if ((demo_flag >= 0 && documentation) || (script_flag >= 0 && !documentation) ||
        (demo && (capture_flag + 1 >= arguments.size() || arguments.at(capture_flag + 1).startsWith("--"))) ||
        (script_flag >= 0 && (script_flag + 1 >= arguments.size() || arguments.at(script_flag + 1).startsWith("--")))) {
        std::fprintf(stderr, "usage: edi_app --demo <output-directory>\n"
                             "       edi_app --docs-capture <output-directory> [--docs-script <walkthrough.js>]\n");
        return 2;
    }
    if (demo) {
        // The images are 1280x768 at a device-pixel ratio of 1 on every platform: a Retina screen (2) is
        // scaled back by QT_SCALE_FACTOR, which Qt reads only at start, so the demo restarts itself once.
        // EDI_DEMO_ANY_RATIO keeps the screen's ratio, for a look at a high-DPI screen's drawing (`--demo-only lines-`).
        const qreal ratio = QGuiApplication::primaryScreen()->devicePixelRatio();
        if (!qFuzzyCompare(ratio, 1.0) && qEnvironmentVariableIsEmpty("EDI_DEMO_ANY_RATIO")) {
#if defined(Q_OS_UNIX)
            if (qEnvironmentVariableIsEmpty("QT_SCALE_FACTOR")) {
                qputenv("QT_SCALE_FACTOR", QByteArray::number(1.0 / ratio));
                execv(argv[0], argv);
            }
#endif
            std::fprintf(stderr, "edi_app --demo: the device-pixel ratio is %g, not 1\n", ratio);
            return 2;
        }
        // The images read the window's framebuffer: 8 bits per channel, as a desktop display has (an EGL
        // display can offer 16-bit RGB565 first).
        QSurfaceFormat format = QSurfaceFormat::defaultFormat();
        format.setRedBufferSize(8);
        format.setGreenBufferSize(8);
        format.setBlueBufferSize(8);
        QSurfaceFormat::setDefaultFormat(format);
        QGuiApplication::styleHints()->setCursorFlashTime(0);  // no blinking caret in the images
        ApplicationInfo::useDemoIdentity();
        edi_app::use_fresh_settings();  // never the machine's saved settings
    }
    // Every message of this run to the terminal and its log file (ADR-0062), at the level Preferences keeps.
    edi_app::migrate_legacy_settings();  // before anything reads the settings or the data folder
    edi_app::RunLog run_log({edi_app::run_log_directory()});
    const QSettings settings(edi_app::settings_store_path(), QSettings::IniFormat);
    run_log.setLevel(settings.value(QStringLiteral("develop/loggingLevel"), QStringLiteral("Info")).toString());
    edi_app::RunLog::install(&run_log);
    if (!run_log.start(edi_app::run_log_header()) && !edi_app::run_log_directory().isEmpty()) {
        qWarning("cannot write the run log in %s; this run logs to the terminal only",
                 qPrintable(edi_app::run_log_directory()));
    }
    // Off unless EDI_STALL_PROBE is set; its summary is written before the log finishes.
    edi_app::install_stall_probe(app);
    // Off unless EDI_UI_TRACE=1 (ADR-0096): the observation trace the GUI watchdog reads.
    edi_app::install_ui_probe(app);
    QObject::connect(&app, &QCoreApplication::aboutToQuit, &run_log, &edi_app::RunLog::finish);
    edi_app::quit_on_termination_signals();
    QQmlApplicationEngine engine;
    edi_app::configure_engine(engine);
    edi_app::configure_test_observer(engine);
    engine.loadFromModule("edi.app", "Main");
    if (engine.rootObjects().isEmpty()) {
        return -1;
    }
    edi_app::install_test_observer(engine);
#if defined(Q_OS_MACOS) || defined(Q_OS_WIN)
    // The app bar is drawn under the system title bar (Qt 6.9 expanded client area); Main.qml sets the same flags.
    auto* merged = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    if (merged && merged->property("mergedTitleBar").toBool()) {
        merged->setFlag(Qt::ExpandedClientAreaHint, true);
        merged->setFlag(Qt::NoTitleBarBackgroundHint, true);
#ifdef Q_OS_WIN
        // Qt draws this strip itself on Windows (qwindowswindow.cpp, updateCustomTitlebar): the icon and title only
        // when the window has a title hint, the three buttons from their own hints. Keep the buttons, drop the title.
        merged->setFlags(Qt::Window | Qt::CustomizeWindowHint | Qt::WindowMinMaxButtonsHint | Qt::WindowCloseButtonHint
                         | Qt::ExpandedClientAreaHint | Qt::NoTitleBarBackgroundHint);
#endif
#ifdef Q_OS_MACOS
        // The app bar's first button lines up with the red traffic light (Main.qml).
        const double red = merge_mac_title_bar(merged);
        if (red >= 0) merged->setProperty("trafficLightsLeft", red);
#endif
    }
#endif
    #ifndef __EMSCRIPTEN__
    if (smoke_flag >= 0) {
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        if (!window) return 2;
        start_installer_smoke(*window, arguments.at(smoke_flag + 1));
    }
#endif
    edi_app::install_web_page_hooks(engine);  // the web build's page hooks for the browser checks
    std::unique_ptr<edi_app::DemoDriver> driver;
    if (demo) {
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        if (window == nullptr) {
            return -1;
        }
        window->resize(documentation ? 1480 : 1280, documentation ? 800 : 768);
        const qsizetype only_flag = arguments.indexOf(QStringLiteral("--demo-only"));
        driver = std::make_unique<edi_app::DemoDriver>(*window, arguments.at(capture_flag + 1),
                                                       only_flag >= 0 ? arguments.value(only_flag + 1) : QString());
        if (documentation) {
            QString error;
            const auto script = script_flag >= 0 ? arguments.at(script_flag + 1)
                                                 : QStringLiteral(":/edi/docs/y2o3-spodi.js");
            if (!driver->loadDocumentationScript(script, &error)) {
                std::fprintf(stderr, "edi_app --docs-capture: %s\n", qPrintable(error));
                return 2;
            }
        }
        driver->start();
    }
    const int code = QGuiApplication::exec();
    // Work on the shared thread pool (a scan's file reads, a report build) must not outlive the objects it reports to:
    // queued work is dropped and running work finishes before the engine and its view models are destroyed.
    QThreadPool::globalInstance()->clear();
    QThreadPool::globalInstance()->waitForDone();
    return code;
}
