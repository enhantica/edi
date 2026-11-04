// SPDX-License-Identifier: BSD-3-Clause
#include <memory>
#include <limits>
#include <vector>
#include <QCoreApplication>
#include <QFileInfo>
#include <QColor>
#include <QImage>
#include <QDir>
#include <QDirIterator>
#include <QCryptographicHash>
#include <QFile>
#include <QJsonDocument>
#include <QTextDocument>
#include <QTextTable>
#include <QProcess>
#include <QProcessEnvironment>
#include <QStandardPaths>
#include <QTemporaryDir>
#if defined(Q_OS_LINUX) || defined(Q_OS_MACOS)
#include <unistd.h>
#endif
#include <QUrl>
#include <QQmlEngine>
#include <QtQml/qqml.h>
#include "project_view_model.hpp"
#include "report_view_model.hpp"
#include "edi/io.hpp"
#include "scan_session.hpp"
#include <filesystem>
#include <fstream>
#include "edi/report_save.hpp"

class ReportBoundaryProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantMap scanTemporary(const QUrl& location, const QUrl& outside,
                                          const QString& route, const QString& alias, bool linked,
                                          int which, bool late) const {
        namespace fs = std::filesystem;
        const fs::path root(location.toLocalFile().toStdString()),
            external(outside.toLocalFile().toStdString());
        const char* names[] = {"results.csv", "results-provenance.csv", "scan-run.json",
                               "scan-notes.csv"};
        try {
            fs::create_directories(root / "analysis");
            for (const auto* name : names)
                std::ofstream(root / "analysis" / name) << "previous " << name << '\n';
            std::ofstream(root / "analysis/carried") << "independent carried artifact";
            if (linked) {
                fs::rename(root / "analysis", external / "analysis");
                fs::create_directory_symlink(external / "analysis", root / "analysis");
            }
            const auto sentinel = external / "sentinel";
            std::ofstream(sentinel) << "independent outside inode";
            const bool moduleWriter = route == "writeRun" || route == "putRunFile" ||
                                      route == "swapRunFile" || route == "restoreRunFile" ||
                                      route == "dropRunFile";
            const auto temporary = moduleWriter
                ? (linked ? root / ("." + std::string(names[which]) + ".tmp")
                          : root / "analysis" / (std::string(names[which]) + ".tmp"))
                : root / "analysis" / (std::string(names[which]) + ".edi-staged");
            if (alias == "hard")
                fs::create_hard_link(sentinel, temporary);
            else if (alias == "symbolic")
                fs::create_symlink(sentinel, temporary);
            else if (alias == "carried")
                std::ofstream(temporary) << "retained ordinary staged bytes";
            const auto before = inventory(outside);
            auto published = inventory(
                QUrl::fromLocalFile(QString::fromStdString((root / "analysis").string())));
            edi::Project project;
            project.path = root.string();
            edi_app::ScanSession session(nullptr);
            QString refusal;
            QVariantMap keptBefore, keptAfter, wantedFiles;
            std::string kept;
            if (late) {
                qputenv("EDI_REPORT_FAULT_DIR",
                        QByteArray::fromStdString((root / "analysis").string()));
                qputenv("EDI_REPORT_FAULT_KIND", "scan-rename");
                qputenv("EDI_REPORT_FAULT_LOG",
                        QByteArray::fromStdString((root / "failure-receipt").string()));
            }
            if (route == "writeRun") {
                edi_app::ScanSession::Run run;
                run.identity = "authored-identity";
                run.seconds = 1.25;
                run.outcome = "success";
                refusal = session.writeRun(project, run);
            } else if (route == "putFiles" || route.startsWith("putFilesMask:")) {
                edi_app::ScanSession::Files wanted;
                const int mask=route=="putFiles"?15:route.mid(QStringLiteral("putFilesMask:").size()).toInt();
                const std::string bytes[]={"new results\n","new provenance\n","{}\n","new notes\n"};
                std::optional<std::string>* fields[]={&wanted.results,&wanted.provenance,&wanted.run,&wanted.skipped};
                for(int index=0;index<4;++index)if(mask&(1<<index)) {
                    *fields[index]=bytes[index];
                    wantedFiles[names[index]]=QString::fromLatin1(QCryptographicHash::hash(
                        QByteArray::fromStdString(bytes[index]),QCryptographicHash::Sha256).toHex());
                }
                wantedFiles["carried"]=published.value("carried");
                refusal = session.putFiles(project, wanted);
            } else if (route == "putRunFile")
                refusal = session.putRunFile(project, std::string("{}\n"));
            else if (route == "swapRunFile" || route == "restoreRunFile" ||
                     route == "dropRunFile") {
                refusal = session.swapRunFile(project, std::string("{}\n"), kept);
                if (refusal.isEmpty() && route == "restoreRunFile")
                    refusal = session.restoreRunFile(project, kept);
                if (refusal.isEmpty() && route != "restoreRunFile") session.dropRunFile(kept);
            } else if (route == "takeFiles") {
                edi_app::ScanSession::Files taken;
                refusal = session.takeFiles(project, taken);
                if (refusal.isEmpty()) {
                    if (late) {
                        published = inventory(QUrl::fromLocalFile(QString::fromStdString((root / "analysis").string())));
                        keptBefore = inventory(QUrl::fromLocalFile(QString::fromStdString(taken.kept)));
                    }
                    refusal = session.putFiles(project, taken);
                    if (late) keptAfter = inventory(QUrl::fromLocalFile(QString::fromStdString(taken.kept)));
                }
            } else if (route == "removeRunFile")
                refusal = session.putRunFile(project, std::nullopt);
            clearFailure();
            auto after = inventory(outside);
            auto final = inventory(
                QUrl::fromLocalFile(QString::fromStdString((root / "analysis").string())));
            // Temporary names are owned workspace; compare published files separately on refusal.
            auto filtered = [&temporary](QVariantMap map) {
                for (auto it = map.begin(); it != map.end();) {
                    if (it.key() == QString::fromStdString(temporary.filename().string()) ||
                        it.key().endsWith(".edi-staged") || it.key().startsWith(".edi-set-aside/"))
                        it = map.erase(it);
                    else
                        ++it;
                }
                return map;
            };
            return {{"before", before},
                    {"after", after},
                    {"publishedBefore", filtered(published)},
                    {"publishedAfter", filtered(final)},
                    {"wanted", wantedFiles},
                    {"refusal", refusal},
                    {"receipt", fs::exists(root / "failure-receipt")},
                    {"kept", keptBefore == keptAfter},
                    {"carried", final.value("carried") == published.value("carried")}};
        } catch (const std::exception& error) {
            clearFailure();
            return {{"setupError", error.what()}};
        }
    }
    Q_INVOKABLE bool temporaryAlias(const QUrl& location, const QUrl& outside, const QString& name,
                                    bool hard, bool linked) const {
        namespace fs = std::filesystem;
        try {
            const fs::path root(location.toLocalFile().toStdString()),
                ext(outside.toLocalFile().toStdString());
            std::ofstream(ext / "sentinel") << "independent retained output inode";
            if (linked) {
                fs::rename(root / "reports", ext / "reports");
                fs::create_directory_symlink(ext / "reports", root / "reports");
            }
            const auto part =
                linked ? root / ("." + name.toStdString() + ".tmp")
                       : root / "reports" / (name.toStdString() + ".tmp");
            if (hard)
                fs::create_hard_link(ext / "sentinel", part);
            else
                fs::create_symlink(ext / "sentinel", part);
            return true;
        } catch (...) {
            return false;
        }
    }

    Q_INVOKABLE QVariantList staticCorrelationCellBorders() const {
        const double missing = std::numeric_limits<double>::quiet_NaN();
        edi::ReportModel model;
        model.sections = {edi::ReportSection::Correlations};
        model.contents = {{"correlations", "Correlations", true}};
        model.correlations = edi::ReportCorrelations{{"alpha", "beta"}, {missing, missing, .65, missing}, .2, 2, {}};
        QTextDocument document;
        document.setHtml(QString::fromStdString(edi::report_static_html(model, 400)));
        QVariantList result;
        for (auto* frame : document.rootFrame()->childFrames()) {
            auto* table = qobject_cast<QTextTable*>(frame);
            if (!table || table->rows() != 3 || table->columns() != 3) continue;
            for (int row = 1; row <= 2; ++row) for (int column = 1; column <= 2; ++column) {
                const auto cell = table->cellAt(row, column).format().toTableCellFormat();
                result.append(QVariantMap{{"row", row}, {"column", column},
                    {"top", cell.topBorder()}, {"right", cell.rightBorder()},
                    {"bottom", cell.bottomBorder()}, {"left", cell.leftBorder()}});
            }
        }
        return result;
    }
    Q_INVOKABLE bool retainedLink(const QUrl& location, const QUrl& outside,
                                  const QString& kind, const QString& name) const {
        const QDir project(location.toLocalFile()), external(outside.toLocalFile());
        if (kind == "directory") {
            const auto source = project.filePath("reports");
            const auto target = external.filePath("reports");
            return QDir().rename(source, target) && QFile::link(target, source);
        }
        QFile sentinel(external.filePath("target"));
        if (!sentinel.open(QIODevice::WriteOnly) || sentinel.write("external bytes must survive") < 0) return false;
        sentinel.close();
        const auto output = project.filePath("reports/" + name);
        if (QFileInfo::exists(output) && !QFile::remove(output)) return false;
        return QFile::link(sentinel.fileName(), output);
    }
    Q_INVOKABLE QVariantMap inventory(const QUrl& location) const {
        const QDir root(location.toLocalFile());
        QVariantMap result;
        QDirIterator files(root.path(), QDir::Files | QDir::Hidden | QDir::NoDotAndDotDot,
                           QDirIterator::Subdirectories);
        while (files.hasNext()) {
            QFile file(files.next());
            if (!file.open(QIODevice::ReadOnly)) return {{"error", file.fileName()}};
            result.insert(root.relativeFilePath(file.fileName()),
                          QString::fromLatin1(QCryptographicHash::hash(file.readAll(), QCryptographicHash::Sha256).toHex()));
        }
        return result;
    }
    Q_INVOKABLE bool ownedOutput(const QUrl& location, const QString& name) const {
        const QDir root(location.toLocalFile());
        const QFileInfo parent(root.filePath("reports")), file(root.filePath("reports/" + name));
        return parent.isDir() && !parent.isSymLink() && file.isFile() && !file.isSymLink();
    }
    Q_INVOKABLE QString reportDigest(QObject* object) const {
        auto* report = qobject_cast<edi_app::ReportViewModel*>(object);
        return report ? QString::fromStdString(edi::report_digest(report->reportModel(), "html")) : QString{};
    }
    Q_INVOKABLE QString htmlFromJson(const QString& document, const QString& dataDir) const {
        const auto model = edi::report_from_json(document.toStdString());
        const auto libraries =
            edi::read_report_libraries(std::filesystem::path(dataDir.toStdString()));
        return QString::fromStdString(edi::report_html(model, libraries));
    }
    Q_INVOKABLE QString jsonDigest(const QString& document) const {
        return QString::fromStdString(edi::report_digest(edi::report_from_json(document.toStdString()), "html"));
    }
    Q_INVOKABLE QVariantMap reopenedModel(const QUrl& location) const {
        auto project = edi::load_project(location.toLocalFile().toStdString());
        project.calculate();
        auto model = edi::build_report(project, edi::effective_report_options(project, {}));
        return QJsonDocument::fromJson(QByteArray::fromStdString(edi::report_to_json(model))).toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap fullModel(QObject* object) const {
        auto* report = qobject_cast<edi_app::ReportViewModel*>(object);
        return report ? QJsonDocument::fromJson(QByteArray::fromStdString(edi::report_to_json(report->reportModel()))).toVariant().toMap() : QVariantMap{};
    }
    Q_INVOKABLE QObject* privateReport(const QUrl& location) {
        try {
            auto* project = new edi_app::ProjectViewModel(edi::load_project(location.toLocalFile().toStdString()), this);
            QQmlEngine::setObjectOwnership(project, QQmlEngine::CppOwnership);
            QQmlEngine::setObjectOwnership(project->report(), QQmlEngine::CppOwnership);
            project->report()->setActive(true);
            return project->report();
        } catch (const std::exception&) { return nullptr; }
    }
    Q_INVOKABLE bool referenceRow(QObject* object, const QString& format, const QString& name) const {
        auto* project = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (!project) return false;
        try {
            edi::ReportFile row;
            row.format = format.toStdString(); row.name = name.toStdString();
            row.saved = std::string("2031-02-03T04:05:06Z");
            row.project_last_modified = std::string("2030-01-02T03:04:05Z");
            row.digest = edi::report_digest(project->report()->reportModel(), format.toStdString());
            project->recordReportFiles({std::move(row)});
            project->report()->refresh();
            return true;
        } catch (const std::exception&) { return false; }
    }
    Q_INVOKABLE void armFailure(const QUrl& location, const QString& kind) const {
        qputenv("EDI_REPORT_FAULT_DIR", QDir(location.toLocalFile()).filePath("reports").toUtf8());
        qputenv("EDI_REPORT_FAULT_KIND", kind.toUtf8());
        qputenv("EDI_REPORT_FAULT_LOG", QDir(location.toLocalFile()).filePath("failure-receipt").toUtf8());
    }
    Q_INVOKABLE void clearFailure() const {
        qunsetenv("EDI_REPORT_FAULT_DIR"); qunsetenv("EDI_REPORT_FAULT_KIND"); qunsetenv("EDI_REPORT_FAULT_LOG");
    }
    Q_INVOKABLE QVariantList reopenedStates(const QUrl& location) const {
        QVariantList out;
        auto project = edi::load_project(location.toLocalFile().toStdString());
        project.calculate();
        for (const auto& state : edi::report_file_states(project, {}))
            out.append(QVariantMap{{"name", QString::fromStdString(state.name)}, {"state", QString::fromStdString(state.state)}});
        return out;
    }
    Q_INVOKABLE int colourObserverControl() const {
        QImage image(2, 3, QImage::Format_RGB32);
        image.fill(QColor("#123456")); image.setPixelColor(0, 0, Qt::white);
        return figureColours({{"independent", QVariant::fromValue(image)}}, "#123456").value("independent").toInt();
    }
    Q_INVOKABLE QVariantMap figureColours(const QVariantMap& figures, const QString& colour) const {
        QVariantMap out;
        const QColor wanted(colour);
        for (auto it = figures.cbegin(); it != figures.cend(); ++it) {
            const auto image = it.value().value<QImage>();
            int count = 0;
            for (int y = 0; y < image.height(); ++y)
                for (int x = 0; x < image.width(); ++x)
                    if (image.pixelColor(x, y).rgb() == wanted.rgb()) ++count;
            out.insert(it.key(), count);
        }
        return out;
    }
    Q_INVOKABLE QVariantMap surfaceFacts(const QUrl& location, const QString& scheme, const QString& experiment) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()); root.cd("../../..");
        QProcess process;
        auto env = QProcessEnvironment::systemEnvironment();
        const auto extension = env.value("EDI_REPORT_ACCEPTANCE_EXTENSION_DIR");
        if (!extension.isEmpty()) env.insert("EDI_EXTENSION_DIR", extension);
        env.insert("PYTHONPATH", root.filePath("lib") + QDir::listSeparator() + root.path() + QDir::listSeparator() + env.value("PYTHONPATH"));
        process.setProcessEnvironment(env);
        process.start(QStandardPaths::findExecutable("python"), {root.filePath("tests/fixtures/report_context/observe.py"), location.toLocalFile(), scheme, experiment});
        if (!process.waitForFinished(25000)) { process.kill(); return {{"error", "The report surface observer did not finish"}}; }
        const auto text = process.readAllStandardOutput();
        const auto document = QJsonDocument::fromJson(text);
        return document.isNull() ? QVariantMap{{"error", QString::fromUtf8(text + process.readAllStandardError())}} : document.toVariant().toMap();
    }
};
static void register_report_boundaries() {
#if defined(Q_OS_LINUX) || defined(Q_OS_MACOS)
    // Every ordinary app runner gets the real failure library before any gate.
    // Faults remain unarmed outside the test's exact report directory.
    if (!qEnvironmentVariableIsSet("EDI_REPORT_ACCEPTANCE_PRELOADED")) {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()); root.cd("../../..");
        QTemporaryDir scratch(QDir::tempPath() + "/edi-report-faults-XXXXXX");
        if (!scratch.isValid()) qFatal("Cannot create the report failure witness");
        const QString library = scratch.filePath("faults.so");
        QStringList arguments;
#ifdef Q_OS_MACOS
        arguments = {"-dynamiclib", "-undefined", "dynamic_lookup"};
#else
        arguments = {"-shared", "-fPIC"};
#endif
        arguments << root.filePath("tests/fixtures/report_publication/faults.c") << "-o" << library;
#ifndef Q_OS_MACOS
        arguments << "-ldl";
#endif
        QProcess compiler;
        compiler.start(QStandardPaths::findExecutable("cc"), arguments);
        if (!compiler.waitForFinished(15000) || compiler.exitStatus() != QProcess::NormalExit || compiler.exitCode() != 0) {
            compiler.kill();
            compiler.waitForFinished(1000);
            scratch.remove();
            qFatal("Cannot compile the report failure witness: %s", compiler.readAllStandardError().constData());
        }
#ifdef Q_OS_MACOS
        const char* key = "DYLD_INSERT_LIBRARIES";
        qputenv("DYLD_FORCE_FLAT_NAMESPACE", "1");
#else
        const char* key = "LD_PRELOAD";
#endif
        const QByteArray previous = qgetenv(key);
        qputenv(key, QFile::encodeName(library) + (previous.isEmpty() ? QByteArray{} : ":" + previous));
        qputenv("EDI_REPORT_ACCEPTANCE_PRELOADED", QFile::encodeName(scratch.path()));
        qputenv("EDI_REPORT_ACCEPTANCE_OWNER_PID", QByteArray::number(QCoreApplication::applicationPid()));
        const auto strings = QCoreApplication::arguments();
        std::vector<QByteArray> bytes;
        for (const auto& argument : strings) bytes.push_back(argument.toLocal8Bit());
        std::vector<char*> argv;
        for (auto& argument : bytes) argv.push_back(argument.data());
        argv.push_back(nullptr);
        ::execv(QFile::encodeName(QCoreApplication::applicationFilePath()).constData(), argv.data());
        scratch.remove();
        qFatal("Cannot relaunch the app test runner with its report failure witness");
    }
    // Qt Quick Test can return without QCoreApplication::exec(), hence without aboutToQuit.
    // Post routines also run when the app object is destroyed after a failed test result.
    qAddPostRoutine([] {
        bool validOwner = false;
        const auto owner = qgetenv("EDI_REPORT_ACCEPTANCE_OWNER_PID").toLongLong(&validOwner);
        const QFileInfo folder(QString::fromLocal8Bit(qgetenv("EDI_REPORT_ACCEPTANCE_PRELOADED")));
        if (validOwner && owner == QCoreApplication::applicationPid() && !folder.isSymLink()
            && folder.fileName().startsWith("edi-report-faults-")
            && QDir(folder.absolutePath()).canonicalPath() == QDir(QDir::tempPath()).canonicalPath())
            QDir(folder.absoluteFilePath()).removeRecursively();
    });
#endif
    qmlRegisterSingletonType<ReportBoundaryProof>("ReportBoundaryAcceptance", 1, 0, "BoundaryProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new ReportBoundaryProof; });
}
Q_COREAPP_STARTUP_FUNCTION(register_report_boundaries)
#include "test_report_boundary_observer.moc"
