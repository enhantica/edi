// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QtTest/QtTest>
#include "edi/io.hpp"
#include "scan_session.hpp"
#include "scan_view_model.hpp"

class ScanRefreshTests : public QObject {
    Q_OBJECT
private slots:
    void resultsRefreshKeepsMeasuredPatterns() {
        auto project = edi::load_project(EDI_SOURCE_DIR "/tests/fixtures/correlations/scan-sequential",
                                         edi::ProjectLoadMode::Construction);
        edi_app::ScanSession session(nullptr);
        QVERIFY2(session.load(project).isEmpty(), "the scan fixture must load");
        edi_app::ScanViewModel model(nullptr);
        model.setScan(&session, &project, {});
        QCOMPARE(model.count(), 2);
        model.setWanted(true);
        QTRY_COMPARE_WITH_TIMEOUT(model.loaded(), 2, 10000);
        QCOMPARE(model.failed(), 0);
        const auto first = model.patterns()[0].generation;
        const auto second = model.patterns()[1].generation;
        const auto* shown = model.patterns()[0].shown.data();
        const auto revision = model.revision();
        QSignalSpy changed(&model, &edi_app::ScanViewModel::revisionChanged);
        model.setScan(&session, &project, {});
        QCOMPARE(model.patterns()[0].generation, first);
        QCOMPARE(model.patterns()[1].generation, second);
        QCOMPARE(model.patterns()[0].shown.data(), shown);
        QCOMPARE(model.revision(), revision);
        QCOMPARE(changed.size(), 0);
        project.experiment().excluded_regions.push_back(edi::ExcludedRegion(44, 48));
        model.setScan(&session, &project, {});
        QVERIFY(model.patterns()[0].generation != first);
        QVERIFY(model.patterns()[1].generation != second);
        QCOMPARE(changed.size(), 1);
        QVERIFY(!model.patterns()[0].excluded_shown.empty());
        QCOMPARE(model.loaded(), 2);
    }
};

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    ScanRefreshTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "scan_refresh_tests.moc"
