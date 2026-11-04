// SPDX-License-Identifier: BSD-3-Clause
#include <QtTest/QtTest>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QStandardItemModel>
#include <QDir>
#include <QFile>
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
        qputenv("QT_QUICK_CONTROLS_HOVER_ENABLED", "1");
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
        QTRY_VERIFY((titleCell = findTitle(table, findTitle)));
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
