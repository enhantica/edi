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

#include "analysis_view_model.hpp"
#include "assistant_view_model.hpp"
#include "edi/categories.hpp"
#include "edi/display.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "engine_setup.hpp"
#include "fit_view_model.hpp"
#include "parameter_item.hpp"
#include "project_view_model.hpp"
#include "load_wait.hpp"
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
        if (!experiment.data) QFAIL("the CIF loaded no measured data");
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
        const auto& measured = copy.experiments[0]->data;
        if (!measured) return 0.0;
        const auto& data = *measured;
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
        const auto& measured = held.experiments[0]->data;
        if (!measured) return 0.0;
        std::vector<double> levels = measured->intensity_meas.get();
        if (levels.empty()) return 0.0;
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
        QVERIFY(wait_for_load(project, project.loadData(0, data)));
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
        QVERIFY(wait_for_load(project, project.loadData(0, data)));  // the same file again is still a load
        QVERIFY(std::abs(peakRatioOf(*project.assistantProject()) - 1.0) < 1e-6);
    }
    // A new project declares no minimizer settings and shows the defaults the owner chose (2026-11-17): 50 iterations,
    // a chi-square change of 1e-4 and magnetic moments kept free.
    void newProjectShowsTheMinimizerDefaults() {
        Session session(nullptr);
        QVERIFY(session.createProject(QStringLiteral("defaults"), {}));
        const AnalysisViewModel& analysis = *session.project()->analysis();
        QVERIFY(!analysis.hasMaxIterations());
        QVERIFY(!analysis.hasChiSquareTolerance());
        QCOMPARE(analysis.defaultMaxIterations(), 50);
        QCOMPARE(analysis.defaultChiSquareTolerance(), 1e-4);
        QCOMPARE(analysis.momentsNearZero(), QStringLiteral("keep_free"));
    }
    // One excluded region may be written as items instead of a loop; it is read, not passed over.
    void excludedRegionWrittenAsItemsIsRead() {
        const edi::Project held = lbcoProject(std::nullopt);
        const std::string relative = "experiments/hrpt.edi";
        std::string text;
        for (const auto& [name, file] : edi::project_edi_files(held)) {
            if (name == relative) text = file;
        }
        QVERIFY(!text.empty());
        QVERIFY(text.find("_excluded_region") == std::string::npos);
        text += "\n_excluded_region.start 10\n_excluded_region.end 12.5\n";
        const edi::Project read = edi::project_with_file_text(held, relative, text);
        const auto& regions = read.experiments[0]->excluded_regions;
        QCOMPARE(regions.size(), std::size_t(1));
        QCOMPARE(regions[0]->first.get(), 10.0);
        QCOMPARE(regions[0]->second.get(), 12.5);
        // A powder's region is on its pattern's axis: naming one is refused, written either way.
        bool refused = false;
        try {
            edi::project_with_file_text(held, relative, text + "_excluded_region.axis d_spacing\n");
        } catch (const std::exception&) {
            refused = true;
        }
        QVERIFY(refused);
    }
    // The Analysis slider never reaches outside a parameter's admissible range. The expectations are worked by hand from
    // the rule: value ± half width rounded outward to a whole unit, a side cut at a limit giving its width to the other.
    void sliderStaysInsideTheLimits() {
        const double inf = std::numeric_limits<double>::infinity();
        const auto is = [](std::pair<double, double> got, double from, double to) {
            return std::abs(got.first - from) < 1e-12 && std::abs(got.second - to) < 1e-12;
        };
        QVERIFY(is(edi::slider_limits(0.0, 1e-3, 0.01, 0.0, 10.0), 0.0, 0.01));      // B iso 0: from 0, one step up
        QVERIFY(is(edi::slider_limits(4e-4, 1e-3, 1e-4, 0.0, 10.0), 0.0, 0.002));    // near a limit: the full width above
        QVERIFY(is(edi::slider_limits(1.0, 0.5, 0.01, 0.0, 1.0), 0.0, 1.0));         // occupancy at its maximum: width 1 below
        QVERIFY(is(edi::slider_limits(10.0, 5.0, 0.01, 0.0, 10.0), 0.0, 10.0));      // a width over the whole range
        QVERIFY(is(edi::slider_limits(3.84127, 0.05, 1e-5, 0.0, inf), 3.79, 3.9));   // a cell length, inside its range
        QVERIFY(is(edi::slider_limits(-2.0, 1.0, 0.1, -inf, inf), -3.0, -1.0));      // no limits
        QVERIFY(is(edi::slider_limits(-1.0, 0.5, 0.01, 0.0, 10.0), 0.0, 1.0));       // a value kept below its range
        // Every parameter of a project with values at their limits: B iso 0, occupancy 1.
        edi::Project held = lbcoProject(std::nullopt);
        for (const auto& site : held.structures[0]->atom_sites) {
            site->adp_iso.value = 0.0;
            site->occupancy.value = 1.0;
        }
        ProjectViewModel project(std::move(held), nullptr);
        int checked = 0;
        for (const edi::NamedSlot& slot : edi::named_slots(*project.assistantProject())) {
            const ParameterItem* item = project.parameterNamed(QString::fromStdString(slot.unique_name));
            if (item == nullptr) continue;
            QVERIFY2(item->sliderLower() >= item->minimum() && item->sliderUpper() <= item->maximum() &&
                         item->sliderUpper() > item->sliderLower(),
                     slot.unique_name.c_str());
            ++checked;
        }
        QVERIFY(checked > 10);
    }
    // An open's warning about a value in one file leaves Messages once a Text-tab edit of that file corrects it; a refused
    // edit changes nothing there, and Undo of the correction brings the warning back.
    void textEditSettlesTheOpensWarning() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        const QDir source(QString::fromUtf8(EDI_SOURCE_DIR) + "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project");
        for (const QString& folder : {QStringLiteral("."), QStringLiteral("analysis"), QStringLiteral("structures"),
                                     QStringLiteral("experiments")}) {
            QVERIFY(QDir(dir.path()).mkpath(folder));
            for (const QString& name : QDir(source.filePath(folder)).entryList({QStringLiteral("*.edi")}, QDir::Files))
                QVERIFY(QFile::copy(source.filePath(folder + "/" + name), dir.filePath(folder + "/" + name)));
        }
        const QString relative = QStringLiteral("structures/lbco.edi");
        QFile structure(dir.filePath(relative));
        QVERIFY(structure.open(QIODevice::ReadOnly));
        const QString good = QString::fromUtf8(structure.readAll());
        structure.close();
        const QString row = QStringLiteral("Co Co 0.5 0.5 0.5 b 1 0.5() Biso");
        QVERIFY(good.contains(row));
        QString bad = good;
        bad.replace(row, QStringLiteral("Co Co 0.5 0.5 0.5 b 1 -0.5() Biso"));
        QVERIFY(structure.open(QIODevice::WriteOnly | QIODevice::Truncate));
        structure.write(bad.toUtf8());
        structure.close();
        Session session(nullptr);
        QVERIFY(session.openProject(QUrl::fromLocalFile(dir.path())));
        ProjectViewModel& project = *session.project();
        WarningListModel& messages = *session.loadWarnings();
        const QString opened = WarningListModel::fileKey(QStringLiteral("load-file:"), relative, {});
        QCOMPARE(messages.keys(opened).size(), 1);
        // A refused edit (an unknown category) leaves the warning.
        QVERIFY(!project.applyText(relative, good + QStringLiteral("\n_no_such_category.item 1\n")).isEmpty());
        QCOMPARE(messages.keys(opened).size(), 1);
        QVERIFY2(project.applyText(relative, good).isEmpty(), "the corrected text applies");
        QVERIFY(messages.keys(opened).isEmpty());
        QVERIFY(messages.keys(QStringLiteral("text-apply:")).isEmpty());
        project.undo();
        QCOMPARE(messages.keys(WarningListModel::fileKey(QStringLiteral("text-apply:"), relative, {})).size(), 1);
    }
    // Several files loaded as separate experiments: each new one takes the scale and the one background point, the
    // Messages line about it comes with the addition, and one Undo takes all of it back.
    void separateExperimentsKeepTheBackgroundPoint() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        const QString source = QString::fromUtf8(EDI_SOURCE_DIR) + "/app/tutorials/files/hrpt.xye";
        QList<QUrl> files;
        for (const QString& name : {QStringLiteral("first.xye"), QStringLiteral("second.xye")}) {
            QVERIFY(QFile::copy(source, dir.filePath(name)));
            files.append(QUrl::fromLocalFile(dir.filePath(name)));
        }
        ProjectViewModel project(lbcoProject(std::nullopt), nullptr);
        QSignalSpy notes(&project, &ProjectViewModel::information);
        QVERIFY(wait_for_load(project, project.loadDatasets(project.experimentModels().value(0), files, false)));
        const edi::Project& model = *project.assistantProject();
        QCOMPARE(model.experiments.size(), std::size_t(3));
        int started = 0;
        for (const auto& note : notes) started += note.at(0).toString().contains("one was added") ? 1 : 0;
        QCOMPARE(started, 2);
        for (std::size_t i = 1; i < model.experiments.size(); ++i) {
            edi::Project alone = model;
            std::vector<edi::ItemVec<edi::BraggPdExperiment>::Ptr> held{alone.experiments[i]};
            alone.experiments.assign(std::move(held));
            alone.adopt_experiments();
            QCOMPARE(alone.experiments[0]->background.size(), std::size_t(1));
            QVERIFY(std::abs(alone.experiments[0]->background[0]->intensity.value.get() - tenthPercentile(alone)) < 1e-9);
            QVERIFY(std::abs(peakRatioOf(alone) - 1.0) < 1e-6);
        }
        project.undo();
        QCOMPARE(project.assistantProject()->experiments.size(), std::size_t(1));
    }
    // The owner's first case: the experiment's default 1 Å wavelength, so the calculated peaks miss HRPT's. The peak
    // heights still set the level, and Messages warns about the positions.
    void defaultWavelengthWarnsAndStillScales() {
        const QUrl data = QUrl::fromLocalFile(QString::fromUtf8(EDI_SOURCE_DIR) + "/app/tutorials/files/hrpt.xye");
        ProjectViewModel project(lbcoProject(1.0), nullptr);  // the 1 Å a new experiment starts at
        QSignalSpy notes(&project, &ProjectViewModel::information);
        QVERIFY(wait_for_load(project, project.loadData(0, data)));
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
