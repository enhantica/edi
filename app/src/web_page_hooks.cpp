// SPDX-License-Identifier: BSD-3-Clause
#include "web_page_hooks.hpp"

#include <QQmlApplicationEngine>

#if defined(Q_OS_WASM)
#include <emscripten.h>

#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaObject>
#include <QPointer>
#include <QQuickItem>
#include <string>

#include "app_info.hpp"
#include "session.hpp"

namespace {

QPointer<QQmlApplicationEngine> g_engine;

QObject* named(const char* name) {
    if (g_engine == nullptr || g_engine->rootObjects().isEmpty()) {
        return nullptr;
    }
    return g_engine->rootObjects().constFirst()->findChild<QObject*>(QLatin1String(name));
}

// The control's own action: a button's clicked handler, a tab button's click (which checks it in its bar).
bool press(QObject* control) {
    if (control == nullptr) {
        return false;
    }
    if (control->metaObject()->indexOfMethod("click()") >= 0) {
        return QMetaObject::invokeMethod(control, "click");
    }
    return QMetaObject::invokeMethod(control, "clicked");
}

QJsonObject state() {
    QObject* preferences = named("preferences");
    QObject* develop = named("preferences.tab.develop");
    QObject* diagnostics = named("diagnostics");
    auto* text = qobject_cast<QQuickItem*>(named("diagnostics.text"));
    auto* info = g_engine != nullptr ? g_engine->singletonInstance<ApplicationInfo*>("edi.app", "ApplicationInfo")
                                     : nullptr;
    if (preferences == nullptr || develop == nullptr || diagnostics == nullptr || text == nullptr || info == nullptr) {
        return {{QStringLiteral("error"), QStringLiteral("the Preferences, Develop or Diagnostics controls were not found")}};
    }
    return {
        {QStringLiteral("preferencesVisible"), preferences->property("visible").toBool()},
        {QStringLiteral("developSelected"), develop->property("checked").toBool()},
        {QStringLiteral("diagnosticsVisible"), diagnostics->property("visible").toBool()},
        {QStringLiteral("textVisible"), text->isVisible()},
        {QStringLiteral("text"), text->property("text").toString()},
        {QStringLiteral("providerText"), info->diagnostics()},
    };
}

QJsonObject act(const std::string& action) {
    if (action == "open") {
        if (!press(named("appBar.button.preferences")) || !press(named("preferences.tab.develop")) ||
            !press(named("preferences.diagnostics"))) {
            return {{QStringLiteral("error"), QStringLiteral("Preferences, Develop or Diagnostics could not be opened")}};
        }
        return state();
    }
    if (action == "read") {
        return state();
    }
    if (action == "close") {
        QObject* diagnostics = named("diagnostics");
        QObject* preferences = named("preferences");
        if (diagnostics == nullptr || preferences == nullptr || !QMetaObject::invokeMethod(diagnostics, "close") ||
            !QMetaObject::invokeMethod(preferences, "close")) {
            return {{QStringLiteral("error"), QStringLiteral("Diagnostics or Preferences could not be closed")}};
        }
        return state();
    }
    return {{QStringLiteral("error"), QStringLiteral("unknown action (open, read, close)")}};
}

}  // namespace

// Called by the page on the main thread, which is Qt's: the result stays valid until the next call.
extern "C" EMSCRIPTEN_KEEPALIVE const char* edi_develop_diagnostics(const char* action) {
    static std::string result;
    result = QJsonDocument(act(action)).toJson(QJsonDocument::Compact).toStdString();
    return result.c_str();
}

// The status bar's live fit progress: its bar's text and effective visibility, and whether the fit is running.
extern "C" EMSCRIPTEN_KEEPALIVE const char* edi_fit_progress() {
    static std::string result;
    auto* bar = qobject_cast<QQuickItem*>(named("statusBar.fit.progress"));
    QObject* fit = named("statusBar.fit");
    const QJsonObject state =
        bar == nullptr || fit == nullptr
            ? QJsonObject{{QStringLiteral("error"), QStringLiteral("the status bar's fit progress was not found")}}
            : QJsonObject{{QStringLiteral("text"), bar->property("text").toString()},
                          {QStringLiteral("visible"), bar->isVisible()},
                          {QStringLiteral("running"), fit->property("running").toBool()}};
    result = QJsonDocument(state).toJson(QJsonDocument::Compact).toStdString();
    return result.c_str();
}

// Session::openExample(id) on Qt's main thread: 1 opened, 0 refused (Session names why), -1 no Session.
extern "C" EMSCRIPTEN_KEEPALIVE int edi_open_example(const char* example_id) {
    auto* session = g_engine != nullptr ? g_engine->singletonInstance<edi_app::Session*>("edi.app", "Session") : nullptr;
    if (session == nullptr) {
        return -1;
    }
    return session->openExample(QString::fromUtf8(example_id)) ? 1 : 0;
}

EM_JS_DEPS(edi_develop, "$UTF8ToString,$stringToUTF8OnStack,$withStackSave");
EM_JS(void, edi_install_web_page_hooks, (), {
    const call = (action) => {
        const state = JSON.parse(UTF8ToString(withStackSave(() => _edi_develop_diagnostics(stringToUTF8OnStack(action)))));
        if (state.error) {
            throw new Error(`ediDevelopDiagnostics(${action}): ${state.error}`);
        }
        return state;
    };
    globalThis.ediDevelopDiagnostics = (action) => {
        if (action !== "close") {
            return call(action);
        }
        call("close");
        // Resolved once both dialogs have closed, after their close transitions.
        return new Promise((resolve, reject) => {
            const started = Date.now();
            const poll = () => {
                const state = call("read");
                if (!state.preferencesVisible && !state.diagnosticsVisible) {
                    resolve(state);
                } else if (Date.now() - started > 10000) {
                    reject(new Error("ediDevelopDiagnostics(close): the dialogs did not close"));
                } else {
                    setTimeout(poll, 20);
                }
            };
            poll();
        });
    };
    globalThis.ediFitProgress = () => {
        const state = JSON.parse(UTF8ToString(_edi_fit_progress()));
        if (state.error) {
            throw new Error(`ediFitProgress: ${state.error}`);
        }
        return state;
    };
    globalThis.ediOpenExample = (exampleId) => {
        const opened = withStackSave(() => _edi_open_example(stringToUTF8OnStack(String(exampleId))));
        if (opened < 0) {
            throw new Error("ediOpenExample: the app's Session is not available");
        }
        return opened === 1;
    };
});

void edi_app::install_web_page_hooks(QQmlApplicationEngine& engine) {
    g_engine = &engine;
    edi_install_web_page_hooks();
}

#else

void edi_app::install_web_page_hooks(QQmlApplicationEngine& /*engine*/) {}

#endif
