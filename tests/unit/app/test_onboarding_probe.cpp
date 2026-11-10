// SPDX-License-Identifier: BSD-3-Clause
#include <QAbstractAnimation>
#include <QSortFilterProxyModel>
#include <QClipboard>
#include <QGuiApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QPointer>
#include <QSettings>
#include <QTemporaryDir>
#include <memory>
#if __has_include("run_log.hpp")
#include "run_log.hpp"
#define HAS_ONBOARDING_LOG 1
#endif
#include <QCoreApplication>
#include <QDesktopServices>
#include <QJSEngine>
#include <QObject>
#include <QQmlEngine>
#include <QQmlIncubationController>
#include <QUrl>
#include <QtQml/qqml.h>

// A deterministic Qt animation clock also drives QML Timer. A sentinel in the
// actor proves that elapsed time was delivered, rather than merely pumping events.
class OnboardingClock final : public QAnimationDriver {
    qint64 now_ = 0;
public:
    qint64 elapsed() const override { return now_; }
    void advanceBy(qint64 ms) { now_ += ms; advanceAnimation(); }
};

class OnboardingProbe final : public QObject {
    Q_OBJECT
    QStringList urls_;
    QPointer<QObject> remembered_;
    QTemporaryDir scratch_;
    std::unique_ptr<OnboardingClock> clock_;
#ifdef HAS_ONBOARDING_LOG
    std::unique_ptr<edi_app::RunLog> log_;
    QPointer<edi_app::RunLog> previous_log_;
#endif
public:
    using QObject::QObject;
    Q_INVOKABLE bool settingsContain(const QString& file, const QString& value) const {
        const QUrl url(file);
        QSettings settings(url.isLocalFile() ? url.toLocalFile() : file, QSettings::IniFormat);
        settings.sync();
        for (const auto& key : settings.allKeys())
            if ((key.contains("seen", Qt::CaseInsensitive) || key.contains("changes", Qt::CaseInsensitive))
                && settings.value(key).toString() == value) return true;
        return false;
    }
    Q_INVOKABLE void injectChangelog(const QString& json) {
        qputenv("EDI_CHANGELOG_JSON", json.toUtf8());
    }
    Q_INVOKABLE void startClock() {
        clock_ = std::make_unique<OnboardingClock>();
        clock_->install();
    }
    Q_INVOKABLE void advanceClock(int ms) {
        if (!clock_) return;
        QCoreApplication::processEvents();
        for (int elapsed = 0; elapsed < ms; elapsed += 10000) {
            clock_->advanceBy(qMin(10000, ms - elapsed));
            QCoreApplication::processEvents();
        }
    }
    Q_INVOKABLE void stopClock() {
        if (clock_) clock_->uninstall();
        clock_.reset();
    }
    Q_INVOKABLE void incubate(QObject* object) {
        auto* engine = qmlEngine(object);
        if (engine && engine->incubationController()) engine->incubationController()->incubateFor(10);
        QCoreApplication::processEvents();
    }
    Q_INVOKABLE bool inheritsType(QObject* object, const QString& type) const {
        for (const QMetaObject* meta = object ? object->metaObject() : nullptr; meta; meta = meta->superClass())
            if (QString::fromLatin1(meta->className()).startsWith(type)) return true;
        return false;
    }
    Q_INVOKABLE void rememberProject(QObject* project) { remembered_ = project; }
    Q_INVOKABLE bool rememberedAlive() const { return !remembered_.isNull(); }
    Q_INVOKABLE bool isRemembered(QObject* project) const { return remembered_ && remembered_ == project; }
    Q_INVOKABLE QVariant rememberedProperty(const QString& name) const {
        return remembered_ ? remembered_->property(name.toUtf8().constData()) : QVariant();
    }
    Q_INVOKABLE bool sortByRole(QObject* object, const QString& role, bool descending) const {
        auto* proxy = qobject_cast<QSortFilterProxyModel*>(object);
        if (!proxy || !proxy->sourceModel()) return false;
        const auto roles = proxy->sourceModel()->roleNames();
        const auto key = roles.key(role.toUtf8(), -1);
        if (key < 0) return false;
        proxy->setSortRole(key);
        proxy->sort(0, descending ? Qt::DescendingOrder : Qt::AscendingOrder);
        return true;
    }
    Q_INVOKABLE QString homePath() const { return QDir::homePath(); }
    Q_INVOKABLE QString userName() const { return qEnvironmentVariable("USER"); }
    Q_INVOKABLE QString clipboard() const { return QGuiApplication::clipboard()->text(); }
    Q_INVOKABLE QVariant citation() const {
        return QJsonDocument::fromJson(qgetenv("EDI_ONBOARDING_CITATION_JSON")).toVariant();
    }
    Q_INVOKABLE QString sourceText(const QString& relative) const {
        const auto root = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");
        QFile file(QDir(root).filePath(relative));
        if (!file.open(QIODevice::ReadOnly)) return {};
        return QString::fromUtf8(file.readAll());
    }
    Q_INVOKABLE QVariantMap actualLogHeader() const {
        QVariantMap result;
#ifdef HAS_ONBOARDING_LOG
        for (const auto& entry : edi_app::run_log_header()) result[entry.first] = entry.second;
#endif
        return result;
    }
    Q_INVOKABLE QString prepareCrashLog() {
#ifdef HAS_ONBOARDING_LOG
        const auto root = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");
        const auto request_path = QDir(scratch_.path()).filePath("crash-request.json");
        QFile request(request_path);
        if (!request.open(QIODevice::WriteOnly)) return {};
        request.write(QJsonDocument(QJsonObject{{"operation", "crash"}, {"time", "2026-07-18T09:41:26.125+02:00"},
            {"directory", scratch_.path()}, {"header", QJsonObject{{"app", "crash acceptance"}}}}).toJson());
        request.close();
        QProcess child;
        child.start(QDir(root).filePath("build/onboarding-native/log_probe"), {request_path});
        if (!child.waitForFinished(3000) || child.exitCode() != 0) return {};
        log_ = std::make_unique<edi_app::RunLog>(edi_app::RunLog::Options{
            scratch_.path(), [] { return QDateTime::fromString("2026-07-19T09:41:26.125+02:00", Qt::ISODateWithMs); }, 3, 5'000'000, false});
        if (!log_->start(edi_app::run_log_header())) return {};
        edi_app::RunLog::install(log_.get());
        return log_->crashedLog();
#else
        return {};
#endif
    }
    Q_INVOKABLE QString startHostLog() {
#ifdef HAS_ONBOARDING_LOG
        previous_log_ = edi_app::RunLog::instance();
        auto* source = edi_app::RunLog::create(qmlEngine(this), qmlEngine(this));
        log_ = std::make_unique<edi_app::RunLog>(edi_app::RunLog::Options{
            scratch_.path(), [] { return QDateTime::fromString("2026-07-18T09:41:26.125+02:00", Qt::ISODateWithMs); }, 3, 5'000'000, false});
        // The capture changes storage and clock, never the user's active severity.
        // Preferences holds the existing QML singleton even after install replaces the sink.
        log_->setLevel(source->level());
        QObject::connect(source, &edi_app::RunLog::levelChanged, log_.get(),
            [source = QPointer<edi_app::RunLog>(source), capture = log_.get()] {
                if (source) capture->setLevel(source->level());
            });
        if (!log_->start(edi_app::run_log_header())) return {};
        edi_app::RunLog::install(log_.get());
        return log_->path();
#else
        return {};
#endif
    }
    Q_INVOKABLE QString finishHostLog() {
#ifdef HAS_ONBOARDING_LOG
        if (!log_) return {};
        edi_app::RunLog::install(previous_log_);
        const auto path = log_->path();
        log_->finish();
        QFile file(path);
        if (file.open(QIODevice::ReadOnly)) return QString::fromUtf8(file.readAll());
#endif
        return {};
    }
    Q_INVOKABLE void emitNativeMessage() const {
        QMessageLogger("onboarding-native.cpp", 73, "acceptance", "onboarding").info("host-cpp-sentinel");
    }
    Q_INVOKABLE void interceptUrls() {
        urls_.clear();
        for (const auto& scheme : QStringList{"https", "http", "qrc", "file", "", "mailto", "feedback", "data", "javascript"})
            QDesktopServices::setUrlHandler(scheme, this, "captureUrl");
    }
    Q_INVOKABLE void releaseUrls() {
        for (const auto& scheme : QStringList{"https", "http", "qrc", "file", "", "mailto", "feedback", "data", "javascript"})
            QDesktopServices::unsetUrlHandler(scheme);
    }
    Q_INVOKABLE QStringList urls() const { return urls_; }
public slots:
    void captureUrl(const QUrl& url) { urls_.append(url.toString()); }
};
static void register_onboarding_probe() {
    qmlRegisterSingletonType<OnboardingProbe>("OnboardingAcceptance", 1, 0, "OnboardingProbe",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new OnboardingProbe; });
}
Q_COREAPP_STARTUP_FUNCTION(register_onboarding_probe)
#include "test_onboarding_probe.moc"
