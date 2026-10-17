// SPDX-License-Identifier: BSD-3-Clause
#include "app_info.hpp"

#include "app_build_info.hpp"
#include "engine_setup.hpp"
#include "edi/palette.hpp"
#include "edi/structure_scene.hpp"
#include "edi/threading.hpp"

#include <QClipboard>
#include <QFile>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickWindow>
#include <QScreen>
#include <QSGRendererInterface>
#include <QStringList>
#include <QSysInfo>
#include <QThread>
#include <QUrl>
#include <QtGlobal>
#include <algorithm>
#include <string_view>

#ifdef _OPENMP
#include <omp.h>
#endif
#ifdef Q_OS_WASM
#include <emscripten.h>
#include <emscripten/val.h>
#endif

namespace {
bool g_demo_identity = false;

// The bundled resource behind a licence URL the About window offers; empty for any other URL.
QString bundled_resource(const QString& url) {
    for (const char* name : {"LICENSE", "COPYING", "THIRD-PARTY-NOTICES", "app/DISTRIBUTION-LICENSE.md"}) {
        if (url == QStringLiteral("qrc:/") + QLatin1String(name)) {
            return QStringLiteral(":/") + QLatin1String(name);
        }
    }
    return {};
}

QString read_resource(const QString& path) {
    QFile file(path);
    if (path.isEmpty() || !file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}
}  // namespace


#ifdef Q_OS_WASM
// Keep bounded navigator inspection/throw handling inside the existing browser bridge (ADR-0041).
EM_JS(int, edi_assistant_device_available, (), {
    try {
        const nav = globalThis.navigator;
        if (!nav || typeof nav !== "object") return 0;
        const bounded = value => typeof value === "string" && value.length <= 4096;
        const uaValue = nav.userAgent;
        if (!bounded(uaValue) || uaValue.trim().length === 0) return 0;
        const platformValue = nav.platform;
        if (platformValue !== undefined && !bounded(platformValue)) return 0;
        const touch = nav.maxTouchPoints;
        if (touch !== undefined && (!Number.isSafeInteger(touch) || touch < 0)) return 0;
        const hints = nav.userAgentData;
        let hintPlatform = "";
        if (hints !== undefined) {
            if (hints === null || typeof hints !== "object" || Array.isArray(hints)) return 0;
            const mobile = hints.mobile;
            if (mobile !== undefined && typeof mobile !== "boolean") return 0;
            if (mobile === true) return 0;
            const value = hints.platform;
            if (value !== undefined && !bounded(value)) return 0;
            hintPlatform = value === undefined ? "" : value.toLowerCase();
        }
        const ua = uaValue.toLowerCase();
        const platform = platformValue === undefined ? "" : platformValue.toLowerCase();
        const mobile = value => /iphone|ipad|ipod|android|mobile|windows phone|iemobile|wince/.test(value);
        if (mobile(ua) || mobile(platform) || mobile(hintPlatform)) return 0;
        const family = value => {
            let bits = 0;
            if (/windows|win32|win64/.test(value)) bits |= 1;
            if (/macintosh|macintel|macppc|mac68k|macos|mac os|^mac$/.test(value)) bits |= 2;
            if (/linux|x11/.test(value)) bits |= 4;
            if (/cros|chrome os|chromium os|chromeos/.test(value)) bits |= 8;
            return bits;
        };
        const uaFamily = family(ua);
        const platformFamily = family(platform);
        const hintFamily = family(hintPlatform);
        if (uaFamily === 0 || (platform.trim() !== "" && platformFamily === 0)
            || (hintPlatform.trim() !== "" && hintFamily === 0)) return 0;
        let combined = uaFamily | platformFamily | hintFamily;
        // Chromium's CrOS UA and Linux legacy platform are compatible aliases.
        if (combined === (4 | 8)) combined = 8;
        if ((combined & (combined - 1)) !== 0) return 0;
        if (combined === 2) {
            const explicitDesktopHint = hintFamily === 2;
            if (!explicitDesktopHint && (touch === undefined || touch > 1)) return 0;
        }
        return 1;
    } catch (_) {
        return 0;
    }
});
#endif

namespace {
bool assistant_device_available() {
#ifdef Q_OS_WASM
    return edi_assistant_device_available() != 0;
#else
    return true;
#endif
}
}  // namespace

ApplicationInfo::ApplicationInfo(QObject* parent)
    : QObject(parent), assistant_available_(assistant_device_available()) {}

bool ApplicationInfo::assistantAvailable() const { return assistant_available_; }

QString ApplicationInfo::assistantUnavailableReason() const {
    return assistant_available_ ? QString() : tr("AI chat is not available on this device. Use a supported computer.");
}

void ApplicationInfo::useDemoIdentity() { g_demo_identity = true; }

bool ApplicationInfo::demoIdentity() { return g_demo_identity; }

QString ApplicationInfo::version() const {
    return g_demo_identity ? QStringLiteral("demo") : QStringLiteral(EDI_APP_VERSION);
}

QString ApplicationInfo::releaseDate() const {
    return g_demo_identity ? QStringLiteral("demo build") : QStringLiteral(EDI_APP_DATE);
}

QString ApplicationInfo::description() const {
    return tr("EasyDiffraction is a software for calculating diffraction patterns based on structural models and "
              "refining their parameters against experimental data.");
}

QString ApplicationInfo::licenceText(const QString& url) const { return read_resource(bundled_resource(url)); }

QString ApplicationInfo::licenceLinkTarget(const QString& from, const QString& link) const {
    const QString target = QUrl(from).resolved(QUrl(link)).toString();
    return bundled_resource(from).isEmpty() || bundled_resource(target).isEmpty() ? QString() : target;
}

// The notices' "Components" list: from its heading to the next, one "- name | licence: X | use" line each.
QStringList ApplicationInfo::componentColumn(int column) {
    QStringList values;
    bool inList = false;
    const QStringList lines = read_resource(QStringLiteral(":/THIRD-PARTY-NOTICES")).split(QLatin1Char('\n'));
    for (qsizetype i = 0; i < lines.size(); ++i) {
        const QString& line = lines[i];
        const bool heading = i + 1 < lines.size() && lines[i + 1].startsWith(QLatin1String("---"));
        if (heading) {
            if (inList) {
                break;
            }
            inList = line.trimmed() == QLatin1String("Components");
            continue;
        }
        const QStringList cells = line.split(QLatin1String(" | "));
        if (!inList || !line.startsWith(QLatin1String("- ")) || cells.size() != 3) {
            continue;
        }
        if (column == 0 || column == 3) {
            // "- Qt Graphs 6.11.2": the name, then the version when the last word is a dotted number ("Baloo 2" is a
            // name).
            const QString named = cells[0].trimmed().mid(2);
            const qsizetype space = named.lastIndexOf(QLatin1Char(' '));
            const bool versioned =
                space > 0 && named.at(space + 1).isDigit() && named.indexOf(QLatin1Char('.'), space) > 0;
            values.append(column == 0 ? (versioned ? named.left(space) : named) : (versioned ? named.mid(space + 1) : QString()));
            continue;
        }
        const QString cell = cells[column].trimmed();
        values.append(column == 1 ? QString(cell).remove(QLatin1String("licence: ")) : cell);
    }
    return values;
}

// The notices' "## <name>" section of a component: its indented licence text, the indent removed.
QString ApplicationInfo::componentLicenceText(int index) const {
    const QStringList names = componentNames();
    if (index < 0 || index >= names.size()) {
        return {};
    }
    const QStringList lines = read_resource(QStringLiteral(":/THIRD-PARTY-NOTICES")).split(QLatin1Char('\n'));
    const QString heading = QStringLiteral("## ") + names[index];
    QStringList text;
    bool inSection = false;
    for (const QString& line : lines) {
        if (line.startsWith(QLatin1Char('#'))) {
            if (inSection) {
                break;
            }
            inSection = line == heading;
            continue;
        }
        if (inSection && (text.size() > 0 || line.startsWith(QLatin1String("    ")))) {
            text.append(line.startsWith(QLatin1String("    ")) ? line.mid(4) : line);
        }
    }
    while (!text.isEmpty() && text.last().trimmed().isEmpty()) {
        text.removeLast();
    }
    return text.join(QLatin1Char('\n'));
}

QStringList ApplicationInfo::elementSymbols() const {
    QStringList symbols;
    for (const edi::ElementStyle& style : edi::element_style_table()) {
        symbols.append(QString::fromStdString(style.symbol));
    }
    return symbols;
}

namespace {
edi::ColourScheme colour_scheme(const QString& name) {
    return edi::colour_scheme_from_name(name.toStdString()).value_or(edi::kDefaultColourScheme);
}
}  // namespace

QColor ApplicationInfo::patternColour(const QString& scheme, int place, int count, bool dark) const {
    return QColor(QString::fromStdString(edi::pattern_colour(colour_scheme(scheme), static_cast<std::size_t>(std::max(place, 0)),
                                                             static_cast<std::size_t>(std::max(count, 1)), dark)));
}

QPoint ApplicationInfo::onScreenPosition(int x, int y, int width, int height) const {
    const QList<QScreen*> screens = QGuiApplication::screens();
    for (const QScreen* screen : screens) {
        if (screen->virtualGeometry().contains(x, y)) {
            return {x, y};
        }
    }
    const QScreen* primary = QGuiApplication::primaryScreen();
    if (primary == nullptr) {
        return {x, y};
    }
    const QRect area = primary->availableGeometry();
    return {area.x() + std::max(0, (area.width() - width) / 2), area.y() + std::max(0, (area.height() - height) / 2)};
}

QColor ApplicationInfo::structureColour(const QString& scheme, int place, bool dark) const {
    return QColor(QString::fromStdString(
        edi::structure_colour(colour_scheme(scheme), static_cast<std::size_t>(std::max(place, 0)), dark)));
}

QColor ApplicationInfo::elementColor(const QString& typeSymbol, const QColor& fallback, const QString& scheme) const {
    const edi::ColorScheme colors = scheme == QLatin1String("vesta") ? edi::ColorScheme::Vesta : edi::ColorScheme::Jmol;
    const edi::ElementColor found = edi::element_color(edi::element_of(typeSymbol.toStdString()), colors);
    return found.known ? QColor(found.color.r, found.color.g, found.color.b) : fallback;
}

namespace {

QString graphics_api(QSGRendererInterface::GraphicsApi api) {
    switch (api) {
        case QSGRendererInterface::Software: return QStringLiteral("software");
        case QSGRendererInterface::OpenGL: return QStringLiteral("OpenGL");
        case QSGRendererInterface::Direct3D11: return QStringLiteral("Direct3D 11");
        case QSGRendererInterface::Direct3D12: return QStringLiteral("Direct3D 12");
        case QSGRendererInterface::Vulkan: return QStringLiteral("Vulkan");
        case QSGRendererInterface::Metal: return QStringLiteral("Metal");
        case QSGRendererInterface::Null: return QStringLiteral("none");
        default: return QStringLiteral("other (%1)").arg(static_cast<int>(api));
    }
}

}  // namespace

QString ApplicationInfo::diagnostics() const {
    QStringList lines;
    const auto add = [&lines](const QString& name, const QString& value) { lines.append(name + QStringLiteral(": ") + value); };
    add(QStringLiteral("EasyDiffraction"), QStringLiteral(EDI_APP_VERSION " (" EDI_APP_DATE ")"));
    add(QStringLiteral("crysta"), QStringLiteral(EDI_APP_CRYSTA_VERSION));
    add(QStringLiteral("crysta SDK commit"), QStringLiteral(EDI_APP_CRYSTA_COMMIT));
    add(QStringLiteral("Platform"), QSysInfo::prettyProductName() + QStringLiteral(" (") + QSysInfo::currentCpuArchitecture() +
                                        QStringLiteral(", ") + QSysInfo::kernelType() + QStringLiteral(" ") +
                                        QSysInfo::kernelVersion() + QStringLiteral(")"));
    add(QStringLiteral("Qt"), QString::fromLatin1(qVersion()) + QStringLiteral(", platform plugin ") +
                                  QGuiApplication::platformName());
    QString graphics = QStringLiteral("no window yet");
    for (QWindow* window : QGuiApplication::topLevelWindows()) {
        if (auto* quick = qobject_cast<QQuickWindow*>(window); quick != nullptr && quick->rendererInterface() != nullptr) {
            graphics = graphics_api(quick->rendererInterface()->graphicsApi());
            break;
        }
    }
    add(QStringLiteral("Graphics backend"), graphics);
    add(QStringLiteral("Threads (ideal)"), QString::number(QThread::idealThreadCount()));
#ifdef _OPENMP
    add(QStringLiteral("Threads (OpenMP team)"), QString::number(omp_get_max_threads()));
#else
    add(QStringLiteral("Threads (OpenMP team)"), QStringLiteral("no OpenMP"));
#endif
    // The engine's own report: which backend its parallel fill runs on, with how many threads, and SIMD.
    const edi::EngineThreading engine = edi::engine_threading();
    add(QStringLiteral("Engine backend"), QString::fromLatin1(engine.backend));
    const int threads = edi::engine_threads_setting();
    add(QStringLiteral("Engine threads (preference)"), threads > 0 ? QString::number(threads) : QStringLiteral("Auto"));
    add(QStringLiteral("Engine workers"), QString::number(engine.workers));
    add(QStringLiteral("WebAssembly SIMD"), engine.wasm_simd ? QStringLiteral("on") : QStringLiteral("off"));
#ifdef Q_OS_WASM
    using emscripten::val;
    const val window = val::global("window");
    const val navigator = val::global("navigator");
    add(QStringLiteral("Browser"), QString::fromStdString(navigator["userAgent"].as<std::string>()));
    add(QStringLiteral("Browser cores (hardwareConcurrency)"),
        QString::number(navigator["hardwareConcurrency"].isNumber() ? navigator["hardwareConcurrency"].as<int>() : 0));
    add(QStringLiteral("crossOriginIsolated"), window["crossOriginIsolated"].as<bool>() ? QStringLiteral("yes") : QStringLiteral("no"));
    add(QStringLiteral("SharedArrayBuffer"), window["SharedArrayBuffer"].isUndefined() ? QStringLiteral("absent") : QStringLiteral("present"));
    add(QStringLiteral("Service worker controls the page"),
        !navigator["serviceWorker"].isUndefined() && !navigator["serviceWorker"]["controller"].isNull() ? QStringLiteral("yes") : QStringLiteral("no"));
    // What the start page chose and why (app/web/index.html records it).
    const val info = window["ediBuildInfo"];
    if (info.isUndefined() || info.isNull()) {
        add(QStringLiteral("Build"), QStringLiteral("unknown (the start page recorded nothing)"));
    } else {
        const QJsonObject recorded =
            QJsonDocument::fromJson(QByteArray::fromStdString(val::global("JSON").call<std::string>("stringify", info))).object();
        for (auto it = recorded.begin(); it != recorded.end(); ++it) {
            add(QStringLiteral("Build ") + it.key(), it.value().isString() ? it.value().toString()
                                                    : it.value().isBool() ? (it.value().toBool() ? QStringLiteral("yes") : QStringLiteral("no"))
                                                    : QString::fromUtf8(QJsonDocument(QJsonObject{{QStringLiteral("v"), it.value()}}).toJson(QJsonDocument::Compact)));
        }
    }
#ifdef __EMSCRIPTEN_PTHREADS__
    add(QStringLiteral("Build flavour"), QStringLiteral("multithreaded (WebAssembly threads)"));
#else
    add(QStringLiteral("Build flavour"), QStringLiteral("single-threaded (no WebAssembly threads)"));
#endif
#else
    add(QStringLiteral("Build flavour"), QStringLiteral("desktop, multithreaded"));
#endif
    return lines.join(QLatin1Char('\n'));
}

void ApplicationInfo::copyText(const QString& text) const { QGuiApplication::clipboard()->setText(text); }

bool ApplicationInfo::engineThreadsSelectable() const {
    return std::string_view(edi::engine_threading().backend) != "serial";
}

int ApplicationInfo::engineThreadsMaximum() const { return std::clamp(2 * QThread::idealThreadCount(), 16, 64); }

void ApplicationInfo::setEngineThreads(int count) const { edi::set_engine_threads(count); }

void ApplicationInfo::storeSettings() const { edi_app::store_settings_now(); }
