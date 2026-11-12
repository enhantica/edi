// SPDX-License-Identifier: BSD-3-Clause
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
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
