// : test-only introspection. No product rule or correctness oracle lives here.
// Link this TU into the Qt Quick Test runner alongside the production edi.app module.
#include <QAbstractItemModel>
#include <QCoreApplication>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QJSEngine>
#include <QJsonDocument>
#include <QMetaMethod>
#include <QMetaProperty>
#include <QQmlEngine>
#include <QSignalSpy>
#include <QQuickItem>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTextDocument>
#include <QtQml/qqml.h>
#include <memory>
#include <vector>
#include <iostream>
#include <sstream>
#include <filesystem>
#include <edi/scan.hpp>
#include "evolution_view_model.hpp"
#include <edi/io.hpp>
#include "experiment_view_model.hpp"
#include "project_view_model.hpp"

class AcceptanceProbe final : public QObject {
    Q_OBJECT
    struct Watch {
        std::vector<std::unique_ptr<QSignalSpy>> spies;
        QList<QByteArray> names;
    };
    std::vector<Watch> watches_;
    static QString root() {
        return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
            .absoluteFilePath(QStringLiteral("../../.."));
    }
public:
    using QObject::QObject;
    Q_INVOKABLE bool nativeText(QObject *object) const {
        return object && (object->inherits("QQuickTextEdit") || object->inherits("QQuickText"));
    }
    Q_INVOKABLE QString plainText(const QString &richText) const {
        QTextDocument document;
        document.setHtml(richText);
        return document.toPlainText();
    }
    Q_INVOKABLE bool writable(QObject *object, const QString &name) const {
        if (!object) return false;
        const int index = object->metaObject()->indexOfProperty(name.toUtf8().constData());
        return index >= 0 && object->metaObject()->property(index).isWritable();
    }
    Q_INVOKABLE bool writeProperty(QObject *object, const QString &name,
                                   const QVariant &value) const {
        return writable(object, name) && object->setProperty(name.toUtf8().constData(), value);
    }
    Q_INVOKABLE bool computedCurrent(QObject *object) const {
        const auto *experiment = qobject_cast<edi_app::ExperimentViewModel *>(object);
        if (!experiment) {
            qCritical(": currentness probe requires an ExperimentViewModel");
            return false;
        }
        return experiment->experiment()->computed_current();
    }
    // The independent library surface, on the actual std::cerr channel (review-4 F1).
    // Capture is scoped and exception-safe; production Session is never called here.
    Q_INVOKABLE QString libraryLoadWarning(const QUrl &url) const {
        if (!url.isLocalFile()) return QStringLiteral("invalid local fixture URL");
        std::ostringstream diagnostic;
        struct Restore {
            std::streambuf *previous;
            ~Restore() { std::cerr.rdbuf(previous); }
        } restore{std::cerr.rdbuf(diagnostic.rdbuf())};
        try {
            const auto project = edi::load_project(url.toLocalFile().toStdString());
            (void)project;
        } catch (const std::exception &error) {
            return QStringLiteral("fixture load failed: ") + QString::fromUtf8(error.what());
        }
        return QString::fromStdString(diagnostic.str()).trimmed();
    }
    Q_INVOKABLE QUrl repoUrl(const QString &path) const {
        return QUrl::fromLocalFile(QDir(root()).absoluteFilePath(path));
    }
    Q_INVOKABLE bool appendNotes(const QUrl &url, const QString &text) const {
        if (!url.isLocalFile() || !QFileInfo(url.toLocalFile()).isFile()) return false;
        QFile file(url.toLocalFile());
        if (!file.open(QIODevice::WriteOnly | QIODevice::Append)) return false;
        const QByteArray bytes = text.toUtf8();
        return file.write(bytes) == bytes.size() && file.flush();
    }
    Q_INVOKABLE QString scanIndexError(QObject *object) const {
        const auto *project = qobject_cast<edi_app::ProjectViewModel *>(object);
        if (!project || !project->scanSession()) return QStringLiteral("not a scan project");
        return QString::fromStdString(project->scanSession()->index().error);
    }
    Q_INVOKABLE bool datasetReady(QObject *object) const {
        const auto *project = qobject_cast<edi_app::ProjectViewModel *>(object);
        return project && project->pendingRefusal().isEmpty();
    }
    Q_INVOKABLE bool scanLastSingle(QObject *object) const {
        const auto *project = qobject_cast<edi_app::ProjectViewModel *>(object);
        return project && project->scanSession() && project->scanSession()->run().last_single;
    }
    Q_INVOKABLE bool replaceState(const QUrl &target, const QUrl &replacement) const {
        if (!target.isLocalFile() || !replacement.isLocalFile()) return false;
        const std::filesystem::path path(target.toLocalFile().toStdString());
        std::error_code error;
        std::filesystem::rename(path, path.string() + ".retained", error);
        if (error) return false;
        std::filesystem::rename(replacement.toLocalFile().toStdString(), path, error);
        return !error;
    }
    Q_INVOKABLE QString scanReread(QObject *object, const QString &reader) const {
        auto *project = qobject_cast<edi_app::ProjectViewModel *>(object);
        if (!project || !project->scanSession()) return QStringLiteral("not a scan project");
        const auto *session = project->scanSession();
        try {
            if (reader == "offset") {
                (void)edi::read_scan_row(project->project(), session->index().rows.at(0).offset);
            } else if (reader == "row") {
                (void)session->row(project->project(), 0);
            } else if (reader == "evolution") {
                project->evolution()->setCurrentParameter(1 - project->evolution()->currentParameter());
                // Evolution catches stream errors and publishes the project error channel.
                return project->lastError();
            } else {
                return QStringLiteral("unknown reader");
            }
        } catch (const std::exception &error) {
            return QString::fromUtf8(error.what());
        }
        return {};
    }
    Q_INVOKABLE QString readFile(const QString &path) const {
        QFile file(QDir(root()).absoluteFilePath(path));
        if (!file.open(QIODevice::ReadOnly)) {
            qCritical(": required fixture cannot be read: %s", qPrintable(path));
            return {};
        }
        return QString::fromUtf8(file.readAll());
    }
    Q_INVOKABLE QUrl referenceUrl(const QString &path) const {
        const QString base = qEnvironmentVariable(
            "EDI_ACCEPTANCE_REFERENCE", QDir(root()).filePath("tests/fixtures/e04_t1/reference"));
        return QUrl::fromLocalFile(QDir(base).absoluteFilePath(path));
    }
    Q_INVOKABLE QVariantList reference() const {
        QFile file(referenceUrl("reference.json").toLocalFile());
        if (!file.open(QIODevice::ReadOnly)) {
            qCritical(": committed wiring regression reference is missing");
            return {};
        }
        return QJsonDocument::fromJson(file.readAll()).toVariant().toList();
    }
    Q_INVOKABLE QString linkedCrystaSha() const {
        QFile cache(QDir(root()).filePath("build/app/CMakeCache.txt"));
        if (!cache.open(QIODevice::ReadOnly)) {
            qCritical(": app build cache is missing its linked prefix");
            return {};
        }
        QString prefix;
        for (const QByteArray& line : cache.readAll().split('\n')) {
            if (!line.startsWith("CMAKE_PREFIX_PATH:")) continue;
            if (!prefix.isEmpty()) {
                qCritical(": app build cache has multiple linked prefix records");
                return {};
            }
            prefix = QString::fromUtf8(line.mid(line.indexOf('=') + 1).split(';').first());
        }
        const QString buildRoot = QDir(root()).canonicalPath() + "/build/";
        const QString selected = QDir(prefix).canonicalPath();
        if (selected != buildRoot + "crysta-prefix-app" &&
                selected != buildRoot + "crysta-consumer-prefix-app") {
            qCritical(": app build cache selects no declared crysta prefix");
            return {};
        }
        QFile file(selected + "/.crysta-sha");
        if (!file.open(QIODevice::ReadOnly)) {
            qCritical(": linked crysta source stamp is missing: %s", qPrintable(file.fileName()));
            return {};
        }
        const QByteArray stamp = file.readAll().trimmed();
        const QString sha = QString::fromLatin1(stamp.constData(), stamp.size());
        static const QRegularExpression fullSha(QStringLiteral("^[0-9a-f]{40}$"));
        if (!fullSha.match(sha).hasMatch()) {
            qCritical(": linked crysta source stamp is not a full SHA");
            return {};
        }
        return sha;
    }
    Q_INVOKABLE QVariantList rows(QAbstractItemModel *model) const {
        if (!model) {
            qCritical(": a required typed item model is null");
            return {};
        }
        QVariantList output;
        const auto roles = model->roleNames();
        for (int row = 0; row < model->rowCount(); ++row) {
            QVariantMap values;
            for (auto it = roles.cbegin(); it != roles.cend(); ++it)
                values.insert(QString::fromUtf8(it.value()), model->data(model->index(row, 0), it.key()));
            output.append(values);
        }
        return output;
    }
    Q_INVOKABLE bool writeRole(QAbstractItemModel *model, int row,
                              const QString &role, const QVariant &value) const {
        if (!model) return false;
        const auto roles = model->roleNames();
        for (auto it = roles.cbegin(); it != roles.cend(); ++it)
            if (QString::fromUtf8(it.value()) == role)
                return model->setData(model->index(row, 0), value, it.key());
        return false;
    }
    Q_INVOKABLE int watch(QObject *object) {
        if (!object) {
            qCritical(": cannot watch a missing contract object");
            return -1;
        }
        Watch watch;
        const auto *meta = object->metaObject();
        for (int i = 0; i < meta->methodCount(); ++i) {
            const auto method = meta->method(i);
            // Qt clones a signal with default arguments into shorter meta-methods.
            // Observe the full declaration once; the dataChanged clone has no roles.
            if (method.methodType() != QMetaMethod::Signal ||
                (method.attributes() & QMetaMethod::Cloned)) continue;
            watch.names.append(method.name());
            watch.spies.push_back(std::make_unique<QSignalSpy>(object, method));
        }
        watches_.push_back(std::move(watch));
        return static_cast<int>(watches_.size()) - 1;
    }
    Q_INVOKABLE QVariantMap events(int handle) const {
        QVariantMap result;
        if (handle < 0 || handle >= static_cast<int>(watches_.size())) {
            qCritical(": invalid signal watch");
            return result;
        }
        const auto &watch = watches_[handle];
        for (size_t i = 0; i < watch.spies.size(); ++i) {
            const auto &spy = *watch.spies[i];
            if (spy.isEmpty()) continue;
            QVariantList calls;
            for (const auto &args : spy) {
                if (watch.names[static_cast<int>(i)] == "dataChanged") {
                    if (args.size() != 3) {
                        qCritical("I3: dataChanged observation requires its complete three-argument payload");
                        continue;
                    }
                    calls.append(QVariantMap{{"first", args[0].value<QModelIndex>().row()},
                        {"last", args[1].value<QModelIndex>().row()},
                        {"roles", QVariant::fromValue(args[2].value<QList<int>>())}});
                } else {
                    calls.append(QVariant(args));
                }
            }
            result.insert(QString::fromUtf8(watch.names[static_cast<int>(i)]), calls);
        }
        return result;
    }
    Q_INVOKABLE int roleNumber(QAbstractItemModel *model, const QString &name) const {
        if (!model) return -1;
        const auto roles = model->roleNames();
        for (auto it = roles.cbegin(); it != roles.cend(); ++it)
            if (QString::fromUtf8(it.value()) == name) return it.key();
        return -1;
    }
    Q_INVOKABLE void clearWatches() { watches_.clear(); }
    Q_INVOKABLE bool writableLocalDirectory(const QUrl &url) const {
        return url.isLocalFile() && QFileInfo(QFileInfo(url.toLocalFile()).absolutePath()).isWritable();
    }
    Q_INVOKABLE QObject *visibleControl(QObject *root, const QString &name) const {
        if (!root) return nullptr;
        if (root->objectName() == name && root->property("visible").toBool()) return root;
        for (auto *child : root->children())
            if (auto *found = visibleControl(child, name)) return found;
        return nullptr;
    }
    Q_INVOKABLE QStringList visibleGroupNames(QObject *root) const {
        if (!root) return {};
        if (const auto *item = qobject_cast<QQuickItem *>(root); item && !item->isVisible())
            return {};
        QStringList names;
        if (root->objectName().startsWith(QStringLiteral("group.")))
            names.append(root->objectName().mid(6));
        for (auto *child : root->children()) names.append(visibleGroupNames(child));
        return names;
    }
    Q_INVOKABLE QString visibleText(QObject *root) const {
        if (!root) return {};
        if (const auto *item = qobject_cast<QQuickItem *>(root); item && !item->isVisible())
            return {};
        QString text = root->property("text").toString();
        for (auto *child : root->children()) text += "\n" + visibleText(child);
        return text;
    }
};

static void registerAcceptanceProbe() {
    QStandardPaths::setTestModeEnabled(true);
    qmlRegisterSingletonType<AcceptanceProbe>("EdiAcceptance", 1, 0, "Probe",
        [](QQmlEngine *, QJSEngine *) -> QObject * { return new AcceptanceProbe; });
}
Q_COREAPP_STARTUP_FUNCTION(registerAcceptanceProbe)
#include "test_e04_t1_probe.moc"
