// SPDX-License-Identifier: BSD-3-Clause
#include <QtTest/QtTest>
#include <QTemporaryDir>
#include <QDir>
#include "project_view_model.hpp"
#include "fit_view_model.hpp"
#include "assistant_view_model.hpp"
#include "edi/io.hpp"
#include "engine_setup.hpp"

namespace edi_app {
class TrialLockTests : public QObject {
    Q_OBJECT
    static edi::Project model() {
        edi::Project value;
        value.metadata.name = "accepted";
        edi::Structure structure;
        structure.name = "sample";
        value.structures.push_back(structure);
        return value;
    }
    static void candidate(ProjectViewModel& project) {
        auto* fit = project.fit();
        fit->accepted_fit_ = std::make_shared<const edi::Project>(*project.assistantProject());
        fit->candidate_ = true;
        fit->candidate_owner_ = 11;
        fit->setAssistantBusy(true);
    }
private slots:
    void initTestCase() { use_fresh_settings(); }
    void settlementObservers_data() {
        QTest::addColumn<bool>("accepted");
        QTest::newRow("first-fit") << false;
        QTest::newRow("accepted-fit-without-setup") << true;
    }
    void settlementObservers() {
        QFETCH(bool, accepted);
        ProjectViewModel project(model(), nullptr);
        auto* fit = project.fit();
        if (accepted) fit->accepted_fit_ = std::make_shared<const edi::Project>(*project.assistantProject());
        fit->running_ = true;
        fit->native_completion_ = [](const edi::FitReport&, bool) {};
        QTemporaryDir destination;
        bool called = false;
        connect(fit, &FitViewModel::runningChanged, this, [&] {
            if (fit->running()) return;
            called = true;
            QVERIFY(fit->trialOpen());
            const auto outcome = project.applyRecordedEdit(edi::Edit::assign(project.assistantProject()->metadata.name, std::string("foreign")), false);
            QVERIFY(!outcome.applied);
            QVERIFY(outcome.message.contains("published"));
            QVERIFY(project.saveTo(destination.path()).contains("published"));
        });
        fit->ended(edi::FitReport{});
        QVERIFY(called);
        QCOMPARE(project.assistantProject()->metadata.name, std::string("accepted"));
        QVERIFY(QDir(destination.path()).entryList(QDir::Files).isEmpty());
    }
    void stopKeepsOriginalOwner() {
        ProjectViewModel project(model(), nullptr);
        candidate(project);
        auto* fit = project.fit();
        fit->running_ = true;
        fit->restoreAcceptedOnStop(11);
        project.assistantProject()->structures[0]->cell.length_a.value = 9.0;
        fit->native_completion_ = [&](const edi::FitReport&, bool) { fit->candidate_owner_ = 22; };
        fit->ended(edi::FitReport{});
        QCOMPARE(project.assistantProject()->structures[0]->cell.length_a.value.get(), 9.0);
    }
    void stopDoesNotRestoreANewerAttempt() {
        ProjectViewModel project(model(), nullptr);
        candidate(project);
        auto* fit = project.fit();
        fit->submitted_attempt_ = fit->latest_attempt_ = 1;
        fit->running_ = true;
        fit->restoreAcceptedOnStop(11);
        project.assistantProject()->structures[0]->cell.length_a.value = 8.0;
        fit->native_completion_ = [&](const edi::FitReport&, bool) { fit->latest_attempt_ = 2; };
        fit->ended(edi::FitReport{});
        QCOMPARE(project.assistantProject()->structures[0]->cell.length_a.value.get(), 8.0);
    }
    void viewSettingsRefusedDuringTrial() {
        ProjectViewModel project(model(), nullptr);
        candidate(project);
        const auto before = project.assistantProject()->structures[0]->view.get();
        project.structureViewOptions()->setShowLabels(!project.structureViewOptions()->showLabels());
        QCOMPARE(project.assistantProject()->structures[0]->view.get(), before);
        QVERIFY(!project.lastError().isEmpty());
    }
    void reportRefusedBeforeWriting() {
        ProjectViewModel project(model(), nullptr);
        QTemporaryDir folder;
        project.assistantProject()->path = folder.path().toStdString();
        candidate(project);
        QSignalSpy failure(project.report(), &ReportViewModel::saveFailed);
        project.report()->saveReport(QStringLiteral("sans-serif"));
        QCOMPARE(failure.size(), 1);
        QVERIFY(!QDir(folder.path()).exists("reports"));
        QVERIFY(project.assistantProject()->report_files.empty());
    }
    void reportBetweenTurnsRetiresCandidate() {
        auto source = edi::load_project(std::string(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project");
        source.report_html_offline = false;
        ProjectViewModel project(std::move(source), nullptr);
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        QTemporaryDir folder;
        const auto saved = project.saveTo(folder.path());
        QVERIFY2(saved.isEmpty(), qPrintable(saved));
        AssistantViewModel assistant;
        assistant.setProject(&project);
        candidate(project);
        project.fit()->setAssistantBusy(false);
        QSignalSpy failures(project.report(), &ReportViewModel::saveFailed);
        project.report()->saveReport(QStringLiteral("sans-serif"));
        QCOMPARE(failures.size(), 0);
        QVERIFY(!project.assistantProject()->report_files.empty());
        for (const auto& row : project.assistantProject()->report_files)
            QVERIFY(QFile::exists(folder.filePath("reports/" + QString::fromStdString(row->name.value()))));
        const auto disk = edi::load_project(folder.path().toStdString());
        QCOMPARE(disk.report_files.size(), project.assistantProject()->report_files.size());
        QVERIFY(!project.fit()->candidate_);
        QVERIFY(!project.fit()->restoreAccepted(11));
        for (const auto& row : project.assistantProject()->report_files)
            QVERIFY(QFile::exists(folder.filePath("reports/" + QString::fromStdString(row->name.value()))));
    }
    void assistantFollowupCanFreeAndSave() {
        const auto source = std::string(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project";
        ProjectViewModel project(edi::load_project(source), nullptr);
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        candidate(project);
        auto& coefficient = project.assistantProject()->experiment().peak.broad_gauss_u;
        {
            ProjectViewModel::AssistantEditScope edit(&project, 7);
            const auto result = project.applyRecordedEdit(edi::Edit::assign(coefficient->free, true), false);
            QVERIFY2(result.applied, qPrintable(result.message));
        }
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        QVERIFY(coefficient->free.get());
        QTemporaryDir target;
        {
            ProjectViewModel::AssistantEditScope edit(&project, 8);
            const auto error = project.saveTo(target.path());
            QVERIFY2(error.isEmpty(), qPrintable(error));
        }
        const auto saved = edi::load_project(target.path().toStdString());
        QVERIFY(saved.experiment().peak.broad_gauss_u->free.get());
        QCOMPARE(saved.experiment().peak.broad_gauss_u->value.get(), coefficient->value.get());
        QVERIFY(!project.fit()->trialOpen());
    }
    void retiringEditClearsOriginalProject() {
        ProjectViewModel original(model(), nullptr), successor(model(), nullptr);
        std::optional<ProjectViewModel::AssistantEditScope> edit;
        edit.emplace(&original, 7);
        QCOMPARE(original.assistant_edit_, std::uint64_t(7));
        edit.reset();
        QCOMPARE(original.assistant_edit_, std::uint64_t(0));
        edit.emplace(&successor, 8);
        QCOMPARE(original.assistant_edit_, std::uint64_t(0));
        edit.reset();
        QCOMPARE(successor.assistant_edit_, std::uint64_t(0));
    }
    void notificationCannotBorrowAssistantMarker() {
        ProjectViewModel project(model(), nullptr);
        candidate(project);
        project.assistant_edit_ = 7;
        connect(&project, &ProjectViewModel::projectEdited, this, [&] {
            QVERIFY(!project.criticalEditRefusal().isEmpty());
            QVERIFY(!project.saveRefusal().isEmpty());
        });
        project.notifyProjectEdited(7);
        QVERIFY(project.criticalEditRefusal().isEmpty());
        project.assistant_edit_ = 0;
        QVERIFY(!project.criticalEditRefusal().isEmpty());
    }
    void transportStopRestoresCompletedFit() {
        ProjectViewModel project(model(), nullptr);
        project.assistantProject()->fit_result.fitting_time = 1.0;
        candidate(project);
        auto* fit = project.fit();
        fit->running_ = true;
        fit->submitted_single_joint_ = true;
        fit->submitted_attempt_ = 1;
        fit->latest_attempt_ = 1;
        project.assistantProject()->structures[0]->cell.length_a.value = 7.0;
        project.assistantProject()->fit_result.fitting_time = 2.0;
        fit->restoreAcceptedOnStop(11);
        edi::FitReport report;
        report.status = edi::FitStatus::DONE;
        report.result.emplace();
        fit->ended(report);
        QCOMPARE(project.assistantProject()->structures[0]->cell.length_a.value.get(), 1.0);
        QCOMPARE(project.assistantProject()->fit_result.fitting_time, 1.0);
    }
};
}
QTEST_MAIN(edi_app::TrialLockTests)
#include "trial_lock_tests.moc"
