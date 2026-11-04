// SPDX-License-Identifier: BSD-3-Clause
#include <QtTest/QtTest>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QtQml/qqmlextensionplugin.h>
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include "session.hpp"
#include "assistant_widget_input.hpp"
#include "project_view_model.hpp"
#include "online_search.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

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
        edi_app::use_fresh_settings();
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
        const auto click = [&](const char* name) {
            auto* target = root->findChild<QQuickItem*>(name);
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
        QVERIFY(!dataFile->isEnabled());
        QVERIFY2(click("experiments.create"), qPrintable(diagnostic));
        QTRY_VERIFY(project.currentExperiment());
        QVERIFY2(click("experiments.load"), qPrintable(diagnostic));
        auto* menu = root->findChild<QObject*>("experiments.load.menu");
        QVERIFY(menu);
        QTRY_VERIFY(menu->property("visible").toBool());
        QVERIFY(dataFile->isEnabled());
        QVERIFY2(click("experiments.load.dataWeb"), qPrintable(diagnostic));
        auto* popup = root->findChild<QObject*>("onlineLoad");
        QVERIFY(popup);
        QTRY_VERIFY(popup->property("visible").toBool());
        QCOMPARE(popup->property("kind").toString(), QString("data"));
        QVERIFY(root->findChild<QObject*>("onlineLoad.source"));
        QVERIFY(root->findChild<QObject*>("onlineLoad.search"));
        QVERIFY(QMetaObject::invokeMethod(popup, "close"));
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
    void shownActionsKeepWorkingIndicator() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        WorkingAssistant assistant;
        assistant.setShowActions(true);
        engine.rootContext()->setContextProperty("testAssistant", &assistant);
        QQmlComponent component(&engine);
        component.setData("import QtQuick\nimport QtQuick.Controls\nimport edi.app\nApplicationWindow { width: 1200; height: 200; visible: true; footer: StatusBar { assistantChatShown: true } }", QUrl());
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
};
QTEST_MAIN(AssistantUiTests)
#include "assistant_ui_tests.moc"
