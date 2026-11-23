// SPDX-License-Identifier: BSD-3-Clause
#include <atomic>
#include <cmath>
#include <condition_variable>
#include <mutex>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QSignalSpy>
#include <QtTest/QtTest>
#include <QtQml/qqmlextensionplugin.h>
#ifdef Q_OS_LINUX
#include <sys/prctl.h>
#endif
#include "edi/io.hpp"
#include "edi/live_preview.hpp"
#include "edi/selectors.hpp"
#include "edi/threading.hpp"
#include "engine_setup.hpp"
#include "project_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

extern "C" Q_NEVER_INLINE void edi_link_probe_phase(const char* text) { qInfo("%s", text); }

class LinkedStructureCalculationTests : public QObject {
    Q_OBJECT
private slots:
    void supersededRequestsCancelAndCoalesce() {
        edi::set_engine_threads(2);
        auto project = edi::load_project(EDI_SOURCE_DIR "/tests/fixtures/excluded_display/tof",
                                         edi::ProjectLoadMode::Construction);
        auto second = *project.structures.front(); second.name = "phase2";
        auto third = second; third.name = "phase3";
        project.structures.push_back(second); project.structures.push_back(third);
        std::atomic<int> calls{0};
        std::atomic<bool> cancelled{false};
        std::atomic<std::size_t> newestLinks{0};
        std::mutex mutex;
        std::condition_variable ready;
        bool release = false;
        int published = 0;
        edi::work::Worker worker([this](edi::work::Delivery delivery) {
            QMetaObject::invokeMethod(this, std::move(delivery), Qt::QueuedConnection);
        });
        edi::LivePreview::Hooks hooks;
        hooks.published = [&](const edi::PreviewResult&) { ++published; };
        edi::LivePreview::Seams seams;
        seams.calculate = [&](edi::WorkSnapshot& snapshot, const edi::work::CancelToken& token) {
            if (++calls == 1) {
                std::unique_lock lock(mutex);
                ready.wait_for(lock, std::chrono::seconds(2), [&] { return release; });
                cancelled = token.cancelled();
                edi::CalculationResult result;
                result.stamps = snapshot.stamps; result.cancelled = token.cancelled();
                return result;
            }
            newestLinks = snapshot.project.experiment().linked_structures.size();
            return edi::calculate(snapshot, token);
        };
        edi::LivePreview preview(project, worker, hooks, seams);
        preview.recalculate();
        QTRY_COMPARE_WITH_TIMEOUT(calls.load(), 1, 1000);
        for (const char* id : {"phase2", "phase3"}) {
            edi::LinkedStructure link; link.structure_id = id;
            preview.apply(edi::Edit::append(project.experiment().linked_structures, link));
        }
        { std::lock_guard lock(mutex); release = true; }
        ready.notify_one();
        QTRY_VERIFY_WITH_TIMEOUT(!preview.busy(), 10000);
        QCOMPARE(calls.load(), 2);
        QVERIFY(cancelled.load());
        QCOMPARE(newestLinks.load(), std::size_t(3));
        QCOMPARE(published, 1);
        QVERIFY(project.experiment().computed_current());
    }
    void oneAppendCalculatesOnce() {
        edi::set_engine_threads(2);
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto project = edi::load_project(EDI_SOURCE_DIR "/tests/fixtures/excluded_display/tof",
                                         edi::ProjectLoadMode::Construction);
        auto second = *project.structures.front();
        second.name = "phase2";
        project.structures.push_back(second);
        edi_app::ProjectViewModel model(std::move(project), nullptr);
        QTRY_VERIFY_WITH_TIMEOUT(!model.calculating(), 30000);
        auto* links = model.currentExperiment()->linkedStructures();
        QVERIFY(links->canAppend());
        edi::Project reference = model.project();
        edi::LinkedStructure link;
        link.structure_id = "phase2";
        reference.experiment().linked_structures.push_back(link);
        const auto referenceStart = edi::engine_structure_factor_evaluations();
        reference.calculate();
        const auto oneCalculation = edi::engine_structure_factor_evaluations() - referenceStart;
        QVERIFY(oneCalculation > 0);
        if (qEnvironmentVariableIsSet("EDI_LINK_PROBE_HOLD")) {
#ifdef Q_OS_LINUX
            prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY);
#endif
            qInfo("Attach debugger to pid %lld", static_cast<long long>(QCoreApplication::applicationPid()));
            QTest::qWait(15000);
        }
        QSignalSpy started(&model, &edi_app::ProjectViewModel::calculationStarted);
        const auto before = edi::engine_structure_factor_evaluations();
        edi_link_probe_phase("LINK BEGIN");
        links->append();
        QTRY_VERIFY_WITH_TIMEOUT(!model.calculating(), 30000);
        // Let coalesced text/spelling publication run too.
        QTest::qWait(1200);
        edi_link_probe_phase("LINK END");
        const auto actual = edi::engine_structure_factor_evaluations() - before;
        qInfo("LINK work: %llu structure factors; one forward calculation: %llu; preview starts: %lld",
              static_cast<unsigned long long>(actual), static_cast<unsigned long long>(oneCalculation),
              static_cast<long long>(started.count()));
        QCOMPARE(links->count(), 2);
        QCOMPARE(started.count(), 1);
        QVERIFY2(model.lastError().isEmpty(), qPrintable(model.lastError()));
        // The independent control may warm Crysta's factor cache. Never exceed one forward pass;
        // count.gdb counts actual pattern calls as well, including calls that reuse those factors.
        QVERIFY(actual <= oneCalculation);
        const auto& calculated = model.project().experiment();
        QVERIFY(calculated.computed_current());
        const auto& referenceData = reference.experiment().data;
        if (!referenceData || !calculated.data) QFAIL("Both experiments must keep their data");
        const auto& expected = referenceData->intensity_calc.values();
        const auto& observed = calculated.data->intensity_calc.values();
        QCOMPARE(observed.size(), expected.size());
        for (std::size_t row = 0; row < expected.size(); ++row) {
            if (std::isnan(expected[row])) QVERIFY(std::isnan(observed[row]));
            else QCOMPARE(observed[row], expected[row]);
        }
    }
};
int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    LinkedStructureCalculationTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "linked_structure_calculation_tests.moc"
