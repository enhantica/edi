// SPDX-License-Identifier: BSD-3-Clause
#include <memory>
#include <vector>
#include <QCoreApplication>
#include <QFileInfo>
#include <QColor>
#include <QImage>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
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
#include "edi/report_save.hpp"

class ReportBoundaryProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QString reportDigest(QObject* object) const {
        auto* report = qobject_cast<edi_app::ReportViewModel*>(object);
        return report ? QString::fromStdString(edi::report_digest(report->reportModel(), "html")) : QString{};
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
        scratch.setAutoRemove(false);
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
        if (!compiler.waitForFinished(15000) || compiler.exitStatus() != QProcess::NormalExit || compiler.exitCode() != 0)
            qFatal("Cannot compile the report failure witness: %s", compiler.readAllStandardError().constData());
#ifdef Q_OS_MACOS
        const char* key = "DYLD_INSERT_LIBRARIES";
        qputenv("DYLD_FORCE_FLAT_NAMESPACE", "1");
#else
        const char* key = "LD_PRELOAD";
#endif
        const QByteArray previous = qgetenv(key);
        qputenv(key, QFile::encodeName(library) + (previous.isEmpty() ? QByteArray{} : ":" + previous));
        qputenv("EDI_REPORT_ACCEPTANCE_PRELOADED", QFile::encodeName(scratch.path()));
        const auto strings = QCoreApplication::arguments();
        std::vector<QByteArray> bytes;
        for (const auto& argument : strings) bytes.push_back(argument.toLocal8Bit());
        std::vector<char*> argv;
        for (auto& argument : bytes) argv.push_back(argument.data());
        argv.push_back(nullptr);
        ::execv(QFile::encodeName(QCoreApplication::applicationFilePath()).constData(), argv.data());
        qFatal("Cannot relaunch the app test runner with its report failure witness");
    }
    QObject::connect(QCoreApplication::instance(), &QCoreApplication::aboutToQuit, [] {
        QDir(QString::fromLocal8Bit(qgetenv("EDI_REPORT_ACCEPTANCE_PRELOADED"))).removeRecursively();
    });
#endif
    qmlRegisterSingletonType<ReportBoundaryProof>("ReportBoundaryAcceptance", 1, 0, "BoundaryProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new ReportBoundaryProof; });
}
Q_COREAPP_STARTUP_FUNCTION(register_report_boundaries)
#include "test_report_boundary_observer.moc"
