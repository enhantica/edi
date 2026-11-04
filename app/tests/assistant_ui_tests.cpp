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
