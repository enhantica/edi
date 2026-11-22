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
#include <QTemporaryDir>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QCryptographicHash>
#include <QGuiApplication>
#include <iostream>
#ifndef __EMSCRIPTEN__
#include "codex_agent.hpp"
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
#include "project_view_model.hpp"
#include "online_search.hpp"
#if defined(Q_OS_UNIX)
#include "assistant_file_primitives.hpp"
#include <sys/stat.h>
#include <sys/xattr.h>
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
    for (std::string line; std::getline(std::cin, line);) {
        const auto request = QJsonDocument::fromJson(QByteArray::fromStdString(line)).object();
        const auto method = request.value("method").toString();
        const auto params = request.value("params").toObject();
        if (method.isEmpty()) {
            if (request.value("id") != "load-call") continue;
            item["status"] = "completed";
            item["success"] = request.value("result").toObject().value("success");
            item["contentItems"] = request.value("result").toObject().value("contentItems");
            event("item/completed", {{"threadId", "load-thread"}, {"turnId", "load-turn"}, {"item", item}});
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
            const auto arguments = QJsonDocument::fromJson(qgetenv("EDI_UI_LOAD_ARGUMENTS")).object();
            const auto tool = qEnvironmentVariable("EDI_UI_TOOL", "load_data");
            item = {{"id", "load-item"}, {"type", "dynamicToolCall"}, {"tool", tool},
                {"arguments", arguments}, {"status", "inProgress"}};
            event("item/started", {{"threadId", "load-thread"}, {"turnId", "load-turn"}, {"item", item}});
            write({{"id", "load-call"}, {"method", "item/tool/call"}, {"params", Object{{"threadId", "load-thread"},
                {"turnId", "load-turn"}, {"callId", "load-item"}, {"tool", tool}, {"arguments", arguments}}}});
        }
    }
    return 0;
}

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

class AssistantUiTests : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() {
        qputenv("QT_QUICK_CONTROLS_HOVER_ENABLED", "1");
        edi_app::use_fresh_settings();
        QVERIFY(QDir().mkpath(QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)));
        const auto root = QString::fromUtf8(EDI_SOURCE_DIR);
        const auto cod = QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/cod/").toString();
        const auto edb = QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/easydiffraction/").toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + cod + ";easydiffraction=" + edb).toUtf8());
    }
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
        QVERIFY(!uniqueName.isEmpty());
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
            if (content && option >= 0 && typed == path &&
                QMetaObject::invokeMethod(content, "itemAtIndex", Q_RETURN_ARG(QQuickItem*, entry), Q_ARG(int, option)) &&
                entry && entry->isVisible() && entry->mapRectToScene(entry->boundingRect()).contains(pointer))
                selectedEntryPressed = true;
        });
        assistant->send(alias ? "Alias the La atom isotropic displacement as la_adp." : "Name the background points from their positions.");
        QTRY_COMPARE_WITH_TIMEOUT(assistant->state(), QString("idle"), 30000);
        searchObserver.stop();
        if (alias) {
            QCOMPARE(typed, path);
            QVERIFY(selectedEntryPressed);
            auto* combo = find("alias.parameter.0");
            QVERIFY(combo);
            const auto option = combo->property("names").toStringList().indexOf(uniqueName);
            QVERIFY(option >= 0);
            QCOMPARE(combo->property("currentIndex").toInt(), option);
            QCOMPARE(combo->property("model").toStringList()[option].section(" · ", 1), path);
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

