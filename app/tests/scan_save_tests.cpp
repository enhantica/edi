// SPDX-License-Identifier: BSD-3-Clause
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QQuickWindow>
#include <QSettings>
#include "scan_layer.hpp"
#include <QTemporaryDir>
#include <QtTest/QtTest>
#include <QtQml/qqmlextensionplugin.h>
#include "engine_setup.hpp"
#include "session.hpp"
#include "project_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class ScanSaveTests : public QObject {
    Q_OBJECT
private slots:
    void hiddenWorkflowPagesDeferSelection() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/app/examples/pd-xray-cwl_lif/project"))),
            qPrintable(session->lastError()));
        auto* project = session->project();
        QVERIFY(project->duplicateExperiment());
        QVERIFY(project->duplicateStructure());
        for (const auto& kind : {QString("Experiment"), QString("Structure")}) {
            const bool experiment = kind == "Experiment";
            project->setCurrentExperimentIndex(0);
            project->setCurrentStructureIndex(0);
            QQmlComponent component(&engine);
            component.setData(("import edi.app; " + kind + "Page { width: 800; height: 600; current: true }").toUtf8(), QUrl());
            QScopedPointer<QObject> page(component.create());
            QVERIFY2(page, qPrintable(component.errorString()));
            const auto field = kind.toLower().toUtf8();
            QObject* first = page->property(field).value<QObject*>();
            QVERIFY(first);
            page->setProperty("current", false);
            if (experiment) project->setCurrentExperimentIndex(1);
            else project->setCurrentStructureIndex(1);
            QCOMPARE(page->property(field).value<QObject*>(), first);
            page->setProperty("current", true);
            QObject* selected = experiment ? static_cast<QObject*>(project->currentExperiment())
                                          : static_cast<QObject*>(project->currentStructure());
            QVERIFY(selected != first);
            QCOMPARE(page->property(field).value<QObject*>(), selected);
        }
    }
    void numericPatternAxisProjection() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import QtGraphs
            import edi.app
            Item {
                id: chart
                property alias low: axis.min
                property alias high: axis.max
                property alias interval: axis.tickInterval
                property alias anchor: axis.tickAnchor
                property var ticks: ApplicationInfo.patternTickValues(axis)
                ValueAxis { id: axis; min: -2; max: 4; tickInterval: 2; tickAnchor: 0 }
                PatternChartController { id: controller }
                function label(text: string, scale: int): string {
                    return ApplicationInfo.patternYLabelText(text, axis, scale, "0|3|0");
                }
            }
        )", QUrl());
        QScopedPointer<QObject> chart(component.create());
        QVERIFY2(chart, qPrintable(component.errorString()));
        const auto ticks = [&] { return chart->property("ticks").value<QJSValue>().toVariant().toList(); };
        QCOMPARE(ticks(), QVariantList({-2.0, 0.0, 2.0, 4.0}));
        const auto label = [&](const QString& text, int scale) {
            QQmlExpression expression(qmlContext(chart.data()), chart.data(),
                QString(R"(label("%1", %2))").arg(text).arg(scale));
            const auto result = expression.evaluate().toString();
            if (expression.hasError()) QTest::qFail(qPrintable(expression.error().toString()), __FILE__, __LINE__);
            return result;
        };
        QCOMPARE(label("3", 0), QString("2"));
        QCOMPARE(label("2", 1), QString("4"));
        QCOMPARE(label("2", 2), QString("100"));
        QCOMPARE(label("invalid", 0), QString("invalid"));
        chart->setProperty("anchor", 1.0);
        QCOMPARE(ticks(), QVariantList({-1.0, 1.0, 3.0}));
        chart->setProperty("low", 0.0);
        QCOMPARE(ticks(), QVariantList({1.0, 3.0}));
        chart->setProperty("high", 0.0);
        QVERIFY(ticks().isEmpty());
        QCOMPARE(label("3", 0), QString("3"));
        chart->setProperty("high", 1.0);
        chart->setProperty("interval", 0.0);
        QVERIFY(ticks().isEmpty());
    }
    void hiddenChartsCreateNoDatasetLabels() {
        QTemporaryDir root;
        QVERIFY(root.isValid());
        const QDir source(QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/correlations/scan-sequential"));
        const QDir destination(root.path());
        for (const auto& relative : {"project.edi", "structures/phase.edi", "experiments/bank.edi",
                                     "experiments/scan/01.xy", "experiments/scan/02.xy", "analysis/analysis.edi"}) {
            const auto target = destination.filePath(QString::fromUtf8(relative));
            QVERIFY(QDir().mkpath(QFileInfo(target).absolutePath()));
            QVERIFY(QFile::copy(source.filePath(QString::fromUtf8(relative)), target));
        }
        for (int file = 3; file <= 64; ++file)
            QVERIFY(QFile::copy(source.filePath("experiments/scan/01.xy"),
                destination.filePath(QString("experiments/scan/%1.xy").arg(file, 2, 10, QLatin1Char('0')))));
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(root.path())), qPrintable(session->lastError()));
        auto* project = session->project();
        QCOMPARE(project->scanViews()->count(), 64);
        for (const auto& mode : {"stacked", "map"}) {
            QQmlComponent component(&engine);
            component.setData((QByteArray("import edi.app; ScanViewChart { width: 400; height: 300; shown: false; project: Session.project; mode: \"") + mode + "\" }").constData(), QUrl());
            QScopedPointer<QObject> chart(component.create());
            QVERIFY2(chart, qPrintable(component.errorString()));
            auto* labels = chart->findChild<QObject*>(QString("scanView.%1.labels").arg(mode));
            QVERIFY(labels);
            QCOMPARE(labels->property("count").toInt(), 0);
            chart->setProperty("shown", true);
            auto* layer = chart->findChild<edi_app::ScanLayer*>(QString("scanView.%1.layer").arg(mode));
            QVERIFY(layer);
            layer->setHeight(100);
            layer->setYMin(0);
            layer->setYMax(QString::fromUtf8(mode) == "stacked" ? 1 : 65);
            layer->setLabelGap(20);
            bool retained = false;
            for (int dataset = 16; dataset < 32; ++dataset) {
                const int before = labels->property("count").toInt();
                QQuickItem* first = nullptr;
                QVERIFY(QMetaObject::invokeMethod(labels, "itemAt", Q_RETURN_ARG(QQuickItem*, first), Q_ARG(int, 0)));
                QPointer<QQuickItem> original(first);
                layer->setCurrent(dataset);
                if (before > 0 && labels->property("count").toInt() == before) {
                    QVERIFY(original);
                    QQuickItem* after = nullptr;
                    QVERIFY(QMetaObject::invokeMethod(labels, "itemAt", Q_RETURN_ARG(QQuickItem*, after), Q_ARG(int, 0)));
                    QCOMPARE(after, original.data());
                    retained = true;
                }
            }
            QVERIFY(retained);
        }
        edi_app::ScanLayer layer;
        layer.setMode("map");
        layer.setModel(project->scanViews());
        layer.setHeight(100);
        layer.setYMin(0);
        layer.setYMax(65);
        layer.setLabelGap(20);
        layer.setLabelled(true);
        layer.setCurrent(30);
        const auto labels = layer.labelledDatasets();
        QVERIFY(labels.contains(30));
        QVERIFY(labels.size() <= 7);
        layer.setActive(false);
        QVERIFY(layer.labelledDatasets().isEmpty());
    }
    void freeMenuVisitsRowsOnlyWhileOpen() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(EDI_SOURCE_DIR "/tests/fixtures/correlations/scan-sequential")),
                 qPrintable(session->lastError()));
        QQmlComponent component(&engine);
        component.setData("import edi.app; FreeHeaderMenu { project: Session.project; filter: ParameterFilterModel { sourceModel: Session.project.parameters } }", QUrl());
        QScopedPointer<QObject> menu(component.create());
        QVERIFY2(menu, qPrintable(component.errorString()));
        QQmlExpression count(QQmlEngine::contextForObject(menu.data()), menu.data(), "shown.length");
        QCOMPARE(count.evaluate().toInt(), 0);
        QQuickWindow window;
        window.setGeometry(0, 0, 400, 300);
        window.show();
        menu->setProperty("parent", QVariant::fromValue(window.contentItem()));
        QVERIFY(QMetaObject::invokeMethod(menu.data(), "open"));
        QTRY_VERIFY(menu->property("visible").toBool());
        QVERIFY(count.evaluate().toInt() > 0);
        QVERIFY(QMetaObject::invokeMethod(menu.data(), "close"));
        QTRY_VERIFY(!menu->property("visible").toBool());
        QCOMPARE(count.evaluate().toInt(), 0);
    }
    void selectionIsStoredAfterSwitchAndOnClose() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        const auto source = QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/report_context/joint");
        QVERIFY2(session->openProject(QUrl::fromLocalFile(source)), qPrintable(session->lastError()));
        auto* project = session->project();
        const auto key = QString("Selections/%1").arg(QString::fromLatin1(QUrl::toPercentEncoding(QFileInfo(source).absoluteFilePath())));
        const auto stored = [&] { QSettings settings(edi_app::settings_file_path(), QSettings::IniFormat); return settings.value(key).toStringList(); };
        const auto before = stored();
        project->setCurrentExperimentIndex(project->currentExperimentIndex() == 0 ? 1 : 0);
        const auto selected = project->currentExperiment()->name();
        QCOMPARE(stored(), before);
        QTRY_COMPARE_WITH_TIMEOUT(stored().value(1), selected, 2000);
        project->setCurrentExperimentIndex(project->currentExperimentIndex() == 0 ? 1 : 0);
        const auto last = project->currentExperiment()->name();
        session->closeProject();
        QTRY_COMPARE_WITH_TIMEOUT(stored().value(1), last, 2000);
    }
    void generatedRunRecordIsPartOfSave() {
        QTemporaryDir root;
        QVERIFY(root.isValid());
        const QDir source(QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/correlations/scan-sequential"));
        const QDir destination(root.path());
        for (const auto& relative : {"project.edi", "structures/phase.edi", "experiments/bank.edi",
                                     "experiments/scan/01.xy", "experiments/scan/02.xy", "analysis/analysis.edi"}) {
            const auto target = destination.filePath(QString::fromUtf8(relative));
            QVERIFY(QDir().mkpath(QFileInfo(target).absolutePath()));
            QVERIFY(QFile::copy(source.filePath(QString::fromUtf8(relative)), target));
        }
        QFile rows(destination.filePath("analysis/results.csv"));
        QVERIFY(rows.open(QIODevice::WriteOnly));
        rows.write("file_path,fit_result.reduced_chi_square,fit_result.success,fit_result.iterations,bank.background.base.coef,bank.background.base.coef.uncertainty,bank.background.ramp.coef,bank.background.ramp.coef.uncertainty,bank.background.curve.coef,bank.background.curve.coef.uncertainty,fit_result.descent,fit_result.chi_square_tolerance,fit_result.max_iterations,fit_result.termination\n"
                   "experiments/scan/01.xy,0.12,True,6,4.98151,0.00013,2.00,0.56,3.00,0.68,fast,0.000001,80,chi_converged\n"
                   "experiments/scan/02.xy,0.016,True,6,5.300,0.065,0.800,0.096,1.70,0.14,fast,0.000001,80,chi_converged\n");
        rows.close();
        const auto run = destination.filePath("analysis/scan-run.json");
        QVERIFY(!QFileInfo::exists(run));
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(root.path())), qPrintable(session->lastError()));
        auto* project = session->project();
        QVERIFY(project);
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 10000);
        QVERIFY(project->scanProcessed());
        QVERIFY2(session->save(), qPrintable(session->lastError()));
        QVERIFY(QFileInfo(run).isFile());
        QVERIFY2(session->save(), qPrintable(session->lastError()));
    }
};
int main(int argc, char** argv) {
    edi_app::select_freetype_engine(argc, argv);
    QGuiApplication app(argc, argv);
    edi_app::use_fresh_settings();
    edi_app::use_design_font();
    const auto catalogue = edi_app::fresh_settings_dir() + "/catalogue";
    QDir().mkpath(catalogue);
    QFile index(catalogue + "/index.json");
    if (!index.open(QIODevice::WriteOnly)) return 2;
    index.write("{\"schema\":\"edi-data-index/1\",\"entries\":[]}");
    index.close();
    const auto url = QUrl::fromLocalFile(catalogue + "/").toString();
    qputenv("EDI_ONLINE_SOURCES", ("cod=" + url + ";easydiffraction=" + url).toUtf8());
    ScanSaveTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "scan_save_tests.moc"
