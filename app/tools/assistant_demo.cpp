// SPDX-License-Identifier: BSD-3-Clause
// The assistant's tools called by a local peer (tools/dev/assistant_peer.py) in place of a model, each with every
// sidebar group folded first. Test tooling (tools/dev/assistant-tools.sh), never part of the host: it connects and
// sends without a person. Runs until the peer's turn ends.
#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <thread>

#include <QCoreApplication>
#include <QDir>
#include <QElapsedTimer>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QMouseEvent>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlApplicationEngine>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSettings>
#include <QSurfaceFormat>
#include <QTemporaryDir>
#include <QTextStream>
#include <QThread>
#include <QThreadPool>
#include <QTimer>
#include <QUrl>
#include <QtQml/qqmlextensionplugin.h>
#include <cstdio>
#include <cstdlib>
#include <exception>

#include "app_info.hpp"
#include "assistant_view_model.hpp"
#include "demo_driver.hpp"
#include "engine_setup.hpp"
#include "project_folder_lock.hpp"
#include "project_view_model.hpp"
#include "run_log.hpp"
#include "session.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace edi_app {
namespace {

// The run's environment:
//   EDI_CODEX_DEVELOPMENT_EXECUTABLE  the peer
//   EDI_ASSISTANT_PEER_DIR            where the peer and this demo leave their notes
//   EDI_ASSISTANT_SHOW                1: Show actions on
//   EDI_ASSISTANT_PROJECT             a CLI project to open first; empty: start with no project
//   EDI_ASSISTANT_FILES               the files to attach, separated by |
//   EDI_ASSISTANT_INACTIVE            1: the window is never made active; first: not before a project is open
// Takes every press, as a popup or an overlay over a control does.
class Cover : public QQuickItem {
   public:
    using QQuickItem::QQuickItem;

   protected:
    void mousePressEvent(QMouseEvent* event) override { event->accept(); }
    void mouseReleaseEvent(QMouseEvent* event) override { event->accept(); }
};

// Whether the app's log reported a step it could not show.
std::atomic<bool> step_reported = false;
QtMessageHandler log_before = nullptr;
void watch_log(QtMsgType type, const QMessageLogContext& context, const QString& text) {
    if (text.contains(QLatin1String("a shown step could not be shown"))) step_reported = true;
    if (log_before != nullptr) log_before(type, context, text);
}

class AssistantDemo : public QObject {
   public:
    explicit AssistantDemo(QQuickWindow& window) : QObject(&window), window_(window), dir_(qEnvironmentVariable("EDI_ASSISTANT_PEER_DIR")) {}

    void start() {
        auto* engine = qmlEngine(window_.contentItem());
        session_ = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        assistant_ = session_ ? session_->assistant() : nullptr;
        clock_.start();
        window_.installEventFilter(this);
        if (!assistant_ || dir_.path().isEmpty()) return fail(QStringLiteral("no assistant or no EDI_ASSISTANT_PEER_DIR"));
        QSettings settings(settings_file_path(), QSettings::IniFormat);
        settings.setValue(QStringLiteral("Assistant/Providers/chatgpt/selection"),
                          QStringList{QStringLiteral("local-peer"), QStringLiteral("medium")});
        settings.sync();
        // Only the local peer: this connects and approves without a person, so it must never reach a provider.
        if (QFileInfo(qEnvironmentVariable("EDI_CODEX_DEVELOPMENT_EXECUTABLE")).fileName() != QLatin1String("assistant_peer.py"))
            return fail(QStringLiteral("EDI_CODEX_DEVELOPMENT_EXECUTABLE is not tools/dev/assistant_peer.py"));
        // Show actions moves its pointer in an active window only; the capture display has no window manager to activate it.
        if (inactive_.isEmpty()) window_.requestActivate();
        assistant_->setActionWindow(&window_);
        assistant_->setShowActions(qEnvironmentVariableIntValue("EDI_ASSISTANT_SHOW") != 0);
        connect(assistant_, &AssistantViewModel::actionPointerMoved, this, [this](const QPointF& at) { pointer_ = at; });
        connect(assistant_, &AssistantViewModel::actionPointerPressed, this, [this] { note(QStringLiteral("press\t") + named_at(pointer_)); });
        watch_.setInterval(20);
        connect(&watch_, &QTimer::timeout, this, [this] {
            fold_when_asked();
            spoil();
            if (inactive_ == QLatin1String("first") && session_ && session_->project() != nullptr) {
                inactive_.clear();
                window_.requestActivate();
            }
        });
        watch_.start();
        const QString project = qEnvironmentVariable("EDI_ASSISTANT_PROJECT");
        if (!project.isEmpty()) {
            const QString copy = copies_.isValid() ? copy_cli_project(project, QDir(copies_.path())) : QString();
            if (copy.isEmpty() || !session_->openProject(QUrl::fromLocalFile(copy))) return fail(QStringLiteral("cannot open ") + project);
        }
        step_.setInterval(200);
        connect(&step_, &QTimer::timeout, this, [this] { advance(); });
        step_.start();
    }

   private:
    QList<QQuickItem*> items() const {
        QList<QQuickItem*> all{window_.contentItem()};
        for (int at = 0; at < all.size(); ++at) all.append(all[at]->childItems());
        return all;
    }
    QQuickItem* find(const QString& name) const {
        for (QQuickItem* item : items())
            if (item->objectName() == name) return item;
        return nullptr;
    }
    // The named control drawn last, so on top, at a point.
    QString named_at(const QPointF& at) const {
        QString name;
        double area = 0;
        for (QQuickItem* item : items()) {
            if (item->objectName().isEmpty() || item->objectName() == QLatin1String("assistant.actionPointer") || !item->isVisible() || item->opacity() <= 0 || !item->contains(item->mapFromScene(at))) continue;
            if (name.isEmpty() || item->width() * item->height() <= area) {
                name = item->objectName();
                area = item->width() * item->height();
            }
        }
        return name;
    }
    void note(const QString& line) {
        QFile out(dir_.filePath(QStringLiteral("presses.tsv")));
        if (out.open(QIODevice::Append | QIODevice::Text)) QTextStream(&out) << call_ << '\t' << line << '\t' << clock_.elapsed() << '\n';
    }
    // A click that is taken as it is made and given to the window 8 s later, as a held press is replayed.
    bool eventFilter(QObject* watched, QEvent* event) override {
        const bool press = event->type() == QEvent::MouseButtonPress, release = event->type() == QEvent::MouseButtonRelease;
        // A control that answers every press with nothing: its release never reaches it.
        if (mute_ && watched == mute_ && release) return true;
        if (late_ && watched == &window_ && (press || release)) {
            QQuickItem* item = find(spoiled_);
            const QPointF at = static_cast<QMouseEvent*>(event)->position();
            if (item == nullptr || !item->mapRectToScene(QRectF(0, 0, item->width(), item->height())).contains(at)) return false;
            std::shared_ptr<QEvent> kept(event->clone());
            QTimer::singleShot(8000, this, [this, kept] { QCoreApplication::sendEvent(&window_, kept.get()); });
            note(QStringLiteral("held\t") + (press ? QStringLiteral("press") : QStringLiteral("release")));
            return true;
        }
        return QObject::eventFilter(watched, event);
    }
    // The spoiled controls: of one name, or of every name that starts as one ending in * does.
    QList<QQuickItem*> spoiled_items() const {
        QList<QQuickItem*> found;
        const bool start = spoiled_.endsWith(QLatin1Char('*'));
        for (QQuickItem* item : items())
            if (start ? item->objectName().startsWith(QStringView(spoiled_).chopped(1)) : item->objectName() == spoiled_) found << item;
        return found;
    }
    // Spoils the control the peer named for its next call, as soon as it is there: `covered`, `absent`, `disabled`,
    // `late`, `mute`, or `gone` (renamed, so not found); once-... until the app reports the step, soon-... for 4 s. moving-...
    // has an unrelated list scroll meanwhile, busy-... the window's thread work 3 s of every 3.2 s. `folder`: the project's
    // folder keeps changing under its lock for 8 s.
    void spoil() {
        if ((once_ && step_reported) || (soon_ && since_.elapsed() > 4000)) mend();
        if (moving_) moving_->setProperty("contentY", since_.elapsed() / 5 % 1000);
        if (busy_ && since_.elapsed() - worked_ > 3200 && since_.elapsed() < 40000) {
            QThread::msleep(3000);
            worked_ = since_.elapsed();
        }
        if (spoil_.isEmpty()) return;
        if (spoil_ == QLatin1String("folder")) return change_folder();
        const QList<QQuickItem*> found = spoiled_items();
        if (found.isEmpty()) return;
        QQuickItem* item = found.constFirst();
        if (spoil_ == QLatin1String("covered")) {
            if (!cover_) {
                cover_ = new Cover(window_.contentItem());
                cover_->setObjectName(QStringLiteral("demo.cover"));
                cover_->setZ(10000);
                cover_->setAcceptedMouseButtons(Qt::AllButtons);
            }
            cover_->setVisible(true);
            cover_->setEnabled(true);
            const QRectF at = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
            cover_->setPosition(at.topLeft());
            cover_->setSize(at.size());
        } else if (spoil_ == QLatin1String("absent")) {
            for (QQuickItem* one : found) {
                if (!one->isVisible()) continue;
                one->setVisible(false);
                hidden_ << one;
            }
        } else if (spoil_ == QLatin1String("gone")) {
            item->setObjectName(QStringLiteral("demo.gone"));
            gone_ = item;
        } else if (spoil_ == QLatin1String("disabled")) {
            item->setEnabled(false);
        } else if (spoil_ == QLatin1String("mute")) {
            if (!mute_) {
                mute_ = item;
                item->installEventFilter(this);
            }
        } else {
            late_ = true;
        }
        if (changed_ != item && spoil_ == QLatin1String("disabled")) changed_ = item;
    }
    void mend() {
        if (cover_) {
            cover_->setVisible(false);
            cover_->setEnabled(false);
        }
        late_ = false;
        if (mute_) mute_->removeEventFilter(this);
        mute_ = nullptr;
        for (const auto& item : hidden_)
            if (item) item->setVisible(true);
        hidden_.clear();
        if (gone_) gone_->setObjectName(spoiled_);
        gone_ = nullptr;
        if (changed_ && spoil_ == QLatin1String("disabled")) changed_->setEnabled(true);
        changed_ = nullptr;
        spoil_.clear();
        once_ = soon_ = busy_ = false;
        delete moving_.data();
    }
    // The assistant's report being written: its lock held, and a file in the project's folder written again and again.
    void change_folder() {
        spoil_.clear();
        const QString folder = session_ && session_->project() ? session_->project()->path() : QString();
        if (folder.isEmpty()) return;
        std::thread([folder] {
            const std::lock_guard writing(project_folder_mutex());
            const QString name = QDir(folder).filePath(QStringLiteral("demo-changing.txt"));
            for (int at = 0; at < 800; ++at) {
                if (QFile out(name); out.open(QIODevice::WriteOnly)) out.write(QByteArray::number(at));
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            QFile::remove(name);
        }).detach();
    }
    // The peer leaves the file `fold` (the call it is about to make) and waits until it is gone.
    void fold_when_asked() {
        QFile ask(dir_.filePath(QStringLiteral("fold")));
        if (!ask.open(QIODevice::ReadOnly)) return;
        const QStringList asked = QString::fromUtf8(ask.readAll()).split(QLatin1Char('\n'));
        call_ = asked.value(0).trimmed();
        ask.close();
        mend();
        step_reported = false;
        spoil_ = asked.value(1).section(QLatin1Char(' '), 0, 0);
        once_ = spoil_.startsWith(QLatin1String("once-"));
        if (once_) spoil_.remove(0, 5);
        soon_ = spoil_.startsWith(QLatin1String("soon-"));
        if (soon_) spoil_.remove(0, 5);
        busy_ = spoil_.startsWith(QLatin1String("busy-"));
        if (busy_) spoil_.remove(0, 5);
        if (spoil_.startsWith(QLatin1String("moving-"))) {
            spoil_.remove(0, 7);
            QQmlComponent component(qmlEngine(window_.contentItem()));
            component.setData("import QtQuick\nFlickable { contentHeight: 4000; width: 20; height: 20; enabled: false }", QUrl());
            moving_ = qobject_cast<QQuickItem*>(component.create());
            if (moving_) moving_->setParentItem(window_.contentItem());
        }
        since_.start();
        worked_ = 0;
        spoiled_ = asked.value(1).section(QLatin1Char(' '), 1);
        int folded = 0;
        for (QQuickItem* item : items()) {
            if (!item->objectName().startsWith(QLatin1String("group.")) || !item->property("collapsed").isValid() ||
                !item->property("collapsible").toBool() || item->property("collapsed").toBool())
                continue;
            item->setProperty("collapsed", true);
            ++folded;
        }
        note(QStringLiteral("folded\t%1").arg(folded));
        note(QStringLiteral("modified\t%1").arg(session_ && session_->project() && session_->project()->modified() ? 1 : 0));
        ask.remove();
    }
    void advance() {
        waited_ += step_.interval();
        if (waited_ > 60000 && stage_ < 4) return fail(QStringLiteral("stage %1 did not end: %2").arg(stage_).arg(assistant_->lastError()));
        switch (stage_) {
        case 0:  // past Home, where the assistant is not offered
            if (QQuickItem* start = find(QStringLiteral("home.start")); start && session_->project() == nullptr) QMetaObject::invokeMethod(start, "click");
            else if (QQuickItem* tab = find(QStringLiteral("appBar.tab.project"))) QMetaObject::invokeMethod(tab, "click");
            next();
            break;
        case 1:
            if (auto* project = session_->project(); project && (project->calculating() || !project->viewSettled())) break;
            if (waited_ < 1500) break;
            // Before the connection, whose approval covers them.
            if (const QStringList files = qEnvironmentVariable("EDI_ASSISTANT_FILES").split(QLatin1Char('|'), Qt::SkipEmptyParts); !files.isEmpty()) {
                QList<QUrl> urls;
                for (const QString& file : files) urls << QUrl::fromLocalFile(file);
                const QString token = assistant_->beginFileSelection();
                if (token.isEmpty() || !assistant_->addSelectedFiles(token, urls)) return fail(QStringLiteral("cannot attach: ") + assistant_->lastError());
            }
            assistant_->signIn();
            next();
            break;
        case 2:
            if (!assistant_->connected() || !assistant_->draftAdmissionReady()) break;
            next();
            break;
        case 3:
            if (!assistant_->draftAdmissionReady() || waited_ < 1000) break;
            assistant_->send(QStringLiteral("Call every tool"));
            next();
            break;
        default:
            if (waited_ > 1800000) return fail(QStringLiteral("the turn did not end"));
            if (waited_ < 2000 || assistant_->state() == QLatin1String("agent_active") || assistant_->state() == QLatin1String("connecting")) break;
            std::fprintf(stdout, "assistant-tools: %s %s\n", qPrintable(assistant_->state()), qPrintable(assistant_->lastError()));
            QCoreApplication::exit(0);
            step_.stop();
        }
    }
    void next() {
        ++stage_;
        waited_ = 0;
    }
    void fail(const QString& message) {
        step_.stop();
        std::fprintf(stderr, "assistant-tools: %s\n", qPrintable(message));
        QTimer::singleShot(0, this, [] { QCoreApplication::exit(1); });
    }

    QQuickWindow& window_;
    QDir dir_;
    QPointer<Session> session_;
    QPointer<AssistantViewModel> assistant_;
    QTemporaryDir copies_;
    QTimer watch_, step_;
    QPointF pointer_;
    QElapsedTimer clock_;
    QString call_, spoil_, spoiled_, inactive_ = qEnvironmentVariable("EDI_ASSISTANT_INACTIVE");
    QPointer<QQuickItem> cover_, changed_, mute_;
    QPointer<QQuickItem> gone_, moving_;
    QElapsedTimer since_;
    qint64 worked_ = 0;
    QList<QPointer<QQuickItem>> hidden_;
    bool late_ = false, once_ = false, soon_ = false, busy_ = false;
    int stage_ = 0, waited_ = 0;
};

int run(int argc, char** argv) {
    select_freetype_engine(argc, argv);
    QGuiApplication app(argc, argv);
    QGuiApplication::setOrganizationName(settings_organisation());
    QGuiApplication::setApplicationName(QStringLiteral("EasyDiffraction"));
    use_design_font();
    require_freetype_engine();
    // As a demo of the app: 8 bits per channel, the demo's identity and never the machine's saved settings.
    QSurfaceFormat format = QSurfaceFormat::defaultFormat();
    format.setRedBufferSize(8);
    format.setGreenBufferSize(8);
    format.setBlueBufferSize(8);
    QSurfaceFormat::setDefaultFormat(format);
    ApplicationInfo::useDemoIdentity();
    use_fresh_settings();
    RunLog run_log({run_log_directory()});
    RunLog::install(&run_log);
    run_log.start(run_log_header());
    log_before = qInstallMessageHandler(watch_log);
    QObject::connect(&app, &QCoreApplication::aboutToQuit, &run_log, &RunLog::finish);
    QQmlApplicationEngine engine;
    configure_engine(engine);
    engine.loadFromModule("edi.app", "Main");
    auto* window = engine.rootObjects().isEmpty() ? nullptr : qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    if (window == nullptr) return 1;
    window->resize(1280, 768);
    auto* demo = new AssistantDemo(*window);
    QTimer::singleShot(1000, demo, [demo] { demo->start(); });
    const int code = QGuiApplication::exec();
    QThreadPool::globalInstance()->clear();
    QThreadPool::globalInstance()->waitForDone();
    return code;
}

}  // namespace
}  // namespace edi_app

int main(int argc, char** argv) {
    try {
        return edi_app::run(argc, argv);
    } catch (const std::exception& error) {
        std::fprintf(stderr, "edi_app_assistant_demo: %s\n", error.what());
        return 1;
    }
}
