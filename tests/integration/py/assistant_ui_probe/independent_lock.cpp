// SPDX-License-Identifier: BSD-3-Clause
#include <QDir>
#include <QFile>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QSettings>
#include <QtQml/qqmlextensionplugin.h>
#include "../../../../app/tests/assistant_test_settings.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)
#include <QTemporaryDir>
#include <QtTest/QtTest>
#include "project_view_model.hpp"
#include "fit_view_model.hpp"
#include "engine_setup.hpp"

namespace edi_app {
class TrialLockTests : public QObject {
    Q_OBJECT
    static edi::Project initial() {
        edi::Project p;
        p.metadata.name = "reference";
        edi::Structure s;
        s.name = "reference_cell";
        s.cell.length_a.value = 3.625;
        p.structures.push_back(s);
        return p;
    }
    static void begin(ProjectViewModel& p) {
        auto* f = p.fit();
        f->accepted_fit_ = std::make_shared<const edi::Project>(*p.assistantProject());
        f->markCandidate(41);
        f->setAssistantBusy(true);
    }
private slots:
    void initTestCase() { use_fresh_settings(); }
    void freshAssistantTestsUseTheRequestedModelAndKeepExplicitChoices() {
        QQmlApplicationEngine engine;
        configure_engine(engine);
        test::assistant_defaults();
        QSettings settings(settings_file_path(), QSettings::IniFormat);
        const QString key = QStringLiteral("Assistant/Providers/chatgpt/selection");
        QVERIFY2(settings.value(key).toStringList() == QStringList({"gpt-6-luna", "medium"}),
                 "Fresh assistant test settings must select GPT-6-Luna at medium effort");
        settings.setValue(key, QStringList({"explicit-model", "high"}));
        settings.sync();
        test::assistant_defaults();
        settings.sync();
        QVERIFY2(settings.value(key).toStringList() == QStringList({"explicit-model", "high"}),
                 "Test defaults must preserve an explicitly selected model and effort");
    }
    void downloadLinkUsesTheAboutLinkStyleInBothThemes() {
        QQmlApplicationEngine engine;
        configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(R"(
            import QtQuick
            import EasyApplication.Gui.Style as Style
            import edi.app
            Item {
                IconLink { objectName: "aboutReference"; text: "Download"; fontIcon: "external-link-alt" }
                AssistantDownloadLink { objectName: "downloadSubject" }
                function theme(dark) {
                    Style.Colors.theme = dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
                }
            }
        )", QUrl());
        QScopedPointer<QObject> root(component.create());
        QVERIFY2(root, qPrintable(component.errorString()));
        auto* reference = root->findChild<QObject*>("aboutReference");
        auto* subject = root->findChild<QObject*>("downloadSubject");
        QVERIFY2(reference && subject, "The About-style reference and popup link must instantiate");
        for (bool dark : {false, true}) {
            QVERIFY2(QMetaObject::invokeMethod(root.data(), "theme", Q_ARG(QVariant, dark)),
                     "The style comparison must exercise both app themes");
            for (const char* property : {"color", "font", "fontIcon"})
                QVERIFY2(reference->property(property) == subject->property(property),
                         "The assistant download link must share the About link's presentation");
            QVERIFY2(subject->property("text").toString().contains("page"),
                     "The download link must explain that it opens a page");
        }
    }
    void observersCannotEditOrSaveDuringSettlement() {
        ProjectViewModel p(initial(), nullptr);
        const auto acceptedCell = p.assistantProject()->structures[0]->cell.length_a.value.get();
        begin(p);
        auto* f = p.fit();
        f->running_ = true;
        f->native_completion_ = [](const edi::FitReport&, bool) {};
        QTemporaryDir output;
        bool reached = false, edit_refused = false, save_refused = false;
        connect(f, &FitViewModel::runningChanged, this, [&] {
            if (f->running()) return;
            reached = true;
            auto& a = p.assistantProject()->structures[0]->cell.length_a;
            edit_refused = !p.applyRecordedEdit(edi::Edit::value(a, 17.125), false).applied;
            save_refused = !p.saveTo(output.path()).isEmpty();
        });
        f->ended(edi::FitReport{});
        QVERIFY2(reached && edit_refused && save_refused,
                 "A settlement observer must reach and be refused by both write entrances");
        QVERIFY2(p.assistantProject()->structures[0]->cell.length_a.value.get() == acceptedCell,
                 "Settlement observers must preserve the accepted cell value");
        QVERIFY2(QDir(output.path()).entryList(QDir::Files).isEmpty(),
                 "A refused settlement save must leave no project files");
    }
    void stopCannotRestoreAnotherOwner() {
        ProjectViewModel p(initial(), nullptr);
        begin(p);
        auto* f = p.fit();
        f->running_ = true;
        f->restoreAcceptedOnStop(41);
        p.assistantProject()->structures[0]->cell.length_a.value = 8.875;
        f->native_completion_ = [&](const edi::FitReport&, bool) { f->candidate_owner_ = 42; };
        f->ended(edi::FitReport{});
        QVERIFY2(p.assistantProject()->structures[0]->cell.length_a.value.get() == 8.875,
                 "A stopped trial must not restore over the successor owner's candidate");
    }
    void markerUnwindsOnExceptionAndDeletedOwner() {
        ProjectViewModel p(initial(), nullptr);
        try {
            ProjectViewModel::AssistantEditScope scope(&p, 73);
            throw std::runtime_error("fixture exit");
        } catch (const std::runtime_error&) {}
        QVERIFY2(p.assistant_edit_ == 0, "An exceptional assistant edit must release its marker");
        auto* retired = new ProjectViewModel(initial(), nullptr);
        auto scope = std::make_unique<ProjectViewModel::AssistantEditScope>(retired, 74);
        delete retired;
        scope.reset();
        QVERIFY2(p.assistant_edit_ == 0, "Retiring another owner must preserve the current marker");
    }
    void notificationCannotLendItsWriteExemption() {
        ProjectViewModel p(initial(), nullptr);
        begin(p);
        p.assistant_edit_ = 73;
        bool reached = false, refused = false;
        connect(&p, &ProjectViewModel::projectEdited, this, [&] {
            reached = true;
            refused = !p.criticalEditRefusal().isEmpty() && !p.saveRefusal(false).isEmpty();
        });
        p.notifyProjectEdited(73);
        QVERIFY2(reached && refused, "Edit observers cannot borrow the assistant's active marker");
        QVERIFY2(p.assistant_edit_ == 73, "The assistant's own continuation must keep its edit marker");
        p.assistant_edit_ = 0;
    }
    void structureViewAndReportCannotWriteDuringTrial() {
        ProjectViewModel p(initial(), nullptr);
        QTemporaryDir output;
        p.assistantProject()->path = output.path().toStdString();
        begin(p);
        const bool labels = p.structureViewOptions()->showLabels();
        p.structureViewOptions()->setShowLabels(!labels);
        QVERIFY2(p.structureViewOptions()->showLabels() == labels,
                 "Persisted Structure view changes must respect the trial lock");
        QSignalSpy failed(p.report(), &ReportViewModel::saveFailed);
        p.report()->saveReport(QStringLiteral("sans-serif"));
        QVERIFY2(failed.size() == 1 && !QDir(output.path()).exists("reports"),
                 "A report refused by trial ownership must publish no files");
    }
    void rollbackRemovesOnlyTrialReportFiles() {
        ProjectViewModel p(initial(), nullptr);
        QTemporaryDir output;
        p.assistantProject()->path = output.path().toStdString();
        begin(p);
        QDir(output.path()).mkdir("reports");
        const auto reportPath = output.filePath("reports/trial.html");
        QFile report(reportPath);
        QVERIFY2(report.open(QIODevice::WriteOnly), "The trial report fixture must be created");
        report.write("trial report");
        report.close();
        QFile unrelated(output.filePath("reports/notes.txt"));
        QVERIFY2(unrelated.open(QIODevice::WriteOnly), "The unrelated file fixture must be created");
        unrelated.write("keep");
        unrelated.close();
        edi::ReportFile row;
        row.name = "trial.html";
        row.format = "html";
        p.assistantProject()->report_files.push_back(std::move(row));
        QVERIFY2(p.fit()->restoreAccepted(41), "The trial owner must restore the accepted project");
        QVERIFY2(!QFile::exists(reportPath), "Whole-project rollback must remove the trial's report file");
        QVERIFY2(QFile::exists(unrelated.fileName()), "Rollback must preserve unrelated report-folder files");
    }
    void interruptedSecondFitRestoresFirstRecord() {
        ProjectViewModel p(initial(), nullptr);
        p.assistantProject()->fit_result.fitting_time = 1.375;
        const auto acceptedCell = p.assistantProject()->structures[0]->cell.length_a.value.get();
        begin(p);
        auto* f = p.fit();
        p.assistantProject()->fit_result.fitting_time = 9.125;
        p.assistantProject()->structures[0]->cell.length_a.value = 7.25;
        f->running_ = true;
        f->submitted_single_joint_ = true;
        f->submitted_attempt_ = f->latest_attempt_ = 2;
        f->restoreAcceptedOnStop(41);
        edi::FitReport result;
        result.status = edi::FitStatus::DONE;
        result.result.emplace();
        f->ended(result);
        QVERIFY2(p.assistantProject()->fit_result.fitting_time == 1.375 &&
                 p.assistantProject()->structures[0]->cell.length_a.value.get() == acceptedCell,
                 "Transport interruption during fit B must restore fit A's model and record together");
    }
};
}
QTEST_MAIN(edi_app::TrialLockTests)
#include "independent_lock.moc"
