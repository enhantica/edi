// SPDX-License-Identifier: BSD-3-Clause
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QScreen>
#include <QQuickWindow>
#include <QStyleHints>
#include <QSurfaceFormat>
#include <QtQml/qqmlextensionplugin.h>
#include <cstdio>
#include <memory>
#if defined(Q_OS_UNIX)
#include <unistd.h>
#endif

#include "app_info.hpp"
#include "demo_driver.hpp"
#include "engine_setup.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

// Thin QML host (ADR-0009): it hosts the QML tree and wires the product core through the app-layer
// view-models. No product logic here. One host, two build targets — desktop and WASM — from this one
// source tree (ADR-0006).
int main(int argc, char* argv[]) {
    edi_app::select_freetype_engine(argc, argv);  // before the QGuiApplication reads the platform
    QGuiApplication app(argc, argv);
    QGuiApplication::setOrganizationName(QStringLiteral("EasyScience"));
    QGuiApplication::setApplicationName(QStringLiteral("EasyDiffraction"));
    edi_app::use_design_font();
    edi_app::require_freetype_engine();
    // `--demo <dir>`: the scripted click-through that saves one image per page state.
    const QStringList arguments = QGuiApplication::arguments();
    const qsizetype demo_flag = arguments.indexOf(QStringLiteral("--demo"));
    const bool demo = demo_flag >= 0;
    if (demo && demo_flag + 1 >= arguments.size()) {
        std::fprintf(stderr, "usage: edi_app --demo <output-directory>\n");
        return 2;
    }
    if (demo) {
        // The images are 1280x768 at a device-pixel ratio of 1 on every platform: a Retina screen (2) is
        // scaled back by QT_SCALE_FACTOR, which Qt reads only at start, so the demo restarts itself once.
        const qreal ratio = QGuiApplication::primaryScreen()->devicePixelRatio();
        if (!qFuzzyCompare(ratio, 1.0)) {
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
    QQmlApplicationEngine engine;
    edi_app::configure_engine(engine);
    engine.loadFromModule("edi.app", "Main");
    if (engine.rootObjects().isEmpty()) {
        return -1;
    }
    std::unique_ptr<edi_app::DemoDriver> driver;
    if (demo) {
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        if (window == nullptr) {
            return -1;
        }
        window->resize(1280, 768);  // the originals' logical window size
        driver = std::make_unique<edi_app::DemoDriver>(*window, arguments.at(demo_flag + 1));
        driver->start();
    }
    return QGuiApplication::exec();
}
