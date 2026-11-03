// SPDX-License-Identifier: BSD-3-Clause
#include "run_log.hpp"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJSEngine>
#include <QMutexLocker>
#include <QQuickWindow>
#include <QSettings>
#include <QSocketNotifier>
#include <QStandardPaths>
#include <QSysInfo>
#include <algorithm>
#include <array>
#include <cstdio>
#if defined(Q_OS_UNIX) && !defined(Q_OS_WASM)
#include <csignal>
#include <sys/socket.h>
#include <unistd.h>
#endif

#include "app_build_info.hpp"
#include "app_info.hpp"
#include "edi/version.hpp"
#include "engine_setup.hpp"
#include "rendering_info.hpp"

Q_LOGGING_CATEGORY(lcCrysta, "crysta")
Q_LOGGING_CATEGORY(lcApp, "app")

namespace edi_app {

namespace {

constexpr std::array<const char*, 4> kLevels{"Debug", "Info", "Error", "Disabled"};

RunLog* g_log = nullptr;
QtMessageHandler g_previous_handler = nullptr;

// The ISO offset name, UTC+hh:mm: Qt for WebAssembly builds without the time-zone feature, so it is spelled
// from the offset QDateTime always has.
QString utcOffsetName(const QDateTime& when) {
    const int offset = when.offsetFromUtc();
    const int minutes = qAbs(offset) / 60;
    return QStringLiteral("UTC%1%2:%3")
        .arg(offset < 0 ? u'-' : u'+')
        .arg(minutes / 60, 2, 10, QLatin1Char('0'))
        .arg(minutes % 60, 2, 10, QLatin1Char('0'));
}
void handle_message(QtMsgType type, const QMessageLogContext& context, const QString& message) {
    if (g_log != nullptr) {
        g_log->write(type, context, message);
    } else if (g_previous_handler != nullptr) {
        g_previous_handler(type, context, message);
    }
}

// 0 debug, 1 info and warnings, 2 errors; a fatal message is always written.
int rank(QtMsgType type) {
    switch (type) {
        case QtDebugMsg:
            return 0;
        case QtInfoMsg:
        case QtWarningMsg:
            return 1;
        default:
            return 2;
    }
}

QString level_name(QtMsgType type) {
    switch (type) {
        case QtDebugMsg:
            return QStringLiteral("DEBUG");
        case QtInfoMsg:
            return QStringLiteral("INFO");
        case QtWarningMsg:
            return QStringLiteral("WARNING");
        case QtCriticalMsg:
            return QStringLiteral("ERROR");
        case QtFatalMsg:
            return QStringLiteral("FATAL");
    }
    return QStringLiteral("INFO");
}

// Seconds since the previous record in exactly five characters, rounded to fit: 0.091, 50.65, 116.2, 12345.
QString secondsField(qint64 milliseconds) {
    const double seconds = std::min(static_cast<double>(std::max<qint64>(0, milliseconds)) / 1000.0, 99999.0);
    for (int decimals = 3; decimals > 0; --decimals) {
        const QString text = QString::number(seconds, 'f', decimals);
        if (text.size() <= 5) {
            return text;
        }
    }
    return QString::number(seconds, 'f', 0).rightJustified(5);
}

QString base_name(const QString& file) {
    const qsizetype slash = std::max(file.lastIndexOf(u'/'), file.lastIndexOf(u'\\'));
    return file.mid(slash + 1);
}

// The run's name, sortable as text: session-20261102-140327.
QString session_stem(const QDateTime& time) {
    return QStringLiteral("session-") + time.toString(QStringLiteral("yyyyMMdd-HHmmss"));
}

QString marker_path(const QString& log_path) {
    return log_path.left(log_path.size() - 4) + QStringLiteral(".running");
}

// A lock file left by a process that is gone; a live run's lock is never taken, however old.
bool abandoned(const QString& marker) {
    QLockFile probe(marker);
    probe.setStaleLockTime(0);
    if (!probe.tryLock(0)) {
        return false;
    }
    probe.unlock();  // removes it
    return true;
}

}  // namespace

RunLog::RunLog(Options options, QObject* parent) : QObject(parent), options_(std::move(options)) {
    if (!options_.clock) {
        options_.clock = [] { return QDateTime::currentDateTime(); };
    }
}

RunLog::~RunLog() {
    if (g_log == this) {
        install(nullptr);
    }
    finish();
}

bool RunLog::start(const Header& header) {
    QMutexLocker lock(&mutex_);
    header_ = header;  // a report's details, with or without a file
    if (options_.directory.isEmpty() || !QDir().mkpath(options_.directory)) {
        return false;
    }
    const QDir dir(options_.directory);
    const QDateTime now = options_.clock();

    // A crashed run left its lock file; the newest one's log is offered.
    for (const QString& name : dir.entryList({QStringLiteral("session-*.running")}, QDir::Files, QDir::Name)) {
        const QString log = dir.filePath(name.left(name.size() - 8) + QStringLiteral(".log"));
        if (abandoned(dir.filePath(name)) && QFileInfo::exists(log)) {
            crashed_log_ = log;
        }
    }

    // Earlier logs beyond the newest `keep - 1` go, except a crashed run's and any whose run still holds its lock file:
    // another instance, perhaps starting now, takes its lock file before it creates its log.
    const QStringList logs =
        dir.entryList({QStringLiteral("session-*.log")}, QDir::Files, QDir::Name | QDir::Reversed);
    for (qsizetype i = std::max(0, options_.keep - 1); i < logs.size(); ++i) {
        const QString old = dir.filePath(logs.at(i));
        if (old != crashed_log_ && !QFileInfo::exists(marker_path(old))) {
            QFile::remove(old);
        }
    }

    // This run's name is reserved by its lock file before its log is created, and an existing log is never opened:
    // two runs starting in the same second take different names, and neither overwrites the other.
    const QString base = session_stem(now);
    for (int n = 1; n <= 100 && !file_.isOpen(); ++n) {
        const QString stem = n == 1 ? base : base + QStringLiteral("-") + QString::number(n);
        const QString log = dir.filePath(stem + QStringLiteral(".log"));
        auto lock = std::make_unique<QLockFile>(marker_path(log));
        lock->setStaleLockTime(0);
        if (!lock->tryLock(0)) {
            continue;  // another run holds this name
        }
        file_.setFileName(log);
        if (!file_.open(QIODevice::WriteOnly | QIODevice::NewOnly)) {
            continue;  // a log of that name exists; the lock is released with `lock`
        }
        running_ = std::move(lock);
        path_ = log;
    }
    if (!file_.isOpen()) {
        path_.clear();
        return false;
    }
    writeRaw(QStringLiteral("# EasyDiffraction run log"));
    for (const auto& [key, value] : header) {
        writeRaw(QStringLiteral("# ") + key + QStringLiteral(": ") + value);
    }
    previous_ = now;
    lock.unlock();
    if (!crashed_log_.isEmpty()) {
        emit crashedLogChanged();
    }
    return true;
}

void RunLog::finish() {
    QMutexLocker lock(&mutex_);
    if (file_.isOpen()) {
        file_.close();
    }
    running_.reset();  // unlocks, which removes the lock file
}

bool RunLog::wanted(QtMsgType type) const {
    return type == QtFatalMsg || (threshold_ < 3 && rank(type) >= threshold_);
}

void RunLog::write(QtMsgType type, const QMessageLogContext& context, const QString& message) {
    QMutexLocker lock(&mutex_);
    if (!wanted(type)) {
        return;
    }
    const QDateTime now = options_.clock();
    qint64 since = previous_.isValid() ? std::max<qint64>(0, previous_.msecsTo(now)) : 0;
    previous_ = now;
    QString text = message;
    text.replace(QStringLiteral("\r\n"), QStringLiteral("\n"));
    const QStringList lines = text.split(u'\n');
    for (const QString& part : lines) {
        const QString line = formatLine(now, since, type, context, part);
        since = 0;
        if (options_.terminal) {
            std::fprintf(stderr, "%s\n", line.toLocal8Bit().constData());
        }
        writeRaw(line);
    }
    if (options_.terminal) {
        std::fflush(stderr);
    }
}

void RunLog::writeRaw(const QString& line) {
    if (!file_.isOpen() || full_) {
        return;
    }
    QByteArray bytes = line.toUtf8();
    bytes.append('\n');
    // Room is kept for the notice that ends a full log, so the file never passes maxBytes.
    QMessageLogContext none;
    QByteArray notice = formatLine(options_.clock(), 0, QtWarningMsg, none,
                                   QStringLiteral("the log reached its size limit; later lines go to the "
                                                  "terminal only"))
                            .toUtf8();
    notice.append('\n');
    if (written_ + bytes.size() + notice.size() > options_.maxBytes) {
        full_ = true;
        if (written_ + notice.size() > options_.maxBytes) {
            return;
        }
        bytes = notice;
    }
    written_ += file_.write(bytes);
    file_.flush();  // a crash keeps every line written before it
}

QString RunLog::formatLine(const QDateTime& time, qint64 sincePreviousMs, QtMsgType type,
                           const QMessageLogContext& context, const QString& messageLine) {
    const QString file = context.file != nullptr ? QString::fromUtf8(context.file) : QString();
    const QString category = context.category != nullptr ? QString::fromLatin1(context.category) : QString();
    const QString base = base_name(file);
    const bool qml = base.endsWith(QLatin1String(".qml")) || base.endsWith(QLatin1String(".js")) ||
                     base.endsWith(QLatin1String(".mjs")) || category == QLatin1String("qml") ||
                     category == QLatin1String("js");
    // One source column (the owner, 2026-11-02): crysta's reports, the QML side's, or the app's own C++; the file the
    // message came from stays in the location.
    const QString source = category.startsWith(QLatin1String("crysta")) ? QStringLiteral("crysta")
                           : qml                                         ? QStringLiteral("qml")
                                                                         : QStringLiteral("app");
    QString message = messageLine;
    message.replace(u'\t', u' ');
    message = message.trimmed();
    if (message.isEmpty()) {
        message = QStringLiteral("-");
    }
    const QString location =
        base.isEmpty() ? QStringLiteral("-")
                       : (context.line > 0 ? base + u':' + QString::number(context.line) : base);
    return time.toString(QStringLiteral("HH:mm:ss.zzz")) + QStringLiteral("  +") + secondsField(sincePreviousMs) +
           QStringLiteral("  ") + level_name(type).leftJustified(8) + QStringLiteral("  ") + source.leftJustified(6) +
           QStringLiteral("  ") + message + QStringLiteral("  ") + location;
}

QString RunLog::level() const {
    QMutexLocker lock(&mutex_);
    return QString::fromLatin1(kLevels.at(static_cast<std::size_t>(threshold_)));
}

void RunLog::setLevel(const QString& level) {
    QMutexLocker lock(&mutex_);
    const auto found = std::find_if(kLevels.begin(), kLevels.end(), [&](const char* name) {
        return level.compare(QLatin1String(name), Qt::CaseInsensitive) == 0;
    });
    if (found == kLevels.end() || threshold_ == found - kLevels.begin()) {
        return;
    }
    threshold_ = static_cast<int>(found - kLevels.begin());
    lock.unlock();
    emit levelChanged();
}

QString RunLog::crashedLogText() const {
    QFile file(crashed_log_);
    if (crashed_log_.isEmpty() || !file.open(QIODevice::ReadOnly)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}

void RunLog::note(const QString& text) const { qCInfo(lcApp).noquote() << text; }

QString RunLog::logText() const {
    QMutexLocker lock(&mutex_);
    QFile file(path_);
    if (path_.isEmpty() || !file.open(QIODevice::ReadOnly)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}

RunReport RunLog::reportInfo() const {
    QMutexLocker lock(&mutex_);
    RunReport report;
    for (const auto& [key, value] : header_) {
        if (key == QLatin1String("app")) {
            // "<version> (commit <sha>)"
            const qsizetype commit = value.lastIndexOf(QLatin1String(" (commit "));
            report.version = commit < 0 ? value : value.left(commit);
            if (commit >= 0) {
                report.commit = value.mid(commit + 9).chopped(1);
            }
        } else if (key == QLatin1String("crysta")) {
            report.crysta = value;
        } else if (key == QLatin1String("Qt")) {
            report.qt = value;
        } else if (key == QLatin1String("OS")) {
            report.os = value;
        } else if (key == QLatin1String("graphics")) {
            report.graphics = value;
        }
    }
    return report;
}

QString RunLog::homePath() { return QDir::homePath(); }

QString RunLog::userName() {
    QString name = qEnvironmentVariable("USER");
    if (name.isEmpty()) {
        name = qEnvironmentVariable("USERNAME");
    }
    return name.isEmpty() ? QFileInfo(QDir::homePath()).fileName() : name;
}

void RunLog::dismissCrash() {
    if (crashed_log_.isEmpty()) {
        return;
    }
    crashed_log_.clear();
    emit crashedLogChanged();
}

void RunLog::install(RunLog* log) {
    if (log != nullptr && g_log == nullptr) {
        g_previous_handler = qInstallMessageHandler(handle_message);
    } else if (log == nullptr && g_log != nullptr) {
        qInstallMessageHandler(g_previous_handler);
        g_previous_handler = nullptr;
    }
    g_log = log;
}

RunLog* RunLog::instance() { return g_log; }

RunLog* RunLog::create(QQmlEngine*, QJSEngine*) {
    // A QML test has no run log of the app's: it gets one that writes nowhere.
    static RunLog* const fallback = new RunLog(Options{QString(), {}, 3, 0, false}, QCoreApplication::instance());
    RunLog* log = g_log != nullptr ? g_log : fallback;
    QJSEngine::setObjectOwnership(log, QJSEngine::CppOwnership);
    return log;
}

void quit_on_termination_signals() {
#if defined(Q_OS_UNIX) && !defined(Q_OS_WASM)
    // A signal handler may only write to a descriptor; the notifier quits from the event loop.
    static int fds[2] = {-1, -1};
    if (fds[0] >= 0 || ::socketpair(AF_UNIX, SOCK_STREAM, 0, fds) != 0) {
        return;
    }
    struct sigaction action {};
    action.sa_handler = [](int) {
        const char byte = 1;
        [[maybe_unused]] const auto written = ::write(fds[0], &byte, 1);
    };
    sigemptyset(&action.sa_mask);
    action.sa_flags = SA_RESTART;
    ::sigaction(SIGINT, &action, nullptr);
    ::sigaction(SIGTERM, &action, nullptr);
    auto* notifier = new QSocketNotifier(fds[1], QSocketNotifier::Read, QCoreApplication::instance());
    QObject::connect(notifier, &QSocketNotifier::activated, notifier, [] { QCoreApplication::quit(); });
#endif
}

QString run_log_directory() {
#if defined(Q_OS_WASM)
    return {};
#else
    const QString injected = qEnvironmentVariable("EDI_APP_DATA_DIR");
    if (!injected.isEmpty()) {
        return QDir(injected).filePath(QStringLiteral("logs"));
    }
    const QString fresh = fresh_settings_dir();
    const QString data =
        fresh.isEmpty() ? QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) : fresh;
    return data.isEmpty() ? QString() : QDir(data).filePath(QStringLiteral("logs"));
#endif
}

RunLog::Header run_log_header() {
    const ApplicationInfo info;
    const QSettings settings(QSettings::IniFormat, QSettings::UserScope, QStringLiteral("EasyScience"),
                             QStringLiteral("EasyDiffraction"));
    const QDateTime now = QDateTime::currentDateTime();
    const auto value = [&](const char* key, const QVariant& fallback) {
        return settings.value(QLatin1String(key), fallback).toString();
    };
    const int threads = settings.value(QStringLiteral("develop/engineThreads"), 0).toInt();
    const QStringList preferences{
        QStringLiteral("logging level ") + value("develop/loggingLevel", QStringLiteral("Info")),
        QStringLiteral("engine threads ") + (threads > 0 ? QString::number(threads) : QStringLiteral("Auto")),
        QStringLiteral("colour scheme ") + value("Appearance/colourScheme", QStringLiteral("earth")),
        QStringLiteral("sidebar ") + value("Edi.Preferences/sideBarSide", QStringLiteral("Right")),
        QStringLiteral("tooltips ") + value("Edi.Preferences/toolTips", true)};
    return {
        {QStringLiteral("date"), now.toString(QStringLiteral("yyyy-MM-dd")) + QStringLiteral(" (") + utcOffsetName(now) +
                                     QStringLiteral(")")},
        {QStringLiteral("app"), info.version() + QStringLiteral(" (commit ") +
                                    QString::fromLatin1(edi::build_commit()) + QStringLiteral(")")},
        {QStringLiteral("crysta"), QStringLiteral(EDI_APP_CRYSTA_VERSION " (commit " EDI_APP_CRYSTA_COMMIT ")")},
        {QStringLiteral("Qt"), QString::fromLatin1(qVersion())},
        {QStringLiteral("OS"), QSysInfo::prettyProductName() + QStringLiteral(" (") + QSysInfo::kernelType() +
                                   u' ' + QSysInfo::kernelVersion() + QStringLiteral(", ") +
                                   QSysInfo::currentCpuArchitecture() + QStringLiteral(")")},
        {QStringLiteral("graphics"), RenderingInfo::apiName(QQuickWindow::graphicsApi())},
        {QStringLiteral("preferences"), preferences.join(QStringLiteral(", "))},
    };
}

}  // namespace edi_app
