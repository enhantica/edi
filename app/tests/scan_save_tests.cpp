// SPDX-License-Identifier: BSD-3-Clause
#include <cmath>
#include <functional>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QImage>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QScopeGuard>
#include <QSettings>
#include "scan_layer.hpp"
#include <QTemporaryDir>
#include <QtTest/QtTest>
#include <QtQml/qqmlextensionplugin.h>
#include "engine_setup.hpp"
#include "session.hpp"
#include "edi/duration_text.hpp"
#include "edi/edits.hpp"
#include "project_view_model.hpp"
#include "structure_view_model.hpp"

// Keeps what a retried check found, for the steps after it, without an assignment inside the check.
template <class T, class U>
bool take(T*& slot, U* found) {
    slot = found;
    return found != nullptr;
}
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class ScanSaveTests : public QObject {
    Q_OBJECT
private slots:
    void fitProgressAndResultsUseSolverTime() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QTemporaryDir root;
        QVERIFY(root.isValid());
        const QDir source(QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/correlations/polynomial-1"));
        const QDir destination(root.path());
        for (const auto& relative : {"project.edi", "structures/phase.edi", "experiments/bank.edi", "analysis/analysis.edi"}) {
            QFile input(source.filePath(QString::fromUtf8(relative)));
            QVERIFY(input.open(QIODevice::ReadOnly));
            QByteArray text = input.readAll();
            if (QString::fromUtf8(relative) == "analysis/analysis.edi")
                text = "_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 3\n";
            const auto target = destination.filePath(QString::fromUtf8(relative));
            QVERIFY(QDir().mkpath(QFileInfo(target).absolutePath()));
            QFile output(target);
            QVERIFY(output.open(QIODevice::WriteOnly));
            QCOMPARE(output.write(text), text.size());
        }
        QVERIFY2(session->openProject(QUrl::fromLocalFile(root.path())), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 15000);
        auto* fit = session->project()->fit();
        QVERIFY2(fit->available(), qPrintable(fit->unavailableReason()));
        QList<double> runningTimes;
        connect(fit, &edi_app::FitViewModel::elapsedChanged, this, [&] {
            if (!fit->running()) return;
            QString text = fit->elapsed();
            text.chop(1);
            bool ok = false;
            const double value = text.toDouble(&ok);
            if (ok) runningTimes.append(value);
        });
        QSignalSpy done(fit, &edi_app::FitViewModel::finished);
        fit->start();
        QTRY_COMPARE_WITH_TIMEOUT(done.count(), 1, 15000);
        QVERIFY(!runningTimes.isEmpty());
        const auto& result = session->project()->project().fit_result;
        const QString duration = QString::fromStdString(edi::duration_text(result.fitting_time));
        QCOMPARE(fit->elapsed(), duration + "s");
        QCOMPARE(fit->results()->text(1, "value"), duration + " s");
        for (const double time : runningTimes) QVERIFY(time <= duration.toDouble());
    }
    // Opened on Analysis, at once or from another project's Analysis page, the structure view draws its atoms and the
    // parameter table fits its columns, as when the pages are visited in order.
    void projectOpenedOnAnalysisDrawsStructureAndTable() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        // The named item on screen: each page holds its own copy of the main view and the tables.
        const auto shown = [window](const QString& name) -> QQuickItem* {
            QQuickItem* result = nullptr;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->objectName() == name && child->isVisible() && at.x() >= 0 && at.x() < window->width())
                        result = child;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return result;
        };
        const auto click = [window](QQuickItem* item) {
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        const auto openAnalysis = [&] {
            QQuickItem* tab = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown("appBar.tab.analysis")) && tab->isEnabled(), 20000);
            click(tab);
        };
        // Atoms in the middle of the view: there a blank view has no letter, legend or toolbar.
        const auto drawn = [&]() {
            QQuickItem* view = shown("structure.view");
            if (view == nullptr || !view->property("has3D").toBool()) return view != nullptr && view->property("atomCount").toInt() > 0;
            const QImage image = window->grabWindow();
            const QPointF origin = view->mapToScene(QPointF());
            const QRect middle(int(origin.x() + view->width() * 0.2), int(origin.y() + view->height() * 0.3), int(view->width() * 0.4), int(view->height() * 0.5));
            const QColor background = view->property("color").value<QColor>();
            const double scale = image.width() / double(window->width());
            int marked = 0;
            for (int y = middle.top(); y < middle.bottom(); y += 2)
                for (int x = middle.left(); x < middle.right(); x += 2) {
                    const QColor pixel = image.pixelColor(int(x * scale), int(y * scale));
                    if (std::abs(pixel.red() - background.red()) + std::abs(pixel.green() - background.green()) + std::abs(pixel.blue() - background.blue()) > 60) ++marked;
                }
            return marked > middle.width() * middle.height() / 4 / 50;
        };
        // Every column fitted: a table measured while hidden keeps all but Name at their least width.
        const auto fitted = [&]() {
            QQuickItem* table = shown("parameters.list");
            if (table == nullptr || table->property("unfitted").toBool() || table->property("refitting").toBool()) return false;
            const QVariantList widths = table->property("columnWidths").value<QJSValue>().toVariant().toList();
            if (widths.size() < 4) return false;
            for (qsizetype column = 2; column < widths.size(); ++column)
                if (widths[column].toDouble() <= 12) return false;
            return true;
        };
        const QString ncaf = QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-tof_ncaf-wish/project");
        QVERIFY2(session->openProject(QUrl::fromLocalFile(ncaf)), qPrintable(session->lastError()));
        openAnalysis();
        // Analysis opens on Pattern; the Structure tab then draws its view at once.
        QTRY_VERIFY_WITH_TIMEOUT(shown("mainArea.tab.structure") && shown("mainArea.tab.structure")->isEnabled(), 20000);
        click(shown("mainArea.tab.structure"));
        QTRY_VERIFY_WITH_TIMEOUT(shown("structure.view"), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(drawn(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(fitted(), 60000);
        // Another project opened from Analysis: its pages are built while the Project page shows.
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/app/examples/pd-xray-cwl_lif/project"))), qPrintable(session->lastError()));
        openAnalysis();
        QVERIFY2(session->openProject(QUrl::fromLocalFile(ncaf)), qPrintable(session->lastError()));
        // Its Analysis page built beside the Project page, before it is shown.
        const auto builtHidden = [window]() {
            bool found = false;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    if (child->objectName() == "parameters.list" && child->property("count").toInt() > 200 && child->mapToScene(QPointF()).x() >= window->width())
                        found = true;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return found;
        };
        QTRY_VERIFY_WITH_TIMEOUT(builtHidden(), 30000);
        openAnalysis();
        QTRY_VERIFY_WITH_TIMEOUT(shown("structure.view"), 20000);
        click(shown("mainArea.tab.structure"));
        QTRY_VERIFY_WITH_TIMEOUT(drawn(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(fitted(), 60000);
    }
    void computedTablesReadOnlyWithFadingBarsAndNoZeroNoise() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        const auto all = [window](const std::function<bool(QQuickItem*)>& match) {
            QList<QQuickItem*> found;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->isVisible() && at.x() >= 0 && at.x() < window->width() && match(child)) found.append(child);
                    walk(child);
                }
            };
            walk(window->contentItem());
            return found;
        };
        const auto shown = [&](const QString& name) -> QQuickItem* {
            const QList<QQuickItem*> found = all([&](QQuickItem* item) { return item->objectName() == name; });
            return found.isEmpty() ? nullptr : found.constLast();
        };
        const auto click = [window](QQuickItem* item) {
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        // The page's own first group on screen first: while the pages slide, the previous page's Extra tab is still
        // found and a click on it changes nothing here.
        const auto openExtras = [&](const char* page, const char* group) {
            QQuickItem* tab = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown(QString::fromLatin1(page))) && tab->isEnabled(), 20000);
            click(tab);
            QTRY_VERIFY_WITH_TIMEOUT(shown(QString::fromLatin1(group)), 20000);
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown("sideBar.tab.extras")), 20000);
            click(tab);
        };
        const auto expand = [&](const QString& group) {
            QQuickItem* item = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(item, shown(group)), 20000);
            QVERIFY(item->setProperty("collapsed", false));
        };
        // A table's horizontal bar follows the vertical bar's policy (AsNeeded, fading when idle), never AlwaysOn.
        const auto barFades = [](QQuickItem* table) {
            for (QObject* child : table->children()) {
                if (QString::fromLatin1(child->metaObject()->className()).contains("ScrollBar") && child->property("orientation").toInt() == Qt::Horizontal)
                    return child->property("policy").toInt() != 2;
            }
            return true;
        };
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"))), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 30000);

        openExtras("appBar.tab.structure", "group.structures");
        // One group at a time: with auto-collapse on, expanding the next folds the one before.
        expand("group.expanded_atom_site");
        QQuickItem* atoms = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(atoms, shown("generated.expanded_atom_site.list")) && atoms->property("count").toInt() > 0, 20000);
        QVERIFY(barFades(atoms));
        // Cartesian and fractional coordinates at a rounding error from zero show as 0, never in scientific notation.
        QList<QQuickItem*> coordinates;
        QTRY_VERIFY_WITH_TIMEOUT([&] {
            coordinates = all([](QQuickItem* item) {
                const QString name = item->objectName();
                return name.startsWith("generated.expanded_atom_site.cartn_") || name.startsWith("generated.expanded_atom_site.fract_");
            });
            return !coordinates.isEmpty();
        }(), 20000);
        int zeros = 0;
        for (QQuickItem* cell : coordinates) {
            const QString text = cell->property("text").toString();
            QVERIFY2(!text.contains(QChar(0x00D7)) && !text.contains('e'), qPrintable(cell->objectName() + ": " + text));
            if (text.toDouble() == 0.0 && !text.isEmpty()) ++zeros;
        }
        QVERIFY(zeros > 0);

        expand("group.geom");
        QQuickItem* bonds = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(bonds, shown("geom.bonds")) && bonds->property("count").toInt() > 0, 20000);
        QVERIFY(bonds->property("readOnly").toBool());
        QVERIFY(barFades(bonds));
        QQuickItem* symmetry = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(symmetry, shown("geom.bonds.symmetry2.0")), 20000);
        QVERIFY2(QRegularExpression("^\\d+_\\d{3,}$").match(symmetry->property("text").toString()).hasMatch(), qPrintable(symmetry->property("text").toString()));
        QQuickItem* site = shown("geom.bonds.site1.0");
        QVERIFY(site);
        // A read-only table's value cells take the grey of a cell shown, not edited.
        QVERIFY(site->property("readOnlyRow").toBool());

        // The magnetic space group's BNS and UNI symbols share the row in two equal columns.
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"))), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 30000);
        {
            QQuickItem* tab = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown("appBar.tab.structure")) && tab->isEnabled(), 20000);
            click(tab);
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown("sideBar.tab.basic")), 20000);
            click(tab);
        }
        expand("group.space_group_magn");
        QQuickItem* bns = nullptr;
        QQuickItem* uni = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(bns, shown("magneticSpaceGroup.selector")) && take(uni, shown("magneticSpaceGroup.nameUni")), 20000);
        QVERIFY(bns->width() > 0);
        QCOMPARE(bns->width(), uni->width());

        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"))), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 30000);
        openExtras("appBar.tab.experiment", "group.experiments");
        expand("group.refln");
        QQuickItem* reflections = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(reflections, shown("reflections.list")) && reflections->property("count").toInt() > 0, 20000);
        QVERIFY(reflections->property("readOnly").toBool());
        QVERIFY(barFades(reflections));
    }
    // Controls moving between a toolbar's row and its ⋯ popup, chart tabs switching and the popup opening and closing
    // leave no QML warning (the owner's log: attached tooltips binding on controls being moved or destroyed).
    // A new experiment switched from powder to single crystal shows the linked structure's simulated reflections
    // before any data, and the switch reports nothing.
    void newSingleCrystalExperimentShowsSimulatedReflections() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QTemporaryDir root;
        QVERIFY(session->createProject(QStringLiteral("sc"), {}, root.filePath(QStringLiteral("project"))));
        edi_app::ProjectViewModel* project = session->project();
        QVERIFY(project);
        QVERIFY(project->createStructure());
        QVERIFY(project->createExperiment());
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 30000);
        const auto messages = [session] {
            QStringList lines;
            edi_app::WarningListModel* list = session->loadWarnings();
            const auto roles = list->roleNames();
            for (int row = 0; row < list->rowCount(); ++row)
                for (const QByteArray& role : roles)
                    lines.append(list->text(row, QString::fromUtf8(role)));
            return lines.join(QLatin1String(" | "));
        };
        const int before = session->loadWarnings()->rowCount();
        QVERIFY2(project->setExperimentType(0, QStringLiteral("sampleForm"), QStringLiteral("single crystal")),
                 qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 30000);
        edi_app::ExperimentViewModel* experiment = project->currentExperiment();
        QVERIFY(experiment);
        QCOMPARE(experiment->sampleForm(), edi_app::ExperimentViewModel::SingleCrystal);
        edi_app::SingleCrystalReflectionModel* reflections = experiment->singleCrystalReflections();
        QTRY_VERIFY2_WITH_TIMEOUT(reflections->simulated() && !reflections->calculated().isEmpty(), qPrintable(messages()), 30000);
        QVERIFY2(session->loadWarnings()->rowCount() == before, qPrintable(messages()));
    }

    // A filter that leaves a few rows shows them at once from the table's top, with no blank band easing away.
    void filteredTableShowsItsRowsAtOnceFromTheTop() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"))), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 30000);
        QQuickItem* tab = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(tab, window->findChild<QQuickItem*>(QStringLiteral("appBar.tab.analysis"))) && tab->isEnabled(), 20000);
        QTest::mouseClick(window, Qt::LeftButton, {}, tab->mapToScene(QPointF(tab->width() / 2, tab->height() / 2)).toPoint());
        QQuickItem* table = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(table, window->findChild<QQuickItem*>(QStringLiteral("parameters.list"))) && table->isVisible() && table->property("count").toInt() > table->property("maxRowCountShow").toInt(), 20000);
        // Scrolled to the end of the whole list, then filtered down to a few rows.
        const double end = table->property("originY").toDouble() + table->property("contentHeight").toDouble() - table->height();
        table->setProperty("contentY", end);
        QCOMPARE(table->property("contentY").toDouble(), end);
        auto* filter = table->property("sourceModel").value<QObject*>();
        QVERIFY(filter);
        QVERIFY(filter->setProperty("nameFilter", QStringLiteral("adp")));
        QTRY_VERIFY_WITH_TIMEOUT(table->property("count").toInt() > 0 && table->property("count").toInt() <= table->property("maxRowCountShow").toInt(), 5000);
        QCoreApplication::processEvents();
        // At the top on the first frame after the filter, with nothing left moving.
        QCOMPARE(table->property("contentY").toDouble(), table->property("originY").toDouble());
        QVERIFY(!table->property("moving").toBool());
    }

    // A parameter at zero still slides by a useful step: ±0.1° for the 2θ offset, the table's floor for its kind.
    void slidersStartWideEnoughAtZero() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"))), qPrintable(session->lastError()));
        auto* parameters = session->project()->parameters();
        const auto find = [parameters](const QString& path) -> edi_app::ParameterItem* {
            for (int row = 0; row < parameters->rowCount(); ++row)
                if (parameters->text(row, QStringLiteral("path")).endsWith(path))
                    return qobject_cast<edi_app::ParameterItem*>(parameters->item(row, QStringLiteral("parameter")));
            return nullptr;
        };
        edi_app::ParameterItem* offset = find(QStringLiteral("instrument.calib_twotheta_offset"));
        QVERIFY(offset);
        QCOMPARE(offset->sliderHalfWidth(), std::max(0.1, std::abs(offset->value()) * 0.5));
        edi_app::ParameterItem* length = find(QStringLiteral("cell.length_a"));
        QVERIFY(length);
        QCOMPARE(length->sliderHalfWidth(), 0.05);
    }

    // A fit with live updates on draws its patterns on the shown Pattern chart while it runs, not only at the end.
    // A sequential fit seen on Meas vs calc alone: each dataset it follows is drawn there, not only the first.
    void measCalcFollowsASequentialFit() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-tof_ncaf-wish-5bank_scan-6p/project"))), qPrintable(session->lastError()));
        edi_app::ProjectViewModel* project = session->project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        // The shown one of several items of that name (every page has its main view's tabs).
        const auto shown = [window](const QString& name) -> QQuickItem* {
            QQuickItem* result = nullptr;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->objectName() == name && child->isVisible() && child->isEnabled() && at.x() >= 0 && at.x() < window->width()) result = child;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return result;
        };
        QQuickItem* item = nullptr;
        for (const char* name : {"appBar.tab.analysis", "mainArea.tab.measCalc"}) {
            QTRY_VERIFY_WITH_TIMEOUT(take(item, shown(QString::fromLatin1(name))), 20000);
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        }
        edi_app::ExperimentViewModel* experiment = project->currentExperiment();
        QVERIFY(experiment);
        QTRY_VERIFY_WITH_TIMEOUT(experiment->patternShown(), 20000);
        edi_app::FitViewModel* fit = project->fit();
        fit->setPatternUpdates(0);  // every pattern
        int duringFit = 0;
        QObject::connect(experiment, &edi_app::ExperimentViewModel::patternSourceChanged, window, [&] {
            if (fit->running() && experiment->presentedGeneration() == experiment->patternGeneration()) ++duringFit;
        });
        fit->start();
        QTRY_VERIFY_WITH_TIMEOUT(fit->running(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(!fit->running(), 600000);
        QVERIFY2(duringFit >= 2, qPrintable(QString("datasets presented on Meas vs calc while running: %1").arg(duringFit)));
    }

    void patternChartFollowsARunningFit() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project"))), qPrintable(session->lastError()));
        edi_app::ProjectViewModel* project = session->project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        QQuickItem* tab = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(tab, window->findChild<QQuickItem*>(QStringLiteral("appBar.tab.analysis"))) && tab->isEnabled(), 20000);
        QTest::mouseClick(window, Qt::LeftButton, {}, tab->mapToScene(QPointF(tab->width() / 2, tab->height() / 2)).toPoint());
        edi_app::ExperimentViewModel* experiment = project->currentExperiment();
        QVERIFY(experiment);
        QTRY_VERIFY_WITH_TIMEOUT(experiment->patternShown(), 20000);
        edi_app::FitViewModel* fit = project->fit();
        fit->setPatternUpdates(0);  // every pattern
        int duringFit = 0;
        // Counted only when the shown chart presented it: the controller draws on the same signal, before this.
        QObject::connect(experiment, &edi_app::ExperimentViewModel::patternSourceChanged, window, [&] {
            if (fit->running() && experiment->presentedGeneration() == experiment->patternGeneration()) ++duringFit;
        });
        fit->start();
        QTRY_VERIFY_WITH_TIMEOUT(fit->running(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(!fit->running(), 300000);
        QVERIFY2(duringFit >= 2, qPrintable(QString("patterns presented while running: %1").arg(duringFit)));
    }

    void toolbarOverflowLeavesNoQmlWarning() {
        static QStringList warnings;
        warnings.clear();
        static QtMessageHandler previous = nullptr;
        previous = qInstallMessageHandler([](QtMsgType type, const QMessageLogContext& context, const QString& message) {
            if (type != QtDebugMsg && type != QtInfoMsg && (message.contains(QLatin1String(".qml:")) || message.contains(QLatin1String("QML "))))
                warnings.append(message);
            if (previous) previous(type, context, message);
        });
        const auto restore = qScopeGuard([] { qInstallMessageHandler(previous); });
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        const auto shown = [window](const QString& name) -> QQuickItem* {
            QQuickItem* result = nullptr;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->objectName() == name && child->isVisible() && at.x() >= 0 && at.x() < window->width()) result = child;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return result;
        };
        const auto click = [window](QQuickItem* item) {
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        QVERIFY2(session->openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"))), qPrintable(session->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!session->project()->calculating(), 30000);
        QQuickItem* tab = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown("appBar.tab.analysis")) && tab->isEnabled(), 20000);
        click(tab);
        // Each chart tab at a wide and a narrow window: the narrow one puts controls in the popup, which opens and closes.
        for (const char* key : {"pattern", "measCalc", "structure", "pattern"}) {
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown(QStringLiteral("mainArea.tab.%1").arg(QLatin1String(key)))) && tab->isEnabled(), 20000);
            click(tab);
            const QString toolbar = QLatin1String(key) == QLatin1String("pattern") ? "chart.toolbar" : QLatin1String(key) == QLatin1String("measCalc") ? "measCalc.toolbar" : "structure.toolbar";
            QTRY_VERIFY_WITH_TIMEOUT(shown(toolbar), 20000);
            for (int round = 0; round < 2; ++round) {
                window->resize(1024, 700);
                QQuickItem* more = nullptr;
                // A toolbar with fewer controls (Meas vs calc) may still fit: then it has no popup to open, and the
                // resize alone is what must stay free of warnings.
                if (!QTest::qWaitFor([&] { return (more = shown(toolbar + ".more")) != nullptr; }, 3000)) {
                    window->resize(1480, 900);
                    continue;
                }
                click(more);
                QTRY_VERIFY_WITH_TIMEOUT(more->property("checked").toBool(), 5000);
                click(more);
                QTRY_VERIFY_WITH_TIMEOUT(!more->property("checked").toBool(), 5000);
                click(more);
                QTRY_VERIFY_WITH_TIMEOUT(more->property("checked").toBool(), 5000);
                // Wider with the popup open: its controls go back to the row.
                window->resize(1480, 900);
                QTRY_VERIFY_WITH_TIMEOUT(!shown(toolbar + ".more"), 20000);
            }
        }
        QVERIFY2(warnings.isEmpty(), qPrintable(warnings.join(QLatin1Char('\n'))));
    }
    // A Replace on untitled work (ADR-0100 point 6) writes over the folder the user confirmed and nothing else: a
    // dialog's answer for an operation that gave way does nothing, and a folder swapped or removed after the
    // confirmation is refused with what is there left alone.
    void untitledReplaceIsTheConfirmedFolder() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QTemporaryDir root;
        QVERIFY(root.isValid());
        const QString target = root.filePath(QStringLiteral("alpha"));
        const QString moved = root.filePath(QStringLiteral("alpha-moved"));
        const auto fileText = [](const QString& path) {
            QFile file(path);
            return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString();
        };
        const auto replacedLeft = [&root] {
            return !QDir(root.path()).entryList({QStringLiteral("alpha.edi-replaced*")}, QDir::AllEntries | QDir::Hidden).isEmpty();
        };
        const auto fresh = [session] {
            if (session->hasProject()) session->closeProject();
            return !session->hasProject() && session->startUntitledProject() && session->untitled();
        };
        QVERIFY(fresh());
        QVERIFY2(session->createProject(QStringLiteral("alpha"), QStringLiteral("first"), target),
                 qPrintable(session->lastError()));
        QVERIFY(QFileInfo::exists(target + QStringLiteral("/project.edi")));

        // An answer for an operation that gave way: nothing written, no message, the newer operation still open.
        QVERIFY(fresh());
        const quint64 older = session->beginUntitled(QStringLiteral("manual-create"));
        const quint64 newer = session->beginUntitled(QStringLiteral("save"));
        QVERIFY(older > 0 && newer > older);
        const auto stale = session->createProjectWithOutcome(QStringLiteral("beta"), {}, root.filePath(QStringLiteral("beta")),
                                                             QStringLiteral("iucr_99"), {}, {}, false, {}, false, older);
        QVERIFY(!stale.success);
        QVERIFY(stale.error.isEmpty());
        QVERIFY(!QFileInfo::exists(root.filePath(QStringLiteral("beta"))));
        QVERIFY(session->untitled());
        QCOMPARE(session->untitledOperationId(), newer);

        // Confirmed, then swapped for another folder before the Create goes on: refused, both folders as they were.
        QVERIFY(session->approveUntitledReplace(newer, target));
        QVERIFY(QDir().rename(target, moved));
        QVERIFY(QDir().mkpath(target));
        {
            QFile other(target + QStringLiteral("/project.edi"));
            QVERIFY(other.open(QIODevice::WriteOnly));
            other.write("someone else's\n");
        }
        const auto swapped = session->createProjectWithOutcome(QStringLiteral("alpha"), QStringLiteral("second"), target,
                                                               QStringLiteral("iucr_99"), {}, {}, false, {}, true, newer);
        QVERIFY(!swapped.success);
        QVERIFY2(swapped.error.contains(QStringLiteral("changed after you chose")), qPrintable(swapped.error));
        QCOMPARE(fileText(target + QStringLiteral("/project.edi")), QStringLiteral("someone else's\n"));
        QVERIFY(fileText(moved + QStringLiteral("/project.edi")).contains(QStringLiteral("first")));
        QVERIFY(session->untitled());
        QVERIFY(!replacedLeft());
        QVERIFY(QDir(target).removeRecursively());
        QVERIFY(QDir().rename(moved, target));

        // Confirmed, then removed: refused, and nothing is made in its place.
        QVERIFY(fresh());
        quint64 id = session->beginUntitled(QStringLiteral("save"));
        QVERIFY(session->approveUntitledReplace(id, target));
        QVERIFY(QDir().rename(target, moved));
        QVERIFY(!session->createProjectWithOutcome(QStringLiteral("alpha"), {}, target, QStringLiteral("iucr_99"), {}, {},
                                                   false, {}, true, id).success);
        QVERIFY(!QFileInfo::exists(target));
        QVERIFY(session->untitled());
        QVERIFY(QDir().rename(moved, target));

        // Not confirmed: refused even though a project folder is there.
        QVERIFY(fresh());
        id = session->beginUntitled(QStringLiteral("save"));
        QVERIFY(!session->createProjectWithOutcome(QStringLiteral("alpha"), {}, target, QStringLiteral("iucr_99"), {}, {},
                                                   false, {}, true, id).success);
        QVERIFY(fileText(target + QStringLiteral("/project.edi")).contains(QStringLiteral("first")));

        // Confirmed and unchanged: replaced, and the old folder is gone.
        QVERIFY(fresh());
        id = session->beginUntitled(QStringLiteral("save"));
        QVERIFY(session->approveUntitledReplace(id, target));
        const auto replaced = session->createProjectWithOutcome(QStringLiteral("alpha"), QStringLiteral("second"), target,
                                                                QStringLiteral("iucr_99"), {}, {}, false, {}, true, id);
        QVERIFY2(replaced.success, qPrintable(replaced.error));
        QVERIFY(!session->untitled());
        QVERIFY(fileText(target + QStringLiteral("/project.edi")).contains(QStringLiteral("second")));
        QVERIFY(!replacedLeft());
    }
    // Each untitled request stays bound to what asked for it (ADR-0100 points 3 and 5): a guard Save for another
    // question is another request, a request made while an older one settles is never lost, and a desktop Create
    // without a folder is refused rather than named.
    void untitledRequestsStayBound() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY(session->startUntitledProject());
        QSignalSpy settled(session, &edi_app::Session::untitledSettled);
        const auto settledAs = [&settled](quint64 id) {
            QStringList states;
            for (const auto& arguments : settled)
                if (arguments.at(0).toULongLong() == id) states << arguments.at(1).toString();
            return states;
        };
        const quint64 first = session->beginUntitled(QStringLiteral("guard-save"), QStringLiteral("question-1"));
        QVERIFY(first > 0);
        QCOMPARE(session->beginUntitled(QStringLiteral("guard-save"), QStringLiteral("question-1")), first);
        QVERIFY(settled.isEmpty());
        const quint64 second = session->beginUntitled(QStringLiteral("guard-save"), QStringLiteral("question-2"));
        QVERIFY(second > first);
        QCOMPARE(settledAs(first), QStringList{QStringLiteral("superseded")});

        // A listener of the settlement asks again: its request supersedes the one being opened, which reports no id.
        quint64 inner = 0;
        const auto connection = connect(session, &edi_app::Session::untitledSettled, session,
                                        [&](quint64 id, const QString&) {
                                            if (id == second && inner == 0)
                                                inner = session->beginUntitled(QStringLiteral("save"));
                                        });
        const quint64 outer = session->beginUntitled(QStringLiteral("manual-create"));
        disconnect(connection);
        QCOMPARE(outer, quint64{0});
        QVERIFY(inner > second);
        QCOMPARE(session->untitledOperationId(), inner);
        QCOMPARE(settledAs(second), QStringList{QStringLiteral("superseded")});
        QCOMPARE(settledAs(inner - 1), QStringList{QStringLiteral("superseded")});
        QVERIFY(settledAs(inner).isEmpty());

        // No folder on the desktop: refused, nothing named.
        const QString name = session->project()->name();
        QVERIFY(!session->acceptUntitled(inner, QStringLiteral("gamma"), QStringLiteral("described")));
        QCOMPARE(settledAs(inner), QStringList{QStringLiteral("refused")});
        QVERIFY(session->untitled());
        QVERIFY(!session->lastError().isEmpty());
        QCOMPARE(session->project()->name(), name);
    }
    // Work before Create (the owner, 2026-11-19): the open Project page holds an untitled project that takes a
    // structure at once, Create names and saves that same project with its structure, and the Create form's fields say
    // what each is for.
    void untitledWorkIsKeptByCreate() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session && !session->hasProject());
        const auto named = [window](const char* name) {
            const QString wanted = QString::fromLatin1(name);
            const auto visit = [&](auto&& self, QQuickItem* item) -> QQuickItem* {
                if (item->objectName() == wanted) return item;
                for (auto* child : item->childItems()) {
                    if (auto* found = self(self, child)) return found;
                }
                return nullptr;
            };
            return visit(visit, window->contentItem());
        };
        const auto click = [&](const char* name) {
            QQuickItem* item = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(item, named(name)) && item->isVisible() && item->isEnabled()
                && window->contentItem()->boundingRect().contains(item->mapRectToScene(item->boundingRect())), 20000);
            QTest::mouseClick(window, Qt::LeftButton, {},
                              item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        QQmlExpression state(qmlContext(window), window, QStringLiteral(
            "JSON.stringify([EaGlobals.Vars.appBarCurrentIndex, AppState.reached, Session.hasProject, Session.untitled, "
            "AppState.projectPageEnabled, AppState.structurePageEnabled, AppState.experimentPageEnabled, "
            "AppState.analysisPageEnabled, AppState.reportPageEnabled])"));
        const QString startup = state.evaluate().toString();
        QVERIFY(!state.hasError());
        QCOMPARE(startup, QStringLiteral("[0,0,false,false,false,false,false,false,false]"));
        click("home.start");
        QTRY_VERIFY_WITH_TIMEOUT(session->hasProject(), 20000);
        QVERIFY(session->untitled());
        QVERIFY(session->needsSaveAs());
        click("project.create");
        QTRY_VERIFY_WITH_TIMEOUT(named("createProject.name") && named("createProject.name")->isVisible(), 20000);
        const auto placeholder = [&](const char* name) {
            const auto* field = named(name);
            return field ? field->property("placeholderText").toString() : QString();
        };
        QVERIFY2(placeholder("createProject.name").contains(QStringLiteral("project folder")), qPrintable(placeholder("createProject.name")));
        QVERIFY(placeholder("createProject.title").contains(QStringLiteral("report")));
        QVERIFY(placeholder("createProject.authors").contains(QStringLiteral("report")));
        QVERIFY(placeholder("createProject.location").contains(QStringLiteral("folder in which")));
        QTest::keyClick(window, Qt::Key_Escape);
        QTRY_VERIFY_WITH_TIMEOUT(!named("createProject.name") || !named("createProject.name")->isVisible(), 20000);
        QVERIFY(session->project()->createStructure());
        QCOMPARE(session->project()->project().structures.size(), std::size_t{1});
        QTemporaryDir folder;
        QVERIFY(folder.isValid());
        const QString location = folder.path() + QStringLiteral("/lbco_hrpt-7");
        edi_app::ProjectViewModel* before = session->project();
        QVERIFY2(session->createProject(QStringLiteral("lbco_hrpt-7"), QStringLiteral("Before Create"), location),
                 qPrintable(session->lastError()));
        QCOMPARE(session->project(), before);
        QVERIFY(!session->untitled());
        QVERIFY(!session->needsSaveAs());
        QCOMPARE(session->project()->project().structures.size(), std::size_t{1});
        QVERIFY(QFileInfo::exists(location + QStringLiteral("/project.edi")));
        click("appBar.button.reset");
        QTRY_VERIFY(!session->hasProject());
        QTRY_COMPARE(state.evaluate().toString(), startup);
        QVERIFY(!state.hasError());
        click("home.start");
        QTRY_VERIFY(session->hasProject());
        QVERIFY(session->untitled());
        QVERIFY(session->needsSaveAs());
        QVERIFY(session->project()->project().structures.empty());
        QVERIFY(session->project()->project().experiments.empty());
        click("appBar.button.reset");
        QTRY_VERIFY(!session->hasProject());
        QTRY_COMPARE(state.evaluate().toString(), startup);
    }

    // A 2θ offset that moves the lowest points below 0° leaves them out of the calculation instead of refusing it, and
    // says so once (the owner, 2026-11-19). The expected outcome is independent of the engine: with an offset one
    // degree above the first angle, every point below that angle plus 0° has no d-spacing.
    void offsetBelowZeroLeavesPointsOut() {
        edi_app::Session session(nullptr);
        QVERIFY2(session.openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"))),
                 qPrintable(session.lastError()));
        edi_app::ProjectViewModel* project = session.project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        edi::BraggPdExperiment& experiment = *project->project().experiments[0];
        if (!experiment.data || !experiment.instrument.calib_twotheta_offset) QFAIL("The experiment must have data and a two-theta offset");
        const std::vector<double>& axis = experiment.data->axis();
        const double offset = axis.front() + 1.0;
        const auto below = std::count_if(axis.begin(), axis.end(), [offset](double angle) { return angle - offset <= 0.0; });
        QVERIFY(below > 0);
        QVERIFY(project->assign_parameter_value(*experiment.instrument.calib_twotheta_offset, offset).isEmpty());
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        edi_app::ExperimentViewModel* model = project->experimentModels().value(0);
        QVERIFY(model);
        QVERIFY2(model->pattern()->calculationError().isEmpty(), qPrintable(model->pattern()->calculationError()));
        QVERIFY(model->pattern()->calculatedPointCount() > 0);
        const QStringList notes = session.loadWarnings()->keys(QStringLiteral("domain:"));
        QCOMPARE(notes.size(), 1);
        QVERIFY2(notes.front().endsWith(u':' + QString::number(below)), qPrintable(notes.front()));
    }

    // A form-factor coefficient the chosen approximation does not use keeps its value but no longer fits (the owner,
    // 2026-11-19): switching Co to <j0> fixes a free C2, its row still names the type and the ion, and one Undo brings
    // back the dipole approximation with C2 free.
    void unusedFormFactorCoefficientIsFixed() {
        edi_app::Session session(nullptr);
        QVERIFY2(session.openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"))),
                 qPrintable(session.lastError()));
        edi_app::ProjectViewModel* project = session.project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        edi_app::StructureViewModel* structure = project->structureModels().value(0);
        QVERIFY(structure);
        edi_app::MagneticFormFactorListModel* rows = structure->magneticFormFactors();
        QVERIFY(rows);
        int co = -1;
        for (int row = 0; row < rows->rowCount(); ++row) {
            if (rows->text(row, QStringLiteral("type")).startsWith(QStringLiteral("Co"))) co = row;
        }
        QVERIFY2(co >= 0, "CoSiO lists Co's form factor");
        const auto c2 = [&]() -> const edi::Parameter* {
            for (const auto& item : structure->structure()->magnetic_form_factors) {
                if (QString::fromStdString(item->id.value()).startsWith(QStringLiteral("Co"))) return &item->j2_coefficient;
            }
            return nullptr;
        };
        // The example's Co row: dipole, C2 free (written `0()`).
        QCOMPARE(rows->text(co, QStringLiteral("approximation")), QStringLiteral("dipole"));
        QVERIFY(c2() != nullptr && c2()->free.get());
        const double value = c2()->value.get();
        rows->setApproximation(co, QStringLiteral("j0"));
        QTRY_COMPARE_WITH_TIMEOUT(rows->text(co, QStringLiteral("approximation")), QStringLiteral("j0"), 20000);
        QVERIFY(c2() != nullptr);
        QCOMPARE(c2()->value.get(), value);
        QVERIFY(!c2()->free.get());
        QVERIFY(!rows->text(co, QStringLiteral("type")).isEmpty());
        QVERIFY(!rows->text(co, QStringLiteral("ion")).isEmpty());
        project->undo();
        QTRY_COMPARE_WITH_TIMEOUT(rows->text(co, QStringLiteral("approximation")), QStringLiteral("dipole"), 20000);
        QVERIFY(c2() != nullptr && c2()->free.get());
    }

    // The owner's path of 2026-11-19 (a crash after two binding-loop warnings): the Experiments row's data file is
    // replaced, the new data is calculated, and Pattern, Meas vs calc and the pages switch without a warning or a fault.
    void replacedDataIsCalculatedAndPagesSwitch() {
        static QStringList loops;
        loops.clear();
        static QtMessageHandler previous = nullptr;
        previous = qInstallMessageHandler([](QtMsgType type, const QMessageLogContext& context, const QString& text) {
            if (text.contains(QStringLiteral("Binding loop"))) loops.append(text);
            if (previous) previous(type, context, text);
        });
        const auto restore = qScopeGuard([] { qInstallMessageHandler(previous); });
        QTemporaryDir copy;
        QVERIFY(copy.isValid());
        const QString source = QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_2k/project");
        std::function<bool(const QString&, const QString&)> copyTree = [&](const QString& from, const QString& to) {
            if (!QDir().mkpath(to)) return false;
            for (const QFileInfo& entry : QDir(from).entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot)) {
                const QString target = to + u'/' + entry.fileName();
                if (entry.isDir() ? !copyTree(entry.filePath(), target) : !QFile::copy(entry.filePath(), target)) return false;
            }
            return true;
        };
        QVERIFY(copyTree(source, copy.path() + QStringLiteral("/project")));
        const QString data = copy.path() + QStringLiteral("/d20_2K.dat");
        QVERIFY(QFile::copy(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project/experiments/d20_scan/01_001_497p3790.dat"), data));

        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        QVERIFY2(session->openProject(QUrl::fromLocalFile(copy.path() + QStringLiteral("/project"))), qPrintable(session->lastError()));
        edi_app::ProjectViewModel* project = session->project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        const auto shown = [window](const QString& name) -> QQuickItem* {
            QQuickItem* result = nullptr;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->objectName() == name && child->isVisible() && child->isEnabled() && at.x() >= 0 && at.x() < window->width()) result = child;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return result;
        };
        const auto click = [&](const char* name) {
            QQuickItem* item = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(item, shown(QString::fromLatin1(name))), 20000);
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        click("appBar.tab.experiment");
        click("mainArea.tab.measCalc");
        QVERIFY(project->currentExperiment());
        QTRY_VERIFY_WITH_TIMEOUT(project->currentExperiment()->pattern()->calculatedPointCount() > 0, 60000);

        // Hover moves across the middle of the window, where the charts are (the owner's crash came from a mouse move
        // over a chart after the replacement).
        const auto hover = [window] {
            for (int x = 420; x < window->width() - 40; x += 23) {
                QTest::mouseMove(window, QPoint(x, window->height() / 2 + (x % 97) - 48));
                QCoreApplication::processEvents();
            }
        };
        hover();
        // A fit first, as the owner had one: its results are what the replacement makes outdated.
        project->fit()->start();
        QTRY_VERIFY_WITH_TIMEOUT(project->fit()->running(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(!project->fit()->running(), 900000);
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        QVERIFY2(!project->currentExperiment()->fitOutcome().isEmpty(), "the fit left its outcome on the experiment");
        QVERIFY(!project->fit()->outOfDate());
        QVERIFY2(project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(data)), qPrintable(project->lastError()));
        hover();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        hover();
        // The new data is calculated as any other edit's is.
        QTRY_VERIFY_WITH_TIMEOUT(project->currentExperiment()->pattern()->calculatedPointCount() > 0, 60000);
        // The fit described the old data: the project no longer holds it, so the experiment's line drops its outcome
        // (and a save writes none).
        QVERIFY(project->currentExperiment()->fitOutcome().isEmpty());
        QVERIFY(project->project().fit_result.result_kind.empty());
        for (const char* name : {"mainArea.tab.pattern", "mainArea.tab.measCalc", "appBar.tab.structure", "appBar.tab.analysis",
                                 "mainArea.tab.measCalc", "mainArea.tab.pattern", "appBar.tab.experiment", "mainArea.tab.measCalc"}) {
            click(name);
            hover();
            QTest::qWait(200);
            hover();
        }
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        QVERIFY2(loops.isEmpty(), qPrintable(loops.join(u'\n')));
        // A second replacement, then one Undo: the data is the first replacement's, which no fit described.
        const QString second = copy.path() + QStringLiteral("/d20_second.dat");
        QVERIFY(QFile::copy(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project/experiments/d20_scan/01_002_497p3410.dat"), second));
        QVERIFY2(project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(second)), qPrintable(project->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        project->undo();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        QVERIFY(project->project().fit_result.result_kind.empty());
        QVERIFY(project->currentExperiment()->fitOutcome().isEmpty());
        // A second Undo brings back the fitted data and the fit that described it.
        project->undo();
        QTRY_VERIFY_WITH_TIMEOUT(!project->project().fit_result.result_kind.empty(), 20000);
        QTRY_VERIFY_WITH_TIMEOUT(!project->currentExperiment()->fitOutcome().isEmpty(), 20000);
    }

    void undoReplacementRestoresTheAbsenceOfFit() {
        edi_app::Session session(nullptr);
        QVERIFY2(session.openProject(QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"))),
                 qPrintable(session.lastError()));
        auto* project = session.project();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        auto& model = const_cast<edi::Project&>(project->project());
        edi::clear_fit_result(model);
        const QString data = QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project/experiments/d20_scan/01_001_497p3790.dat");
        QVERIFY2(project->loadDataInto(project->currentExperiment(), QUrl::fromLocalFile(data)), qPrintable(project->lastError()));
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        model.fit_result.result_kind = "single";
        model.fit_result.message = "describes only the replacement";
        model.experiments.front()->fit_n_data_points = 7;
        project->undo();
        QTRY_VERIFY_WITH_TIMEOUT(!project->calculating(), 60000);
        QVERIFY(project->project().fit_result.result_kind.empty());
        QVERIFY(!project->project().experiments.front()->fit_share_held());
    }

    void eachPageOpensOnItsDefaultTabThenTheUsersPick() {
        QQmlApplicationEngine engine;
        edi_app::configure_engine(engine);
        engine.loadFromModule("edi.app", "Main");
        QVERIFY(!engine.rootObjects().isEmpty());
        auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
        QVERIFY(window);
        window->resize(1480, 900);
        window->show();
        QVERIFY(QTest::qWaitForWindowExposed(window));
        auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
        QVERIFY(session);
        const auto onScreen = [window](const std::function<bool(QQuickItem*)>& match) -> QQuickItem* {
            QQuickItem* result = nullptr;
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    const QPointF at = child->mapToScene(QPointF());
                    if (child->isVisible() && at.x() >= 0 && at.x() < window->width() && match(child)) result = child;
                    walk(child);
                }
            };
            walk(window->contentItem());
            return result;
        };
        const auto shown = [&](const QString& name) { return onScreen([&](QQuickItem* item) { return item->objectName() == name; }); };
        // The shown page's main view, by its current tab's key.
        const auto currentKey = [&]() {
            QQuickItem* view = onScreen([](QQuickItem* item) { return item->property("defaultKey").isValid() && item->property("shown").toBool(); });
            return view ? view->property("currentKey").toString() : QString();
        };
        const auto click = [window](QQuickItem* item) {
            QTest::mouseClick(window, Qt::LeftButton, {}, item->mapToScene(QPointF(item->width() / 2, item->height() / 2)).toPoint());
        };
        const auto openPage = [&](const char* name) {
            QQuickItem* tab = nullptr;
            QTRY_VERIFY_WITH_TIMEOUT(take(tab, shown(QString::fromLatin1(name))) && tab->isEnabled(), 20000);
            click(tab);
        };
        const QUrl lbco = QUrl::fromLocalFile(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_lbco-hrpt/project"));
        QVERIFY2(session->openProject(lbco), qPrintable(session->lastError()));
        openPage("appBar.tab.analysis");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("pattern"), 20000);
        openPage("appBar.tab.structure");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("structure"), 20000);
        openPage("appBar.tab.experiment");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("pattern"), 20000);
        // The user's pick on Analysis is what Analysis opens on with the next project; the other pages keep theirs.
        openPage("appBar.tab.analysis");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("pattern"), 20000);
        QQuickItem* structureTab = nullptr;
        QTRY_VERIFY_WITH_TIMEOUT(take(structureTab, shown("mainArea.tab.structure")), 20000);
        click(structureTab);
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("structure"), 20000);
        QVERIFY2(session->openProject(lbco), qPrintable(session->lastError()));
        openPage("appBar.tab.analysis");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("structure"), 20000);
        openPage("appBar.tab.experiment");
        QTRY_COMPARE_WITH_TIMEOUT(currentKey(), QStringLiteral("pattern"), 20000);
    }
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
                QCoreApplication::processEvents();  // the labels are announced once per event-loop turn
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
        // Announced once per event-loop turn, against what was last announced: a read before delivery (which
        // refreshes the cache) and a second move in the same turn still end in one announcement of the new choice,
        // and a turn with no move announces nothing.
        QSignalSpy announced(&layer, &edi_app::ScanLayer::labelledDatasetsChanged);
        QCoreApplication::processEvents();
        announced.clear();
        layer.setCurrent(5);
        QVERIFY(layer.labelledDatasets() != labels);
        layer.setHeight(100.001);
        QCOMPARE(announced.size(), 0);
        QCoreApplication::processEvents();
        QVERIFY(layer.labelledDatasets() != labels);
        QCOMPARE(announced.size(), 1);
        QCoreApplication::processEvents();
        QCOMPARE(announced.size(), 1);
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
    // A target read from a file may hold what the editor refuses (the fit's reserved prefix, a comma); Duplicate still
    // gives the copy a target the editor accepts.
    void duplicateGivesALoadedRuleAnAcceptedTarget() {
        for (const QByteArray& loaded : {QByteArrayLiteral("fit_result.user_reading"), QByteArrayLiteral("user,reading")}) {
            QQmlApplicationEngine engine;
            edi_app::configure_engine(engine);
            auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
            QVERIFY(session);
            QTemporaryDir root;
            QVERIFY(root.isValid());
            const QDir source(QStringLiteral(EDI_SOURCE_DIR "/docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project"));
            QDirIterator files(source.path(), QDir::Files, QDirIterator::Subdirectories);
            while (files.hasNext()) {
                const QString path = files.next();
                const QString target = QDir(root.path()).filePath(source.relativeFilePath(path));
                QVERIFY(QDir().mkpath(QFileInfo(target).absolutePath()));
                QFile input(path);
                QVERIFY(input.open(QIODevice::ReadOnly));
                QByteArray text = input.readAll();
                if (path.endsWith("analysis/analysis.edi"))
                    text.replace("temperature diffrn.ambient_temperature ", "temperature " + loaded + " ");
                QFile output(target);
                QVERIFY(output.open(QIODevice::WriteOnly));
                QCOMPARE(output.write(text), text.size());
            }
            QVERIFY2(session->openProject(QUrl::fromLocalFile(root.path())), qPrintable(session->lastError()));
            auto* rules = session->project()->analysis()->sequentialExtract();
            QTRY_COMPARE_WITH_TIMEOUT(rules->count(), 1, 10000);
            QCOMPARE(rules->text(0, "target"), QString::fromUtf8(loaded));
            rules->duplicate(0);
            QTRY_COMPARE_WITH_TIMEOUT(rules->count(), 2, 10000);
            const std::string copied = rules->text(1, "target").toStdString();
            QVERIFY2(!copied.empty() && copied != loaded.toStdString(), copied.c_str());
            try {
                edi::check_extract_target(session->project()->project(), nullptr, copied);
            } catch (const std::invalid_argument& error) {
                QFAIL(error.what());
            }
        }
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

