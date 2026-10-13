// SPDX-License-Identifier: BSD-3-Clause
#include <memory>
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

class ReportSettingsProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
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
    std::vector<std::unique_ptr<QTemporaryDir>> directories_;
};

static void register_report_settings_proof() {
    qmlRegisterSingletonType<ReportSettingsProof>("ReportAcceptance", 1, 0, "SettingsProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new ReportSettingsProof; });
}
Q_COREAPP_STARTUP_FUNCTION(register_report_settings_proof)
#include "test_report_settings_observer.moc"
