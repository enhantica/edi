// SPDX-License-Identifier: BSD-3-Clause
// The edi app's Qt Quick Test runner: runs the tst_*.qml cases of the hidden tier (tests/unit/app,
// or the directory `-input` names) over the host's own module and engine setup.
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlEngine>
#include <QQmlError>
#include <QtQml/qqmlextensionplugin.h>
#include <QtQuickTest/quicktest.h>

#include <array>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <vector>

#ifdef Q_OS_LINUX
#include <execinfo.h>
#endif

#include "edi/version.hpp"
#include "engine_setup.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class Setup : public QObject {
    Q_OBJECT

    QFile binding_stack_;
    std::vector<QMetaObject::Connection> binding_stack_connections_;
    std::atomic_bool binding_stack_taken_{false};
    bool binding_stack_write_failed_ = false;

    void writeBindingStack(const QJsonObject& record) {
        if (binding_stack_write_failed_) return;
        const auto bytes = QJsonDocument(record).toJson(QJsonDocument::Compact) + '\n';
        if (binding_stack_.write(bytes) != bytes.size() || !binding_stack_.flush()) {
            binding_stack_write_failed_ = true;
            std::fputs("binding-stack: diagnostic file write failed\n", stderr);
        }
    }
    void observeBindingLoop(const QList<QQmlError>& errors) {
        for (const auto& error : errors) {
            if (!error.description().contains(QStringLiteral("Binding loop detected for property \"resolvedColumnWidths\":"))) continue;
            if (binding_stack_taken_.exchange(true)) return;
            QJsonArray frames;
            bool supported = false, symbols_available = false, truncated = false, frame_limit_reached = false;
#ifdef Q_OS_LINUX
            supported = true;
            std::array<void*, 64> addresses{};
            const int count = ::backtrace(addresses.data(), static_cast<int>(addresses.size()));
            frame_limit_reached = count == static_cast<int>(addresses.size());
            char** symbols = count > 0 ? ::backtrace_symbols(addresses.data(), count) : nullptr;
            symbols_available = symbols != nullptr;
            for (int i = 0; i < count; ++i) {
                QString symbol;
                if (symbols && symbols[i]) {
                    constexpr std::size_t limit = 2048;
                    std::size_t length = 0;
                    while (length <= limit && symbols[i][length] != '\0') ++length;
                    if (length > limit) { truncated = true; length = limit; }
                    symbol = QString::fromLocal8Bit(symbols[i], static_cast<qsizetype>(length));
                }
                frames.append(QJsonObject{{"pc", QString::number(reinterpret_cast<quintptr>(addresses[static_cast<std::size_t>(i)]), 16)},
                                          {"module_symbol_offset", symbol}});
            }
            std::free(symbols);
#endif
            writeBindingStack({{"event", "binding_loop_stack"}, {"property", "resolvedColumnWidths"},
                               {"supported", supported}, {"symbols_available", symbols_available},
                               {"symbol_text_truncated", truncated}, {"frame_limit_reached", frame_limit_reached}, {"frames", frames}});
            return;
        }
    }
    void installBindingStackCapture(QQmlEngine* engine) {
        const auto path = qEnvironmentVariable("EDI_TEST_BINDING_STACK_FILE");
        if (path.isEmpty()) return;
        if (!binding_stack_.isOpen()) {
            binding_stack_.setFileName(path);
            if (!QFileInfo(path).isAbsolute() || !binding_stack_.open(QIODevice::WriteOnly | QIODevice::NewOnly)
                || !binding_stack_.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner)) {
                std::fputs("binding-stack: cannot create new absolute diagnostic file\n", stderr);
                std::exit(EXIT_FAILURE);
            }
            writeBindingStack({{"event", "capture_started"}, {"format", 1}});
        }
        binding_stack_connections_.push_back(QObject::connect(engine, &QQmlEngine::warnings, this,
            [this](const QList<QQmlError>& errors) { observeBindingLoop(errors); }, Qt::DirectConnection));
    }

   public:
    ~Setup() override {
        for (const auto& connection : binding_stack_connections_) QObject::disconnect(connection);
        if (binding_stack_.isOpen()) {
            writeBindingStack({{"event", "capture_finished"}, {"matched", binding_stack_taken_.load()},
                               {"write_failed", binding_stack_write_failed_}});
        }
    }

   public slots:
    // Before any engine exists: the application font the host uses (engine_setup.hpp).
    void applicationAvailable() {
        edi_app::use_design_font();
        edi_app::use_fresh_settings();  // never the machine's saved settings
    }
    void qmlEngineAvailable(QQmlEngine* engine) {
        installBindingStackCapture(engine);
        edi_app::configure_engine(*engine);
    }
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
