// SPDX-License-Identifier: BSD-3-Clause
#include <QtTest/QtTest>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QStandardItemModel>
#include <QStandardPaths>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QCryptographicHash>
#include <QGuiApplication>
#include <QElapsedTimer>
#include <QMouseEvent>
#include <QRegularExpression>
#include <QTimer>
#include <QUuid>
#include <algorithm>
#include <iostream>
#include <memory>
#ifndef __EMSCRIPTEN__
#include "codex_agent.hpp"
#include "claude_session.hpp"
#include "assistant_runtime_config.hpp"
#endif
#include "edi/io.hpp"
#include "fit_view_model.hpp"
#include <QtQml/qqmlextensionplugin.h>
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include "session.hpp"
#include "assistant_test_settings.hpp"
#include "assistant_widget_input.hpp"
#include "row_table_model.hpp"
#include "project_view_model.hpp"
#include "run_log.hpp"
#include "online_search.hpp"
#include "parameter_item.hpp"
#if defined(Q_OS_UNIX)
#include "assistant_file_primitives.hpp"
#include <sys/stat.h>
#include <sys/xattr.h>
#endif
#if defined(Q_OS_LINUX)
#include <cerrno>
#include <sys/inotify.h>
#include <unistd.h>
#endif

// Keeps what a retried check found, for the steps after it, without an assignment inside the check.
template <class T, class U>
bool take(T*& slot, U* found) {
    slot = found;
    return found != nullptr;
}
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

#ifndef __EMSCRIPTEN__
// An authored local peer delivers one requested tool call through the real assistant transport.
// It has no provider connection and never performs an application edit itself.
static int assistantToolPeer() {
    using Object = QJsonObject;
    const auto write = [](const Object& row) {
        std::cout << QJsonDocument(row).toJson(QJsonDocument::Compact).toStdString() << '\n' << std::flush;
    };
    const auto event = [&](const QString& method, const Object& params) {
        write({{"method", method}, {"params", params}});
    };
    Object policy, item;
    const auto sequence = QJsonDocument::fromJson(qgetenv("EDI_UI_TOOL_SEQUENCE")).array();
    qsizetype step = 0;
    const auto issue = [&] {
        const auto specification = sequence.isEmpty() ? Object{} : sequence.at(step).toObject();
        const auto tool = specification.value("tool").toString(qEnvironmentVariable("EDI_UI_TOOL", "load_data"));
        const auto arguments = sequence.isEmpty() ? QJsonDocument::fromJson(qgetenv("EDI_UI_LOAD_ARGUMENTS")).object()
                                                  : specification.value("arguments").toObject();
        const auto identity = sequence.isEmpty() ? QStringLiteral("load-item") : QStringLiteral("load-item-%1").arg(step);
        const auto rpc = sequence.isEmpty() ? QStringLiteral("load-call") : QStringLiteral("load-call-%1").arg(step);
        item = {{"id", identity}, {"type", "dynamicToolCall"}, {"tool", tool},
            {"arguments", arguments}, {"status", "inProgress"}};
        event("item/started", {{"threadId", "load-thread"}, {"turnId", "load-turn"}, {"item", item}});
        if (tool == "request_user_input") {
            write({{"id", rpc}, {"method", "item/tool/requestUserInput"}, {"params", Object{
                {"threadId", "load-thread"}, {"turnId", "load-turn"}, {"itemId", identity},
                {"questions", arguments.value("questions")}, {"isBlocking", true}, {"autoResolutionMs", QJsonValue::Null}}}});
            return;
        }
        write({{"id", rpc}, {"method", "item/tool/call"},
            {"params", Object{{"threadId", "load-thread"}, {"turnId", "load-turn"}, {"callId", identity},
                {"tool", tool}, {"arguments", arguments}}}});
    };
    for (std::string line; std::getline(std::cin, line);) {
        const auto request = QJsonDocument::fromJson(QByteArray::fromStdString(line)).object();
        const auto method = request.value("method").toString();
        const auto params = request.value("params").toObject();
        if (method.isEmpty()) {
            const auto rpc = sequence.isEmpty() ? QStringLiteral("load-call") : QStringLiteral("load-call-%1").arg(step);
            if (request.value("id") != rpc) continue;
            item["status"] = "completed";
            const auto result = request.value("result").toObject();
            if (item.value("tool") == "request_user_input") {
                QFile answer(qEnvironmentVariable("EDI_UI_POLICY_RECEIPT") + ".answer");
                if (!answer.open(QIODevice::WriteOnly | QIODevice::Truncate)) return 1;
                answer.write(QJsonDocument(result).toJson(QJsonDocument::Compact));
                item["success"] = result.contains("answers");
                item["contentItems"] = QJsonArray{};
            } else {
                item["success"] = result.value("success");
                item["contentItems"] = result.value("contentItems");
            }
            event("item/completed", {{"threadId", "load-thread"}, {"turnId", "load-turn"}, {"item", item}});
            if (++step < sequence.size()) { issue(); continue; }
            event("turn/completed", {{"threadId", "load-thread"}, {"turn", Object{{"id", "load-turn"}, {"status", "completed"}, {"error", QJsonValue::Null}}}});
            continue;
        }
        if (!request.contains("id")) continue;
        Object result;
        if (method == "account/read")
            result = {{"account", Object{{"type", "chatgpt"}, {"email", "ui@example.invalid"}, {"planType", "plus"}}}, {"requiresOpenaiAuth", false}};
        else if (method == "model/list")
            result = {{"data", QJsonArray{Object{{"id", "gpt-6-luna"}, {"model", "gpt-6-luna"}, {"displayName", "Local UI peer"},
                {"hidden", false}, {"defaultReasoningEffort", "medium"},
                {"supportedReasoningEfforts", QJsonArray{Object{{"reasoningEffort", "medium"}}}}}}}, {"nextCursor", QJsonValue::Null}};
        else if (method == "skills/list") {
            QJsonArray skills;
            const auto folders = params.value("cwds").toArray();
            if (!folders.isEmpty()) {
                const QString folder = folders.first().toString();
                const QDir root(folder + "/.agents/skills");
                for (const auto& name : root.entryList(QDir::Dirs | QDir::NoDotAndDotDot))
                    skills.append(Object{{"name", name}, {"path", root.filePath(name + "/SKILL.md")}, {"enabled", true}});
                result = {{"data", QJsonArray{Object{{"cwd", folder}, {"skills", skills}, {"errors", QJsonArray{}}}}}};
            }
        } else if (method == "thread/start") {
            const auto receipt = qEnvironmentVariable("EDI_UI_POLICY_RECEIPT");
            if (!receipt.isEmpty()) {
                QFile file(receipt);
                if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) return 1;
                file.write(params.value("developerInstructions").toString().toUtf8());
            }
            const auto effort = params.value("config").toObject().value("model_reasoning_effort");
            const auto tools = params.value("dynamicTools").toArray();
            QJsonArray advertised;
            for (const auto& value : tools) {
                const auto tool = value.toObject();
                advertised.append(Object{{"type", "function"}, {"name", tool.value("name")}, {"parameters", tool.value("inputSchema")}});
            }
            policy = {{"schema", "edi.runtime-policy/1"}, {"flavour", "edi-app-server/1"},
                {"upstreamVersion", EDI_CODEX_RUNTIME_VERSION}, {"upstreamCommit", "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"},
                {"sourcePatchSha256", edi_app::CodexAgent::policyPatch()}, {"threadId", "load-thread"}, {"turnId", QJsonValue::Null},
                {"isolation", "isolated"}, {"toolMode", "direct"}, {"sandbox", "readOnly"}, {"approvalPolicy", "never"},
                {"modelNetwork", false}, {"requestedTools", tools}, {"advertisedTools", advertised}, {"dispatchEqualsAdvertisement", true},
                {"model", params.value("model")}, {"reasoningEffort", effort}};
            result = {{"thread", Object{{"id", "load-thread"}, {"ephemeral", false}}}, {"cwd", params.value("cwd")},
                {"modelProvider", "openai"}, {"model", params.value("model")}, {"reasoningEffort", effort},
                {"approvalPolicy", "never"}, {"approvalsReviewer", "user"},
                {"sandbox", Object{{"type", "readOnly"}, {"networkAccess", false}}}, {"ediPolicy", policy}};
        } else if (method == "turn/start") {
            policy["turnId"] = "load-turn";
            result = {{"turn", Object{{"id", "load-turn"}, {"status", "inProgress"}}}, {"ediPolicy", policy}};
        } else if (method == "thread/list") result = {{"data", QJsonArray{}}, {"nextCursor", QJsonValue::Null}};
        else if (method == "account/rateLimits/read") result = {{"rateLimits", QJsonValue::Null}};
        write({{"id", request.value("id")}, {"result", result}});
        if (method == "turn/start") {
            event("turn/started", {{"threadId", "load-thread"}, {"turn", Object{{"id", "load-turn"}, {"status", "inProgress"}}}});
            step = 0;
            issue();
        }
    }
    return 0;
}

namespace {
QQuickItem* namedItem(QQuickItem* item, const QString& name) {
    if (!item || item->objectName() == name) return item;
    for (auto* child : item->childItems())
        if (auto* match = namedItem(child, name)) return match;
    return nullptr;
}

QRectF sceneBox(const QQuickItem& item) {
    return item.mapRectToScene(QRectF(0, 0, item.width(), item.height()));
}

// Owner's limits for a stuck control and all controls of one shown item.
constexpr int shownControlLimit = 10000;
constexpr int shownItemLimit = 45000;
constexpr int shownObservationMargin = 750;

QString fileText(const QString& path) {
    QFile file(path);
    return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString{};
}

bool copyEditableProject(const QDir& copy) {
    const QDir fixture(QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/e04_t1/editable-project"));
    for (const auto* relative : {"project.edi", "analysis/analysis.edi", "experiments/hrpt.edi", "structures/lbco.edi"}) {
        const auto name = QString::fromLatin1(relative);
        const auto path = copy.filePath(name);
        if (!QDir().mkpath(QFileInfo(path).absolutePath()) || !QFile::copy(fixture.filePath(name), path)) return false;
    }
    return true;
}

QStringList assistantErrors(edi_app::RunLog& log) {
    QStringList errors;
    for (const auto& line : log.logText().split('\n'))
        if (line.contains("ERROR") && line.contains("assistant:")) errors.append(line);
    return errors;
}

auto offlinePeer(const QJsonArray& sequence, const QString& receipt = {}) {
    const QList<QPair<QByteArray, QByteArray>> values{
        {"EDI_CODEX_DEVELOPMENT_EXECUTABLE", QCoreApplication::applicationFilePath().toUtf8()},
        {"EDI_UI_TOOL_SEQUENCE", QJsonDocument(sequence).toJson(QJsonDocument::Compact)},
        {"EDI_UI_POLICY_RECEIPT", receipt.toUtf8()},
    };
    QList<QPair<QByteArray, QByteArray>> originals;
    for (const auto& [name, value] : values) {
        originals.append(qMakePair(name, qgetenv(name.constData())));
        qputenv(name.constData(), value);
    }
    return qScopeGuard([originals] {
        for (const auto& [name, value] : originals) {
            if (value.isNull()) qunsetenv(name.constData());
            else qputenv(name.constData(), value);
        }
    });
}

// Observe and retain Qt's delivered events, including their original device and timestamp.
// A later copy with a new device would be a new manual click and prove nothing about retirement.
class HeldAssistantPress : public QObject {
public:
    QPointer<QQuickItem> target;
    std::unique_ptr<QMouseEvent> press, release;
    QElapsedTimer sincePress;

    bool eventFilter(QObject*, QEvent* event) override {
        if (!target || (event->type() != QEvent::MouseButtonPress && event->type() != QEvent::MouseButtonRelease))
            return false;
        const auto* mouse = static_cast<const QMouseEvent*>(event);
        if (mouse->pointingDevice()->name() != QStringLiteral("EDI assistant input") ||
            !sceneBox(*target).contains(mouse->scenePosition())) return false;
        if (event->type() == QEvent::MouseButtonPress && !press) {
            sincePress.start();
            press.reset(mouse->clone());
        }
        if (event->type() == QEvent::MouseButtonRelease && press && !release) release.reset(mouse->clone());
        return false;
    }
};
}  // namespace

#endif

class WorkingAssistant : public edi_app::AssistantViewModel {
    Q_OBJECT
    Q_PROPERTY(QString state READ fixtureState NOTIFY fixtureStateChanged)
public:
    QString fixtureState() const { return state_; }
    void setFixtureState(const QString& value) { state_ = value; emit fixtureStateChanged(); }
signals:
    void fixtureStateChanged();
private:
    QString state_ = "idle";
};

#ifndef __EMSCRIPTEN__
class AssistantProviderProbe : public QObject {
    Q_OBJECT
private slots:
    void claudeSignIn() {
        const auto home = qEnvironmentVariable("EDI_PROVIDER_TEST_LOGIN_HOME");
        QFile identity(home + "/fixture-account.txt");
        QVERIFY2(identity.open(QIODevice::WriteOnly), "Prepare the offline login's own config home");
        identity.close();

        edi_app::ClaudeSession runtime;
        edi_app::AssistantRuntimeLaunch launch;
        launch.executable = qEnvironmentVariable("EDI_PROVIDER_TEST_LOGIN_EXECUTABLE");
        launch.account.home = home;
        launch.environment = QProcessEnvironment::systemEnvironment();
        QSignalSpy opened(&runtime, &edi_app::AssistantRuntimeSession::signInOpened);
        QSignalSpy finished(&runtime, &edi_app::AssistantRuntimeSession::signInFinished);
        runtime.signIn(launch);
        QTRY_VERIFY2_WITH_TIMEOUT(std::any_of(opened.cbegin(), opened.cend(), [](const auto& event) {
            return event.at(0) == QString("https://claude.ai/oauth/authorize") &&
                event.at(2) == QString("Paste the sign-in code") && event.at(3).toBool();
        }), "The real login process must publish its browser and callback prompt", 3000);
        QPointer<QProcess> login = runtime.findChild<QProcess*>();
        QVERIFY2(login && login->state() == QProcess::Running && finished.isEmpty(),
                 "The original process must remain alive while the fixture withholds the callback");
        if (qEnvironmentVariableIsSet("EDI_PROVIDER_TEST_CANCEL_LOGIN")) {
            runtime.cancelSignIn();
            QTRY_VERIFY2_WITH_TIMEOUT(login.isNull(), "Cancel must stop and dispose of the login child", 3000);
            QCOMPARE(finished.size(), 1);
            QVERIFY2(!finished.at(0).at(0).toBool() &&
                     finished.at(0).at(1).toString().contains("cancelled", Qt::CaseInsensitive),
                     "Cancel must report one unsuccessful login without waiting for the callback");
            return;
        }
        // Deliver any login deadline as Qt would, without waiting minutes for wall time.
        for (auto* timer : login->findChildren<QTimer*>()) {
            if (!timer->isActive()) continue;
            QTimerEvent elapsed(timer->timerId());
            QCoreApplication::sendEvent(timer, &elapsed);
        }
        QVERIFY2(login && login->state() == QProcess::Running && finished.isEmpty(),
                 "The original login process must survive its former deadline");
        runtime.answerSignIn("offline-fixture-code");
        QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 3000);
        QVERIFY2(finished.at(0).at(0).toBool() && finished.at(0).at(1).toString().isEmpty(),
                 "The delayed callback must finish the same login successfully");
        QTRY_VERIFY2_WITH_TIMEOUT(login.isNull(), "The successful login must dispose of its child", 3000);
    }

    void accountTurn() {
        edi_app::use_fresh_settings();
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QFile fixture(qEnvironmentVariable("EDI_PROVIDER_TEST_CASE"));
        QVERIFY2(fixture.open(QIODevice::ReadOnly), "The provider probe needs an isolated account case");
        const auto test = QJsonDocument::fromJson(fixture.readAll()).object();
        QSettings settings(edi_app::settings_file_path(), QSettings::IniFormat);
        const auto provider = test.value("provider").toString();
        const auto scenario = test.value("scenario").toString();
        auto account = test.value("account").toObject();
        const auto id = account.value("id").toString();
        const auto otherLogin = test.value("otherLogin").toString();
        const auto accountParent = edi_app::app_local_data_location()
            + "/assistant/accounts/" + provider + "/";
        const auto home = accountParent + id;
        QVERIFY2(QDir().mkpath(home), "Each selected account needs its own config home");
        QVERIFY2(QFile::setPermissions(home, QFileDevice::ReadOwner | QFileDevice::WriteOwner |
                                      QFileDevice::ExeOwner), "The fixture must have an owner-only account home");
        account.insert("home", home);
        QFile identity(home + "/fixture-account.txt");
        QVERIFY2(identity.open(QIODevice::WriteOnly), "Set the identity returned by the offline runtime");
        identity.write(test.value("runtimeEmail").toString().toUtf8());
        identity.close();
        QFile credential(home + "/.credentials.json");
        QVERIFY2(credential.open(QIODevice::WriteOnly), "Plant a credential file that edi must leave alone");
        credential.write("{\"fixture\": \"private account sentinel\"}");
        credential.close();
#if defined(Q_OS_LINUX)
        const int watcher = ::inotify_init1(IN_CLOEXEC | IN_NONBLOCK);
        QVERIFY2(watcher >= 0, "The credential test needs a real file-access observer");
        const auto closeWatcher = qScopeGuard([&] { ::close(watcher); });
        QVERIFY2(::inotify_add_watch(watcher, QFile::encodeName(credential.fileName()).constData(),
                                  IN_OPEN | IN_ACCESS | IN_MODIFY | IN_MOVE_SELF | IN_DELETE_SELF) >= 0,
                 "The credential observer must watch the planted file");
        char activity[1024];
        QVERIFY2(credential.open(QIODevice::ReadOnly), "Prove the credential observer detects a read");
        credential.read(1);
        credential.close();
        QVERIFY2(::read(watcher, activity, sizeof(activity)) > 0,
                 "An actual open and read must reach the observer");
#endif
        auto other = account;
        const auto otherId = test.value("otherId").toString();
        const auto otherHome = accountParent + otherId;
        other.insert("id", otherId);
        other.insert("email", otherLogin);
        other.insert("home", otherHome);
        QVERIFY2(QDir().mkpath(otherHome), "The other signed-in account must have a separate home");
        QFile otherIdentity(otherHome + "/fixture-account.txt");
        QVERIFY2(otherIdentity.open(QIODevice::WriteOnly), "Set the other account's offline identity");
        otherIdentity.write(otherLogin.toUtf8());
        otherIdentity.close();
        const auto key = "Assistant/Providers/" + provider;
        settings.setValue(key + "/accounts",
                          QJsonDocument(QJsonObject{{"version", 1}, {"accounts", QJsonArray{other, account}}})
                              .toJson(QJsonDocument::Compact));
        settings.setValue("Assistant/activeAccount", provider + "/" + id);
        const auto foreignThread = QUuid::createUuid().toString(QUuid::WithoutBraces);
        const QJsonObject foreign{
            {"thread", foreignThread}, {"originator", "edi"}, {"account", otherId},
            {"provider", provider}, {"title", "Other account conversation"}};
        settings.setValue(key + "/sessions",
                          QJsonDocument(QJsonObject{{"version", 1}, {"threads", QJsonObject{{foreignThread, foreign}}}})
                              .toJson(QJsonDocument::Compact));
        settings.sync();
        QVERIFY2(settings.status() == QSettings::NoError, "The account fixture must reach the settings store");

        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY2(session, "The probe must reach the application's normal desktop session");
        auto* assistant = session->assistant();
        QStringList available;
        QStringList offered;
        for (const auto& entry : assistant->providers()) {
            offered.append(entry.provider);
            if (entry.installed) available.append(entry.provider);
        }
        offered.sort();
        QVERIFY2((offered == QStringList{"chatgpt", "claude", "copilot"}),
                 "The Account dialog must get one availability record for each provider");
        QVERIFY2((available == QStringList{provider}),
                 "An installed runtime must be usable without enabling the other providers");
        assistant->switchAccount(provider, id);
        QVERIFY2(assistant->activeProvider().provider == provider,
                 "The connection offer must use the installed provider the user selected");
        // The owner's order (attach-after-connect): connect with nothing attached and no project, then attach
        // files and send them in the first turn.
        const bool attachLater = scenario == "attach-after-connect";
        QString fileId;
        if (!attachLater) {
            const auto selection = assistant->beginFileSelection();
            QVERIFY2(!selection.isEmpty(), "The assistant must accept file selection before the connection offer");
            QVERIFY2(assistant->addSelectedFiles(selection, {QUrl::fromLocalFile(test.value("file").toString())}),
                     qPrintable(assistant->lastError()));
            fileId = assistant->selectedFiles()->text(0, "id");
            QVERIFY2(!fileId.isEmpty(), "The attached sample must have an edi file identity");
        }
        const auto consent = assistant->contextConsentIdentity();
        QVERIFY2(!consent.isEmpty() && (attachLater || assistant->contextConsentRequired()),
                 "The newly attached sample must be covered by the user's outgoing context approval");
        const auto approval = assistant->acceptConnectionOffer(consent);
        QVERIFY2(approval == "submitted", qPrintable(assistant->lastError() + " Approval: " + approval));
        if (test.value("mismatch").toBool()) {
            QTRY_VERIFY2_WITH_TIMEOUT(assistant->lastError().contains(test.value("runtimeEmail").toString()),
                                     qPrintable(assistant->lastError()), 3000);
            QVERIFY2(!assistant->connected(), "A mismatched runtime must not connect");
            assistant->send("Do not send this prompt");
            return;
        }
        if (test.value("credential").toBool()) {
            QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->draftAdmissionReady(),
                                     qPrintable(assistant->lastError()), 3000);
            QQmlComponent component(&engine);
            component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
            QScopedPointer<QObject> root(component.create());
            auto* window = qobject_cast<QQuickWindow*>(root.data());
            QVERIFY2(window, qPrintable(component.errorString()));
            auto* dialog = root->findChild<QObject*>("assistant.accountDialog");
            QVERIFY2(dialog && dialog->setProperty("parent", QVariant::fromValue(window->contentItem())) &&
                            QMetaObject::invokeMethod(dialog, "open"),
                     "The desktop Account dialog must open on the test window");
            // The credential line itself, shown only for a key or token: it names the key's environment variable. The
            // account rows are a Repeater's, so they are found through the item tree, not as QObject children.
            const auto showsCredentialSource = [&] {
                const auto shows = [](QQuickItem* item, auto&& self) -> bool {
                    if (item->objectName() == "assistant.accountCredential" && item->isVisible()) {
                        const auto text = item->property("text").toString();
                        if (text.contains("ANTHROPIC_API_KEY") || text.contains("own API key", Qt::CaseInsensitive)) return true;
                    }
                    for (auto* child : item->childItems())
                        if (self(child, self)) return true;
                    return false;
                };
                auto* content = dialog->property("contentItem").value<QQuickItem*>();
                return content && shows(content, shows);
            };
            QTRY_VERIFY2_WITH_TIMEOUT(dialog->property("visible").toBool(),
                                      "The Account dialog must actually open", 500);
            for (const auto* child : dialog->findChildren<QObject*>())
                QVERIFY2(!child->property("text").toString().contains("fixture-api-key-never-displayed"),
                         "Account details must never display the key value");
            QVERIFY2(showsCredentialSource(), "The Account dialog must identify the active Claude environment key");
            return;
        }
        if (attachLater) {
            QTRY_VERIFY2_WITH_TIMEOUT(assistant->state() == "idle" && assistant->draftAdmissionReady(),
                                     qPrintable(assistant->lastError()), 3000);
            QVERIFY2(!session->project(), "This case has no project open");
            QList<QUrl> files;
            for (const auto& path : test.value("files").toArray()) files.append(QUrl::fromLocalFile(path.toString()));
            QVERIFY2(files.size() >= 2, "The case attaches two files, as the owner did");
            const auto selection = assistant->beginFileSelection();
            QVERIFY2(!selection.isEmpty() && assistant->addSelectedFiles(selection, files), qPrintable(assistant->lastError()));
            QCOMPARE(assistant->selectedFiles()->rowCount(), files.size());
            fileId = assistant->selectedFiles()->text(0, "id");
            const auto attached = assistant->contextConsentIdentity();
            QVERIFY2(!attached.isEmpty() && assistant->contextConsentRequired(),
                     "Files attached after connecting must be covered by a new approval");
            // What the panel does when Send finds new attachments: the dialog's approval, then the held draft.
            const auto again = assistant->acceptConnectionOffer(attached);
            QVERIFY2(again == "approved", qPrintable(assistant->lastError() + " Approval: " + again));
        }
        const auto prompt = "Read the attached sample. fixture-file-id=" + fileId;
        if (scenario == "wrong-login" || scenario == "wrong-host") {
            const QString differing = scenario == "wrong-login" ? "different-user" : "other.ghe.com";
            QTRY_VERIFY2_WITH_TIMEOUT(assistant->lastError().contains(differing),
                                     qPrintable(assistant->lastError()), 3000);
            QVERIFY2(!assistant->connected() && assistant->submitDraft(prompt).isEmpty(),
                     "Copilot must refuse Send when its selected login or host differs");
            return;
        }
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->state() == "idle" && assistant->draftAdmissionReady(),
                                 qPrintable(assistant->lastError()), 3000);
        if (provider == "claude") {
            assistant->setSelectedModel("sonnet");
            QVERIFY2(assistant->selectedModel() == "sonnet", "The selected model must come from Claude's readback");
        }
        assistant->refreshSessions();
        QTRY_VERIFY2_WITH_TIMEOUT(!assistant->sessionsLoading(), "The account thread list must settle", 1000);
        const auto* sessions = assistant->sessions();
        for (int row = 0; row < sessions->rowCount(); ++row)
            QVERIFY2(sessions->text(row, "id") != foreignThread, "Another account's thread must stay out of this list");
        QStringList errors;
        const auto errorObservation = QObject::connect(assistant, &edi_app::AssistantViewModel::lastErrorChanged,
            [&] { errors.append(assistant->lastError()); });
        const auto disconnectErrors = qScopeGuard([&] { QObject::disconnect(errorObservation); });
        if (attachLater) {
            // The held draft goes once the panel's conditions hold (composerSubmitApprovedDraft); the model choice
            // above restarts Claude's process first.
            QTRY_VERIFY2_WITH_TIMEOUT(!assistant->connected() || (!assistant->contextConsentRequired() &&
                                          assistant->state() == "idle" && !assistant->canCancel()),
                                      qPrintable(assistant->lastError()), 3000);
            QVERIFY2(assistant->connected(), qPrintable("Opening the conversation for the attached files kept the "
                                                        "account connected: " + assistant->lastError()));
        }
        assistant->send(prompt);
        const auto appearsInTranscript = [&] {
            auto* rows = assistant->messages();
            for (int row = 0; row < rows->rowCount(); ++row)
                if (rows->text(row, "kind") == "assistant" && rows->text(row, "text").contains("visible")) return true;
            return false;
        };
        if (scenario == "foreign-tool") {
            QTRY_VERIFY2_WITH_TIMEOUT(
                std::any_of(errors.cbegin(), errors.cend(), [](const QString& failure) {
                    return failure.contains("fixture_unlisted_tool") && failure.contains("turn was stopped");
                }),
                qPrintable(errors.join(u'\n')), 3000);
            QVERIFY2(!appearsInTranscript(), "An unlisted tool must stop the turn without a tool reply");
            return;
        }
        if (attachLater) {
            // The first turn with attachments and no project keeps the account connected: no connection failure.
            QTRY_VERIFY2_WITH_TIMEOUT(appearsInTranscript() || !assistant->connected() ||
                                          std::any_of(errors.cbegin(), errors.cend(), [](const QString& failure) {
                                              return failure.contains("could not connect");
                                          }),
                                      qPrintable(assistant->lastError()), 3000);
            QVERIFY2(std::none_of(errors.cbegin(), errors.cend(), [](const QString& failure) {
                         return failure.contains("could not connect");
                     }), qPrintable(errors.join(u'\n')));
            QVERIFY2(assistant->connected(), "The account must stay connected through its first turn");
        }
        QTRY_VERIFY2_WITH_TIMEOUT(appearsInTranscript(), qPrintable(assistant->lastError()), 3000);
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 3000);
        if (provider == "claude") {
            QVERIFY2(QMetaObject::invokeMethod(assistant, "switchAccount", Q_ARG(QString, provider), Q_ARG(QString, otherId)),
                     "Switch account must reach the view model's normal account action");
            if (!assistant->connected() && assistant->state() != "connecting")
                QVERIFY2(assistant->resumeConnection(), "The newly selected saved account must be available to reconnect");
            QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->account().email == otherLogin,
                                     "Switching must connect using the other account's own identity", 3000);
            QVERIFY2(!appearsInTranscript(), "Switch account must not carry over the previous account's reply");
        }

#if defined(Q_OS_LINUX)
        const auto events = ::read(watcher, activity, sizeof(activity));
        const auto readError = errno;
        QVERIFY2(events == -1 && readError == EAGAIN,
                 "The credential observer must report no opens, reads or changes");
#endif
    }
};
#endif

class AssistantUiTests : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() {
        qputenv("QT_QUICK_CONTROLS_HOVER_ENABLED", "1");
        edi_app::use_fresh_settings();
        QVERIFY(QDir().mkpath(edi_app::app_local_data_location()));
        const auto root = QString::fromUtf8(EDI_SOURCE_DIR);
        const auto cod = QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/cod/").toString();
        const auto edb = QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/easydiffraction/").toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + cod + ";easydiffraction=" + edb).toUtf8());
    }
#ifndef __EMSCRIPTEN__
    void shownStepFallback_data() {
        QTest::addColumn<QString>("fault");
        for (const auto* fault : {"absent", "covered", "disabled", "late", "mute", "working", "unrelated-motion"})
            QTest::newRow(fault) << QString::fromLatin1(fault);
    }
    void shownStepFallback() {
        QFETCH(QString, fault);
        // One stuck control gets 10 s and one item gets 45 s. The loaded absent
        // runs logged up to 10,536 ms of product wait (h6-abs.log). Keep the
        // 750 ms observation margin and measure the peer's admission separately.
        const QString control = QStringLiteral("experiments.create");
        const QString tool = QStringLiteral("create_experiment");
        const QJsonObject step{{"tool", tool}, {"arguments", QJsonObject{}}};
        const auto restore = offlinePeer(QJsonArray{step, step});
        QTemporaryDir storage;
        QVERIFY2(storage.isValid(), "The actor needs its own real run log");
        edi_app::RunLog log({storage.path(), {}, 3, 5'000'000, false});
        auto* previous = edi_app::RunLog::instance();
        edi_app::RunLog::install(&log);
        const auto restoreLog = qScopeGuard([&] { edi_app::RunLog::install(previous); });
        QVERIFY2(log.start({}), "The app's regular logging path must write to disk");
        log.setLevel("Info");

        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY2(window, "The actor must have a real app window");
        window->requestActivate();
        QVERIFY2(QTest::qWaitForWindowActive(window), "Shown input needs the active app window");
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY2(session && (session->hasProject() || session->startUntitledProject()) && session->untitled(),
                 "The fallback actor must use untitled work without a saved fixture directory");
        auto* project = session->project();
        QVERIFY2(project, "Tool effects are counted on the original project owner");
        QVERIFY2(project->loadStructure(QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/tests/fixtures/assistant_save_replay/lbco.cif")),
                 "The saved independent structure enables the ordinary Experiment page");
        auto* assistant = session->assistant();
        assistant->setActionWindow(window);
        assistant->setShowActions(true);
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        const auto find = [window](const QString& name) { return namedItem(window->contentItem(), name); };
        QQuickItem* tab = nullptr;
        QTRY_VERIFY2(take(tab, find("appBar.tab.experiment")) && tab->isEnabled(),
                     "The actual Experiment tab must be reachable before injecting a control fault");
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier, tab->mapToScene(tab->boundingRect().center()).toPoint());
        QQuickItem* target = nullptr;
        QTRY_VERIFY2(take(target, find(control)) && target->isVisible() && target->isEnabled(),
                     "The original Create experiment control exists before the fault");
        const QPointer<QQuickItem> original(target);
        QSignalSpy genuineClicks(target, SIGNAL(clicked()));
        QVERIFY2(genuineClicks.isValid(), "The actor can observe the real button's click delivery");

        const bool replacement = fault == "mute" || fault == "late";
        QScopedPointer<QObject> faultItem;
        QTimer followCoveredButton;
        HeldAssistantPress held, nextInput;
        if (replacement || fault == "covered") {
            QQmlComponent faultComponent(&engine);
            faultComponent.setData(replacement
                ? "import QtQuick.Controls\nButton { anchors.fill: parent; property int taken: 0; onClicked: ++taken }"
                : "import QtQuick\nMouseArea { objectName: \"acceptance.cover\" }", QUrl());
            faultItem.reset(faultComponent.create());
            auto* item = qobject_cast<QQuickItem*>(faultItem.data());
            QVERIFY2(item, qPrintable(faultComponent.errorString()));
            if (replacement) {
                // The Create button's parent is a Row. A sibling would take a
                // new slot. The substitute fills the existing slot instead.
                item->setParentItem(target);
                item->setZ(1);
                original->setObjectName("acceptance.original");
                item->setObjectName(control);
                held.target = item;
                window->installEventFilter(&held);
            } else {
                item->setParentItem(window->contentItem());
                item->setZ(10000);
                const auto follow = [original, item] {
                    if (!original) return;
                    const auto box = original->mapRectToItem(item->parentItem(),
                        QRectF(0, 0, original->width(), original->height()));
                    item->setPosition(box.topLeft());
                    item->setSize(box.size());
                };
                follow();
                connect(&followCoveredButton, &QTimer::timeout, item, follow);
                followCoveredButton.start(16);
            }
            QTRY_VERIFY2(sceneBox(*item).contains(sceneBox(*target).center()),
                         "The fault item actually covers the real button's hit point");
        } else if (fault == "absent" || fault == "unrelated-motion") {
            original->setObjectName("acceptance.original");
            QVERIFY2(!find(control), "The missing control has no same-name substitute in the app");
        } else if (fault == "disabled") {
            original->setEnabled(false);
            QVERIFY2(!original->isEnabled(), "The original target is effectively disabled");
        }

        // A separate viewport changes its scroll position while Create stays absent.
        // It does not cover the control or take focus, so it cannot advance that step.
        QScopedPointer<QObject> unrelatedViewport;
        int moved = 0;
        QTimer unrelatedMotion;
        if (fault == "unrelated-motion") {
            QQmlComponent viewportComponent(&engine);
            viewportComponent.setData("import QtQuick\nFlickable { width: 40; height: 40; contentHeight: 20000; interactive: false }", QUrl());
            unrelatedViewport.reset(viewportComponent.create());
            auto* viewport = qobject_cast<QQuickItem*>(unrelatedViewport.data());
            QVERIFY2(viewport, qPrintable(viewportComponent.errorString()));
            viewport->setParentItem(window->contentItem());
            viewport->setPosition(QPointF(window->width() - 50, window->height() - 50));
            QVERIFY2(viewport->isVisible() && !sceneBox(*viewport).intersects(sceneBox(*original)),
                     "Unrelated visible scroll motion stays away from the Create hit box");
            connect(&unrelatedMotion, &QTimer::timeout, viewport, [viewport, &moved] {
                viewport->setProperty("contentY", viewport->property("contentY").toDouble() + 24);
                ++moved;
            });
            unrelatedMotion.start(100);
        }

        const auto count = [project] { return project->assistantProject()->experiments.size(); };
        const auto base = count();
        QList<decltype(count())> effects;
        QElapsedTimer elapsed;
        QList<qint64> effectTimes;
        qint64 firstRevealAt = -1;
        int firstPress = 0, secondPress = 0, muteClicks = 0;
        QPointF pointer;
        QObject observation;
        connect(assistant, &edi_app::AssistantViewModel::actionControlsRequested, &observation, [&] {
            if (elapsed.isValid() && firstRevealAt < 0) firstRevealAt = elapsed.elapsed();
        });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerMoved, &observation, [&](const QPointF& point) { pointer = point; });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerPressed, &observation, [&] {
            auto* shown = find(control);
            if (!shown || !sceneBox(*shown).contains(pointer)) return;
            if (count() == base) ++firstPress;
            if (count() == base + 1 && shown == original) ++secondPress;
        });
        connect(project, &edi_app::ProjectViewModel::edited, &observation, [&] {
            const auto now = count();
            if (now == base || (!effects.isEmpty() && effects.back() == now)) return;
            effects.append(now);
            effectTimes.append(elapsed.elapsed());
            if (effects.size() != 1) return;
            followCoveredButton.stop();
            unrelatedMotion.stop();
            if (replacement && faultItem) muteClicks = faultItem->property("taken").toInt();
            if (original) {
                original->setObjectName(control);
                original->setEnabled(true);
            }
            if (auto* item = qobject_cast<QQuickItem*>(faultItem.data())) {
                item->setVisible(false);
                item->setObjectName("acceptance.retired");
            }
            if (fault == "late") {
                nextInput.target = original;
                window->installEventFilter(&nextInput);
            }
        });
        if (fault == "unrelated-motion") {
            QTRY_VERIFY2_WITH_TIMEOUT(moved >= 5, "The unrelated viewport is already scrolling when the tool starts", 1500);
            QVERIFY2(unrelatedViewport->property("contentY").toDouble() >= 120 && !find(control),
                     "The observed motion leaves the requested control absent");
        }
        const int movesAtSend = moved;
        elapsed.start();
        assistant->send("Create two new experiments with two separate ordinary actions.");
        const int loggedWaitLimit = shownControlLimit + shownObservationMargin;
        // The watchdog's 500 ms look period can elapse before it notices a stuck control.
        // The unrelated-motion effect must also reach the observer after ordinary fallback.
        constexpr int shownLookPeriod = 500;
        const int firstEffectLimit = fault == "working" ? shownItemLimit + shownObservationMargin
            : loggedWaitLimit + (fault == "unrelated-motion" ? shownLookPeriod : 0);
        constexpr int nextLimit = shownItemLimit + shownObservationMargin;
        QTRY_VERIFY2_WITH_TIMEOUT(firstRevealAt >= 0, "The local peer's first item reaches the app's shown-control route", 10000);
        QTRY_VERIFY2_WITH_TIMEOUT(!effectTimes.isEmpty(), "The initial effect must arrive within the shown step's limit", firstEffectLimit);
        const auto firstEffectDelay = effectTimes[0] - firstRevealAt;
        QVERIFY2(firstEffectDelay >= 0 && firstEffectDelay <= firstEffectLimit,
                 qPrintable(QStringLiteral("The first effect took %1 ms from control reveal after %2 ms of peer admission. The limit is %3 ms.")
                     .arg(firstEffectDelay).arg(firstRevealAt).arg(firstEffectLimit)));
        if (fault == "unrelated-motion" && firstEffectDelay >= 500)
            QVERIFY2(moved > movesAtSend, "Unrelated scroll motion continues while the stuck control is waiting");
        QTRY_COMPARE_WITH_TIMEOUT(count(), base + 2, nextLimit);
        QVERIFY2(effectTimes.size() == 2 && effectTimes[1] - effectTimes[0] <= nextLimit,
                 "The following shown item settles within its own total limit");
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 5000);
        QVERIFY2(assistant->showActions() && secondPress > 0, "The following tool really shows its genuine Create control");
        QCOMPARE(genuineClicks.size(), fault == "working" ? 2 : 1);
        if (fault == "working") QVERIFY2(firstPress > 0, "An ordinary working first step reaches the real pointer press");
        if (replacement) QVERIFY2(muteClicks == 1, "The mute control receives a genuine click and makes no project edit of its own");
        if (fault == "late") {
            QVERIFY2(held.press && held.release, "The late control retained both original device-stamped events");
            QVERIFY2(nextInput.press && nextInput.release && nextInput.press->pointingDevice() == held.press->pointingDevice() &&
                         nextInput.press->timestamp() > held.release->timestamp(),
                     "A later genuine action took a new input frame on the same device before replay");
            QVERIFY2(original && original->isVisible() && original->isEnabled(), "The late replay addresses a live original action");
            // The newly added rows moved the button. Preserve the retired
            // device and stamps at its current hit rectangle on both sides of the backstop.
            const auto replayRetiredClick = [&] {
                const auto centre = sceneBox(*original).center();
                for (const auto* saved : {held.press.get(), held.release.get()}) {
                    QMouseEvent replay(saved->type(), centre, window->mapToGlobal(centre),
                                       saved->button(), saved->buttons(), saved->modifiers(), saved->pointingDevice());
                    replay.setTimestamp(saved->timestamp());
                    QCoreApplication::sendEvent(window, &replay);
                }
                QCoreApplication::processEvents();
            };
            QVERIFY2(elapsed.elapsed() < shownItemLimit,
                     "The first replay follows retirement and precedes the original item's backstop");
            replayRetiredClick();
            QCOMPARE(genuineClicks.size(), 1);
            QCOMPARE(count(), base + 2);
            QTRY_VERIFY2_WITH_TIMEOUT(held.sincePress.elapsed() >= shownItemLimit,
                                     "The second replay is past the backstop even when measured from the original press", nextLimit);
            QVERIFY2(original && original->isVisible() && original->isEnabled(), "The real control still admits ordinary input at the second replay");
            replayRetiredClick();
            QCOMPARE(genuineClicks.size(), 1);
        }
        QCOMPARE(effects, (QList<decltype(count())>{base + 1, base + 2}));
        QCOMPARE(count(), base + 2);

        const auto errors = assistantErrors(log);
        QCOMPARE(errors.size(), fault == "working" ? 0 : 1);
        if (fault != "working") {
            const auto& error = errors.front();
            QVERIFY2(error.contains("tool create_experiment") && error.contains("control experiments.create"), qPrintable(error));
            QVERIFY2(error.contains("page experiment") && error.contains("group group.experiments"), qPrintable(error));
            const auto wait = QRegularExpression(R"(waited (\d+) ms)").match(error);
            QVERIFY2(wait.hasMatch() && wait.captured(1).toLongLong() <= loggedWaitLimit, qPrintable(error));
            if (fault == "absent" || fault == "unrelated-motion") QVERIFY2(error.contains("not in the window"), qPrintable(error));
            if (fault == "covered") QVERIFY2(error.contains("covered by") && error.contains("acceptance.cover"), qPrintable(error));
            if (fault == "disabled") QVERIFY2(error.contains("enabled no"), qPrintable(error));
        }
    }

    void saveAndReportSurviveLostCue_data() {
        QTest::addColumn<QString>("lostTool");
        QTest::newRow("save") << QStringLiteral("save_project");
        QTest::newRow("report") << QStringLiteral("show_report");
    }

    void saveAndReportSurviveLostCue() {
        QFETCH(QString, lostTool);
        const auto restore = offlinePeer({
            QJsonObject{{"tool", "save_project"}, {"arguments", QJsonObject{{"destination", "current"}}}},
            QJsonObject{{"tool", "show_report"}, {"arguments", QJsonObject{}}},
        });
        QTemporaryDir storage;
        QVERIFY2(storage.isValid(), "Save and Report require their own project and run log directory");
        const QDir copy(storage.filePath("editable-project"));
        QVERIFY2(copyEditableProject(copy), "Save operates on an independent, writable copy of a saved project");
        edi_app::RunLog log({storage.path(), {}, 3, 5'000'000, false});
        auto* previous = edi_app::RunLog::instance();
        edi_app::RunLog::install(&log);
        const auto restoreLog = qScopeGuard([&] { edi_app::RunLog::install(previous); });
        QVERIFY2(log.start({}), "A lost cue must be diagnosed in the ordinary run log");

        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY2(window, "The standard window exposes the real Save and Report controls");
        window->requestActivate();
        QVERIFY2(QTest::qWaitForWindowActive(window), "Shown input uses the active app window");
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY2(session && session->openProject(QUrl::fromLocalFile(copy.absolutePath())) && !session->needsSaveAs(),
                 "The ordinary Save route has an owned current directory and requires no human chooser");
        const QPointer<edi_app::ProjectViewModel> project(session->project());
        QVERIFY2(project, "Both operations apply to the same original project");
        const QString title = QStringLiteral("Acceptance edit saved after a lost cue");
        project->setTitle(title);
        const auto diskTitle = [&] {
            const auto saved = edi::load_project(copy.absolutePath().toStdString(), edi::ProjectLoadMode::Construction);
            return QString::fromStdString(saved.metadata.title);
        };
        QVERIFY2(project->modified() && diskTitle() != title, "The unsaved title distinguishes a real disk Save from a cue or reply");

        const auto find = [window](const QString& name) { return namedItem(window->contentItem(), name); };
        const QString saveName = QStringLiteral("appBar.button.save");
        const QString reportName = QStringLiteral("appBar.tab.report");
        QQuickItem* save = nullptr;
        QQuickItem* report = nullptr;
        QTRY_VERIFY2(take(save, find(saveName)) && save->isVisible() && save->isEnabled() &&
                         take(report, find(reportName)) && report->isVisible() && report->isEnabled(),
                     "Both genuine controls are usable before either cue is lost");
        QVERIFY2(!report->property("checked").toBool(), "Report starts unopened so its navigation is observable");
        const bool loseSave = lostTool == "save_project";
        const QPointer<QQuickItem> lost(loseSave ? save : report);
        const QPointer<QQuickItem> intact(loseSave ? report : save);
        auto* assistant = session->assistant();
        assistant->setActionWindow(window);
        assistant->setShowActions(true);
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        QPointF pointer;
        int lostCues = 0, lostPresses = 0, intactPresses = 0;
        QObject observer;
        connect(assistant, &edi_app::AssistantViewModel::actionPointerMoved, &observer, [&](const QPointF& position) {
            pointer = position;
            if (lostCues != 0 || !lost || !sceneBox(*lost).contains(pointer)) return;
            ++lostCues;
            // Lose the visual target between movement and press while the underlying Save/Report action remains valid.
            lost->setOpacity(0);
        });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerPressed, &observer, [&] {
            if (lost && sceneBox(*lost).contains(pointer)) ++lostPresses;
            if (intact && intact->isVisible() && sceneBox(*intact).contains(pointer)) ++intactPresses;
        });
        assistant->send("Save the current project, then open its Report preview.");
        constexpr int limit = shownItemLimit + shownObservationMargin;
        QTRY_COMPARE_WITH_TIMEOUT(lostCues, 1, limit);
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), limit);
        QVERIFY2(lost && lost->opacity() == 0 && assistant->showActions(), "The cue stays lost without turning off Show actions");
        QVERIFY2(project && session->project() == project && !project->modified(), "The ordinary Save settles on the original project");
        QCOMPARE(diskTitle(), title);
        QCOMPARE(lostPresses, 0);
        QCOMPARE(intactPresses, 1);
        QQuickItem* preview = nullptr;
        QTRY_VERIFY2(report->property("checked").toBool() && take(preview, find("report.preview")) &&
                         preview->isVisible() && preview->property("drawn").toBool() &&
                         preview->property("report").value<QObject*>() == project->report(),
                     "Report opens the original project's live preview");
        const auto errors = assistantErrors(log);
        QCOMPARE(errors.size(), 1);
        QVERIFY2(errors.front().contains("tool " + lostTool) &&
                     errors.front().contains("control " + (loseSave ? saveName : reportName)),
                 qPrintable(errors.front()));
    }

    void questionsRequireCards() {
        const QString question = QStringLiteral("Which probe did the measurement use?");
        const QJsonArray choices{QJsonObject{{"label", "Neutrons"}, {"description", "Use the neutron probe."}},
                                 QJsonObject{{"label", "X-rays"}, {"description", "Use the X-ray probe."}}};
        const QJsonArray questions{QJsonObject{{"id", "probe"}, {"header", "Probe"}, {"question", question},
                                             {"isOther", true}, {"isSecret", false}, {"options", choices}}};
        const QJsonArray sequence{QJsonObject{{"tool", "request_user_input"}, {"arguments", QJsonObject{{"questions", questions}}}}};
        QTemporaryDir storage;
        QVERIFY2(storage.isValid(), "The local question peer needs its own runtime instruction receipt");
        const auto path = storage.filePath("instructions.txt");
        const auto restore = offlinePeer(sequence, path);
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY2(window, "The real question actor runs in the ordinary app window");
        window->requestActivate();
        QVERIFY2(QTest::qWaitForWindowActive(window), "The question card must accept ordinary pointer input");
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY2(session && (session->hasProject() || session->startUntitledProject()) && session->untitled(),
                 "The question actor must use untitled work without a saved fixture directory");
        QQuickItem* projectTab = nullptr;
        QTRY_VERIFY2(take(projectTab, namedItem(window->contentItem(), "appBar.tab.project")) && projectTab->isEnabled(),
                     "The ordinary Project page can host the Assistant panel");
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                          projectTab->mapToScene(projectTab->boundingRect().center()).toPoint());
        auto* assistant = session->assistant();
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        assistant->send("Set up a powder measurement. The radiation probe is unspecified.");
        QQuickItem* option = nullptr;
        const auto cardReady = [&] {
            const auto* popup = window->findChild<QObject*>("assistant.popup");
            return popup && popup->property("opened").toBool() &&
                take(option, namedItem(window->contentItem(), "assistant.question.option.0")) &&
                option->isVisible() && option->isEnabled() &&
                QRectF(0, 0, window->width(), window->height()).contains(sceneBox(*option).center());
        };
        QTRY_VERIFY2_WITH_TIMEOUT(cardReady(), "The question panel rests and option zero is inside the window", 10000);
        auto* second = namedItem(window->contentItem(), "assistant.question.option.1");
        auto* free = namedItem(window->contentItem(), "assistant.question.answer");
        QVERIFY2(second && second->isVisible() && free && free->isVisible(),
                 "The card offers both choices and a free answer on the same visible surface");
        const auto hasLabel = [](const QQuickItem* control, const QString& label) {
            const auto descendants = control->findChildren<QQuickItem*>();
            return std::any_of(descendants.cbegin(), descendants.cend(), [&](const auto* item) {
                return item->isVisible() && item->property("text").toString().simplified() == label;
            });
        };
        QVERIFY2(hasLabel(option, "1. Neutrons") && hasLabel(second, "2. X-rays"),
                 "The rendered choices retain the original local peer's options");
        QCOMPARE(assistant->pendingQuestion().text, question);
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier, sceneBox(*option).center().toPoint());
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 10000);
        const auto answer = QJsonDocument::fromJson(fileText(path + ".answer").toUtf8()).object()
            .value("answers").toObject().value("probe").toObject().value("answers").toArray();
        QCOMPARE(answer, QJsonArray{"Neutrons"});

        const auto policy = fileText(path);
        QVERIFY2(policy.contains("Ask every question with the request_user_input tool") &&
                 policy.contains("never request_user_input_async or plain text") &&
                 policy.contains("Where that tool is not offered, say so once, name what is missing and stop"),
                 "The actual runtime contract requires clickable questions and stops when the card tool is unavailable");
        const auto skill = fileText(QString::fromUtf8(EDI_SOURCE_DIR) + "/data/assistant/skills/project-assistance/SKILL.md");
        QVERIFY2(skill.contains("A question is always a card with options to click, never plain text") &&
                 skill.contains("If request_user_input is not offered, say once that questions cannot be asked here and which points are missing, then stop"),
                 "The shipped project skill must also close the plain-question fallback");
        QVERIFY2(!policy.contains("plain final question", Qt::CaseInsensitive) &&
                 !skill.contains("plain final question", Qt::CaseInsensitive),
                 "Neither instruction source may authorize the old plain question escape");
    }

    void fallbackReturnsToShownInsideABatchedTool() {
        constexpr double length = 4.01, adp = 0.65;
        constexpr int stageDelay = 5500;
        const QJsonArray values{
            QJsonObject{{"path", "structure.cell.length_a"}, {"value", length}},
            QJsonObject{{"path", "structure.atom_sites[La].adp_iso"}, {"value", adp}},
        };
        const auto restore = offlinePeer({QJsonObject{{"tool", "set_parameters"}, {"arguments", QJsonObject{{"values", values}}}}});
        QTemporaryDir storage;
        QVERIFY2(storage.isValid(), "The batch needs its own project and run log directory");
        const QDir copy(storage.filePath("editable-project"));
        QVERIFY2(copyEditableProject(copy), "The batch has a writeable copy of the independent input files");
        edi_app::RunLog log({storage.path(), {}, 3, 5'000'000, false});
        auto* previous = edi_app::RunLog::instance();
        edi_app::RunLog::install(&log);
        const auto restoreLog = qScopeGuard([&] { edi_app::RunLog::install(previous); });
        QVERIFY2(log.start({}), "The batch's ordinary run log must be writable");
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY2(window, "The batched native edit uses the real app window");
        window->requestActivate();
        QVERIFY2(QTest::qWaitForWindowActive(window), "Shown batch input uses the active app window");
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY2(session && session->openProject(QUrl::fromLocalFile(copy.absolutePath())),
                 "The isolated copy of the independently saved structure supplies both parameters");
        auto* project = session->project();
        QVERIFY2(project, "The batch retains its current original project");
        auto* a = project->parameterNamed("lbco.cell.length_a");
        auto* b = project->parameterNamed("lbco.atom_site.La.adp_iso");
        QVERIFY2(a && b && a->value() != length && b->value() != adp, "Each test edit has an independent original value");
        auto* assistant = session->assistant();
        assistant->setActionWindow(window);
        assistant->setShowActions(true);
        const auto find = [window](const QString& name) { return namedItem(window->contentItem(), name); };
        QQuickItem* tab = nullptr;
        QTRY_VERIFY2(take(tab, find("appBar.tab.structure")) && tab->isEnabled(), "The Structure page exposes the original cell field");
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier, tab->mapToScene(tab->boundingRect().center()).toPoint());
        QQuickItem* group = nullptr;
        QTRY_VERIFY2(take(group, find("group.cell")) && group->isVisible(), "The original cell group is present");
        QVERIFY2(group->setProperty("collapsed", false), "Opening the cell group materializes its numeric fields");
        QQuickItem* first = nullptr;
        QTRY_VERIFY2(take(first, find("cell.length_a")) && first->isVisible(), "The actual first numeric field is available before the fault");
        first->setEnabled(false);
        QVERIFY2(!first->isEnabled(), "Only the first editor is disabled for the batched operation");
        QQuickItem* adpGroup = nullptr;
        const QString groupName = QStringLiteral("group.atom_site_aniso");
        QTRY_VERIFY2(take(adpGroup, find(groupName)) && adpGroup->isVisible(),
                     "The real Atomic displacement group is available for a timed reveal");
        QVERIFY2(adpGroup->setProperty("collapsed", true) && adpGroup->property("collapsed").toBool(),
                 "The second item must open the Atomic displacement group itself");
        const QPointer<QQuickItem> heldGroup(adpGroup);
        heldGroup->setObjectName("acceptance.heldAdpGroup");
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected() && assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        QPointF point;
        QElapsedTimer elapsed;
        qint64 firstEffect = -1, secondEffect = -1, groupShown = -1, cellShown = -1, editorShown = -1;
        bool editorRestored = false;
        QObject observer;
        connect(project, &edi_app::ProjectViewModel::edited, &observer, [&] {
            if (firstEffect < 0 && a->value() == length) {
                firstEffect = elapsed.elapsed();
                QTimer::singleShot(stageDelay, &observer, [heldGroup, groupName] {
                    if (heldGroup) heldGroup->setObjectName(groupName);
                });
            }
            if (secondEffect < 0 && b->value() == adp) secondEffect = elapsed.elapsed();
        });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerMoved, &observer, [&](const QPointF& position) { point = position; });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerPressed, &observer, [&] {
            if (firstEffect < 0 || b->value() == adp) return;
            // The real group reveal and the cell cue must make progress between the two holds.
            auto* title = heldGroup ? heldGroup->property("titleArea").value<QQuickItem*>() : nullptr;
            if (groupShown < 0 && title && title->isVisible() && sceneBox(*title).contains(point))
                groupShown = elapsed.elapsed();
            QPointer<QQuickItem> cell(find("atomSiteAdp.iso.0"));
            if (cellShown < 0 && cell && cell->isVisible() && sceneBox(*cell).contains(point)) {
                const auto editorComponent = cell->property("editorComponent");
                if (editorComponent.value<QQmlComponent*>() &&
                    cell->setProperty("editorComponent", QVariant::fromValue(static_cast<QQmlComponent*>(nullptr)))) {
                    cellShown = elapsed.elapsed();
                    QTimer::singleShot(stageDelay, &observer, [cell, editorComponent, &editorRestored] {
                        if (cell) editorRestored = cell->setProperty("editorComponent", editorComponent);
                    });
                }
            }
            // Shown input cues the actual popup's editor after its own staged availability.
            if (auto* editor = find("atomSiteAdp.iso.0.popup.value"); editor &&
                editorRestored && editor->isVisible() && editor->isEnabled() &&
                sceneBox(*editor).contains(point))
                editorShown = elapsed.elapsed();
        });
        constexpr int itemLimit = shownItemLimit + shownObservationMargin;
        elapsed.start();
        assistant->send("Set the two specified independent parameter values.");
        QTRY_VERIFY2_WITH_TIMEOUT(firstEffect >= 0, "The disabled field falls back within the first item's total limit", itemLimit);
        QTRY_VERIFY2_WITH_TIMEOUT(secondEffect >= 0, "The next shown edit completes within its own total limit", itemLimit);
        QVERIFY2(firstEffect <= itemLimit && firstEffect <= secondEffect && secondEffect - firstEffect <= itemLimit,
                 "Both effects arrive in order within their respective item limits");
        QCOMPARE(a->value(), length);
        QCOMPARE(b->value(), adp);
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 5000);
        const auto errors = assistantErrors(log);
        QCOMPARE(errors.size(), 1);
        QVERIFY2(errors.front().contains("tool set_parameters control cell.length_a"),
                 "The batched operation really took the first field's diagnosed fallback");
        QVERIFY2(firstEffect < groupShown && groupShown <= cellShown && cellShown < editorShown && editorShown <= secondEffect,
                 "After fallback the genuine group, cell, and popup-editor cues precede the second model effect");
        QVERIFY2(editorShown - firstEffect > shownControlLimit,
                 "The working second item genuinely progresses past the stuck-control limit without another fallback");
    }

    void shippedBinaryExcludesAssistantDemo() {
        const QDir bin(QCoreApplication::applicationDirPath());
        QFile product;
        for (const auto* name : {"edi_app", "edi_app.exe", "EasyDiffraction", "EasyDiffraction.exe",
                                 "edi_app.app/Contents/MacOS/edi_app", "EasyDiffraction.app/Contents/MacOS/EasyDiffraction"}) {
            product.setFileName(bin.filePath(QString::fromLatin1(name)));
            if (product.open(QIODevice::ReadOnly)) break;
        }
        QVERIFY2(product.isOpen(), "The boundary gate inspects an actual product binary next to the app test target");
        auto* mapped = product.map(0, product.size());
        QVERIFY2(mapped, qPrintable(product.errorString()));
        const auto unmap = qScopeGuard([&] { product.unmap(mapped); });
        const QByteArrayView executable(reinterpret_cast<const char*>(mapped), product.size());
        // Public demo selector, former entry and environment key. The Qt
        // launcher used QStringLiteral, so scan UTF-16 as well as ordinary symbols.
        for (const QByteArray token : {"assistant-tools", "start_assistant_demo", "EDI_ASSISTANT_PEER_DIR"}) {
            QByteArray utf16;
            for (const char byte : token) { utf16.append(byte); utf16.append('\0'); }
            QVERIFY2(!executable.contains(token) && !executable.contains(utf16), token.constData());
        }
    }
#endif
    void skillsReplayCurrentLoadMenus() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi::Project empty;
        empty.structures.clear();
        empty.experiments.clear();
        edi_app::ProjectViewModel project(std::move(empty), nullptr);
        engine.rootContext()->setContextProperty("testProject", &project);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtQuick.Controls
            import edi.app
            ApplicationWindow {
                width: 800; height: 1000; visible: true
                ExperimentsGroup { project: testProject; width: 700 }
                StructuresGroup { project: testProject; width: 700; y: 450 }
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window);
        window->requestActivate();
        QVERIFY(QTest::qWaitForWindowActive(window));
        edi_app::AssistantWidgetInput input(*window);
        QString diagnostic;
        const auto findItem = [&](const char* name) {
            const auto walk = [&](QQuickItem* item, auto&& self) -> QQuickItem* {
                if(item->objectName() == name) return item;
                for(auto* child : item->childItems())
                    if(auto* found = self(child, self)) return found;
                return nullptr;
            };
            if(auto* item = walk(window->contentItem(), walk)) return item;
            return root->findChild<QQuickItem*>(name);
        };
        const auto click = [&](const char* name) {
            auto* target = findItem(name);
            if (!target) { diagnostic = QString("Missing %1").arg(name); return false; }
            bool done = false, delivered = false;
            edi_app::AssistantWidgetInput::Request request;
            request.kind = edi_app::AssistantWidgetInput::Kind::Navigate;
            request.target = target;
            request.current = [target, window] { return target->window() == window; };
            request.restoreCurrent = request.current;
            request.prepareCommit = [] { return true; };
            request.finishCommit = [] {};
            request.completed = [&](bool ok, const QString& message, edi_app::ControlCause) {
                delivered = ok; diagnostic = message; done = true;
            };
            if (!QTest::qWaitFor([&] { return input.usableTarget(*target); }, 3000)) {
                diagnostic = QString("Unavailable %1 (visible=%2 enabled=%3 sameWindow=%4)")
                    .arg(name).arg(target->isVisible()).arg(target->isEnabled()).arg(target->window() == window);
                return false;
            }
            try { input.start(std::move(request)); }
            catch (const std::exception& error) { diagnostic = QString::fromUtf8(error.what()); return false; }
            const bool completed = QTest::qWaitFor([&] { return done; }, 5000);
            if (!completed) input.cancel();
            return completed && delivered;
        };
        auto* dataFile = root->findChild<QQuickItem*>("experiments.load.dataFile");
        QVERIFY(dataFile);
        QCOMPARE(dataFile->property("text").toString(), QString("File…"));
        QVERIFY2(click("experiments.create"), qPrintable(diagnostic));
        QTRY_VERIFY(project.currentExperiment());
        auto* group = root->findChild<QQuickItem*>("group.experiments");
        QVERIFY(group);
        group->setProperty("collapsed", true);
        auto* title = qobject_cast<QQuickItem*>(group->property("titleArea").value<QObject*>());
        QVERIFY(title);
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                          title->mapToScene(QPointF(title->width() / 2, title->height() / 2)).toPoint());
        QTRY_VERIFY(!group->property("collapsed").toBool());
        QTRY_VERIFY(findItem("experiments.loadData.0"));
        QVERIFY2(click("experiments.loadData.0"), qPrintable(diagnostic));
        auto* menu = root->findChild<QObject*>("experiments.load.dataMenu");
        QVERIFY(menu);
        QTRY_VERIFY(menu->property("visible").toBool());
        QCOMPARE(menu->property("target").value<QObject*>(), project.currentExperiment());
        QVERIFY(dataFile->isEnabled());
        QVERIFY2(click("experiments.load.dataWeb"), qPrintable(diagnostic));
        auto* popup = root->findChild<QObject*>("onlineLoad");
        QVERIFY(popup);
        QTRY_VERIFY(popup->property("visible").toBool());
        QCOMPARE(popup->property("kind").toString(), QString("data"));
        QVERIFY(root->findChild<QObject*>("onlineLoad.source"));
        QVERIFY(root->findChild<QObject*>("onlineLoad.search"));
        QVERIFY(QMetaObject::invokeMethod(popup, "close"));
        QTRY_VERIFY(!popup->property("visible").toBool());
        auto* structures = root->findChild<QQuickItem*>("group.structures");
        QVERIFY(structures);
        if(structures->property("collapsed").toBool()) {
            auto* structureTitle = qobject_cast<QQuickItem*>(structures->property("titleArea").value<QObject*>());
            QVERIFY(structureTitle);
            QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                              structureTitle->mapToScene(QPointF(structureTitle->width() / 2, structureTitle->height() / 2)).toPoint());
        }
        QTRY_VERIFY(!structures->property("collapsed").toBool());
        QVERIFY2(click("structures.load"), qPrintable(diagnostic));
        auto* structureFile = root->findChild<QQuickItem*>("structures.load.file");
        QVERIFY(structureFile);
        QVERIFY(structureFile->isVisible());
        QVERIFY2(click("structures.load.web"), qPrintable(diagnostic));
        const auto popups = root->findChildren<QObject*>("onlineLoad");
        bool structurePopup = false;
        for (auto* original : popups)
            structurePopup |= original->property("visible").toBool() && original->property("kind") == "structure";
        QVERIFY(structurePopup);
    }
#ifndef __EMSCRIPTEN__
    void keyedAliasAndBackgroundNamingShown_data() {
        QTest::addColumn<bool>("alias");
        QTest::newRow("background-position-button") << false;
        QTest::newRow("keyed-atom-alias") << true;
    }
    void keyedAliasAndBackgroundNamingShown() {
        QFETCH(bool, alias);
        const auto previousPeer = qgetenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE");
        const auto previousArguments = qgetenv("EDI_UI_LOAD_ARGUMENTS");
        const auto previousTool = qgetenv("EDI_UI_TOOL");
        const auto restore = qScopeGuard([&] {
            for (const auto& entry : {qMakePair("EDI_CODEX_DEVELOPMENT_EXECUTABLE", previousPeer),
                     qMakePair("EDI_UI_LOAD_ARGUMENTS", previousArguments), qMakePair("EDI_UI_TOOL", previousTool)}) {
                if (entry.second.isNull()) qunsetenv(entry.first);
                else qputenv(entry.first, entry.second);
            }
        });
        qputenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE", QCoreApplication::applicationFilePath().toUtf8());
        qputenv("EDI_UI_TOOL", alias ? "add_relations" : "edit_background");
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window);
        window->requestActivate();
        QVERIFY(QTest::qWaitForWindowActive(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        if (!session->hasProject()) QVERIFY(session->startUntitledProject());
        auto* project = session->project();
        QVERIFY(project->loadStructure(QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/tests/fixtures/assistant_save_replay/lbco.cif")));
        project->createExperiment();
        QTRY_VERIFY(project->currentExperiment());
        QVERIFY(project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/tests/fixtures/plain_data/cwl/three_columns/pattern.xye")));
        auto* background = project->currentExperiment()->background();
        background->append();
        QVERIFY(background->count() > 0);
        QVERIFY(background->setId(0, "manual-anchor"));
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating() && project->viewSettled(), 10000);
        auto* assistant = session->assistant();
        assistant->setActionWindow(window);
        assistant->setShowActions(true);
        const auto find = [&](const QString& name) {
            const auto walk = [&](QQuickItem* item, auto&& self) -> QQuickItem* {
                if (item->objectName() == name) return item;
                for (auto* child : item->childItems()) if (auto* found = self(child, self)) return found;
                return nullptr;
            };
            return walk(window->contentItem(), walk);
        };
        QString path, uniqueName;
        for (const auto& entry : edi::parameter_entries(*project->assistantProject())) {
            if (!QString::fromStdString(entry.path).contains("atom_sites[La].adp_iso")) continue;
            path = QString::fromStdString(entry.path);
            for (const auto& slot : edi::named_slots(*project->assistantProject()))
                if (slot.parameter == entry.parameter) uniqueName = QString::fromStdString(slot.unique_name);
        }
        QCOMPARE(path, QString("structure.atom_sites[La].adp_iso"));
        QCOMPARE(uniqueName, QString("lbco.atom_site.La.adp_iso"));
        const QJsonObject arguments = alias
            ? QJsonObject{{"purpose", "Alias the La isotropic displacement"},
                {"aliases", QJsonArray{QJsonObject{{"id", "la_adp"}, {"path", path}}}}, {"constraints", QJsonArray{}}}
            : QJsonObject{{"purpose", "Name background points by position"},
                {"experiment", project->experiments()->text(0, "name")}, {"operation", "name_from_positions"}};
        qputenv("EDI_UI_LOAD_ARGUMENTS", QJsonDocument(arguments).toJson(QJsonDocument::Compact));
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected(), qPrintable(assistant->lastError()), 10000);
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        QPointF pointer;
        bool buttonPressed = false, selectedEntryPressed = false;
        QString typed;
        QObject observer;
        connect(assistant, &edi_app::AssistantViewModel::actionPointerMoved, &observer,
            [&](const QPointF& point) { pointer = point; });
        QTimer searchObserver;
        const auto sampleSearch = [&] {
            auto* combo = find("alias.parameter.0");
            auto* popup = combo ? combo->property("popup").value<QObject*>() : nullptr;
            auto* content = popup ? popup->property("contentItem").value<QObject*>() : nullptr;
            auto* header = content ? content->property("headerItem").value<QObject*>() : nullptr;
            auto* search = header ? header->findChild<QObject*>("comboBox.search") : nullptr;
            if (search && !search->property("text").toString().isEmpty())
                typed = search->property("text").toString();
        };
        connect(&searchObserver, &QTimer::timeout, &observer, sampleSearch);
        searchObserver.start(10);
        connect(assistant, &edi_app::AssistantViewModel::actionPointerPressed, &observer, [&] {
            sampleSearch();
            auto* button = find("background.namePoints");
            if (button && button->isVisible() &&
                QLineF(pointer, button->mapToScene(QPointF(button->width() / 2, button->height() / 2))).length() < 1)
                buttonPressed = true;
            auto* combo = find("alias.parameter.0");
            auto* popup = combo ? combo->property("popup").value<QObject*>() : nullptr;
            auto* content = popup ? popup->property("contentItem").value<QObject*>() : nullptr;
            QQuickItem* entry = nullptr;
            const int option = combo ? static_cast<int>(combo->property("names").toStringList().indexOf(uniqueName)) : -1;
            if (content && option >= 0 && typed == uniqueName &&
                QMetaObject::invokeMethod(content, "itemAtIndex", Q_RETURN_ARG(QQuickItem*, entry), Q_ARG(int, option)) &&
                entry && entry->isVisible() && entry->mapRectToScene(entry->boundingRect()).contains(pointer))
                selectedEntryPressed = true;
        });
        assistant->send(alias ? "Alias the La atom isotropic displacement as la_adp." : "Name the background points from their positions.");
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 30000);
        searchObserver.stop();
        if (alias) {
            QCOMPARE(typed, uniqueName);
            QVERIFY(selectedEntryPressed);
            auto* combo = find("alias.parameter.0");
            QVERIFY(combo);
            const auto option = combo->property("names").toStringList().indexOf(uniqueName);
            QVERIFY(option >= 0);
            QCOMPARE(combo->property("currentIndex").toInt(), option);
            QCOMPARE(combo->property("model").toStringList()[option].section(" · ", 1), uniqueName);
            const auto& aliases = project->assistantProject()->aliases;
            QCOMPARE(aliases.size(), std::size_t(1));
            QCOMPARE(QString::fromStdString(aliases[0]->id.value()), QString("la_adp"));
            QCOMPARE(QString::fromStdString(aliases[0]->parameter_unique_name.value()), uniqueName);
            qInfo().noquote() << "Shown alias search:" << typed << "selected:" << uniqueName;
        } else {
            QVERIFY2(buttonPressed, qPrintable(assistant->lastError()));
            const auto expected = edi::position_point_ids(*project->currentExperiment()->experiment());
            for (std::size_t i = 0; i < expected.size(); ++i)
                QCOMPARE(background->text(static_cast<int>(i), "id"), QString::fromStdString(expected[i]));
            qInfo() << "Shown background naming: cue pressed background.namePoints; position IDs applied";
        }
        assistant->clearHistory();
    }
    void loadDataReplaysShownActions_data() {
        QTest::addColumn<bool>("show");
        QTest::newRow("shown") << true;
        QTest::newRow("ordinary") << false;
    }
    void loadDataReplaysShownActions() {
        QFETCH(bool, show);
        const auto previousPeer = qgetenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE");
        const auto previousArguments = qgetenv("EDI_UI_LOAD_ARGUMENTS");
        const auto restore = qScopeGuard([&] {
            if (previousPeer.isNull()) qunsetenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE");
            else qputenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE", previousPeer);
            if (previousArguments.isNull()) qunsetenv("EDI_UI_LOAD_ARGUMENTS");
            else qputenv("EDI_UI_LOAD_ARGUMENTS", previousArguments);
        });
        qputenv("EDI_CODEX_DEVELOPMENT_EXECUTABLE", QCoreApplication::applicationFilePath().toUtf8());
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        edi_app::test::assistant_defaults();
        QQmlComponent component(&engine);
        component.setData("import edi.app\nMain { width: 1400; height: 1000; visible: true }", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window);
        window->requestActivate();
        QVERIFY(QTest::qWaitForWindowActive(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        if (!session->hasProject()) QVERIFY(session->startUntitledProject());
        auto* project = session->project();
        QVERIFY(project->loadStructure(QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/tests/fixtures/assistant_save_replay/lbco.cif")));
        project->createExperiment();
        QTRY_VERIFY(project->currentExperiment());
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating() && project->viewSettled(), 10000);
        auto* assistant = session->assistant();
        assistant->setActionWindow(window);
        assistant->setShowActions(show);
        const auto find = [&](const QString& name) {
            const auto walk = [&](QQuickItem* item, auto&& self) -> QQuickItem* {
                if (item->objectName() == name) return item;
                for (auto* child : item->childItems()) if (auto* found = self(child, self)) return found;
                return nullptr;
            };
            if (auto* item = walk(window->contentItem(), walk)) return item;
            return root->findChild<QQuickItem*>(name);
        };
        auto* tab = find("appBar.tab.experiment");
        QVERIFY(tab);
        QTRY_VERIFY(tab->isEnabled());
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
            tab->mapToScene(QPointF(tab->width() / 2, tab->height() / 2)).toPoint());
        auto* pageLoader = tab->property("page").value<QObject*>();
        QVERIFY(pageLoader);
        QObject* page = nullptr;
        QTRY_VERIFY(take(page, pageLoader->property("item").value<QObject*>()));
        QVERIFY(QMetaObject::invokeMethod(page, "showSidebarTab", Q_ARG(QVariant, QVariant(false))));
        QQuickItem* table = nullptr;
        QTRY_VERIFY(take(table, find("experiments.list")));
        auto* group = table->parentItem();
        while (group && !group->property("collapsed").isValid()) group = group->parentItem();
        QVERIFY(group);
        QVERIFY(group->setProperty("collapsed", true));
        QTRY_VERIFY(group->property("collapsed").toBool());
        QTemporaryDir selected;
        QVERIFY(selected.isValid());
        const auto path = selected.filePath("pattern.xye");
        QVERIFY(QFile::copy(QString::fromUtf8(EDI_SOURCE_DIR) + "/tests/fixtures/plain_data/cwl/three_columns/pattern.xye", path));
        const auto token = assistant->beginFileSelection();
        QVERIFY2(!token.isEmpty(), qPrintable(assistant->lastError()));
        QVERIFY2(assistant->addSelectedFiles(token, {QUrl::fromLocalFile(path)}), qPrintable(assistant->lastError()));
        const auto file = assistant->selectedFiles()->text(0, "id");
        QVERIFY(!file.isEmpty());
        const QJsonObject arguments{{"purpose", "Load the selected measurements"},
            {"experiment", project->experiments()->text(0, "name")}, {"file_id", file}};
        qputenv("EDI_UI_LOAD_ARGUMENTS", QJsonDocument(arguments).toJson(QJsonDocument::Compact));
        assistant->signIn();
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->connected(), qPrintable(assistant->lastError()), 10000);
        QTRY_VERIFY2_WITH_TIMEOUT(assistant->draftAdmissionReady(), qPrintable(assistant->lastError()), 10000);
        QStringList observed;
        QPointF pointer;
        QObject observer;
        connect(assistant, &edi_app::AssistantViewModel::actionPointerMoved, &observer, [&](const QPointF& point) { pointer = point; });
        connect(assistant, &edi_app::AssistantViewModel::actionPointerPressed, &observer, [&] {
            const auto hits = [&](QQuickItem* item) {
                return item && item->isVisible() && item->mapRectToScene(item->boundingRect()).contains(pointer);
            };
            auto* title = qobject_cast<QQuickItem*>(group->property("titleArea").value<QObject*>());
            if (hits(title)) observed << "unfold";
            else if (hits(find("experiments.loadData.0"))) observed << "load-data";
            else if (hits(find("experiments.load.dataFile"))) observed << "from-file";
        });
        const auto loaded = [&] {
            return !project->assistantProject()->experiments[0]->calculation_only;
        };
        connect(project, &edi_app::ProjectViewModel::edited, &observer, [&] {
            if (loaded() && !observed.contains("loaded")) observed << "loaded";
        });
        assistant->send("Load the attached measurements into this experiment.");
        QTRY_VERIFY2_WITH_TIMEOUT(loaded(), qPrintable(assistant->lastError() + " cues=" + observed.join(",")), 20000);
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 10000);
        QVERIFY(observed.contains("loaded"));
        const QStringList expected = show ? QStringList{"unfold", "load-data", "from-file", "loaded"} : QStringList{"loaded"};
        QCOMPARE(observed, expected);
        qInfo().noquote() << "load_data" << (show ? "shown:" : "ordinary:") << observed.join(" -> ");
        // Compare the displayed measurement with the same file through the user's ordinary loader.
        auto* actual = project->currentExperiment()->pattern();
        project->createExperiment();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating() && project->viewSettled(), 10000);
        QVERIFY(project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(path)));
        auto* manual = project->currentExperiment()->pattern();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating() && project->viewSettled(), 10000);
        QTRY_COMPARE(actual->rowCount(), manual->rowCount());
        QVERIFY(actual->rowCount() > 0);
        for (int row = 0; row < actual->rowCount(); ++row)
            for (const int role : {edi_app::PatternModel::XRole, edi_app::PatternModel::IntensityMeasRole, edi_app::PatternModel::IntensityMeasSuRole})
                QCOMPARE(actual->data(actual->index(row), role), manual->data(manual->index(row), role));
        assistant->clearHistory();
    }
#endif
    void aliasSearchTypesPlainNameAndSelectsDecoratedEntry() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtQuick.Controls
            import edi.app
            ApplicationWindow {
                width: 800; height: 600; visible: true
                SearchableComboBox {
                    objectName: "alias.parameter.0"
                    searchThreshold: 0
                    x: 40; y: 40; width: 500
                    readonly property var names: ["phase.cell.length_a", "phase.cell.length_b"]
                    model: ["cube a · phase.cell.length_a", "cube b · phase.cell.length_b"]
                    currentIndex: 0
                }
            }
        )", QUrl("qrc:/alias-search.qml"));
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window);
        QVERIFY(QTest::qWaitForWindowActive(window));
        auto* target = root->findChild<QQuickItem*>("alias.parameter.0");
        QVERIFY(target);
        edi_app::AssistantWidgetInput input(*window);
        QString typed, diagnostic;
        bool done = false, delivered = false;
        edi_app::AssistantWidgetInput::Request request;
        request.kind = edi_app::AssistantWidgetInput::Kind::SearchChoice;
        request.target = target;
        request.option = 1;
        request.value = "phase.cell.length_b";
        request.current = [target, window] { return target->window() == window; };
        request.restoreCurrent = request.current;
        request.prepareCommit = [&] {
            auto* popup = target->property("popup").value<QObject*>();
            auto* content = popup ? popup->property("contentItem").value<QObject*>() : nullptr;
            auto* header = content ? content->property("headerItem").value<QObject*>() : nullptr;
            auto* search = header ? header->findChild<QObject*>("comboBox.search") : nullptr;
            typed = search ? search->property("text").toString() : QString();
            return true;
        };
        request.finishCommit = [] {};
        request.completed = [&](bool ok, const QString& message, edi_app::ControlCause) {
            delivered = ok; diagnostic = message; done = true;
        };
        input.start(std::move(request));
        QVERIFY(QTest::qWaitFor([&] { return done; }, 10000));
        QVERIFY2(delivered, qPrintable(diagnostic));
        QCOMPARE(typed, QString("phase.cell.length_b"));
        QCOMPARE(target->property("currentIndex").toInt(), 1);
    }
    void testModelDefaultsAndExplicitChoice() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QSettings settings(edi_app::settings_file_path(), QSettings::IniFormat);
        const QString key = "Assistant/Providers/chatgpt/selection";
        settings.remove(key);
        settings.sync();
        edi_app::test::assistant_defaults();
        settings.sync();
        QCOMPARE(settings.value(key).toStringList(), (QStringList{"gpt-6-luna", "medium"}));
        const QStringList explicitChoice{"gpt-6.1-sol", "high"};
        settings.setValue(key, explicitChoice);
        settings.sync();
        edi_app::test::assistant_defaults();
        settings.sync();
        QCOMPARE(settings.value(key).toStringList(), explicitChoice);
    }
    void downloadLinkMatchesOrdinaryStyle_data() {
        QTest::addColumn<bool>("dark");
        QTest::newRow("light") << false;
        QTest::newRow("dark") << true;
    }
    void downloadLinkMatchesOrdinaryStyle() {
        QFETCH(bool, dark);
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import edi.app
            import EasyApplication.Gui.Style as EaStyle
            Item {
                width: 800; height: 180
                function useDarkTheme(dark) { EaStyle.Colors.theme = dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme }
                readonly property color linkColor: download.foregroundColor()
                readonly property color referenceColor: reference.foregroundColor()
                readonly property bool linkHovered: download.hovered
                AssistantDownloadLink { id: download; x: 20; y: 20 }
                IconLink { id: reference; x: 20; y: 100; text: "Ordinary About-style link" }
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        QVERIFY(QMetaObject::invokeMethod(root.data(), "useDarkTheme", Q_ARG(QVariant, dark)));
        auto* link = root->findChild<QQuickItem*>("assistant.desktopOnly.download");
        QVERIFY(link);
        QCOMPARE(link->property("fontIcon").toString(), QString("external-link-alt"));
        QCOMPARE(link->property("text").toString(), QString("Open the desktop download page"));
        QCOMPARE(root->property("linkColor"), root->property("referenceColor"));
        const auto normal = root->property("linkColor");
        QQuickWindow window;
        window.resize(800, 180);
        auto* item = qobject_cast<QQuickItem*>(root.data());
        item->setParentItem(window.contentItem());
        const auto detach = qScopeGuard([item] { item->setParentItem(nullptr); });
        window.show();
        QVERIFY(QTest::qWaitForWindowExposed(&window));
        window.requestActivate();
        QVERIFY(QTest::qWaitForWindowActive(&window));
        QTest::mouseMove(&window, QPoint(790, 170));
        QTest::mouseMove(&window, link->mapToScene(QPointF(link->width() / 2, link->height() / 2)).toPoint());
        QTRY_VERIFY2(root->property("linkHovered").toBool(), qPrintable(QString("size=%1x%2 visible=%3 enabled=%4 hover=%5 active=%6").arg(link->width()).arg(link->height()).arg(link->isVisible()).arg(link->isEnabled()).arg(link->property("hoverEnabled").toBool()).arg(window.isActive())));
        QTRY_VERIFY(root->property("linkColor") != normal);
    }
    void exampleOpeningCoversDownloadAndPageBuild() {
        QTemporaryDir source;
        QVERIFY(source.isValid());
        const QString archive = source.filePath("project.zip");
        QVERIFY(QFile::copy(QString::fromUtf8(EDI_SOURCE_DIR)
            + "/tests/fixtures/project_archive/pd-neut-cwl_cosio-d20_scan-3f.zip", archive));
        QFile bytesFile(archive);
        QVERIFY(bytesFile.open(QIODevice::ReadOnly));
        const auto bytes = bytesFile.readAll();
        bytesFile.close();
        const QJsonObject file{{"path", "project.zip"}, {"format", "zip"},
            {"bytes", bytes.size()}, {"sha256", QString::fromLatin1(
                QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex())}};
        const QJsonObject entry{{"id", "pd-neut-cwl_cosio-d20_scan-213f"}, {"kind", "project"},
            {"name", "A scan example"}, {"files", QJsonArray{file}}};
        QFile index(source.filePath("index.json"));
        QVERIFY(index.open(QIODevice::WriteOnly));
        index.write(QJsonDocument(QJsonObject{{"schema", "edi-data-index/1"},
            {"entries", QJsonArray{entry}}}).toJson());
        index.close();
        const QByteArray oldSources = qgetenv("EDI_ONLINE_SOURCES");
        const auto restoreSources = qScopeGuard([&] { qputenv("EDI_ONLINE_SOURCES", oldSources); });
        const auto cod = QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR)
            + "/tests/fixtures/online_sources/cod/").toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + cod + ";easydiffraction="
            + QUrl::fromLocalFile(source.path()).toString() + "/").toUtf8());
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtQuick.Controls
            import edi.app
            ApplicationWindow {
                width: 1400; height: 900; visible: true
                footer: StatusBar { id: bar; objectName: "openingStatusBar" }
                Connections {
                    target: Session
                    function onProjectChanged() {
                        bar.pagesWanted = Session.hasProject ? 5 : 0;
                        bar.pagesBuilt = 0;
                    }
                }
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        auto* bar = root->findChild<QObject*>("openingStatusBar");
        auto* opening = root->findChild<QObject*>("statusBar.opening");
        auto* fitting = root->findChild<QObject*>("statusBar.fit.progress");
        QVERIFY(bar && opening && fitting);
        QSignalSpy finished(session, &edi_app::Session::exampleOpenFinished);
        QSignalSpy transferred(session, &edi_app::Session::exampleDownloadProgressChanged);
        QVERIFY(session->openExample("pd-neut-cwl_cosio-d20_scan-213f"));
        QVERIFY(bar->property("opening").toBool());
        QVERIFY(opening->property("indeterminate").toBool());
        QVERIFY(opening->property("text").toString().contains("Loading"));
        QCOMPARE(opening->property("height"), fitting->property("height"));
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 1, 10000);
        QVERIFY(finished.at(0).at(1).toBool());
        QVERIFY(session->hasProject());
        QVERIFY(transferred.count() >= 3);
        QCOMPARE(session->exampleDownloadReceived(), bytes.size());
        QCOMPARE(session->exampleDownloadTotal(), bytes.size());
        QVERIFY(!opening->property("indeterminate").toBool());
        QTRY_VERIFY(qAbs(opening->property("fraction").toDouble() - 1.0 / 3.0) < 0.001);
        QVERIFY(opening->property("text").toString().contains("Opening"));
        QVERIFY(bar->setProperty("pagesBuilt", 2));
        QTRY_VERIFY(qAbs(opening->property("fraction").toDouble() - 0.6) < 0.001);
        QVERIFY(bar->setProperty("pagesBuilt", 5));
        QTRY_VERIFY(!opening->property("visible").toBool());
        QVERIFY(QFile::remove(archive));
        QVERIFY(session->openExample("pd-neut-cwl_cosio-d20_scan-213f"));
        QVERIFY(bar->property("opening").toBool());
        QTRY_COMPARE_WITH_TIMEOUT(finished.count(), 2, 10000);
        QVERIFY(!finished.at(1).at(1).toBool());
        QTRY_VERIFY(!opening->property("visible").toBool());
        QVERIFY(session->openExample("pd-neut-cwl_cosio-d20_scan-213f"));
        session->closeProject();
        QVERIFY(!session->openingExample());
        QTest::qWait(50);
        QVERIFY(!session->hasProject());
        QVERIFY(!bar->property("opening").toBool());
    }
    void archiveScanRunsWithoutSave_data() {
        QTest::addColumn<bool>("unsaved");
        QTest::addColumn<QString>("mode");
        QTest::newRow("unsaved-sequential") << true << QString("sequential");
        QTest::newRow("folder-sequential") << false << QString("sequential");
        QTest::newRow("unsaved-independent") << true << QString("independent");
        QTest::newRow("folder-independent") << false << QString("independent");
    }
    void archiveScanRunsWithoutSave() {
        QFETCH(bool, unsaved);
        QFETCH(QString, mode);
        const QString archive = QString::fromUtf8(EDI_SOURCE_DIR)
            + "/tests/fixtures/project_archive/pd-neut-cwl_cosio-d20_scan-3f.zip";
        QFile original(archive);
        QVERIFY(original.open(QIODevice::ReadOnly));
        const QByteArray originalBytes = original.readAll();
        original.close();
        edi::Project project = edi::load_project(archive.toStdString());
        QVERIFY(project.path.empty());
        const QString working = QString::fromStdString(project.scan_data_root);
        QVERIFY(!working.isEmpty());
        if (!unsaved) {
            project.path = project.scan_data_root;
            project.metadata.path = project.path;
        }
        project.fitting_mode = mode.toStdString();
        project.minimizer_max_iterations = 1;
        {
            edi_app::ProjectViewModel model(std::move(project), nullptr);
            QVERIFY(model.scan());
            QSignalSpy refused(&model, &edi_app::ProjectViewModel::refused);
            model.setCurrentExperimentIndex(0);
            QTRY_VERIFY_WITH_TIMEOUT(!model.calculating() && model.viewSettled(), 10000);
            QVERIFY(model.fit()->available());
            model.fit()->start();
            QTRY_VERIFY_WITH_TIMEOUT(!model.fit()->running(), 10000);
            QTRY_COMPARE_WITH_TIMEOUT(model.fit()->scanFitted(), 3, 10000);
            QTRY_VERIFY_WITH_TIMEOUT(!model.calculating() && model.viewSettled(), 10000);
            QCOMPARE(refused.count(), 0);
            QCOMPARE(model.lastError(), QString());
            QCOMPARE(model.path().isEmpty(), unsaved);
            QVERIFY(QFile::exists(working + "/analysis/results.csv"));
            QVERIFY(QFile::exists(working + "/analysis/scan-run.json"));
            model.setTitle("Edited after scan completion");
            QCOMPARE(model.title(), QString("Edited after scan completion"));
            QCOMPARE(refused.count(), 0);
        }
        QVERIFY(original.open(QIODevice::ReadOnly));
        QCOMPARE(original.readAll(), originalBytes);
        QVERIFY(QDir(working).removeRecursively());
    }
    void sessionTitlesUseAvailableColumnWidth() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        WorkingAssistant assistant;
        engine.rootContext()->setContextProperty("testAssistant", &assistant);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtQuick.Controls
            import edi.app
            ApplicationWindow {
                width: 1400; height: 900; visible: true
                Item { id: toggle }
                AssistantPanel { assistant: testAssistant; toggleControl: toggle; shown: true }
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window);
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* dialog = root->findChild<QObject*>("assistant.sessionsDialog");
        auto* table = root->findChild<QQuickItem*>("assistant.sessions.list");
        QVERIFY(dialog);
        QVERIFY(table);
        QStandardItemModel model;
        model.setItemRoleNames({{Qt::UserRole + 1, "id"}, {Qt::UserRole + 2, "name"},
                               {Qt::UserRole + 3, "modified"}, {Qt::UserRole + 4, "canArchive"}});
        const QString title = "Neutron powder fit with a shared La/Ba displacement";
        auto* item = new QStandardItem;
        item->setData("session-1", Qt::UserRole + 1);
        item->setData(title, Qt::UserRole + 2);
        item->setData("04 Nov 2026 at 21:01", Qt::UserRole + 3);
        item->setData(false, Qt::UserRole + 4);
        model.appendRow(item);
        QVERIFY(table->setProperty("sourceModel", QVariant::fromValue<QObject*>(&model)));
        QVERIFY(QMetaObject::invokeMethod(dialog, "open"));
        QTRY_COMPARE(table->property("count").toInt(), 1);
        QTRY_VERIFY(dialog->property("visible").toBool());
        QTRY_VERIFY(table->isVisible());
        QQuickItem* titleCell = nullptr;
        const auto findTitle = [&](QQuickItem* start, auto&& self) -> QQuickItem* {
            if (start->isVisible() && start->property("text").toString() == title) return start;
            for (auto* child : start->childItems())
                if (auto* found = self(child, self)) return found;
            return nullptr;
        };
        QTRY_VERIFY(take(titleCell, findTitle(table, findTitle)));  // NOLINT(bugprone-assignment-in-if-condition): polled until found.
        QTRY_VERIFY(table->property("onScreen").toBool());
        QTRY_VERIFY(!table->property("refitting").toBool());
        QTRY_VERIFY(titleCell->width() > 0);
        const auto textRoom = [&] {
            return titleCell->width() - titleCell->property("leftPadding").toDouble()
                - titleCell->property("rightPadding").toDouble();
        };
        QTRY_VERIFY(textRoom() > table->width() / 2);
        QVERIFY(!titleCell->property("truncated").toBool());
        if (const auto capture = qEnvironmentVariable("EDI_SESSION_LAYOUT_CAPTURE"); !capture.isEmpty())
            QVERIFY(window->grabWindow().save(capture));
        const double wide = titleCell->width();
        QVERIFY(window->setProperty("width", 850));
        QTRY_VERIFY(titleCell->width() < wide);
        QVERIFY(titleCell->width() > 0);
        const QString longTitle = title.repeated(8);
        item->setData(longTitle, Qt::UserRole + 2);
        QTRY_COMPARE(titleCell->property("text").toString(), longTitle);
        QTRY_VERIFY(titleCell->property("truncated").toBool());
        QVERIFY(QMetaObject::invokeMethod(dialog, "close"));
        QVERIFY(table->setProperty("sourceModel", QVariant{}));
    }
    void shownActionsKeepWorkingIndicator() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        WorkingAssistant assistant;
        assistant.setShowActions(true);
        engine.rootContext()->setContextProperty("testAssistant", &assistant);
        QQmlComponent component(&engine);
        // The status bar is never shown on Home (owner, 2026-11-17), so the window starts on the next page.
        component.setData("import QtQuick\nimport QtQuick.Controls\nimport EasyApplication.Gui.Globals as EaGlobals\nimport edi.app\nApplicationWindow { width: 1200; height: 200; visible: true; footer: StatusBar { assistantChatShown: true } Component.onCompleted: EaGlobals.Vars.appBarCurrentIndex = 1 }", QUrl());
        QScopedPointer<QObject> bar(component.create());
        QVERIFY2(bar, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(bar.data());
        QVERIFY(window);
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* area = bar->findChild<QObject*>("statusBar.assistant.working");
        QVERIFY(area);
        area->setProperty("assistant", QVariant::fromValue(static_cast<edi_app::AssistantViewModel*>(&assistant)));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        session->assistant()->setShowActions(true);
        assistant.setFixtureState("agent_active");
        QTRY_VERIFY(area->property("working").toBool());
        QTRY_VERIFY2(area->property("visible").toBool(), qPrintable(QString("presented=%1 showActions=%2").arg(area->property("presented").toBool()).arg(session->assistant()->showActions())));
        QVERIFY(area->property("text").toString().contains("working", Qt::CaseInsensitive));
        auto* rotation = area->findChild<QObject*>("assistant.working.rotation");
        QVERIFY(rotation);
        QTRY_VERIFY(rotation->property("running").toBool());
        QTest::qWait(30);
        QVERIFY(area->property("visible").toBool());
        QVERIFY(rotation->property("running").toBool());
        assistant.setFixtureState("idle");
        QTRY_VERIFY(!area->property("visible").toBool());
        QTRY_VERIFY(!rotation->property("running").toBool());
    }
    // The Preferences number boxes step by their minus and plus: a click on either reaches the spin box, never the
    // text field beside it (the owner, 2026-11-11: the Tooltip delay buttons only selected the text).
    void testPreferencesSpinBoxSteps() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtQuick.Controls
            import edi.app
            ApplicationWindow {
                width: 1400; height: 900; visible: true
                AppPreferencesDialog { id: preferences }
                Component.onCompleted: preferences.open()
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* window = qobject_cast<QQuickWindow*>(root.data());
        QVERIFY(window && QTest::qWaitForWindowExposed(window));
        const auto click = [window](QQuickItem* item) {
            QTRY_VERIFY(item->isVisible() && item->width() > 0);
            const QPointF centre = item->mapToScene(QPointF(item->width() / 2, item->height() / 2));
            QTest::mouseClick(window, Qt::LeftButton, {}, centre.toPoint());
        };
        auto* tab = root->findChild<QQuickItem*>("preferences.tab.interface");
        QVERIFY(tab);
        click(tab);
        auto* spin = root->findChild<QQuickItem*>("preferences.toolTipDelay");
        QVERIFY(spin);
        QTRY_VERIFY(spin->isVisible());
        auto* up = qvariant_cast<QQuickItem*>(qvariant_cast<QObject*>(spin->property("up"))->property("indicator"));
        auto* down = qvariant_cast<QQuickItem*>(qvariant_cast<QObject*>(spin->property("down"))->property("indicator"));
        QVERIFY(up && down);
        const int start = spin->property("value").toInt();
        const int step = spin->property("stepSize").toInt();
        click(up);
        QTRY_COMPARE(spin->property("value").toInt(), start + step);
        click(down);
        click(down);
        QTRY_COMPARE(spin->property("value").toInt(), start - step);
    }
#if defined(Q_OS_UNIX)
    // An attached file stays the same input when only its metadata changes: macOS writes the last-used date as an
    // extended attribute after a file dialog opens a file, which moves its change time but not its bytes.
    void testMetadataChangeKeepsTheSelectedInput() {
        // Beside the test binary: /tmp is often a tmpfs that takes no user attributes.
        QTemporaryDir dir(QCoreApplication::applicationDirPath() + "/selected-input-XXXXXX");
        QVERIFY(dir.isValid());
        const QString path = dir.filePath("hrpt.xye");
        {
            QFile file(path);
            QVERIFY(file.open(QIODevice::WriteOnly));
            file.write("10.0 100 10\n");
        }
        const QByteArray name = QFile::encodeName(path);
        struct stat before{}, after{};
        QCOMPARE(::stat(name.constData(), &before), 0);
        QTest::qWait(20);
#if defined(Q_OS_MACOS)
        const int set = ::setxattr(name.constData(), "com.apple.lastuseddate#PS", "0123456789abcdef", 16, 0, 0);
#else
        const int set = ::setxattr(name.constData(), "user.edi.lastused", "1", 1, 0);
#endif
        if (set != 0) QSKIP("This file system takes no extended attributes");
        QCOMPARE(::stat(name.constData(), &after), 0);
        QVERIFY(edi_app::assistant_files::same_file_bytes(before, after));
        QCOMPARE(::chmod(name.constData(), 0400), 0);
        QCOMPARE(::stat(name.constData(), &after), 0);
        QVERIFY(edi_app::assistant_files::same_file_bytes(before, after));
        // New bytes are a different input.
        QCOMPARE(::chmod(name.constData(), 0600), 0);
        {
            QFile file(path);
            QVERIFY(file.open(QIODevice::Append));
            file.write("10.1 101 10\n");
        }
        QCOMPARE(::stat(name.constData(), &after), 0);
        QVERIFY(!edi_app::assistant_files::same_file_bytes(before, after));
    }
#endif
};
int main(int argc, char** argv) {
    try {
#ifndef __EMSCRIPTEN__
        if (argc > 1 && QByteArray(argv[1]) == "--listen") return assistantToolPeer();
#endif
        QStandardPaths::setTestModeEnabled(true);
        QGuiApplication app(argc, argv);
        app.setAttribute(Qt::AA_Use96Dpi, true);
#ifndef __EMSCRIPTEN__
        if (qEnvironmentVariableIsSet("EDI_PROVIDER_TEST_CASE")) {
            AssistantProviderProbe probe;
            return QTest::qExec(&probe, argc, argv);
        }
#endif
        AssistantUiTests tests;
        QTEST_SET_MAIN_SOURCE_PATH
        return QTest::qExec(&tests, argc, argv);
    } catch (const std::exception& error) {
        qCritical("assistant UI tests stopped: %s", error.what());
    } catch (...) {
        qCritical("assistant UI tests stopped");
    }
    return 1;
}
#include "assistant_ui_tests.moc"

