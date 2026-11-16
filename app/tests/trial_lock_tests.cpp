// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QDir>
#include <QEvent>
#include <QPointer>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest/QtTest>
#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <vector>

#include "assistant_view_model.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "engine_setup.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "session.hpp"

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
 void initTestCase() {
     use_fresh_settings();
     qunsetenv("EDI_ONLINE_SOURCES_FILE");
     const auto root = QString::fromUtf8(EDI_SOURCE_DIR);
     const auto cod = QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/cod/").toString();
     const auto edb =
         QUrl::fromLocalFile(root + "/tests/fixtures/online_sources/easydiffraction/").toString();
     qputenv("EDI_ONLINE_SOURCES", ("cod=" + cod + ";easydiffraction=" + edb).toUtf8());
 }
 void replacementOnlyDeletesItsOwnRetiredProject() {
     Session session(nullptr);
     QVERIFY(session.createProject(QStringLiteral("first"), {}));
     const QPointer<ProjectViewModel> previous(session.project());
     QVERIFY(previous);
     const QPointer<QObject> unrelated(new QObject(&session));
     unrelated->deleteLater();
     QVERIFY(session.createProject(QStringLiteral("second"), {}));
     QVERIFY(previous.isNull());
     QVERIFY(!unrelated.isNull());
     QCoreApplication::sendPostedEvents(unrelated, QEvent::DeferredDelete);
     QVERIFY(unrelated.isNull());
 }
    void settlementObservers_data() {
        QTest::addColumn<bool>("accepted");
        QTest::newRow("first-fit") << false;
        QTest::newRow("accepted-fit-without-setup") << true;
    }
    void settlementObservers() {
        QFETCH(bool, accepted);
        Session session(nullptr);
        QVERIFY(session.createProject(QStringLiteral("accepted"), {}));
        ProjectViewModel& project = *session.project();
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
            QVERIFY(!session.saveAs(QUrl::fromLocalFile(destination.filePath("saved"))));
            QVERIFY(session.lastError().contains("published"));
        });
        fit->ended(edi::FitReport{});
        QVERIFY(called);
        QCOMPARE(project.assistantProject()->metadata.name, std::string("accepted"));
        QVERIFY(!QFile::exists(destination.filePath("saved/project.edi")));
    }
    // A project with a structure and every experiment removed: the view model opens
    // it, and the admission, the common scale and its application answer nothing rather than throwing.
    void projectWithoutExperimentOpens() {
        edi::Project bare = model();
        while (!bare.experiments.empty()) bare.experiments.erase_at(0);  // every experiment removed
        QVERIFY(!edi::reflection_admission(bare, 0).has_value());
        QVERIFY(!edi::common_scale_factor(bare, 0).has_value());
        QVERIFY(!edi::apply_common_scale(bare, 0).applied);
        ProjectViewModel project(bare, nullptr);
        QVERIFY(project.assistantProject() != nullptr);
    }
    // A CIF from outside edi, with no edi item: a powder pattern loads as an experiment, its beam mode read from its
    // 2θ column and its profile at the defaults; a structure CIF given as an experiment is named as one.
    void externalCifLoadsAsExperiment() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        const QString pattern = dir.filePath("pattern.cif");
        {
            QFile file(pattern);
            QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Text));
            file.write("data_pattern\n_diffrn_radiation_wavelength.wavelength 1.5\nloop_\n_pd_meas.2theta_scan\n"
                       "_pd_meas.intensity_total\n_pd_meas.intensity_total_su\n10.0 100 10\n10.1 110 10.5\n10.2 120 11\n");
        }
        const edi::BraggPdExperiment experiment = edi::load_experiment_file(pattern.toStdString());
        QVERIFY(experiment.data.has_value());
        QCOMPARE(experiment.data->intensity_meas.get().size(), std::size_t{3});
        QCOMPARE(experiment.data->intensity_meas.get()[2], 120.0);
        QCOMPARE(experiment.effective_beam_mode(), edi::BeamModeEnum::CONSTANT_WAVELENGTH);
        const QString structure = dir.filePath("structure.cif");
        {
            QFile file(structure);
            QVERIFY(file.open(QIODevice::WriteOnly | QIODevice::Text));
            file.write("data_lbco\n_cell.length_a 3.88\n_cell.length_b 3.88\n_cell.length_c 3.88\n_cell.angle_alpha 90\n"
                       "_cell.angle_beta 90\n_cell.angle_gamma 90\n_space_group.name_H-M_alt 'P m -3 m'\nloop_\n"
                       "_atom_site.label\n_atom_site.type_symbol\n_atom_site.fract_x\n_atom_site.fract_y\n"
                       "_atom_site.fract_z\nLa La 0 0 0\n");
        }
        try {
            (void)edi::load_experiment_file(structure.toStdString());
            QFAIL("a structure CIF loaded as an experiment");
        } catch (const std::exception& refusal) {
            QVERIFY2(QString::fromUtf8(refusal.what()).contains("no measured pattern"), refusal.what());
        }
    }
    // The common scale on data load and phase changes (lbco + HRPT, the owner's cases, 2026-11-17). The expectation is
    // the closed form the owner chose, computed here from the arrays: the measured maximum above the 10th percentile
    // of the measured points over the calculated maximum above the background. Once scaled it is 1.
    static double peakRatioOf(const edi::Project& held) {
        edi::Project copy = held;
        copy.refresh_calculated_pattern();
        const auto& data = *copy.experiments[0]->data;
        const auto& meas = data.intensity_meas.get();
        std::vector<double> levels;
        double calculated = -std::numeric_limits<double>::infinity();
        for (std::size_t i = 0; i < meas.size() && i < data.intensity_calc.size(); ++i) {
            const double net = data.intensity_calc[i] - (i < data.intensity_bkg.size() ? data.intensity_bkg[i] : 0.0);
            if (!std::isfinite(net) || !std::isfinite(meas[i])) continue;
            levels.push_back(meas[i]);
            calculated = std::max(calculated, net);
        }
        if (levels.empty() || !(calculated > 0.0)) return 0.0;
        const double highest = *std::max_element(levels.begin(), levels.end());
        std::sort(levels.begin(), levels.end());
        return (highest - levels[levels.size() / 10]) / calculated;
    }
    static double tenthPercentile(const edi::Project& held) {
        std::vector<double> levels = held.experiments[0]->data->intensity_meas.get();
        std::sort(levels.begin(), levels.end());
        return levels[levels.size() / 10];
    }
    // The shipped LBCO project (HRPT's 1.494 Å) before any data, its phase scale back at 1 and no background points,
    // as a new experiment starts; `wavelength` replaces the instrument's.
    static edi::Project lbcoProject(std::optional<double> wavelength) {
        const QString root = QString::fromUtf8(EDI_SOURCE_DIR);
        edi::Project value =
            edi::load_project((root + "/docs/user/cli/pd-neut-cwl_lbco_simulation/project/project.edi").toStdString());
        edi::ExperimentBase& experiment = *value.experiments[0];
        experiment.background.clear();
        experiment.linked_structures[0]->scale.value = 1.0;
        if (wavelength) (*experiment.instrument.setup_wavelength).value = *wavelength;
        return value;
    }
    void dataLoadAndPhaseChangesKeepTheLevel() {
        const QUrl data = QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/app/tutorials/files/hrpt.xye");
        ProjectViewModel project(lbcoProject(std::nullopt), nullptr);  // HRPT's LBCO wavelength, 1.494 Å
        QSignalSpy notes(&project, &ProjectViewModel::information);
        QVERIFY(project.loadData(0, data));
        edi::Project& model = *project.assistantProject();
        edi::ExperimentBase& experiment = *model.experiments[0];
        QVERIFY(std::abs(peakRatioOf(model) - 1.0) < 1e-6);
        QVERIFY(std::abs(experiment.linked_structures[0]->scale.value.get() - 1.0) > 0.01);
        // One background point at the measured baseline, said in Messages; peaks that line up raise no warning.
        QCOMPARE(experiment.background.size(), std::size_t(1));
        QVERIFY(std::abs(experiment.background[0]->intensity.value.get() - tenthPercentile(model)) < 1e-9);
        bool warned = false;
        for (const auto& note : notes) warned = warned || note.at(0).toString().contains("do not line up");
        QVERIFY(!warned);
        edi::Structure second = *model.structures[0];
        second.name = "second";
        model.structures.push_back(second);
        edi::LinkedStructure link;
        link.structure_id = "second";
        edi::Edit::rescaled(model, experiment, edi::Edit::append(experiment.linked_structures, link))();
        QVERIFY(std::abs(peakRatioOf(model) - 1.0) < 1e-6);
        QCOMPARE(experiment.background.size(), std::size_t(1));  // an existing background is never replaced
        edi::Edit::rescaled(model, experiment, edi::Edit::erase(experiment.linked_structures, 1))();
        QVERIFY(std::abs(peakRatioOf(model) - 1.0) < 1e-6);
        // A phase change's undo takes back a background point the scale started.
        experiment.background.clear();
        auto before = edi::capture_experiment_links(model, experiment);
        edi::Edit::rescaled(model, experiment, edi::Edit::append(experiment.linked_structures, link))();
        QCOMPARE(experiment.background.size(), std::size_t(1));
        edi::Edit::restore_experiment_controls(model, std::move(before))();
        QCOMPARE(experiment.background.size(), std::size_t(0));
        QCOMPARE(experiment.linked_structures.size(), std::size_t(1));
        QVERIFY(project.loadData(0, data));  // the same file again is still a load
        QVERIFY(std::abs(peakRatioOf(*project.assistantProject()) - 1.0) < 1e-6);
    }
    // The owner's first case: the experiment's default 1 Å wavelength, so the calculated peaks miss HRPT's. The peak
    // heights still set the level, and Messages warns about the positions.
    void defaultWavelengthWarnsAndStillScales() {
        const QUrl data = QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/app/tutorials/files/hrpt.xye");
        ProjectViewModel project(lbcoProject(1.0), nullptr);  // the 1 Å a new experiment starts at
        QSignalSpy notes(&project, &ProjectViewModel::information);
        QVERIFY(project.loadData(0, data));
        QVERIFY(std::abs(peakRatioOf(*project.assistantProject()) - 1.0) < 1e-6);
        bool warned = false;
        for (const auto& note : notes) warned = warned || note.at(0).toString().contains("do not line up");
        QVERIFY(warned);
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
        Session session(nullptr);
        QVERIFY(session.openProject(
            QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project")));
        ProjectViewModel& project = *session.project();
        project.assistantProject()->report_html_offline = false;
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        QTemporaryDir output;
        const QDir folder(output.filePath("saved"));
        QVERIFY2(session.saveAs(QUrl::fromLocalFile(folder.path())), qPrintable(session.lastError()));
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
        Session session(nullptr);
        QVERIFY(session.openProject(
            QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project")));
        ProjectViewModel& project = *session.project();
        project.assistantProject()->minimizer_max_iterations = 2;
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
        bool fitted = false, adopted = false;
        project.fit()->startNative([&](const edi::FitReport& report, bool presented) {
            fitted = true;
            adopted = report.adopted() && presented;
        }, 0);
        QTRY_VERIFY_WITH_TIMEOUT(fitted, 30000);
        QVERIFY(!project.fit()->native_completion_);
        QVERIFY(adopted);
        QTemporaryDir output;
        const auto target = output.filePath("saved");
        {
            ProjectViewModel::AssistantEditScope edit(&project, 8);
            QVERIFY2(session.saveAs(QUrl::fromLocalFile(target)), qPrintable(session.lastError()));
        }
        const auto saved = edi::load_project(target.toStdString());
        QVERIFY(saved.experiment().peak.broad_gauss_u->free.get());
        QCOMPARE(saved.experiment().peak.broad_gauss_u->value.get(), coefficient->value.get());
        QVERIFY(!project.fit()->trialOpen());
    }
    void observerCannotSaveCopyDuringOwnEdit_data() {
        QTest::addColumn<bool>("existing");
        QTest::newRow("fresh-folder") << false;
        QTest::newRow("existing-folder") << true;
    }
    void observerCannotSaveCopyDuringOwnEdit() {
        QFETCH(bool, existing);
        Session session(nullptr);
        const auto source = QString::fromUtf8(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project";
        QVERIFY(session.openProject(QUrl::fromLocalFile(source)));
        auto* project = session.project();
        QVERIFY(project);
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 30000);
        project->setModified(false);
        candidate(*project);
        QTemporaryDir output;
        const auto destination = existing ? output.path() : output.filePath("foreign");
        bool observed = false, saved = false;
        connect(project, &ProjectViewModel::modifiedChanged, this, [&] {
            if (observed) return;
            observed = true;
            saved = session.saveProjectAs(QUrl::fromLocalFile(destination), false, true);
        });
        {
            ProjectViewModel::AssistantEditScope edit(project, 7);
            const auto result = project->applyRecordedEdit(edi::Edit::assign(project->assistantProject()->metadata.title, std::string("candidate")), false);
            QVERIFY2(result.applied, qPrintable(result.message));
        }
        QVERIFY(observed);
        QVERIFY(!saved);
        QVERIFY(!QFile::exists(QDir(destination).filePath("project.edi")));
    }
    void assistantCanAddSharedSiteRelationAndFit() {
        auto source = edi::load_project(std::string(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project");
        source.aliases.clear();
        source.constraints.clear();
        source.minimizer_max_iterations = 2;
        auto* la = &source.structures[0]->atom_sites[0]->adp_iso;
        auto* ba = &source.structures[0]->atom_sites[1]->adp_iso;
        for (const auto& slot : edi::named_slots(source)) {
            slot.parameter->free = slot.parameter == ba;
            if (slot.parameter != la && slot.parameter != ba) continue;
            edi::ParameterAlias alias;
            alias.id = slot.parameter == la ? "b_la" : "b_ba";
            alias.parameter_unique_name = slot.unique_name;
            source.aliases.push_back(alias);
        }
        ProjectViewModel project(std::move(source), nullptr);
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        candidate(project);
        ProjectEditor::RelationAction action;
        action.kind = ProjectEditor::RelationAction::Kind::ConstraintAppend;
        action.text = "shared_biso";
        action.expression = "b_la = b_ba";
        action.enabled = true;
        {
            ProjectViewModel::AssistantEditScope edit(&project, 7);
            auto input = project.prepareWidgetRelations(action);
            const auto result = project.analysis()->constraints()->appendComplete(action.text, action.expression, true);
            project.finishWidgetRelations(input);
            QVERIFY2(result.applied && result.published, qPrintable(result.message));
            QVERIFY(input->consumed);
            QCOMPARE(input->applied_result.constraint, project.assistantProject()->constraints[0].get());
        }
        QTRY_VERIFY_WITH_TIMEOUT(!project.calculating(), 30000);
        QCOMPARE(project.assistantProject()->constraints.size(), std::size_t(1));
        bool completed = false, adopted = false;
        project.fit()->startNative([&](const edi::FitReport& report, bool presented) {
            completed = true;
            adopted = report.adopted() && presented;
        }, 0);
        QTRY_VERIFY_WITH_TIMEOUT(completed, 30000);
        QVERIFY(adopted);
        const auto& structure = *project.assistantProject()->structures[0];
        QVERIFY(std::abs(structure.atom_sites[0]->adp_iso.value.get() - structure.atom_sites[1]->adp_iso.value.get()) < 1e-8);
        QCOMPARE(project.assistantProject()->constraints[0]->expression.value(), std::string("b_la = b_ba"));
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
