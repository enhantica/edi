// SPDX-License-Identifier: BSD-3-Clause
#include "engine_setup.hpp"

#include <QDir>
#include <QFile>
#include <QFont>
#include <QFontDatabase>
#include <QGuiApplication>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQuickWindow>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QPointer>
#include <QTimer>
#include <QWheelEvent>
#include <QWindow>
#include <QUrl>
#include <utility>

#if defined(Q_OS_WASM)
#include <emscripten.h>
#include <cstdlib>

// ADR-0023: the browser's settings. The settings file lives in the page's memory, which a reload empties, so
// its text is kept in the browser's local storage under one key: read back before any QML loads, written
// again whenever the file changes. A storage the browser refuses (a private window, blocked site data) leaves
// the settings for the session only.
EM_JS_DEPS(edi_settings, "$stringToNewUTF8");
EM_JS(char*, edi_settings_load, (), {
    try {
        const text = globalThis.localStorage.getItem("edi.settings.ini");
        return text === null ? 0 : stringToNewUTF8(text);
    } catch (e) {
        return 0;
    }
});
EM_JS(void, edi_settings_store, (const char* text), {
    try {
        globalThis.localStorage.setItem("edi.settings.ini", UTF8ToString(text));
    } catch (e) {
    }
});

// ADR-0023: the browser's wheel events as the desktop's trackpad gestures. Qt's wasm platform hands every browser
// wheel event to Qt Quick as a mouse wheel's (no scroll phase, not synthesized, the pixel delta copied into the
// angle delta), so a Flickable reads a touchpad's few pixels as small fractions of a 120-unit wheel notch and
// scrolls a short, damped distance. A macOS desktop sends the same gesture with scroll phases, and the Flickable
// moves the content by the pixel deltas, the operating system's momentum included. The page records each wheel
// event's deltaMode: pixel-mode events are passed on as one gesture (ScrollBegin, then ScrollUpdate per event, the
// momentum events the browser forwards included, and ScrollEnd once they stop), with their own deltas and
// timestamps. Line- and page-mode events (a mouse wheel in some browsers) stay a wheel's.
EM_JS(void, edi_watch_wheel_mode, (), {
    if (!globalThis.__ediWheelWatch) {
        globalThis.__ediWheelWatch = true;
        globalThis.addEventListener("wheel", (e) => { globalThis.__ediWheelDeltaMode = e.deltaMode; },
                                    { capture: true, passive: true });
    }
});
EM_JS(int, edi_wheel_delta_mode, (), { return globalThis.__ediWheelDeltaMode ?? 0; });

namespace {
class WheelGestures final : public QObject {
   public:
    explicit WheelGestures(QObject* parent) : QObject(parent) {
        edi_watch_wheel_mode();
        end_.setSingleShot(true);
        end_.setInterval(kGestureGapMs);
        QObject::connect(&end_, &QTimer::timeout, this, [this] { finish(); });
    }

   protected:
    bool eventFilter(QObject* watched, QEvent* event) override {
        if (event->type() != QEvent::Wheel || forwarding_) {
            return false;
        }
        auto* window = qobject_cast<QWindow*>(watched);
        const auto* wheel = static_cast<const QWheelEvent*>(event);
        if (window == nullptr || wheel->phase() != Qt::NoScrollPhase || wheel->source() != Qt::MouseEventNotSynthesized
            || wheel->pixelDelta().isNull() || edi_wheel_delta_mode() != 0) {
            return false;
        }
        if (window_ != window) {
            finish();
            window_ = window;
            send(*wheel, Qt::ScrollBegin, QPoint(), wheel->timestamp() > 1 ? wheel->timestamp() - 1 : 1);
        }
        send(*wheel, Qt::ScrollUpdate, wheel->pixelDelta(), wheel->timestamp());
        last_position_ = wheel->position();
        last_global_ = wheel->globalPosition();
        last_timestamp_ = wheel->timestamp();
        device_ = wheel->pointingDevice();
        end_.start();
        return true;
    }

   private:
    // Longer than any gap between one gesture's events, its momentum included, also on a page busy drawing (a
    // software-rendered page handles a wheel event in up to 250 ms); a late end only delays the return to bounds.
    static constexpr int kGestureGapMs = 400;

    void send(const QWheelEvent& from, Qt::ScrollPhase phase, QPoint delta, quint64 timestamp) {
        QWheelEvent event(from.position(), from.globalPosition(), delta, delta, from.buttons(), from.modifiers(), phase,
                          from.inverted(), Qt::MouseEventSynthesizedByApplication, from.pointingDevice());
        event.setTimestamp(timestamp);
        forwarding_ = true;
        QCoreApplication::sendEvent(window_, &event);
        forwarding_ = false;
    }
    void finish() {
        end_.stop();
        if (window_.isNull()) {
            window_ = nullptr;
            return;
        }
        QWheelEvent event(last_position_, last_global_, QPoint(), QPoint(), Qt::NoButton, Qt::NoModifier,
                          Qt::ScrollEnd, false, Qt::MouseEventSynthesizedByApplication, device_);
        event.setTimestamp(last_timestamp_ + kGestureGapMs);
        forwarding_ = true;
        QCoreApplication::sendEvent(window_, &event);
        forwarding_ = false;
        window_ = nullptr;
    }

    QPointer<QWindow> window_;
    QPointF last_position_, last_global_;
    quint64 last_timestamp_ = 0;
    const QPointingDevice* device_ = nullptr;
    QTimer end_;
    bool forwarding_ = false;
};
}  // namespace
#endif

namespace edi_app {

namespace {
// A bundled font file's family, registered from the base's font resources; empty when the file is missing.
QString registered_family(const char* file) {
    return QFontDatabase::applicationFontFamilies(
               QFontDatabase::addApplicationFont(
                   QStringLiteral(":/qt/qml/EasyApplication/Gui/Resources/Fonts/") + QString::fromUtf8(file)))
        .value(0);
}
// Set by use_fresh_settings(): the process-lifetime directory a demo or a test run keeps its settings in.
QString& fresh_config_dir() {
    static QString dir;
    return dir;
}
// Set by select_freetype_engine(): the platform specification the QGuiApplication starts from.
QByteArray& platform_spec() {
    static QByteArray spec;
    return spec;
}
}  // namespace

void configure_engine(QQmlEngine& engine) {
    // The base's Settings objects write here (Globals/Vars.qml `pySettingsPath`); without it they would
    // point inside the read-only module resources. A demo or a test run uses its fresh directory.
    const QString config_dir = fresh_config_dir().isEmpty()
                                   ? QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation)
                                   : fresh_config_dir();
    QDir().mkpath(config_dir);
    const QString settings_file = QDir(config_dir).filePath(QStringLiteral("settings.ini"));
#if defined(Q_OS_WASM)
    // Once per process: touchpad scrolling as the desktop's (WheelGestures above).
    static WheelGestures* const gestures = [] {
        auto* filter = new WheelGestures(QCoreApplication::instance());
        QCoreApplication::instance()->installEventFilter(filter);
        return filter;
    }();
    static_cast<void>(gestures);
    if (fresh_config_dir().isEmpty()) {
        if (char* stored = edi_settings_load()) {
            QFile file(settings_file);
            if (file.open(QIODevice::WriteOnly)) {
                file.write(stored);
            }
            std::free(stored);
        }
        // The base's Settings write the file on their own schedule; a check per second keeps the stored copy
        // at most a second behind it.
        auto* timer = new QTimer(&engine);
        timer->setInterval(1000);
        QObject::connect(timer, &QTimer::timeout, timer, [settings_file, last = QByteArray()]() mutable {
            QFile file(settings_file);
            if (!file.open(QIODevice::ReadOnly)) {
                return;
            }
            const QByteArray text = file.readAll();
            if (text != last) {
                edi_settings_store(text.constData());
                last = text;
            }
        });
        timer->start();
    }
#endif
    engine.rootContext()->setContextProperty(QStringLiteral("pySettingsPath"),
                                             QUrl::fromLocalFile(settings_file).toString());
    engine.rootContext()->setContextProperty(QStringLiteral("pyIsTestMode"), false);
}

void use_design_font() {
    // The application's default font, set before any QML loads: the base's design font, PT Sans
    // (Style/Fonts.qml `fontFamily`), from the module resources. Without it Qt falls back to its generic
    // "Sans Serif", which macOS lacks: Qt warns while populating family aliases, and the Qt Quick Test
    // tier fails on that warning. One text pipeline on every platform (ADR-0015 §10): Qt Quick draws text
    // from distance fields of the glyph outlines, its default, stated here so that no platform or
    // environment default decides it.
    QQuickWindow::setTextRenderType(QQuickWindow::QtTextRendering);
    const int id = QFontDatabase::addApplicationFont(
        QStringLiteral(":/qt/qml/EasyApplication/Gui/Resources/Fonts/PT_Sans/PTSans-Regular.ttf"));
    const QStringList families = QFontDatabase::applicationFontFamilies(id);
    if (families.isEmpty()) {
        qWarning("edi_app: the design font PT Sans is missing from the module resources");
        return;
    }
    // One hinting on every platform: none, so glyphs keep the shapes and advances the font designs; left
    // to the platform, Linux takes fontconfig's slight hinting (ADR-0015 §10).
    QFont font(families.constFirst());
    font.setHintingPreference(QFont::PreferNoHinting);
    QGuiApplication::setFont(font);
    // PT Sans and PT Mono lack some characters the pages render: the Greek letters and the subscripts ₀ and
    // ₅ to ₉. Each family's are drawn from its bundled Noto counterpart, so none comes from the platform and
    // monospace text stays monospace (ADR-0015 §10): Noto Sans behind PT Sans, Noto Sans Mono behind PT
    // Mono. A substitution heads the fonts Qt tries for a glyph its family lacks, for every text in that
    // family, also those whose QML sets `font.family`.
    const std::pair<const char*, const char*> fallbacks[] = {
        {"PT_Sans/PTSans-Regular.ttf", "Noto_Sans/NotoSans-Regular.ttf"},
        {"PT_Mono/PTMono-Regular.ttf", "Noto_Sans_Mono/NotoSansMono-Regular.ttf"}};
    for (const auto& [family_file, fallback_file] : fallbacks) {
        const QString family = registered_family(family_file);
        const QString fallback = registered_family(fallback_file);
        if (family.isEmpty() || fallback.isEmpty()) {
            qWarning("edi_app: %s or its fallback %s is missing from the module resources", family_file,
                     fallback_file);
            continue;
        }
        QFont::insertSubstitution(family, fallback);
    }
}

void use_fresh_settings() {
    static QTemporaryDir dir;  // removed at exit
    // A directory that could not be created has an empty path, which configure_engine() would read as
    // "the user's own settings": refuse instead, before any settings path is published or QML loads.
    if (!dir.isValid()) {
        qFatal("edi_app: cannot create a fresh settings directory for this demo or test run (%s); refusing "
               "to run on the user's own settings",
               qPrintable(dir.errorString()));
    }
    fresh_config_dir() = dir.path();
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, dir.path());
}

void select_freetype_engine(int argc, char** argv) {
    // A -platform argument outranks QT_QPA_PLATFORM, and Qt removes it from the arguments: it is kept as
    // given, for require_freetype_engine() to judge.
    for (int i = 1; i + 1 < argc; ++i) {
        if (qstrcmp(argv[i], "-platform") == 0 || qstrcmp(argv[i], "--platform") == 0) {
            platform_spec() = argv[i + 1];
        }
    }
    if (!platform_spec().isEmpty()) {
        return;
    }
    QByteArray platform = qgetenv("QT_QPA_PLATFORM");
#if defined(Q_OS_MACOS)
    if (platform.isEmpty()) {
        platform = "cocoa";
    }
#elif defined(Q_OS_WIN)
    if (platform.isEmpty()) {
        platform = "windows";
    }
#endif
    if (platform.isEmpty()) {
        return;  // Linux (xcb, wayland): FreeType through fontconfig already
    }
    QList<QByteArray> parts = platform.split(':');  // "<name>[:<option>]..."
    const QByteArray& name = parts.constFirst();
    if ((name == "cocoa" || name == "windows") && !platform.contains("fontengine=")) {
        parts.append("fontengine=freetype");
    }
    platform_spec() = parts.join(':');
    qputenv("QT_QPA_PLATFORM", platform_spec());
}

void require_freetype_engine() {
    // Public means only, no Qt private API: the platform in use must have been started with the FreeType
    // engine. On Linux every platform draws with FreeType. On macOS and Windows only cocoa and windows take
    // fontengine=freetype, so another platform (macOS offscreen is CoreText-only), or a -platform argument
    // without the option, fails here. That FreeType then renders the glyphs is the UI test's to prove: it
    // compares them with the committed images (ADR-0015 §10).
#if defined(Q_OS_MACOS) || defined(Q_OS_WIN)
    const QString name = QGuiApplication::platformName();
    const QList<QByteArray> started = platform_spec().split(':');
    const bool freetype = (name == QLatin1String("cocoa") || name == QLatin1String("windows")) &&
                          started.constFirst() == name.toLatin1() && started.contains("fontengine=freetype");
    if (!freetype) {
        qFatal("edi_app: text must render with Qt's FreeType font engine (owner decision, ADR-0015), but the "
               "'%s' platform was started as '%s', without fontengine=freetype; run on cocoa or windows",
               qPrintable(name), platform_spec().constData());
    }
#endif
}

}  // namespace edi_app
