#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTimer>
#include <bit>
#include <cstdint>
#include <thread>

#include "edi/io.hpp"
#include "edi/threading.hpp"
#include "engine_observer.hpp"
#include "session.hpp"
#include "example_list_model.hpp"
#if defined(Q_OS_WASM)
#include <emscripten.h>
EM_JS_DEPS(thread_selector, "$stringToNewUTF8,$UTF8ToString");
#endif
namespace {
QString wanted(const char* name, const char* fallback) {
#if defined(Q_OS_WASM)
    char* p = reinterpret_cast<char*>(EM_ASM_PTR(
        {
            return stringToNewUTF8(new URL(location.href).searchParams.get(UTF8ToString($0)) ||
                                   UTF8ToString($1));
        },
        name, fallback));
    QString result = QString::fromUtf8(p);
    free(p);
    return result;
#else
    return QString::fromUtf8(qgetenv(name).isEmpty() ? QByteArray(fallback) : qgetenv(name));
#endif
}
void publish(const QJsonObject& result) {
    const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
#if defined(Q_OS_WASM)
    EM_ASM(
        { globalThis.__threadSelectorObservation = JSON.parse(UTF8ToString($0)); },
        bytes.constData());
#else
    QFile out(wanted("THREAD_SELECTOR_OUTPUT", "thread-selector.json"));
    if (out.open(QIODevice::WriteOnly)) out.write(bytes);
    QCoreApplication::quit();
#endif
}
QString bits(double value) { return QString::number(std::bit_cast<std::uint64_t>(value), 16); }
QJsonArray pattern(const edi::Project& p) {
    QJsonArray result;
    for (const auto& experiment : p.experiments) {
        const auto values = experiment->data->intensity_calc.values();
        const QByteArray bytes(reinterpret_cast<const char*>(values.data()),
                               values.size() * sizeof(double));
        result.append(QString::fromLatin1(
            QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()));
    }
    return result;
}
QJsonObject scientific(const edi::FitResultBase& fit, const edi::Project& p) {
    QJsonObject values, uncertainty;
    for (const auto& [name, value] : fit.values)
        values[QString::fromStdString(name)] = bits(value);
    for (const auto& [name, value] : fit.uncertainty)
        uncertainty[QString::fromStdString(name)] = bits(value);
    return {{"values", values},
            {"uncertainty", uncertainty},
            {"rwp", bits(fit.rwp)},
            {"chi2", bits(fit.reduced_chi_square)},
            {"iterations", fit.iterations},
            {"converged", fit.converged},
            {"status", static_cast<int>(fit.status)},
            {"pattern", pattern(p)}};
}
}  // namespace
void thread_selector_environment() {
#if defined(Q_OS_WASM)
    // Explicit caller environment, planted before the browser's first actual engine fill.
    setenv("OMP_NUM_THREADS", "2", 1);
    const auto escape = wanted("THREAD_SELECTOR_ESCAPE", "").toUtf8();
    setenv("THREAD_SELECTOR_ESCAPE", escape.constData(), 1);
#endif
}
void thread_selector_settings(QQmlApplicationEngine& engine) {
    engine.rootContext()->setContextProperty("threadSelectorEscape",
                                             wanted("THREAD_SELECTOR_ESCAPE", ""));
#if !defined(Q_OS_WASM)
    const auto file = QString::fromUtf8(qgetenv("THREAD_SELECTOR_SETTINGS_FILE"));
    if (file.isEmpty()) qFatal("Thread selector observations require private machine settings");
    engine.rootContext()->setContextProperty("pySettingsPath",
                                             QUrl::fromLocalFile(file).toString());
#else
    static_cast<void>(engine);
#endif
}
void thread_selector_install(QQmlApplicationEngine& engine) {
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
    auto* deadline = new QTimer(window);
    deadline->setSingleShot(true);
    QObject::connect(deadline, &QTimer::timeout, window, [] {
        publish({{"error", "Actual selector work exceeded its bounded observation deadline"}});
    });
    deadline->start(120000);
    QTimer::singleShot(500, window, [=] {
        QJsonObject result{{"initialSetting", edi::engine_threads_setting()}};
        auto* dialog = window->findChild<QObject*>("preferences");
        if (dialog) QMetaObject::invokeMethod(dialog, "open");
        auto* develop = window->findChild<QObject*>("preferences.tab.develop");
        if (develop && !QMetaObject::invokeMethod(develop, "click"))
            QMetaObject::invokeMethod(develop, "clicked");
        auto* selector = window->findChild<QQuickItem*>("preferences.engineThreads");
        result["selectorUsable"] = selector && selector->isVisible() && selector->isEnabled();
        const auto choice = wanted("THREAD_SELECTOR_COUNT", "read");
        if (selector && choice != "read") {
            const int index = choice == "restore" ? 3 : choice.toInt();
            selector->setProperty("currentIndex", index);
            QMetaObject::invokeMethod(selector, "activated", Q_ARG(int, index));
        }
        if (selector && choice == "restore") {
            result["beforeAuto"] = edi::engine_threads_setting();
            selector->setProperty("currentIndex", 0);
            QMetaObject::invokeMethod(selector, "activated", Q_ARG(int, 0));
        }
        result["selectedIndex"] = selector ? selector->property("currentIndex").toInt() : -1;
        result["setting"] = edi::engine_threads_setting();
        result["reportedWorkers"] = edi::engine_threading().workers;
        result["environment"] = QString::fromUtf8(qgetenv("OMP_NUM_THREADS"));
        if (dialog) QMetaObject::invokeMethod(dialog, "close");
        if (!edi_app::ExampleListModel::bundledIds().contains("pd-neut-cwl_cosio-d20")) {
            result["error"] = "Example precondition: the selector's measured CW vehicle must be bundled";
            publish(result);
            return;
        }
        if (!session->openExample("pd-neut-cwl_cosio-d20")) {
            result["error"] = session->lastError();
            publish(result);
            return;
        }
        const auto directory = session->projectLocation().toStdString();
        // Let the normal initial view calculation finish before observing independent worker work.
        QTimer::singleShot(1200, window, [=] {
            std::thread([=]() mutable {
                try {
                    auto project = edi::load_project(directory);
                    thread_selector_reset();
                    project.calculate();
                    result["calculationFills"] =
                        QJsonDocument::fromJson(thread_selector_report()).array();
                    result["calculated"] = pattern(project);
                    thread_selector_reset();
                    const auto fit = project.fit();
                    result["fitFills"] = QJsonDocument::fromJson(thread_selector_report()).array();
                    result["scientific"] = scientific(fit, project);
                } catch (const std::exception& error) {
                    result["error"] = error.what();
                }
                QMetaObject::invokeMethod(
                    window,
                    [=] {
                        deadline->stop();
                        publish(result);
                    },
                    Qt::QueuedConnection);
            }).detach();
        });
    });
}
