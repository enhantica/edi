// SPDX-License-Identifier: BSD-3-Clause
// Which file an error report attaches (ADR-0063): every load route, each failure carrying only the file its own attempt
// failed on. Each route is tried against an earlier attempt's file (a later refusal that read nothing), an attempt
// started while another is being reported, and an example whose download answers after another open failed.
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest/QtTest>
#include <cmath>

#include "edi/project_archive.hpp"
#include "engine_setup.hpp"
#include "example_list_model.hpp"
#include "experiment_view_model.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
#include "structure_view_model.hpp"

// The load refuses, and its refusal attaches `file` (by name; empty for none).
#define REFUSES(call, file)                                   \
    do {                                                      \
        QVERIFY2(!(call), #call " did not refuse");           \
        QCOMPARE(refusals.last(), QStringLiteral(file));      \
    } while (false)

namespace edi_app {
namespace {

const QString kFixtures = QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/app_cases/load_failure");

QUrl fixture(const QString& relative) { return QUrl::fromLocalFile(kFixtures + u'/' + relative); }
// A file by name; one that is gone by the time it is checked is marked, as its popup could no longer attach it.
QString name(const QString& path) {
    if (path.isEmpty()) return {};
    return (QFileInfo(path).isFile() ? QString() : QStringLiteral("gone:")) + QFileInfo(path).fileName();
}
QByteArray bytes(const QString& path) {
    QFile file(path);
    return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray();
}

// The file each loadFailed carried, by name.
QStringList loadFailures(const QSignalSpy& spy) {
    QStringList files;
    for (const QList<QVariant>& arguments : spy) files.append(name(arguments.at(1).toString()));
    return files;
}

}  // namespace

class LoadAttemptTests : public QObject {
    Q_OBJECT
    QTemporaryDir collection_;
    QString missingExample_, brokenExample_;

    // The file a project refusal attaches, asked while the refusal is announced, as the error popup asks.
    struct Refusals {
        QStringList files;
        QMetaObject::Connection connection;
        explicit Refusals(ProjectViewModel* project) {
            connection = QObject::connect(project, &ProjectViewModel::refused, project, [this, project](const QString& message) {
                files.append(name(project->takeRefusedFile(message)));
            });
        }
        ~Refusals() { QObject::disconnect(connection); }
        QString last() const { return files.isEmpty() ? QStringLiteral("<no refusal>") : files.last(); }
    };

    static ProjectViewModel* freshProject(Session& session) {
        if (!session.createProject(QStringLiteral("attempts"), {})) return nullptr;
        return session.project();
    }

private slots:
    void initTestCase() {
        use_fresh_settings();
        // A private collection: one bundled example whose download is not there, one whose project cannot be read.
        const QStringList bundled = ExampleListModel::bundledIds();
        QVERIFY(bundled.size() >= 2);
        missingExample_ = bundled.at(0);
        brokenExample_ = bundled.at(1);
        QVERIFY(collection_.isValid());
        QVERIFY(QDir(collection_.path()).mkpath(QStringLiteral("projects")));
        const QString zip = collection_.filePath(QStringLiteral("projects/broken.zip"));
        edi::write_project_archive((kFixtures + QStringLiteral("/bad_structure")).toStdString(), zip.toStdString());
        QFile archive(zip);
        QVERIFY(archive.open(QIODevice::ReadOnly));
        const QByteArray bytes = archive.readAll();
        const QString entry = QStringLiteral(
            R"({"id":"%1","kind":"project","name":"%1","files":[{"path":"%2","format":"zip","sha256":"%3","bytes":%4}]})");
        const QString index = QStringLiteral(R"({"schema":"edi-data-index/1","entries":[%1,%2]})")
                                  .arg(entry.arg(missingExample_, QStringLiteral("projects/missing.zip"), QString(64, u'0')).arg(10),
                                       entry.arg(brokenExample_, QStringLiteral("projects/broken.zip"),
                                                 QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()))
                                           .arg(bytes.size()));
        QFile out(collection_.filePath(QStringLiteral("index.json")));
        QVERIFY(out.open(QIODevice::WriteOnly));
        out.write(index.toUtf8());
        out.close();
        qunsetenv("EDI_ONLINE_SOURCES_FILE");
        const QString url = QUrl::fromLocalFile(collection_.path() + u'/').toString();
        qputenv("EDI_ONLINE_SOURCES", ("cod=" + url + ";easydiffraction=" + url).toUtf8());
    }

    // Open, Recent (the same Session.openProject), a zip, a URL, a missing folder and an unknown example: a failure
    // that read no file attaches none, even right after one that did.
    void openRoutes() {
        Session session(nullptr);
        QSignalSpy failed(&session, &Session::loadFailed);
        QTemporaryDir zips;
        const QString zip = zips.filePath(QStringLiteral("broken.zip"));
        edi::write_project_archive((kFixtures + QStringLiteral("/bad_experiment")).toStdString(), zip.toStdString());

        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_structure"))));
        QVERIFY(!session.openProject(QUrl(QStringLiteral("https://example.org/project.zip"))));
        QVERIFY(!session.openProject(QUrl::fromLocalFile(zip)));
        QVERIFY(!session.openProject(fixture(QStringLiteral("missing"))));
        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_experiment"))));
        QVERIFY(!session.openExample(QStringLiteral("no-such-example")));
        QCOMPARE(loadFailures(failed), (QStringList{"phase.edi", "", "bank.edi", "", "bank.edi", ""}));
        QCOMPARE(session.takeFailedFile(), QString());  // the last failure carried none
    }

    // An example's download answers after another open has failed: an acquisition error carries nothing, and a
    // downloaded project that cannot be read carries its own file, never the other open's.
    void lateExampleCompletion() {
        Session session(nullptr);
        QSignalSpy failed(&session, &Session::loadFailed);
        QSignalSpy finished(&session, &Session::exampleOpenFinished);

        QVERIFY(session.openExample(missingExample_));  // pending: the collection and the download answer later
        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_experiment"))));
        QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 10000);
        QCOMPARE(loadFailures(failed), (QStringList{"bank.edi", ""}));

        failed.clear();
        QVERIFY(session.openExample(brokenExample_));
        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_experiment"))));
        QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 2, 10000);
        QCOMPARE(finished.at(1).at(1).toBool(), false);
        QCOMPARE(loadFailures(failed), (QStringList{"bank.edi", "phase.edi"}));
    }

    // Every way a file comes into an open project: each refusal attaches its own load's file, and a refusal that read
    // nothing, or that no load made, attaches none.
    void projectRoutes() {
        Session session(nullptr);
        ProjectViewModel* project = freshProject(session);
        QVERIFY(project);
        Refusals refusals(project);

        REFUSES(project->loadStructure(fixture(QStringLiteral("bad_structure/structures/phase.edi"))), "phase.edi");
        REFUSES(project->loadStructure(QUrl(QStringLiteral("https://example.org/phase.cif"))), "");
        REFUSES(project->loadExperiments({fixture(QStringLiteral("bad_experiment/experiments/bank.edi"))}), "bank.edi");
        REFUSES(project->loadExperiments({QUrl(QStringLiteral("https://example.org/bank.edi"))}), "");
        // A linked data file the experiment names: the innermost read is the one to blame.
        REFUSES(project->loadExperiments({fixture(QStringLiteral("linked/experiments/linked.edi"))}), "bad.xye");
        REFUSES(project->loadExperimentWithStructures(fixture(QStringLiteral("bad_experiment/experiments/bank.edi")), {}, {}), "bank.edi");
        REFUSES(project->loadDataIntoNewExperiment(fixture(QStringLiteral("bad.xye"))), "bad.xye");

        QVERIFY(project->createExperiment());
        ExperimentViewModel* experiment = project->experimentModels().constLast();
        QVERIFY(experiment);
        const int index = static_cast<int>(project->experimentModels().size()) - 1;
        REFUSES(project->loadData(index, fixture(QStringLiteral("bad.xye"))), "bad.xye");
        REFUSES(project->loadData(index, QUrl(QStringLiteral("https://example.org/data.xye"))), "");
        REFUSES(project->loadDatasets(experiment, {fixture(QStringLiteral("bad.xye"))}, false, false), "bad.xye");
        REFUSES(project->locateDataFile(experiment, fixture(QStringLiteral("bad.xye"))), "bad.xye");
        // A refusal no load makes: the selector refuses a single crystal with X-rays.
        QVERIFY(project->setNewExperimentType(QStringLiteral("sampleForm"), QStringLiteral("single crystal")));
        REFUSES(project->setNewExperimentType(QStringLiteral("radiationProbe"), QStringLiteral("xray")), "");
    }

    // Another open failing while an example's outcome is announced (its progress ending, its error set) neither takes
    // nor removes the example's file: the example's report still attaches its own phase.edi, bytes intact.
    void exampleOutcomeSurvivesReentry_data() {
        QTest::addColumn<QString>("signal");
        QTest::newRow("opening-example-changed") << QStringLiteral("openingExampleChanged");
        QTest::newRow("last-error-changed") << QStringLiteral("lastErrorChanged");
    }
    void exampleOutcomeSurvivesReentry() {
        QFETCH(QString, signal);
        Session session(nullptr);
        QSignalSpy finished(&session, &Session::exampleOpenFinished);
        QStringList files;
        QByteArray attached;
        QObject::connect(&session, &Session::loadFailed, &session, [&](const QString&, const QString& file) {
            files.append(name(file));
            if (file.endsWith(QStringLiteral("phase.edi"))) attached = bytes(file);
        });
        QVERIFY(session.openExample(brokenExample_));
        bool reentered = false;
        const auto reenter = [&] {
            if (reentered || session.openingExample()) return;
            reentered = true;
            session.openProject(fixture(QStringLiteral("bad_experiment")));
        };
        if (signal == QStringLiteral("openingExampleChanged"))
            QObject::connect(&session, &Session::openingExampleChanged, &session, reenter);
        else
            QObject::connect(&session, &Session::lastErrorChanged, &session, reenter);
        QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 10000);
        QVERIFY(reentered);
        QCOMPARE(files, (QStringList{"bank.edi", "phase.edi"}));
        QCOMPARE(attached, bytes(kFixtures + QStringLiteral("/bad_structure/structures/phase.edi")));
    }

    // An earlier listener failing another open while a failure is delivered: a later listener still finds the first
    // failure's own file, there to attach.
    void reportSurvivesEarlierListener() {
        Session session(nullptr);
        bool reopened = false;
        QObject::connect(&session, &Session::loadFailed, &session, [&] {
            if (reopened) return;
            reopened = true;
            session.openProject(fixture(QStringLiteral("bad_experiment")));
        });
        QStringList later;
        QObject::connect(&session, &Session::loadFailed, &session, [&](const QString&, const QString& file) { later.append(name(file)); });
        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_structure"))));
        // The nested failure reaches the later listener first, inside the outer delivery.
        QCOMPARE(later, (QStringList{"bank.edi", "phase.edi"}));
    }

    // A refusal a listener's own operation makes while a load's refusal is announced is its own: a selector reads no
    // file, so it attaches none, and the load's refusal still attaches the load's file.
    void nonLoadRefusalInsideLoadRefusal() {
        Session session(nullptr);
        ProjectViewModel* project = freshProject(session);
        QVERIFY(project);
        QVERIFY(project->setNewExperimentType(QStringLiteral("sampleForm"), QStringLiteral("single crystal")));
        QStringList files;
        bool nested = false;
        QObject::connect(project, &ProjectViewModel::refused, project, [&](const QString& message) {
            if (!nested) {
                nested = true;
                QVERIFY(!project->setNewExperimentType(QStringLiteral("radiationProbe"), QStringLiteral("xray")));
            }
            files.append(name(project->takeRefusedFile(message)));
        });
        QVERIFY(!project->loadStructure(fixture(QStringLiteral("bad_structure/structures/phase.edi"))));
        QCOMPARE(files, (QStringList{"", "phase.edi"}));
        // Asked outside any announcement, nothing is attached.
        QCOMPARE(project->takeRefusedFile({}), QString());
    }

    // Removing an atom an alias names leaves relations that cannot hold: the edit says so in one popup (a refusal
    // carrying no file), and the moment table, read from a binding, shows undefined s.u. instead of ending the app.
    void brokenRelationsArePoppedUpNotFatal() {
        Session session(nullptr);
        QVERIFY(session.openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/magnetic_stall/frame"))));
        ProjectViewModel* project = session.project();
        QVERIFY(project && !project->structureModels().isEmpty());
        StructureViewModel* structure = project->structureModels().constFirst();
        QStringList refusals, files;
        QObject::connect(project, &ProjectViewModel::refused, project, [&](const QString& message) {
            refusals.append(message);
            files.append(project->takeRefusedFile(message));
        });
        structure->atomSites()->remove(1);  // Co2, named by alias biso_Co2
        QCOMPARE(refusals.size(), 1);
        QVERIFY2(refusals.constFirst().contains(QStringLiteral("no longer hold")), qPrintable(refusals.constFirst()));
        QVERIFY2(refusals.constFirst().contains(QStringLiteral("Co2")), qPrintable(refusals.constFirst()));
        QCOMPARE(files, QStringList{QString()});
        const QList<double> components = structure->atomSiteMoments()->components(0, QStringLiteral("crystal"));
        QVERIFY(components.size() >= 6);
        QVERIFY(std::isnan(components.at(3)));
        // Another structural edit with the same problem says nothing new.
        structure->atomSites()->remove(structure->atomSites()->rowCount() - 1);
        QCOMPARE(refusals.size(), 1);
    }

    // A load started while another load's refusal is announced keeps its own file, and the first refusal, asked
    // after the second load ended, still has its own.
    void overlappingAttempts() {
        Session session(nullptr);
        ProjectViewModel* project = freshProject(session);
        QVERIFY(project);
        QStringList files;
        bool nested = false;
        QObject::connect(project, &ProjectViewModel::refused, project, [&](const QString& message) {
            if (!nested) {
                nested = true;
                project->loadExperiments({fixture(QStringLiteral("bad_experiment/experiments/bank.edi"))});
            }
            files.append(name(project->takeRefusedFile(message)));
        });
        QVERIFY(!project->loadStructure(fixture(QStringLiteral("bad_structure/structures/phase.edi"))));
        QCOMPARE(files, (QStringList{"bank.edi", "phase.edi"}));

        // The same through the session: an open started while another open's failure is announced.
        QSignalSpy failed(&session, &Session::loadFailed);
        bool reopened = false;
        QObject::connect(&session, &Session::loadFailed, &session, [&] {
            if (reopened) return;
            reopened = true;
            session.openProject(fixture(QStringLiteral("bad_experiment")));
        });
        QVERIFY(!session.openProject(fixture(QStringLiteral("bad_structure"))));
        // The nested failure is announced inside the first one, so the spy, connected first, sees the first first.
        QCOMPARE(loadFailures(failed), (QStringList{"phase.edi", "bank.edi"}));
    }
};

}  // namespace edi_app

QTEST_MAIN(edi_app::LoadAttemptTests)
#include "load_attempt_tests.moc"
