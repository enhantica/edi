// SPDX-License-Identifier: BSD-3-Clause
#include <QtTest/QtTest>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QtQml/qqmlextensionplugin.h>

#include "desktop_updates.hpp"
#include "engine_setup.hpp"
#include "session.hpp"
#include "project_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
QJsonObject release(const QString& version, const QString& title = QStringLiteral("Improved powder refinement")) {
    return {{"version", version}, {"date", "2026-11-05"}, {"commit", QString(40, 'a')},
            {"notes", QJsonObject{{"Added", QJsonArray{}}, {"Changed", QJsonArray{}},
                                  {"Fixed", QJsonArray{QJsonObject{{"title", title}, {"pull_request", 1}}}}}}};
}
QByteArray history(const QJsonArray& releases) {
    return QJsonDocument(QJsonObject{{"schema", "edi.releases/1"}, {"releases", releases}}).toJson();
}
class FeedServer {
public:
    QTcpServer server;
    explicit FeedServer(QByteArray body) {
        QObject::connect(&server, &QTcpServer::newConnection, &server, [this, body] {
            auto* socket = server.nextPendingConnection();
            QObject::connect(socket, &QTcpSocket::readyRead, &server, [socket, body] {
                socket->readAll();
                if (socket->state() != QAbstractSocket::ConnectedState) return;
                socket->write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: " + QByteArray::number(body.size()) + "\r\n\r\n" + body);
                socket->disconnectFromHost();
            });
            QObject::connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
        });
        if (!server.listen(QHostAddress::LocalHost)) qFatal("Unable to bind local recorded feed");
    }
    QUrl url() const { return QUrl(QStringLiteral("http://127.0.0.1:%1/releases.json").arg(server.serverPort())); }
};
}

class DesktopUpdateTests : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() {
        const auto directory = edi_app::fresh_settings_dir() + QStringLiteral("/catalogue");
        QVERIFY(QDir().mkpath(directory));
        QFile file(directory + QStringLiteral("/index.json"));
        QVERIFY(file.open(QIODevice::WriteOnly));
        file.write(R"({"schema":"edi-data-index/1","entries":[]})");
        file.close();
        const auto url = QUrl::fromLocalFile(directory + "/").toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + url + ";easydiffraction=" + url).toUtf8());
        qputenv("CODEX_HOME", (edi_app::fresh_settings_dir() + "/codex").toUtf8());
    }
    void calendarOrdering() {
        edi_app::DesktopUpdates updates("2026.11.0", {}, {}, false);
        QVERIFY(updates.newerVersion("2026.11.10", "2026.11.9"));
        QVERIFY(updates.newerVersion("2027.01.0", "2026.12.99"));
        QVERIFY(!updates.newerVersion("2026.11.0\n", "2026.11.0"));
        QVERIFY(!updates.newerVersion("2026.13.0", "2026.11.0"));
        QVERIFY(!updates.newerVersion("2026.11.01", "2026.11.0"));
        QVERIFY(!updates.newerVersion("2026.11.0", "git-build"));
    }
    void orderedBundledRangeAndEscapedTitles() {
        bool valid = false;
        const auto values = edi_app::release_changes(history({release("2026.11.0"), release("2026.11.10", "<image> [link](url)"), release("2026.11.9"), release("2026.12.0")}), "2026.11.10", &valid);
        QVERIFY(valid);
        QCOMPARE(values.size(), 3);
        QCOMPARE(values[0].toMap()["version"].toString(), "2026.11.10");
        QCOMPARE(values[1].toMap()["version"].toString(), "2026.11.9");
        QVERIFY(!values[0].toMap()["text"].toString().contains("<image>"));
        QVERIFY(values[0].toMap()["text"].toString().contains("\\[link\\]"));
    }
    void malformedHistory_data() {
        QTest::addColumn<QByteArray>("content");
        QTest::newRow("invalid-json") << QByteArray("{broken");
        QTest::newRow("duplicate") << history({release("2026.11.0"), release("2026.11.0")});
        auto invalid = release("2026.11.0");
        invalid["date"] = "2026-02-31";
        QTest::newRow("date") << history({invalid});
        invalid = release("2026.11.0"); invalid["commit"] = "unverified";
        QTest::newRow("commit") << history({invalid});
        QTest::newRow("oversize") << QByteArray(1024 * 1024 + 1, 'x');
    }
    void malformedHistory() {
        QFETCH(QByteArray, content);
        bool valid = true;
        QVERIFY(edi_app::release_changes(content, "2026.11.0", &valid).isEmpty());
        QVERIFY(!valid);
    }
    void recordedFallbackAndNoNotificationDependency() {
        FeedServer unavailable("not release metadata");
        FeedServer primary(history({release("2026.11.0"), release("2026.11.1")}));
        edi_app::DesktopUpdates updates("2026.11.0", QCoreApplication::applicationFilePath(), {unavailable.url(), primary.url()}, false);
        QVERIFY(updates.managed());
        updates.checkNow();
        QTRY_VERIFY_WITH_TIMEOUT(!updates.checking(), 3000);
        QVERIFY(updates.available());
        QCOMPARE(updates.availableVersion(), "2026.11.1");
    }
    void upToDateStatusIncludesInstalledVersion() {
        FeedServer feed(history({release("2026.11.0")}));
        edi_app::DesktopUpdates updates("2026.11.0", QCoreApplication::applicationFilePath(), {feed.url()}, false);
        updates.checkNow();
        QTRY_VERIFY_WITH_TIMEOUT(!updates.checking(), 3000);
        QVERIFY(!updates.available());
        QCOMPARE(updates.status(), "You are using the latest release, 2026.11.0.");
    }
    void failedFeedAndDevelopmentBuild() {
        FeedServer feed("malformed");
        edi_app::DesktopUpdates managed("2026.11.0", QCoreApplication::applicationFilePath(), {feed.url()}, false);
        managed.checkNow();
        QTRY_VERIFY_WITH_TIMEOUT(!managed.checking(), 3000);
        QVERIFY(!managed.available());
        QVERIFY(managed.status().contains("Unable"));
        edi_app::DesktopUpdates development("abcdef0-dirty", QCoreApplication::applicationFilePath(), {feed.url()}, false);
        QVERIFY(!development.managed());
        development.checkNow();
        QVERIFY(!development.checking());
    }
    void updaterLaunchFailureKeepsTheApplicationOpen() {
        QTemporaryDir temp;
        const auto executable = temp.filePath("updater.exe");
        QFile script(executable);
        QVERIFY(script.open(QIODevice::WriteOnly));
        script.write("#!/nonexistent-interpreter\n"); script.close();
        QVERIFY(script.setPermissions(QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner));
        FeedServer feed(history({release("2026.11.1")}));
        edi_app::DesktopUpdates updates("2026.11.0", executable, {feed.url()}, false);
        updates.checkNow();
        QTRY_VERIFY_WITH_TIMEOUT(!updates.checking(), 3000);
        QVERIFY(updates.available());
        QVERIFY(!updates.startUpdate());
        QVERIFY(updates.status().contains("still open"));
        QVERIFY(!updates.startMaintenance());
        QCOMPARE(updates.status(), "The Maintenance Tool could not be opened.");
    }
    void updateActionSettlesUnsavedWorkBeforeLaunch() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().first());
        QVERIFY(window);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QTemporaryDir projectDirectory;
        QVERIFY(session->createProject("Update guard", "Unsaved update test", projectDirectory.filePath("project")));
        QVERIFY(session->project());
        session->project()->setName("Keep this unsaved change");
        QVERIFY(session->project()->modified());
        auto* question = window->findChild<QObject*>("unsavedChanges");
        auto* failed = window->findChild<QObject*>("update.launchFailed");
        QVERIFY(question); QVERIFY(failed);
        QVERIFY(QMetaObject::invokeMethod(window, "updateApplication"));
        QTRY_VERIFY(question->property("opened").toBool());
        QVERIFY(!failed->property("opened").toBool());
        QVERIFY(QMetaObject::invokeMethod(question, "reject"));
        QTRY_VERIFY(!question->property("opened").toBool());
        QVERIFY(window->isVisible());
        QVERIFY(session->project()->modified());
        QVERIFY(!failed->property("opened").toBool());
        QVERIFY(QMetaObject::invokeMethod(window, "updateApplication"));
        QTRY_VERIFY(question->property("opened").toBool());
        QVERIFY(QMetaObject::invokeMethod(question, "accept"));
        QTRY_VERIFY(failed->property("opened").toBool());
        QVERIFY(!session->project()->modified());
        QVERIFY(window->isVisible());
        QVERIFY(QMetaObject::invokeMethod(failed, "close"));
        session->project()->setName("Another unsaved change");
        QVERIFY(QMetaObject::invokeMethod(window, "updateApplication"));
        QTRY_VERIFY(question->property("opened").toBool());
        QVERIFY(QMetaObject::invokeMethod(question, "discarded"));
        QTRY_VERIFY(failed->property("opened").toBool());
        QVERIFY(window->isVisible());
        QVERIFY(!window->property("quitting").toBool());
    }
    void whatsNewIncludesSkippedCalendarVersions() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.loadFromModule("edi.app", "WhatsNewDialog");
        QScopedPointer<QObject> dialog(component.create());
        QVERIFY2(dialog, qPrintable(component.errorString()));
        const auto days = edi_app::release_changes(history({release("2026.11.0"), release("2026.11.9"), release("2026.11.10")}), "2026.11.10");
        QVERIFY(dialog->setProperty("days", days));
        QVERIFY(dialog->setProperty("seen", "2026.11.0"));
        const auto raw = dialog->property("newDays");
        const auto list = raw.value<QJSValue>().toVariant().toList();
        QCOMPARE(list.size(), 2);
        QCOMPARE(list[0].toMap()["version"].toString(), "2026.11.10");
        QCOMPARE(list[1].toMap()["version"].toString(), "2026.11.9");
        QVERIFY(dialog->setProperty("seen", ""));
        QCOMPARE(dialog->property("newDays").value<QJSValue>().toVariant().toList().size(), 3);
    }
    void redButtonWithNotificationsDisabled_data() {
        QTest::addColumn<bool>("dark");
        QTest::newRow("light") << false;
        QTest::newRow("dark") << true;
    }
    void redButtonWithNotificationsDisabled() {
        QFETCH(bool, dark);
        FeedServer feed(history({release("2026.11.1")}));
        edi_app::DesktopUpdates updates("2026.11.0", QCoreApplication::applicationFilePath(), {feed.url()}, false);
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* preferences = engine.singletonInstance<QObject*>("edi.app", "Preferences");
        QVERIFY(preferences);
        preferences->setProperty("updateNotifications", false);
        engine.rootContext()->setContextProperty("recordedUpdates", &updates);
        engine.rootContext()->setContextProperty("darkTestTheme", dark);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import edi.app
            import EasyApplication.Gui.Style as EaStyle
            UpdateButton {
                updates: recordedUpdates; width: 120; height: 36
                Component.onCompleted: EaStyle.Colors.theme = darkTestTheme ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme
            }
        )", QUrl());
        QScopedPointer<QObject> button(component.create());
        QVERIFY2(button, qPrintable(component.errorString()));
        QQuickWindow window;
        auto* item = qobject_cast<QQuickItem*>(button.data());
        QVERIFY(item);
        item->setParentItem(window.contentItem());
        window.setWidth(160); window.setHeight(60); window.show();
        QVERIFY(!button->property("visible").toBool());
        updates.checkNow();
        QTRY_VERIFY_WITH_TIMEOUT(!updates.checking(), 3000);
        QVERIFY(updates.available());
        QTRY_VERIFY(button->property("visible").toBool());
        QVERIFY(!preferences->property("updateNotifications").toBool());
        const auto ink = button->property("ink").value<QColor>();
        QVERIFY(ink.red() > ink.green());
        QVERIFY(ink.red() > ink.blue());
    }
};

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    edi_app::use_fresh_settings();
    DesktopUpdateTests test;
    return QTest::qExec(&test, argc, argv);
}
#include "desktop_update_tests.moc"
