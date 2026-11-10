// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_RUN_LOG_HPP
#define EDI_APP_RUN_LOG_HPP

#include <QDateTime>
#include <QFile>
#include <QList>
#include <QLockFile>
#include <QLoggingCategory>
#include <QRecursiveMutex>
#include <QObject>
#include <QPair>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <functional>
#include <memory>

class QJSEngine;
class QQmlEngine;

/// The category the app logs what crysta reports under; its lines name `crysta` as their source.
Q_DECLARE_LOGGING_CATEGORY(lcCrysta)
/// The category of what the user did (a page opened, a project saved, a fit started), one Info line each, naming no
/// file, folder or project name.
Q_DECLARE_LOGGING_CATEGORY(lcApp)

namespace edi_app {

/// The app's details a feedback report carries (ADR-0063), taken from this run's log header.
struct RunReport {
    Q_GADGET
    QML_VALUE_TYPE(runReport)
    Q_PROPERTY(QString version MEMBER version CONSTANT)
    Q_PROPERTY(QString commit MEMBER commit CONSTANT)
    Q_PROPERTY(QString crysta MEMBER crysta CONSTANT)
    Q_PROPERTY(QString qt MEMBER qt CONSTANT)
    Q_PROPERTY(QString os MEMBER os CONSTANT)
    Q_PROPERTY(QString graphics MEMBER graphics CONSTANT)

   public:
    QString version;
    QString commit;
    QString crysta;
    QString qt;
    QString os;
    QString graphics;
};

/// The log of one app run (ADR-0062): every Qt message of the app, its QML and its calls into crysta, at the chosen
/// level, to the terminal and to `logs/session-<date>-<time>.log` in the app's data folder. The last three runs are
/// kept. A run holds a lock file beside its log while it runs; a lock file whose process is gone at the next start
/// means that run crashed, and its log is offered (`crashedLog`).
///
/// One instance per process, made in `main` and installed as Qt's message handler; tests make their own with an
/// injected folder and clock. Writing is thread-safe: a calculation worker logs from its own thread.
class RunLog : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    // "Debug", "Info", "Warning" or "Error": the lowest level written, and edi's message level.
    Q_PROPERTY(QString level READ level WRITE setLevel NOTIFY levelChanged)
    // This run's log file; empty when the run writes to the terminal only (the browser, a log that could not open).
    Q_PROPERTY(QString path READ path CONSTANT)
    // The log of the previous run that crashed, or empty; kept until `dismissCrash`.
    Q_PROPERTY(QString crashedLog READ crashedLog NOTIFY crashedLogChanged)
    // What a report replaces with "~": the user's home folder and user name.
    Q_PROPERTY(QString homePath READ homePath CONSTANT)
    Q_PROPERTY(QString userName READ userName CONSTANT)

   public:
    using Clock = std::function<QDateTime()>;
    struct Options {
        QString directory;           ///< The folder the logs go to; created if missing.
        Clock clock;                 ///< Local time of each line; the system clock when empty.
        int keep = 3;                ///< Logs kept, this run's included.
        qint64 maxBytes = 5'000'000; ///< A log stops growing at this size, after a line saying so.
        bool terminal = true;        ///< Also write each line to stderr.
    };
    using Header = QList<QPair<QString, QString>>;

    explicit RunLog(Options options, QObject* parent = nullptr);
    ~RunLog() override;

    /// Finds a crashed earlier run, removes logs beyond `keep`, opens this run's log and writes a title
    /// line and `header` as `# key: value` lines. False when the folder or the file cannot be written;
    /// the run then logs to the terminal only.
    bool start(const Header& header);
    /// Ends the run normally: the lock file goes, so the next start does not report a crash.
    void finish();

    /// Writes one message, split into one line per line of its text.
    void write(QtMsgType type, const QMessageLogContext& context, const QString& message);

    QString level() const;
    void setLevel(const QString& level);
    QString path() const { return path_; }
    QString crashedLog() const { return crashed_log_; }
    /// The crashed run's log text, for a report.
    Q_INVOKABLE QString crashedLogText() const;
    /// Forgets the crashed run once its report is sent or declined.
    Q_INVOKABLE void dismissCrash();
    /// This run's log text so far, for a report; empty without a file.
    Q_INVOKABLE QString logText() const;
    /// Writes one Info line of what the user did, from QML: a tutorial's step, a page opened, feedback sent.
    Q_INVOKABLE void note(const QString& text) const;
    /// The app's details a report includes, from this run's header: version, commit, crysta, qt, os, graphics.
    Q_INVOKABLE edi_app::RunReport reportInfo() const;
    static QString homePath();
    static QString userName();

    /// One record line, without its line break: `HH:MM:SS.mmm  +S.mmm  LEVEL  source  area  message  location`.
    static QString formatLine(const QDateTime& time, qint64 sincePreviousMs, QtMsgType type,
                              const QMessageLogContext& context, const QString& messageLine);

    /// Makes `log` the process's log and Qt's message handler (null restores Qt's own handler).
    static void install(RunLog* log);
    static RunLog* instance();
    static RunLog* create(QQmlEngine*, QJSEngine*);

   signals:
    void levelChanged();
    void crashedLogChanged();

   private:
    bool wanted(QtMsgType type) const;
    void writeRaw(const QString& line);

    Options options_;
    mutable QRecursiveMutex mutex_;  // a Qt warning raised while writing comes back here
    int threshold_ = 2;  // index into the levels: 0 Debug, 1 Info, 2 Warning, 3 Error
    QString path_;
    Header header_;
    QString crashed_log_;
    std::unique_ptr<QLockFile> running_;
    QFile file_;
    qint64 written_ = 0;
    bool full_ = false;
    QDateTime previous_;
};

/// The folder logs go to: `$EDI_APP_DATA_DIR/logs` when set (tests), a demo or test run's fresh folder, else
/// `logs` in the app's data folder. Empty in the browser, which keeps no log file.
QString run_log_directory();
/// Ctrl+C and SIGTERM quit the app as closing its window does, so the next start does not report a crash.
void quit_on_termination_signals();
/// The header of a run's log: app, crysta, Qt, OS, graphics backend and the main preferences.
RunLog::Header run_log_header();

}  // namespace edi_app

#endif  // EDI_APP_RUN_LOG_HPP
