// SPDX-License-Identifier: BSD-3-Clause
// The edi app's Qt Quick Test runner: runs the tst_*.qml cases of the hidden tier (tests/unit/app,
// or the directory `-input` names) over the host's own module and engine setup.
#include <QQmlEngine>
#include <QtQml/qqmlextensionplugin.h>
#include <QtQuickTest/quicktest.h>

#include <cstdio>

#include "edi/version.hpp"
#include "engine_setup.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class Setup : public QObject {
    Q_OBJECT

   public slots:
    // Before any engine exists: the application font the host uses (engine_setup.hpp).
    void applicationAvailable() {
        edi_app::use_design_font();
        edi_app::use_fresh_settings();  // never the machine's saved settings
    }
    void qmlEngineAvailable(QQmlEngine* engine) { edi_app::configure_engine(*engine); }
};

// QUICK_TEST_MAIN_WITH_SETUP, with the platform settled first. The tier checks behaviour, not pixels, so
// unless the caller chooses a platform it runs on offscreen everywhere: a real window on the CI Mac cannot
// become active, and the cases that need keyboard or pointer focus fail there. Only the UI test's capture
// draws with FreeType as users see it (ADR-0015 §10).
int main(int argc, char** argv) {
    // The revision this runner was built from, first in its output, so whatever it measures is attributed to
    // that revision (tools/ci/latency_bank.py reads this line; `-dirty` names no revision).
    std::printf("edi_app_tests: built at %s\n", edi::build_commit());
    std::fflush(stdout);
    if (qEnvironmentVariableIsEmpty("QT_QPA_PLATFORM")) {
        qputenv("QT_QPA_PLATFORM", "offscreen");
    }
    QTEST_SET_MAIN_SOURCE_PATH
    Setup setup;
    return quick_test_main_with_setup(argc, argv, "edi_app", QUICK_TEST_SOURCE_DIR, &setup);
}

#include "app_tests_main.moc"
