// SPDX-License-Identifier: BSD-3-Clause
// Normal nonblocking Qt app loop over production components, with passive observations.
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QtQml/qqmlextensionplugin.h>
#include "engine_setup.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    edi_app::use_design_font();
    edi_app::use_fresh_settings();
    QQmlApplicationEngine engine;
    edi_app::configure_engine(engine);
    engine.load(QUrl(QStringLiteral("qrc:/chart-fonts/tests/fixtures/chart_fonts/WebFonts.qml")));
    if (engine.rootObjects().isEmpty()) return 1;
    return QGuiApplication::exec();
}
