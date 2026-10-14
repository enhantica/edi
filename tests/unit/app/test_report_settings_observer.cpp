// SPDX-License-Identifier: BSD-3-Clause
#include <memory>
#include <QAnimationDriver>
#include <QPdfWriter>
#include <QPainter>
#include <QProcess>
#include <QProcessEnvironment>
#include <QStandardPaths>
#include <QJsonDocument>
#include <QCryptographicHash>
#include <QJSEngine>
#include <QRegularExpression>
#include <atomic>
#include <vector>
#include <QTemporaryDir>
#include <QDirIterator>
#include <QScreen>
#include <QGuiApplication>
#include <QJSValue>
#include <QKeyEvent>
#include <QQuickItem>
#include <QQuickWindow>
#include <QtTest/qtestkeyboard.h>
#include <QtTest/qtestcase.h>
#include <QLoggingCategory>
#include <QMutex>
#include <QMutexLocker>
#include "measured_layer.hpp"
#include "project_view_model.hpp"
#include "fit_view_model.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QMetaProperty>
#include <QFileInfo>
#include <QFile>
#include <QTextStream>
#include <QSettings>
#include <QUrl>
#include <QVariantMap>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlError>
#include <QtQml/qqml.h>
#include "engine_setup.hpp"

namespace {
QMutex report_console_mutex;
QVariantList report_console_messages;
std::atomic<QtMessageHandler> report_previous_handler{nullptr};
void report_console_handler(QtMsgType type, const QMessageLogContext& context, const QString& message) {
    if ((type == QtWarningMsg || type == QtCriticalMsg) &&
        ((message.contains("Binding loop detected") && message.contains("plotWidth")) ||
         message.contains("window doesn't exist"))) {
        QMutexLocker guard(&report_console_mutex);
        report_console_messages.append(QVariantMap{
            {"severity", type == QtCriticalMsg ? "critical" : "warning"},
            {"category", QString::fromUtf8(context.category ? context.category : "")},
            {"text", message}});
    }
    if (const auto previous = report_previous_handler.load()) previous(type, context, message);
}
}

// Public Qt clock: rendering and machine load cannot skip an observed tween step.
class AcceptanceAnimationDriver : public QAnimationDriver {
public:
    void advance() override {} // Only the gate advances the clock.
    qint64 elapsed() const override { return milliseconds_; }
    void step(int milliseconds) { milliseconds_ += milliseconds; advanceAnimation(); }
protected:
    void start() override { milliseconds_ = 0; QAnimationDriver::start(); }
private:
    qint64 milliseconds_ = 0;
};

class ReportSettingsProof : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool webAvailable READ webAvailable CONSTANT)
public:
    using QObject::QObject;
    bool webAvailable() const { return true; }
    Q_INVOKABLE QObject* creationDialog(QObject* root) const {
        if (!root) return nullptr;
        for (auto* object : root->findChildren<QObject*>())
            if (object->metaObject()->indexOfProperty("projectName") >= 0 &&
                object->metaObject()->indexOfProperty("projectParentDirectory") >= 0)
                return object;
        return nullptr;
    }
    // Capability-only seam: compile the application's actual resource unchanged
    // except for the native/browser availability operand. No path/state output
    // is supplied by this observer, and this is not a browser-download proof.
    Q_INVOKABLE QObject* webExport(QQuickItem* parent, QObject* report, QObject* preview) const {
        auto* engine = parent ? qmlEngine(parent) : nullptr;
        if (!engine) return nullptr;
        const QUrl origin("qrc:/qt/qml/edi/app/Pages/Report/ExportGroup.qml");
        QFile file(":/qt/qml/edi/app/Pages/Report/ExportGroup.qml");
        if (!file.open(QIODevice::ReadOnly)) return nullptr;
        auto source = file.readAll();
        source.replace("import edi.app", "import edi.app\nimport ReportAcceptance 1.0 as Platform");
        source.replace("WebFiles.available", "Platform.SettingsProof.webAvailable");
        QQmlComponent component(engine);
        component.setData(source, origin);
        auto* object = component.createWithInitialProperties({
            {"report", QVariant::fromValue(report)}, {"preview", QVariant::fromValue(preview)}},
            engine->rootContext());
        if (!object) {
            for (const auto& error : component.errors()) qWarning().noquote() << error.toString();
            return nullptr;
        }
        object->setParent(parent);
        if (auto* item = qobject_cast<QQuickItem*>(object)) item->setParentItem(parent);
        return object;
    }
    Q_INVOKABLE QVariantMap htmlFigureFacts(const QString& html) const {
        const QRegularExpression shared("const sharedSites = sites => \\{[\\s\\S]*?\n  \\};");
        const QRegularExpression legend("const legend = document.createElement\\('div'\\);[\\s\\S]*?figure.appendChild\\(legend\\);");
        const auto s = shared.match(html), l = legend.match(html);
        if (!s.hasMatch() || !l.hasMatch()) return {{"error", "Actual HTML must reach its shared-site and legend producers"}};
        auto code = repoText("tests/unit/app/ReportHtmlProof.js");
        code.replace("/* ACTUAL_SHARED_SITE_FUNCTION */", s.captured());
        code.replace("/* ACTUAL_LEGEND */", l.captured());
        QJSEngine engine;
        const auto result = engine.evaluate(code);
        if (result.isError()) return {{"error", result.toString()}};
        return QJsonDocument::fromJson(result.toString().toUtf8()).toVariant().toMap();
    }
    Q_INVOKABLE QString repoText(const QString& relative) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()); root.cd("../../..");
        QFile file(root.filePath(relative));
        return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString{};
    }
    Q_INVOKABLE QVariantMap fileFacts(const QUrl& location, const QString& relative) const {
        QFile file(QDir(location.toLocalFile()).filePath(relative));
        if (!file.open(QIODevice::ReadOnly)) return {};
        const auto bytes = file.readAll();
        return {{"sha256", QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex())},
                {"bytes", bytes.size()}, {"modified", QFileInfo(file).lastModified().toMSecsSinceEpoch()}};
    }
    Q_INVOKABLE QUrl childUrl(const QUrl& location, const QString& relative) const {
        return QUrl::fromLocalFile(QDir(location.toLocalFile()).filePath(relative));
    }
    Q_INVOKABLE QVariantMap pdfFacts(const QUrl& location) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "PDF observer requires the runner's Python"}};
        QProcess process;
        process.start(python, {root.filePath("ReportPdf.py"), location.toLocalFile()});
        if (!process.waitForFinished(10000)) { process.kill(); return {{"error", "PDF observer did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap htmlEvolutionFacts(const QUrl& location) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "Browser observer requires the runner's Python"}};
        QProcess process;
        process.start(python, {root.filePath("tests/fixtures/report_evolution/observe_browser.py"), location.toLocalFile()});
        if (!process.waitForFinished(20000)) { process.kill(); return {{"error", "Actual HTML browser did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap reportHtmlMatrices(const QUrl& location) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "Report surface observer needs Python"}};
        QProcess process;
        auto environment = QProcessEnvironment::systemEnvironment();
        // Local app diagnostics use the task engine's consumer artifact when
        // present. A replay can explicitly select its sealed matching artifact.
        QString extension = environment.value("EDI_REPORT_ACCEPTANCE_EXTENSION_DIR");
        if (extension.isEmpty() && QDir(root.filePath("build/ci-consumer/python/edi")).exists())
            extension = root.filePath("build/ci-consumer/python/edi");
        if (!extension.isEmpty()) environment.insert("EDI_EXTENSION_DIR", extension);
        environment.insert("PYTHONPATH", root.filePath("lib") + QDir::listSeparator() +
                           root.path() + QDir::listSeparator() + environment.value("PYTHONPATH"));
        process.setProcessEnvironment(environment);
        process.start(python, {root.filePath("tests/fixtures/report_effective_template/observe_html.py"), location.toLocalFile()});
        if (!process.waitForFinished(25000)) { process.kill(); return {{"error", "Python and CLI HTML observers did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap pdfWitness() {
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-pdf-proof-XXXXXX");
        if (!directory->isValid()) return {{"error", "PDF witness has no temporary directory"}};
        const auto file = QDir(directory->path()).filePath("independent.pdf");
        {
            QPdfWriter writer(file);
            writer.setResolution(72);
            writer.setPageSize(QPageSize(QPageSize::A4));
            writer.setPageMargins(QMarginsF(25, 25, 25, 25), QPageLayout::Millimeter);
            QPainter painter(&writer);
            QFont font("PT Sans"); font.setPointSizeF(10.04); painter.setFont(font);
            painter.drawText(QPointF(0, 20), "Short name lbco_hrpt_s2");
            QImage image(8, 8, QImage::Format_RGB32); image.fill(Qt::blue);
            painter.drawImage(QRectF(0, 40, 40, 40), image);
            painter.fillRect(QRectF(0, 100, 20, 20), QColor("#4575b4"));
            painter.fillRect(QRectF(20, 100, 20, 20), QColor("#d73027"));
            painter.fillRect(QRectF(40, 100, 20, 20), QColor("#ffffff"));
            painter.drawText(QPointF(220, 690), "1");
            writer.newPage();
            painter.drawText(QPointF(0, 20), "Second page");
            painter.drawText(QPointF(220, 690), "2");
        }
        const auto result = pdfFacts(QUrl::fromLocalFile(file));
        directories_.push_back(std::move(directory));
        return result;
    }
    Q_INVOKABLE bool beginAnimationClock() {
        if (animation_driver_) return false;
        animation_driver_ = std::make_unique<AcceptanceAnimationDriver>();
        animation_driver_->install();
        return true;
    }
    Q_INVOKABLE bool stepAnimationClock(int milliseconds) {
        if (!animation_driver_ || milliseconds <= 0) return false;
        animation_driver_->step(milliseconds);
        return true;
    }
    Q_INVOKABLE void endAnimationClock() {
        if (!animation_driver_) return;
        animation_driver_->uninstall();
        animation_driver_.reset();
    }
    Q_INVOKABLE bool beginConsoleCapture() const {
        const auto previous = qInstallMessageHandler(report_console_handler);
        if (previous != report_console_handler) report_previous_handler.store(previous);
        QMutexLocker guard(&report_console_mutex);
        report_console_messages.clear();
        return report_previous_handler.load() != nullptr;
    }
    Q_INVOKABLE QVariantList consoleMessages() const {
        QMutexLocker guard(&report_console_mutex);
        return report_console_messages;
    }
    Q_INVOKABLE void qualifyConsoleCapture() const {
        QTest::ignoreMessage(QtWarningMsg, "Binding loop detected for property \"plotWidth\"");
        qWarning("Binding loop detected for property \"plotWidth\"");
        QTest::ignoreMessage(QtCriticalMsg, "window doesn't exist.");
        const QLoggingCategory graphs("qt.graphs2d");
        qCCritical(graphs, "window doesn't exist.");
    }
    Q_INVOKABLE bool type(QObject* object, const QString& text) const {
        auto* field = qobject_cast<QQuickItem*>(object);
        if (!field || !field->window() || field->window()->activeFocusItem() != field) return false;
        if (!QMetaObject::invokeMethod(field, "selectAll")) return false;
        QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, text);
        QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, text);
        QCoreApplication::sendEvent(field->window(), &press);
        QCoreApplication::sendEvent(field->window(), &release);
        return field->property("text").toString() == text;
    }
    Q_INVOKABLE bool key(QObject* object, int key) const {
        auto* field = qobject_cast<QQuickItem*>(object);
        if (!field || !field->window()) return false;
        QTest::keyClick(field->window(), static_cast<Qt::Key>(key), Qt::NoModifier, 0);
        return true;
    }
    Q_INVOKABLE QVariantList points(QObject* object) const {
        const auto* layer = qobject_cast<edi_app::MeasuredLayer*>(object);
        if (!layer) return {};
        QVariantList result;
        for (const auto& point : layer->points()) result.append(QVariantMap{{"x", point.x()}, {"y", point.y()}});
        return result;
    }
    Q_INVOKABLE bool publishScanSummary(QObject* object, double seconds = 9.0) const {
        auto* project = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (!project) return false;
        edi_app::ScanSummary summary;
        summary.files = 162;
        summary.fitted = 162;
        summary.ok = 160;
        summary.failed = 2;
        summary.chi_min = 12.34;
        summary.chi_max = 23.45;
        summary.seconds = seconds;
        summary.outcome = "success";
        project->fit()->showScan(summary, true);
        return true;
    }
    Q_INVOKABLE QVariantMap screen() const {
        const auto screen = QGuiApplication::primaryScreen();
        if (!screen) return {};
        const auto bounds = screen->availableGeometry();
        return {{"x", bounds.x()}, {"y", bounds.y()}, {"width", bounds.width()}, {"height", bounds.height()}};
    }
    Q_INVOKABLE QUrl emptyDirectory() {
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-empty-XXXXXX");
        if (!directory->isValid()) return {};
        const auto result = QUrl::fromLocalFile(directory->path());
        directories_.push_back(std::move(directory));
        return result;
    }
    Q_INVOKABLE QUrl copyProject(const QUrl& input) {
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-settings-XXXXXX");
        if (!directory->isValid()) return {};
        QDir source(input.toLocalFile());
        QDirIterator files(source.absolutePath(), QDir::AllEntries | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const auto from = files.next();
            const auto to = QDir(directory->path()).filePath(source.relativeFilePath(from));
            if (QFileInfo(from).isDir()) { if (!QDir().mkpath(to)) return {}; }
            else if (!QFile::copy(from, to)) return {};
        }
        const auto result = QUrl::fromLocalFile(directory->path());
        directories_.push_back(std::move(directory));
        return result;
    }
    Q_INVOKABLE QString text(const QUrl& project, const QString& relative) const {
        QFile file(QDir(project.toLocalFile()).filePath(relative));
        if (!file.open(QIODevice::ReadOnly)) return {};
        return QString::fromUtf8(file.readAll());
    }
    Q_INVOKABLE bool write(const QUrl& project, const QString& relative, const QString& text) const {
        QFile file(QDir(project.toLocalFile()).filePath(relative));
        if (!QDir().mkpath(QFileInfo(file).absolutePath())) return false;
        return file.open(QIODevice::WriteOnly | QIODevice::Truncate) && file.write(text.toUtf8()) == text.toUtf8().size() && file.flush();
    }
    Q_INVOKABLE bool remove(const QUrl& project, const QString& relative) const {
        return QFile::remove(QDir(project.toLocalFile()).filePath(relative));
    }
    Q_INVOKABLE QString localPath(const QUrl& location) const { return location.toLocalFile(); }
    Q_INVOKABLE QVariantMap palette(bool safe) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        QDir directory(root.filePath("data/palettes"));
        QVariantMap output;
        for (const auto& name : directory.entryList({"*.tsv"}, QDir::Files, QDir::Name)) {
            const bool is_default = QFileInfo(name).completeBaseName().toLower() == "default";
            if (is_default == safe) continue;
            QFile file(directory.filePath(name));
            if (!file.open(QIODevice::ReadOnly)) continue;
            QTextStream stream(&file);
            const auto header = stream.readLine().split('\t');
            QVariantList pattern, structure;
            while (!stream.atEnd()) {
                const auto cells = stream.readLine().split('\t');
                if (cells.size() != header.size()) continue;
                QVariantMap row;
                for (qsizetype index = 0; index < cells.size(); ++index) row.insert(header[index], cells[index]);
                if (row.value("role") == "pattern") pattern.append(row);
                if (row.value("role") == "structure") structure.append(row);
            }
            output.insert("pattern", pattern);
            output.insert("structure", structure);
            return output;
        }
        return output;
    }
    Q_INVOKABLE QString fileName(const QUrl& location) const {
        return QFileInfo(location.toLocalFile()).fileName();
    }
    Q_INVOKABLE QString parentName(const QUrl& location) const {
        return QFileInfo(QFileInfo(location.toLocalFile()).absolutePath()).fileName();
    }
    Q_INVOKABLE bool temporary(const QUrl& location) const {
        return QFileInfo(location.toLocalFile()).absoluteFilePath().startsWith(QDir::tempPath() + '/');
    }
    Q_INVOKABLE QUrl legacy(const QUrl& location) const {
        QDir root = QFileInfo(location.toLocalFile()).absoluteDir();
        if (root.dirName() == "EasyScience") root.cdUp();
        return QUrl::fromLocalFile(root.filePath("settings.ini"));
    }
    Q_INVOKABLE void erase(const QUrl& location, const QString& group, const QString& key) const {
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        settings.remove(key);
        settings.sync();
    }
    Q_INVOKABLE QVariantMap settingFacts(const QUrl& location, const QString& group, const QString& key) const {
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        const auto value = settings.value(key);
        return {{"file", location.toLocalFile()}, {"group", group}, {"key", key},
                {"type", QString::fromUtf8(value.typeName() ? value.typeName() : "invalid")},
                {"value", value}, {"list", value.toStringList()}};
    }
    Q_INVOKABLE QVariant value(const QUrl& location, const QString& group, const QString& key) const {
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        return settings.value(key);
    }
    Q_INVOKABLE void seed(const QUrl& location, const QString& group, const QString& key, const QVariant& value) const {
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        settings.setValue(key, value);
        settings.sync();
    }
    Q_INVOKABLE QVariantMap restart(const QString& source) const {
        QQmlEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(source.toUtf8(), QUrl("file:///report-settings-restart.qml"));
        std::unique_ptr<QObject> object(component.create());
        QVariantMap result;
        if (!object) {
            QStringList errors;
            for (const auto& error : component.errors()) errors.append(error.toString());
            result.insert("error", errors.join('\n'));
            return result;
        }
        const auto meta = object->metaObject();
        for (int index = QObject::staticMetaObject.propertyCount(); index < meta->propertyCount(); ++index) {
            const auto property = meta->property(index);
            auto value = property.read(object.get());
            if (value.metaType().flags().testFlag(QMetaType::PointerToQObject)) continue;
            if (value.metaType() == QMetaType::fromType<QJSValue>()) value = value.value<QJSValue>().toVariant();
            result.insert(QString::fromUtf8(property.name()), value);
        }
        return result;
    }
private:
    std::unique_ptr<AcceptanceAnimationDriver> animation_driver_;
    std::vector<std::unique_ptr<QTemporaryDir>> directories_;
};

static void register_report_settings_proof() {
    qmlRegisterSingletonType<ReportSettingsProof>("ReportAcceptance", 1, 0, "SettingsProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new ReportSettingsProof; });
}
Q_COREAPP_STARTUP_FUNCTION(register_report_settings_proof)
#include "test_report_settings_observer.moc"
