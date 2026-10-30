// SPDX-License-Identifier: BSD-3-Clause
#include "app_info.hpp"
#include "assistant_message_presentation.hpp"
#include "assistant_view_model.hpp"

#include "app_build_info.hpp"
#include "engine_setup.hpp"
#include "edi/palette.hpp"
#include "edi/assistant_files.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/scan_views.hpp"
#include "edi/structure_scene.hpp"
#include "edi/threading.hpp"

#include <QClipboard>
#include <QFile>
#include <QGuiApplication>
#include <QJSManagedValue>
#include <QJSPrimitiveValue>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocale>
#include <QQuickWindow>
#include <QQuickItem>
#include <utility>
#include <QPointer>
#include <QQmlEngine>
#include <QRegularExpression>
#include <QScreen>
#include <QSGRendererInterface>
#include <QStringList>
#include <QSysInfo>
#include <QThread>
#include <QUrl>
#include <QtGlobal>
#include <algorithm>
#include <cmath>
#include <optional>
#include <string_view>

#ifdef _OPENMP
#include <omp.h>
#endif
#ifdef Q_OS_WASM
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



namespace {
bool assistant_device_available() {
#ifdef Q_OS_WASM
    return false;
#else
    return true;
#endif
}
}  // namespace

ApplicationInfo::ApplicationInfo(QObject* parent)
    : QObject(parent), assistant_available_(assistant_device_available()) {}

bool ApplicationInfo::assistantAvailable() const { return assistant_available_; }

QString ApplicationInfo::assistantUnavailableReason() const {
    return assistant_available_ ? QString() : tr("AI assistance is only available in the desktop version.");
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

// DEPENDENCIES.md's component rows this build carries: every table under the header `Component | Version | Licence |
// Desktop app | Web app | Python package | CLI | In edi`, a row whose cell for this build's surface is not empty or
// "—". A surface's own version, in brackets in its cell, replaces the Version column's.
QStringList ApplicationInfo::componentColumn(int column) {
#ifdef Q_OS_WASM
    constexpr int kSurface = 4;
#else
    constexpr int kSurface = 3;
#endif
    static const QStringList kHeader{"Component", "Version", "Licence", "Desktop app", "Web app", "Python package", "CLI",
                                     "In edi"};
    const auto cells_of = [](const QString& line) {
        QStringList cells = line.trimmed().split(QLatin1Char('|'));
        cells.removeFirst();
        cells.removeLast();
        for (QString& cell : cells) {
            cell = cell.trimmed();
        }
        return cells;
    };
    QStringList values;
    bool inTable = false;
    for (const QString& line : read_resource(QStringLiteral(":/DEPENDENCIES.md")).split(QLatin1Char('\n'))) {
        if (!line.startsWith(QLatin1Char('|'))) {
            inTable = false;
            continue;
        }
        const QStringList cells = cells_of(line);
        if (cells.value(0) == QLatin1String("Component")) {
            inTable = cells == kHeader;
            continue;
        }
        if (!inTable || cells.size() != kHeader.size() || cells[0].startsWith(QLatin1String("---"))) {
            continue;
        }
        const QString& carried = cells[kSurface];
        if (carried.isEmpty() || carried == QStringLiteral("\u2014")) {
            continue;
        }
        switch (column) {
            case 0: values.append(cells[0]); break;
            case 1: values.append(cells[2]); break;
            case 2: values.append(cells[7]); break;
            default: {
                static const QRegularExpression kOwnVersion(QStringLiteral("\\(([0-9][0-9A-Za-z.]*)\\)"));
                const QRegularExpressionMatch own = kOwnVersion.match(carried);
                values.append(own.hasMatch() ? own.captured(1) : cells[1]);
            }
        }
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
edi::ColourScheme colour_scheme(const QString& name) { return edi::colour_scheme_or_default(name.toStdString()); }
}  // namespace

QColor ApplicationInfo::figureColour(const QString& scheme, int position, int count, bool dark) const {
    return QColor(QString::fromStdString(edi::figure_colour(colour_scheme(scheme),
                                                            static_cast<std::size_t>(std::max(position, 0)),
                                                            static_cast<std::size_t>(std::max(count, 1)), dark)));
}

QColor ApplicationInfo::calculationColour(const QString& scheme, bool dark) const {
    return QColor(
        QString::fromStdString(edi::role_colour(colour_scheme(scheme), edi::ChartRole::TotalCalculation, dark)));
}

bool ApplicationInfo::reservesExperimentColours(const QString& scheme) const {
    return edi::reserves_experiment_colours(colour_scheme(scheme));
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

QStringList ApplicationInfo::colourSchemes() const {
    QStringList names;
    for (const std::string_view name : edi::colour_scheme_names()) {
        names.append(QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size())));
    }
    return names;
}

QStringList ApplicationInfo::colourSchemeTitles() const {
    QStringList titles;
    for (const std::string_view name : edi::colour_scheme_names()) {
        const std::string_view title = edi::colour_scheme_title(colour_scheme(QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size()))));
        titles.append(QString::fromUtf8(title.data(), static_cast<qsizetype>(title.size())));
    }
    return titles;
}

QString ApplicationInfo::colourSchemeOrDefault(const QString& scheme) const {
    const std::string_view name = edi::colour_scheme_names()[static_cast<std::size_t>(colour_scheme(scheme))];
    return QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size()));
}

QStringList ApplicationInfo::scanColourMaps() const {
    QStringList names;
    for (const std::string& name : edi::scan_colour_map_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QString ApplicationInfo::scanColourMapOrDefault(const QString& name) const {
    const std::vector<std::string>& names = edi::scan_colour_map_names();
    return std::find(names.begin(), names.end(), name.toStdString()) != names.end() ? name : QStringLiteral("blue-red");
}

QString ApplicationInfo::scanColourTitle(const QString& choice) const {
    const std::optional<edi::ColourScheme> scheme = edi::colour_scheme_from_name(choice.toStdString());
    if (scheme) {
        const std::string_view title = edi::colour_scheme_title(*scheme);
        return QString::fromUtf8(title.data(), static_cast<qsizetype>(title.size()));
    }
    return QString::fromStdString(edi::scan_colour_map_title(choice.toStdString()));
}

QStringList ApplicationInfo::stackedSpacings() const {
    QStringList names;
    for (const std::string& name : edi::stacked_spacing_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QStringList ApplicationInfo::stackedSpacingTitles() const {
    QStringList titles;
    for (const std::string& name : edi::stacked_spacing_names()) {
        titles.append(QString::fromStdString(edi::stacked_spacing_title(edi::stacked_spacing_or_default(name))));
    }
    return titles;
}

double ApplicationInfo::stackedSpacingShare(const QString& name) const {
    return edi::stacked_spacing_share(edi::stacked_spacing_or_default(name.toStdString()));
}

QStringList ApplicationInfo::scanMapDirections() const {
    QStringList names;
    for (const std::string& name : edi::scan_map_direction_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QStringList ApplicationInfo::scanMapDirectionTitles() const {
    QStringList titles;
    for (const std::string& name : edi::scan_map_direction_names()) {
        titles.append(QString::fromStdString(edi::scan_map_direction_title(edi::scan_map_direction_or_default(name))));
    }
    return titles;
}

QString ApplicationInfo::scanMapDirectionOrDefault(const QString& name) const {
    const edi::ScanMapDirection direction = edi::scan_map_direction_or_default(name.toStdString());
    return QString::fromStdString(edi::scan_map_direction_names()[static_cast<std::size_t>(direction)]);
}

bool ApplicationInfo::scanMapInverted(const QString& map, const QString& direction, const QColor& background,
                                      bool dark) const {
    return edi::scan_map_inverted(edi::scan_colour_map_or_default(map.toStdString()),
                                  edi::scan_map_direction_or_default(direction.toStdString()),
                                  background.name(QColor::HexRgb).toStdString(), dark);
}

QList<QColor> ApplicationInfo::scanColourStops(const QString& map, bool dark, bool inverted, int stops) const {
    const std::vector<edi::ScanMapColour> table =
        edi::scan_colour_map_table(edi::scan_colour_map_or_default(map.toStdString()), dark);
    QList<QColor> out;
    const int count = std::max(stops, 2);
    for (int i = 0; i < count; ++i) {
        const auto at = static_cast<std::size_t>(
            std::lround(static_cast<double>(i) / (count - 1) * static_cast<double>(table.size() - 1)));
        const edi::ScanMapColour& colour = table[inverted ? table.size() - 1 - at : at];
        out.append(QColor(colour.r, colour.g, colour.b));
    }
    return out;
}

QColor ApplicationInfo::elementColor(const QString& typeSymbol, const QColor& fallback, const QString& scheme) const {
    const edi::ColorScheme colors = scheme == QLatin1String("vesta") ? edi::ColorScheme::Vesta : edi::ColorScheme::Jmol;
    const edi::ElementColor found = edi::element_color(edi::element_of(typeSymbol.toStdString()), colors);
    return found.known ? QColor(found.color.r, found.color.g, found.color.b) : fallback;
}

QColor ApplicationInfo::readableColour(const QColor& colour, const QList<QColor>& backgrounds) const {
    // A translucent background is taken as opaque: what shows through it is the same theme's background.
    std::vector<std::string> hexes;
    for (const QColor& background : backgrounds) {
        hexes.push_back(background.name(QColor::HexRgb).toStdString());
    }
    return QColor(QString::fromStdString(edi::readable_colour(colour.name(QColor::HexRgb).toStdString(), hexes)));
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

namespace {
bool messageScriptReady(const QPointer<QJSEngine>& engine) {
    return engine && !engine->hasError();
}
QJSValue messageScriptProperty(const QPointer<QJSEngine>& engine, const QJSValue& source,
                              const QString& name) {
    if (!messageScriptReady(engine)) return {};
    const QJSManagedValue value(source, engine.data());
    if (value.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
        return {};
    }
    // The managed API leaves every thrown value pending; never catch or inspect its type.
    return value.property(name);
}
QJSValue messageScriptIndex(const QPointer<QJSEngine>& engine, const QJSValue& source,
                           quint32 index) {
    if (!messageScriptReady(engine)) return {};
    const QJSManagedValue value(source, engine.data());
    if (value.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
        return {};
    }
    return value.property(index);
}
QJSValue messageScriptCall(const QPointer<QJSEngine>& engine, const QJSValue& function,
                          const QJSValue& receiver, const QJSValueList& arguments) {
    if (!messageScriptReady(engine)) return {};
    const QJSManagedValue callable(function, engine.data());
    const QJSManagedValue instance(receiver, engine.data());
    if (callable.engine() != engine.data() || instance.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
        return {};
    }
    for (const auto& argument : arguments) {
        const QJSManagedValue value(argument, engine.data());
        if (value.engine() != engine.data()) {
            engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
            return {};
        }
    }
    // Qt's managed call keeps the success/throw disposition in the engine, even for
    // non-Error throws. It also supplies TypeError for a non-callable managed value.
    return callable.callWithInstance(receiver, arguments);
}
QJSValue messageScriptArray(const QPointer<QJSEngine>& engine, const QJSValue& value) {
    if (!messageScriptReady(engine)) return {};
    const QJSValue array = messageScriptProperty(engine, engine->globalObject(), QStringLiteral("Array"));
    if (!messageScriptReady(engine)) return {};
    const QJSValue predicate = messageScriptProperty(engine, array, QStringLiteral("isArray"));
    if (!messageScriptReady(engine)) return {};
    return messageScriptCall(engine, predicate, array, {value});
}
std::optional<QString> messageNativeCaption(const QPointer<QJSEngine>& engine, const QJSValue& payload,
                                            const QPointer<edi_app::AssistantViewModel>& original) {
    if (!messageScriptReady(engine)) return std::nullopt;
    QJSValue action(QStringLiteral(""));
    if (payload.toBool()) {
        const QJSValue tool = messageScriptProperty(engine, payload, QStringLiteral("tool"));
        if (!messageScriptReady(engine)) return std::nullopt;
        if (tool.isString()) {
            action = messageScriptProperty(engine, payload, QStringLiteral("tool"));
            if (!messageScriptReady(engine)) return std::nullopt;
        }
    }
    if (original) {
        // This is the SAME existing QObject/CPP slot the original QML invoked,
        // retaining its QString argument conversion and actual empty-string return.
        const QJSValue receiver = engine->newQObject(original.data());
        if (!messageScriptReady(engine)) return std::nullopt;
        const QJSValue label = messageScriptProperty(engine, receiver, QStringLiteral("nativeActionLabel"));
        if (!messageScriptReady(engine)) return std::nullopt;
        const QJSValue value = messageScriptCall(engine, label, receiver, {action});
        if (!messageScriptReady(engine) || !value.isString()) return std::nullopt;
        return value.toString();
    }
    // Nullable owner fallback stays in the ONE original value formatter/dictionary.
    return edi_app::assistant_presentation::presentActivity({}).nativeCaption;
}
}  // namespace

QJSValue ApplicationInfo::assistantHistoryInputFiles(const QString& kind, const QJSValue& payload) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine) || QThread::currentThread() != engine->thread()) return {};
    const auto empty = [&]() { return messageScriptReady(engine) ? engine->newArray() : QJSValue(); };
    const auto read = [&](const QJSValue& source, const char* name) {
        return messageScriptProperty(engine, source, QString::fromLatin1(name));
    };
    const auto number = [&](const QJSValue& value) -> std::optional<double> {
        if (!messageScriptReady(engine)) return std::nullopt;
        const QJSManagedValue converted(value, engine.data());
        if (converted.engine() != engine.data()) {
            engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
            return std::nullopt;
        }
        const auto result = converted.toNumber();
        return messageScriptReady(engine) ? std::optional<double>(result) : std::nullopt;
    };
    const auto numberPredicate = [&](const char* predicate, const QJSValue& source, const char* field) {
        if (!messageScriptReady(engine)) return QJSValue();
        const auto receiver = read(engine->globalObject(), "Number");
        if (!messageScriptReady(engine)) return QJSValue();
        const auto function = read(receiver, predicate);
        if (!messageScriptReady(engine)) return QJSValue();
        const auto argument = read(source, field);
        if (!messageScriptReady(engine)) return QJSValue();
        return messageScriptCall(engine, function, receiver, {argument});
    };
    const auto fieldLength = [&](const QJSValue& file, const char* field) {
        const auto value = read(file, field);
        if (!messageScriptReady(engine)) return QJSValue();
        return read(value, "length");
    };
    if (kind != "user" || !payload.toBool()) return empty();
    const auto type = read(payload, "type");
    if (!messageScriptReady(engine)) return {};
    if (!type.strictlyEquals(QJSValue(QStringLiteral("ediInput")))) return empty();
    const auto offered = read(payload, "files");
    if (!messageScriptReady(engine)) return {};
    if (!offered.toBool()) return empty();
    const auto files = read(payload, "files");
    if (!messageScriptReady(engine)) return {};
    const auto integer = numberPredicate("isInteger", files, "length");
    if (!messageScriptReady(engine)) return {};
    if (!integer.toBool()) return empty();
    auto extent = number(read(files, "length"));
    if (!extent) return {};
    if (*extent < 0) return empty();
    extent = number(read(files, "length"));
    if (!extent) return {};
    if (*extent > static_cast<double>(edi::assistant::SelectedFileLimits::files)) return empty();
    QJSValue result = engine->newArray();
    for (double index = 0; ; index += 1) {
        extent = number(read(files, "length"));
        if (!extent) return {};
        if (!(index < *extent)) break;
        const auto file = messageScriptProperty(engine, files, QJSPrimitiveValue(index).toString());
        if (!messageScriptReady(engine)) return {};
        if (!file.toBool()) return empty();
        auto field = read(file, "id");
        if (!messageScriptReady(engine)) return {};
        if (!field.isString()) return empty();
        auto length = fieldLength(file, "id");
        if (!messageScriptReady(engine)) return {};
        if (length.strictlyEquals(QJSValue(0))) return empty();
        auto measured = number(fieldLength(file, "id"));
        if (!measured) return {};
        if (*measured > static_cast<double>(edi::assistant::Limits::id_bytes)) return empty();
        field = read(file, "name");
        if (!messageScriptReady(engine)) return {};
        if (!field.isString()) return empty();
        measured = number(fieldLength(file, "name"));
        if (!measured) return {};
        if (*measured > static_cast<double>(edi::assistant::SelectedFileLimits::name_bytes)) return empty();
        field = read(file, "bytes");
        if (!messageScriptReady(engine)) return {};
        if (!field.isNumber()) return empty();
        const auto finite = numberPredicate("isFinite", file, "bytes");
        if (!messageScriptReady(engine)) return {};
        if (!finite.toBool()) return empty();
        measured = number(read(file, "bytes"));
        if (!measured) return {};
        if (*measured < 0) return empty();
        field = read(file, "textReadable");
        if (!messageScriptReady(engine)) return {};
        if (!field.isBool()) return empty();
        field = read(file, "format");
        if (!messageScriptReady(engine)) return {};
        if (!field.isString()) return empty();
        const auto push = read(result, "push");
        if (!messageScriptReady(engine)) return {};
        messageScriptCall(engine, push, result, {file});
        if (!messageScriptReady(engine)) return {};
    }
    return result;
}

QVariantMap ApplicationInfo::assistantActivityPresentation(const QString& kind, const QString& status,
                                                           const QJSValue& payload, QObject* assistant) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(engine.data()))
        qml->markCurrentFunctionAsTranslationBinding();
    const QPointer<edi_app::AssistantViewModel> original(qobject_cast<edi_app::AssistantViewModel*>(assistant));
    const auto field = [&](const QJSValue& from, const QString& name) {
        return from.isObject() ? messageScriptProperty(engine, from, name) : QJSValue();
    };
    const auto text = [](const QJSValue& value) { return value.isString() ? value.toString() : QString(); };
    edi_app::assistant_presentation::ActivityInput input;
    input.kind = kind; input.rowStatus = status;
    const bool hasPayload = payload.toBool();
    const bool fixedCaption = kind == "error" || kind == "plan" || kind == "question" ||
        kind == "tool" || kind == "trial";
    if (kind == "activity" && hasPayload) {
        input.type = text(field(payload, QStringLiteral("type")));
        if (!messageScriptReady(engine)) return {};
        input.decisionIsString = field(payload, QStringLiteral("decision")).isString();
        if (!messageScriptReady(engine)) return {};
        if (input.decisionIsString) {
            input.itemIdIsString = field(payload, QStringLiteral("item_id")).isString();
            if (!messageScriptReady(engine)) return {};
        }
    } else if (!fixedCaption && hasPayload) {
        input.type = text(field(payload, QStringLiteral("type")));
        if (!messageScriptReady(engine)) return {};
    }
    // Capture requirements follow the FIRST consumed branches; the helper still owns
    // classification, wording and result composition, not this property adapter.
    const bool command = kind == "activity" && input.type == "commandExecution";
    const bool decision = kind == "activity" && input.decisionIsString && input.itemIdIsString;
    if (command && !decision) {
        QJSValue category = field(payload, QStringLiteral("commandCategory"));
        if (!messageScriptReady(engine)) return {};
        if (category.isString()) {
            category = field(payload, QStringLiteral("commandCategory"));
            if (!messageScriptReady(engine)) return {};
            input.commandCategory = text(category);
        }
    }
    if (!fixedCaption && !decision && !command && input.type == "dynamicToolCall") {
        const auto caption = messageNativeCaption(engine, payload, original);
        if (!messageScriptReady(engine) || !caption) return {};
        input.nativeLabel = *caption; // An actually empty caption is still an observed value.
    }
    if (command) {
        QJSValue actual = field(payload, QStringLiteral("status"));
        if (!messageScriptReady(engine)) return {};
        if (actual.isString()) {
            actual = field(payload, QStringLiteral("status"));
            if (!messageScriptReady(engine)) return {};
            input.payloadStatus = text(actual);
        }
    }
    // Explanation consumes native outcome independently of the command-caption branch.
    if (hasPayload) {
        const QJSValue outcome = field(payload, QStringLiteral("nativeOutcome"));
        if (!messageScriptReady(engine)) return {};
        if (outcome.toBool()) {
            input.nativeOutcomeStatus = text(field(outcome, QStringLiteral("status")));
            if (!messageScriptReady(engine)) return {};
        }
    }
    const auto shown = edi_app::assistant_presentation::presentActivity(input);
    if (!messageScriptReady(engine)) return {};
    return {{"caption", shown.caption}, {"state", shown.state}, {"explanation", shown.explanation},
        {"outcomeKey", shown.outcomeKey}, {"nativeCaption", shown.nativeCaption},
        {"commandActivity", shown.commandActivity}, {"decisionActivity", shown.decisionActivity},
        {"summarizedActivity", shown.summarizedActivity}};
}

QString ApplicationInfo::assistantNativeActivityCaption(const QJSValue& payload, QObject* assistant) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(engine.data()))
        qml->markCurrentFunctionAsTranslationBinding();
    const QPointer<edi_app::AssistantViewModel> original(qobject_cast<edi_app::AssistantViewModel*>(assistant));
    const auto caption = messageNativeCaption(engine, payload, original);
    return messageScriptReady(engine) && caption ? *caption : QString();
}

QString ApplicationInfo::assistantSingleLineText(const QJSValue& value) const {
    return value.isString() ? edi_app::assistant_presentation::singleLineText(value.toString()) : QString();
}

QString ApplicationInfo::assistantWebSearchCaption(const QJSValue& payload) const {
    using namespace edi_app::assistant_presentation;
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(engine.data()))
        qml->markCurrentFunctionAsTranslationBinding();
    if (!payload.isObject() || payload.isCallable()) return {};
    const auto read = [&](const QJSValue& from, const char* name) {
        return messageScriptProperty(engine, from, QString::fromLatin1(name));
    };
    const auto text = [](const QJSValue& value) { return value.isString() ? value.toString() : QString(); };
    WebActionInput input;
    const QJSValue action = read(payload, "action");
    if (!messageScriptReady(engine)) return {};
    if (!action.isUndefined() && !action.isNull()) {
        if (!action.isObject() || action.isCallable()) return {};
        const QJSValue isArray = messageScriptArray(engine, action);
        if (!messageScriptReady(engine)) return {};
        if (isArray.toBool()) return {};
        QJSValue type = read(action, "type");
        if (!messageScriptReady(engine)) return {};
        if (text(type) == "search") input.kind = WebActionKind::Search;
        else {
            type = read(action, "type");
            if (!messageScriptReady(engine)) return {};
            if (text(type) == "openPage") input.kind = WebActionKind::OpenPage;
            else {
                type = read(action, "type");
                if (!messageScriptReady(engine)) return {};
                input.kind = text(type) == "findInPage" ? WebActionKind::FindInPage : WebActionKind::Other;
            }
        }
    }
    if (input.kind == WebActionKind::Search) {
        input.query = text(read(action, "query"));
        if (!messageScriptReady(engine)) return {};
        if (singleLineText(input.query).isEmpty()) {
            // Preserve the original short-circuit guard reads; getters can throw on any read.
            QJSValue queries = read(action, "queries");
            if (!messageScriptReady(engine)) return {};
            if (!queries.isUndefined()) {
                queries = read(action, "queries");
                if (!messageScriptReady(engine)) return {};
                input.queriesPresent = !queries.isNull();
            }
            if (input.queriesPresent) {
                // Original JSON.parse(JSON.stringify(action.queries)) evaluation order:
                // resolve the outer receiver/callee before evaluating its argument.
                const QJSValue outer = read(engine->globalObject(), "JSON");
                if (!messageScriptReady(engine)) return {};
                const QJSValue parse = read(outer, "parse");
                if (!messageScriptReady(engine)) return {};
                const QJSValue inner = read(engine->globalObject(), "JSON");
                if (!messageScriptReady(engine)) return {};
                const QJSValue stringify = read(inner, "stringify");
                if (!messageScriptReady(engine)) return {};
                queries = read(action, "queries");
                if (!messageScriptReady(engine)) return {};
                const QJSValue serialized = messageScriptCall(engine, stringify, inner, {queries});
                if (!messageScriptReady(engine)) return {};
                const QJSValue projected = messageScriptCall(engine, parse, outer, {serialized});
                if (!messageScriptReady(engine)) return {};
                const QJSValue isArray = messageScriptArray(engine, projected);
                if (!messageScriptReady(engine)) return {};
                if (!isArray.toBool()) return {};
                const QJSValue lengthValue = read(projected, "length");
                if (!messageScriptReady(engine)) return {};
                if (!lengthValue.isNumber()) return {};
                const quint32 length = lengthValue.toUInt();
                QStringList values;
                for (quint32 i = 0; i < length; ++i) {
                    const QJSValue value = messageScriptIndex(engine, projected, i);
                    if (!messageScriptReady(engine)) return {};
                    if (!value.isString()) return {};
                    values.append(value.toString());
                }
                input.queries = std::move(values);
            }
        }
    }
    if (input.kind == WebActionKind::Missing || input.kind == WebActionKind::Search) {
        const auto query = webSearchQuery(input);
        if (query && query->isEmpty()) {
            input.fallbackQuery = text(read(payload, "query"));
            if (!messageScriptReady(engine)) return {};
        }
    } else if (input.kind == WebActionKind::OpenPage || input.kind == WebActionKind::FindInPage) {
        input.url = text(read(action, "url"));
        if (!messageScriptReady(engine)) return {};
        if (input.kind == WebActionKind::FindInPage) {
            input.pattern = text(read(action, "pattern"));
            if (!messageScriptReady(engine)) return {};
        }
    }
    if (!messageScriptReady(engine)) return {};
    const QString caption = presentWebSearch(input);
    return messageScriptReady(engine) ? caption : QString();
}

namespace {
void messageScriptWrite(const QPointer<QJSEngine>& engine, const QJSValue& source,
                        const QString& name, const QJSValue& value) {
    if (!messageScriptReady(engine)) return;
    QJSManagedValue target(source, engine.data());
    if (target.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Message value belongs to another engine"));
        return;
    }
    target.setProperty(name, value);
}
struct MessageView {
    QPointer<QJSEngine> engine;
    QPointer<QQuickItem> item;
    QPointer<edi_app::AssistantViewModel> owner;
    QJSValue component, ownerValue, payload;
    QString id, kind, status, text, identity;
    bool lifetime() const {
        return messageScriptReady(engine) && item && QThread::currentThread() == engine->thread() &&
            QThread::currentThread() == item->thread() &&
            (ownerValue.isNull() || (owner && owner->thread() == QThread::currentThread()));
    }
    bool current() const {
        if (!lifetime()) return false;
        for (const auto& field : {std::pair{QStringLiteral("rowId"), id}, std::pair{QStringLiteral("kind"), kind},
             std::pair{QStringLiteral("status"), status}, std::pair{QStringLiteral("text"), text},
             std::pair{QStringLiteral("disclosureIdentity"), identity}}) {
            const auto value = messageScriptProperty(engine, component, field.first);
            if (!lifetime() || !value.isString() || value.toString() != field.second) return false;
        }
        const auto originalPayload = messageScriptProperty(engine, component, QStringLiteral("payload"));
        if (!lifetime() || !originalPayload.strictlyEquals(payload)) return false;
        const auto originalOwner = messageScriptProperty(engine, component, QStringLiteral("assistant"));
        return lifetime() && originalOwner.strictlyEquals(ownerValue);
    }
};
std::optional<MessageView> captureMessageView(const QPointer<QJSEngine>& engine, const QJSValue& component) {
    if (!messageScriptReady(engine) || QThread::currentThread() != engine->thread()) return std::nullopt;
    MessageView view;
    view.engine = engine; view.component = component;
    view.item = qobject_cast<QQuickItem*>(component.toQObject());
    if (!view.item || QThread::currentThread() != view.item->thread()) return std::nullopt;
    for (auto field : {std::pair{QStringLiteral("rowId"), &view.id}, std::pair{QStringLiteral("kind"), &view.kind},
         std::pair{QStringLiteral("status"), &view.status}, std::pair{QStringLiteral("text"), &view.text},
         std::pair{QStringLiteral("disclosureIdentity"), &view.identity}}) {
        const auto value = messageScriptProperty(engine, component, field.first);
        if (!messageScriptReady(engine) || !view.item || !value.isString()) return std::nullopt;
        *field.second = value.toString();
    }
    view.ownerValue = messageScriptProperty(engine, component, QStringLiteral("assistant"));
    if (!messageScriptReady(engine) || !view.item) return std::nullopt;
    view.owner = qobject_cast<edi_app::AssistantViewModel*>(view.ownerValue.toQObject());
    if (!view.ownerValue.isNull() && !view.owner) return std::nullopt;
    view.payload = messageScriptProperty(engine, component, QStringLiteral("payload"));
    if (!view.lifetime()) return std::nullopt;
    return view.current() ? std::optional<MessageView>(view) : std::nullopt;
}
QJSValue messageChild(const MessageView& view, const char* alias) {
    if (!view.current()) return {};
    const auto child = messageScriptProperty(view.engine, view.component, QString::fromLatin1(alias));
    const QPointer<QObject> alive(child.toQObject());
    return view.current() && alive && alive->thread() == QThread::currentThread() ? child : QJSValue();
}
bool invokeMessageChild(const MessageView& view, const QJSValue& child, const char* method) {
    const QPointer<QObject> alive(child.toQObject());
    if (!view.current() || !alive) return false;
    const auto function = messageScriptProperty(view.engine, child, QString::fromLatin1(method));
    if (!view.current() || !alive) return false;
    messageScriptCall(view.engine, function, child, {});
    return view.current() && alive;
}
bool clearMessageFeedback(const MessageView& view, bool stopTimer) {
    if (!view.current()) return false;
    messageScriptWrite(view.engine, view.component, QStringLiteral("technicalCopied"), QJSValue(false));
    if (!view.current()) return false;
    if (!stopTimer) return true;
    const auto timer = messageChild(view, "detailsFeedback");
    return !timer.isQObject() ? view.current() : invokeMessageChild(view, timer, "stop");
}
void showMessageFeedback(const MessageView& view) {
    if (!view.current()) return;
    messageScriptWrite(view.engine, view.component, QStringLiteral("technicalCopied"), QJSValue(true));
    if (!view.current()) return;
    const auto timer = messageChild(view, "detailsFeedback");
    if (timer.isQObject()) invokeMessageChild(view, timer, "restart");
}
void copyMessageLiteral(const QPointer<const ApplicationInfo>& actor, const MessageView& view,
                        const QString& literal) {
    if (!messageScriptReady(view.engine)) return;
    bool failed = false;
    try {
        const auto copy = [&] {
            if (!actor || !view.current()) return;
            actor->copyText(literal);
            if (!actor || !view.current()) return;
            showMessageFeedback(view);
        };
        copy();
    } catch (...) { failed = true; }
    // This is the original copy operation's explicit catch, not the formatter boundary.
    if (view.engine && view.engine->hasError()) {
        view.engine->catchError();
        failed = true;
    }
    if (failed && view.current())
        messageScriptWrite(view.engine, view.component, QStringLiteral("technicalCopied"), QJSValue(false));
}
using HumanSnapshot = edi_app::assistant_presentation::HumanActivitySnapshot;
HumanSnapshot snapshotFrom(const edi_app::AssistantViewModel::PreparedActivityRead& detail) {
    return {detail.payload, detail.text.toString(), detail.provenance, detail.rowId, detail.kind, detail.status};
}
std::optional<edi_app::assistant_presentation::HumanActivityInput> prepareHumanPresentation(
    const QPointer<QJSEngine>& engine, const HumanSnapshot& snapshot, const QString& kind,
    const QJSValue& compact, const QJSValue& payload, const QPointer<edi_app::AssistantViewModel>& owner) {
    using namespace edi_app::assistant_presentation;
    if (!messageScriptReady(engine)) return std::nullopt;
    HumanActivityInput input;
    input.kind = kind; input.payload = snapshot.payload; input.text = snapshot.text; input.provenance = snapshot.provenance;
    const auto caption = messageScriptProperty(engine, compact, QStringLiteral("caption"));
    if (!messageScriptReady(engine) || !caption.isString()) return std::nullopt;
    input.caption = caption.toString();
    const auto command = messageScriptProperty(engine, compact, QStringLiteral("commandActivity"));
    if (!messageScriptReady(engine) || !command.isBool()) return std::nullopt;
    input.commandActivity = command.toBool();
    const auto decision = messageScriptProperty(engine, compact, QStringLiteral("decisionActivity"));
    if (!messageScriptReady(engine) || !decision.isBool()) return std::nullopt;
    input.decisionActivity = decision.toBool();
    if (nativeDescriptionPlaceholder(input)) {
        input.nativeLabel = messageNativeCaption(engine, payload, owner);
        if (!messageScriptReady(engine) || !input.nativeLabel) return std::nullopt;
    }
    const auto lines = humanDescriptionLines(input);
    if (needsHumanFallback(input, lines) && input.payload.value("type") == "dynamicToolCall" && owner)
        input.nativeDescription = owner->nativeActionDescription(input.payload.value("tool").toString(), QString());
    if (!nonblankLiteral(humanOutcomeMessage(input)) && humanOutcomeCode(input) == "project_required" && owner)
        input.nativeErrorDescription = owner->nativeActionDescription(input.payload.value("tool").toString(), QStringLiteral("project_required"));
    return messageScriptReady(engine) ? std::optional<HumanActivityInput>(std::move(input)) : std::nullopt;
}
void clearHumanSnapshot(const MessageView& view) {
    if (view.current()) messageScriptWrite(view.engine, view.component,
        QStringLiteral("humanDetailsSnapshot"), QJSValue(QJSValue::NullValue));
}
void refreshHumanSnapshot(const MessageView& view) {
    QJSValue snapshot(QJSValue::NullValue);
    if (view.owner) {
        const auto detail = view.owner->prepareActivityRead(view.id, view.kind, view.status, false);
        if (!view.current()) return;
        if (detail.current) snapshot = view.engine->toScriptValue(QVariant::fromValue(snapshotFrom(detail)));
    }
    if (!view.current()) return;
    const auto disclosure = messageChild(view, "detailsDisclosure");
    if (!disclosure.isQObject()) return;
    const auto checked = messageScriptProperty(view.engine, disclosure, QStringLiteral("checked"));
    if (!view.current() || !checked.toBool()) return;
    messageScriptWrite(view.engine, view.component, QStringLiteral("humanDetailsSnapshot"), snapshot);
}
void refreshExpandedHumanSnapshot(const MessageView& view) {
    const auto disclosure = messageChild(view, "detailsDisclosure");
    if (!disclosure.isQObject()) return;
    const auto checked = messageScriptProperty(view.engine, disclosure, QStringLiteral("checked"));
    if (view.current() && checked.toBool()) refreshHumanSnapshot(view);
}
} // namespace

QString ApplicationInfo::assistantActivityDescription(const QJSValue& snapshot, const QString& kind,
    const QJSValue& compact, const QJSValue& payload, QObject* assistant) const {
    using namespace edi_app::assistant_presentation;
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(engine.data())) qml->markCurrentFunctionAsTranslationBinding();
    const auto unavailable = [] { return messageText(
        QT_TRANSLATE_NOOP("AssistantMessage", "This step's description is currently unavailable.")); };
    try {
        // Retain JavaScript objects without traversing them; accept only the exact native snapshot below.
        const auto value = snapshot.toVariant(QJSValue::RetainJSObjects);
        if (value.metaType() != QMetaType::fromType<HumanSnapshot>()) return unavailable();
        const auto input = prepareHumanPresentation(engine, value.value<HumanSnapshot>(), kind, compact, payload,
            qobject_cast<edi_app::AssistantViewModel*>(assistant));
        return input ? fullHumanDescription(*input, humanDescriptionLines(*input)) : unavailable();
    } catch (...) { return unavailable(); }
}

void ApplicationInfo::assistantCopyActivity(const QJSValue& component, bool includeTechnical, bool offered) const {
    if (!offered) return;
    const QPointer<const ApplicationInfo> actor(this);
    const QPointer<QJSEngine> engine(qjsEngine(this));
    try {
        const auto view = captureMessageView(engine, component);
        if (!view || !view->owner) return;
        const auto detail = view->owner->prepareActivityRead(view->id, view->kind, view->status, false);
        if (!detail.current || !view->current()) return;
        const auto compact = messageScriptProperty(engine, component, QStringLiteral("compactPresentation"));
        if (!messageScriptReady(engine)) return;
        const auto input = prepareHumanPresentation(engine, snapshotFrom(detail), view->kind, compact, view->payload, view->owner);
        if (!input) return;
        const auto full = edi_app::assistant_presentation::fullHumanDescription(*input,
            edi_app::assistant_presentation::humanDescriptionLines(*input));
        QString literal = edi_app::assistant_presentation::humanCopyText(input->caption, full);
        if (includeTechnical) {
            const auto technical = view->owner->prepareActivityRead(view->id, view->kind, view->status, true);
            if (!technical.current || technical.technical.isEmpty() || !view->current()) return;
            literal += QStringLiteral("\n\n") + technical.technical;
        }
        copyMessageLiteral(actor, *view, literal);
    } catch (...) {}
}

void ApplicationInfo::assistantCopyUserText(const QJSValue& component, bool offered) const {
    if (!offered) return;
    const QPointer<const ApplicationInfo> actor(this);
    const QPointer<QJSEngine> engine(qjsEngine(this));
    try {
        const auto view = captureMessageView(engine, component);
        if (!view || view->kind != "user" || view->status != "completed" || !view->current() || !actor) return;
        copyMessageLiteral(actor, *view, view->text);
    } catch (...) {}
}

void ApplicationInfo::assistantMessageChanged(const QJSValue& component, const QString& cause) const {
    try {
        const auto view = captureMessageView(qjsEngine(this), component);
        if (!view) return;
        if (cause == "text") { clearMessageFeedback(*view, true); return; }
        if (cause == "payload") {
            messageScriptWrite(view->engine, view->component, QStringLiteral("technicalCopied"), QJSValue(false));
            if (!view->current()) return;
        }
        if (cause != "payload" && cause != "status") return;
        clearHumanSnapshot(*view);
        if (!view->current()) return;
        if (cause == "payload") {
            const auto timer = messageChild(*view, "detailsFeedback");
            if (timer.isQObject() && !invokeMessageChild(*view, timer, "stop")) return;
        }
        if (view->current()) refreshExpandedHumanSnapshot(*view);
    } catch (...) {}
}

void ApplicationInfo::assistantMessageDisclosureChanged(const QJSValue& component, bool checked) const {
    try {
        const auto view = captureMessageView(qjsEngine(this), component);
        if (!view) return;
        if (checked) refreshHumanSnapshot(*view);
        else clearHumanSnapshot(*view);
    } catch (...) {}
}

void ApplicationInfo::assistantMessageClearFeedback(const QJSValue& component, bool stopTimer) const {
    try {
        const auto view = captureMessageView(qjsEngine(this), component);
        if (view) clearMessageFeedback(*view, stopTimer);
    } catch (...) {}
}

void ApplicationInfo::assistantMessageReset(const QJSValue& component) const {
    try {
        const auto view = captureMessageView(qjsEngine(this), component);
        if (!view) return;
        messageScriptWrite(view->engine, view->component, QStringLiteral("technicalCopied"), QJSValue(false));
        if (!view->current()) return;
        clearHumanSnapshot(*view);
        if (!view->current()) return;
        const auto timer = messageChild(*view, "detailsFeedback");
        if (timer.isQObject() && !invokeMessageChild(*view, timer, "stop")) return;
        if (!view->current()) return;
        const auto disclosure = messageChild(*view, "detailsDisclosure");
        const QPointer<QObject> control(disclosure.toQObject());
        if (control) {
            messageScriptWrite(view->engine, disclosure, QStringLiteral("checked"), QJSValue(false));
            if (!view->current() || !control) return;
        }
        for (const auto* alias : {"detailsBody", "detailsEditor"}) {
            const auto editor = messageChild(*view, alias);
            if (editor.isQObject() && !invokeMessageChild(*view, editor, "deselect")) return;
            if (!view->current()) return;
        }
    } catch (...) {}
}

void ApplicationInfo::copyText(const QString& text) const { QGuiApplication::clipboard()->setText(text); }
namespace {
struct SessionBrowserFrame {
    QPointer<QJSEngine> engine;
    QPointer<QObject> panel;
    QJSValue view;
    bool live() const {
        return engine && !engine->hasError() && panel && QThread::currentThread() == engine->thread() &&
            panel->thread() == QThread::currentThread();
    }
};
std::optional<SessionBrowserFrame> sessionBrowserFrame(QObject* panel) {
    if (!panel || panel->thread() != QThread::currentThread()) return std::nullopt;
    SessionBrowserFrame frame;
    frame.engine = qjsEngine(panel); frame.panel = panel;
    if (!frame.live()) return std::nullopt;
    frame.view = frame.engine->newQObject(panel);
    return frame.live() ? std::optional<SessionBrowserFrame>(frame) : std::nullopt;
}
QJSValue sessionBrowserObject(const SessionBrowserFrame& frame, QObject* object) {
    if (!frame.live()) return {};
    if (!object) return QJSValue(QJSValue::NullValue);
    if (object->thread() != QThread::currentThread()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Session browser control belongs to another thread"));
        return {};
    }
    return frame.engine->newQObject(object);
}
QJSValue sessionBrowserRead(const SessionBrowserFrame& frame, const QJSValue& source, const char* name) {
    if (!frame.live()) return {};
    const QJSManagedValue value(source, frame.engine.data());
    if (value.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Session browser value belongs to another engine"));
        return {};
    }
    return value.property(QString::fromLatin1(name));
}
QJSValue sessionBrowserCall(const SessionBrowserFrame& frame, const QJSValue& function,
                           const QJSValue& receiver, const QJSValueList& arguments = {}) {
    if (!frame.live()) return {};
    const QJSManagedValue callable(function, frame.engine.data());
    const QJSManagedValue instance(receiver, frame.engine.data());
    if (callable.engine() != frame.engine.data() || instance.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Session browser value belongs to another engine"));
        return {};
    }
    for (const auto& argument : arguments) {
        const QJSManagedValue value(argument, frame.engine.data());
        if (value.engine() != frame.engine.data()) {
            frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Session browser value belongs to another engine"));
            return {};
        }
    }
    return callable.callWithInstance(receiver, arguments);
}
std::optional<double> sessionBrowserNumber(const SessionBrowserFrame& frame, const QJSValue& value) {
    if (!frame.live()) return std::nullopt;
    const QJSManagedValue number(value, frame.engine.data());
    if (number.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Session browser value belongs to another engine"));
        return std::nullopt;
    }
    const double result = number.toNumber();
    return frame.live() ? std::optional<double>(result) : std::nullopt;
}
} // namespace

void ApplicationInfo::openSessionBrowser(QObject* panel, QObject* dialog) const {
    const auto frame = sessionBrowserFrame(panel);
    if (!frame) return;
    const auto popup = sessionBrowserObject(*frame, dialog);
    const auto open = sessionBrowserRead(*frame, popup, "open");
    sessionBrowserCall(*frame, open, popup);
    if (!frame->live()) return;
    const auto owner = sessionBrowserRead(*frame, frame->view, "assistant");
    const auto refresh = sessionBrowserRead(*frame, owner, "refreshSessions");
    sessionBrowserCall(*frame, refresh, owner);
}
void ApplicationInfo::prefetchSessionBrowser(QObject* panel, QObject* dialog, QObject* table) const {
    const auto frame = sessionBrowserFrame(panel);
    if (!frame) return;
    const auto popup = sessionBrowserObject(*frame, dialog);
    const auto opened = sessionBrowserRead(*frame, popup, "opened");
    if (!frame->live() || !opened.toBool()) return;
    auto owner = sessionBrowserRead(*frame, frame->view, "assistant");
    const auto more = sessionBrowserRead(*frame, owner, "sessionsHaveMore");
    if (!frame->live() || !more.toBool()) return;
    owner = sessionBrowserRead(*frame, frame->view, "assistant");
    const auto loading = sessionBrowserRead(*frame, owner, "sessionsLoading");
    if (!frame->live() || loading.toBool()) return;
    const auto view = sessionBrowserObject(*frame, table);
    const auto position = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, view, "contentY"));
    if (!position) return;
    const auto firstHeight = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, view, "height"));
    if (!firstHeight) return;
    const auto content = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, view, "contentHeight"));
    if (!content) return;
    const auto secondHeight = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, view, "height"));
    if (!secondHeight || !(*position + *firstHeight >= *content - *secondHeight)) return;
    owner = sessionBrowserRead(*frame, frame->view, "assistant");
    const auto refresh = sessionBrowserRead(*frame, owner, "refreshSessions");
    sessionBrowserCall(*frame, refresh, owner, {QJSValue(true)});
}
void ApplicationInfo::activateSessionBrowserRow(QObject* panel, QObject* row) const {
    const auto frame = sessionBrowserFrame(panel);
    if (!frame) return;
    const auto item = sessionBrowserObject(*frame, row);
    const auto activated = sessionBrowserRead(*frame, item, "activated");
    sessionBrowserCall(*frame, activated, item);
    if (!frame->live()) return;
    const auto owner = sessionBrowserRead(*frame, frame->view, "assistant");
    const auto select = sessionBrowserRead(*frame, owner, "selectSession");
    if (!frame->live()) return;
    const auto id = sessionBrowserRead(*frame, item, "threadId");
    sessionBrowserCall(*frame, select, owner, {id});
}
qreal ApplicationInfo::sessionBrowserButtonsWidth(QObject* panel, QObject* buttons) const {
    const auto frame = sessionBrowserFrame(panel);
    if (!frame) return 0;
    const auto box = sessionBrowserObject(*frame, buttons);
    double total = 0;
    for (double index = 0; ; index += 1) {
        const auto count = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, box, "count"));
        if (!count) return 0;
        if (!(index < *count)) break;
        const auto itemAt = sessionBrowserRead(*frame, box, "itemAt");
        const auto button = sessionBrowserCall(*frame, itemAt, box, {QJSValue(index)});
        if (!frame->live()) return 0;
        if (!button.toBool()) continue;
        const auto visible = sessionBrowserRead(*frame, button, "visible");
        if (!frame->live()) return 0;
        if (!visible.toBool()) continue;
        const auto width = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, button, "implicitWidth"));
        if (!width) return 0;
        total += *width;
    }
    const auto math = sessionBrowserRead(*frame, frame->engine->globalObject(), "Math");
    const auto maximum = sessionBrowserRead(*frame, math, "max");
    if (!frame->live()) return 0;
    const auto count = sessionBrowserNumber(*frame, sessionBrowserRead(*frame, box, "count"));
    if (!count) return 0;
    const auto gaps = sessionBrowserCall(*frame, maximum, math, {QJSValue(0), QJSValue(*count - 1)});
    if (!frame->live()) return 0;
    const auto spacing = sessionBrowserRead(*frame, box, "spacing");
    const auto measuredGaps = sessionBrowserNumber(*frame, gaps);
    if (!measuredGaps) return 0;
    const auto measuredSpacing = sessionBrowserNumber(*frame, spacing);
    return measuredSpacing ? total + *measuredGaps * *measuredSpacing : 0;
}

QString ApplicationInfo::fileSizeKilobytes(qint64 bytes) const {
    if(bytes<0)return tr("Size unavailable");
    return tr("%1 KB").arg(QLocale().toString(static_cast<double>(bytes)/1000.0,'f',1));
}

namespace {
struct ComposerDraftFrame {
    QPointer<QJSEngine> engine;
    QPointer<QObject> composer, editor;
    bool hasEditor = false;
    QJSValue view, edit;
    bool live() const {
        return engine && !engine->hasError() && composer && (!hasEditor || editor) &&
            QThread::currentThread() == engine->thread() && composer->thread() == QThread::currentThread() &&
            (!hasEditor || editor->thread() == QThread::currentThread());
    }
};
std::optional<ComposerDraftFrame> composerDraftFrame(QObject* composer, QObject* editor = nullptr) {
    if (!composer || composer->thread() != QThread::currentThread()) return std::nullopt;
    ComposerDraftFrame frame;
    frame.engine = qjsEngine(composer); frame.composer = composer; frame.editor = editor; frame.hasEditor = editor != nullptr;
    if (!frame.live()) return std::nullopt;
    frame.view = frame.engine->newQObject(composer);
    if (editor) frame.edit = frame.engine->newQObject(editor);
    return frame.live() ? std::optional<ComposerDraftFrame>(frame) : std::nullopt;
}
QJSValue composerDraftRead(const ComposerDraftFrame& frame, const QJSValue& source, const char* name) {
    if (!frame.live()) return {};
    const QJSManagedValue value(source, frame.engine.data());
    if (value.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Composer value belongs to another engine"));
        return {};
    }
    return value.property(QString::fromLatin1(name));
}
void composerDraftWrite(const ComposerDraftFrame& frame, const QJSValue& source, const char* name, const QJSValue& value) {
    if (!frame.live()) return;
    QJSManagedValue target(source, frame.engine.data());
    if (target.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Composer value belongs to another engine"));
        return;
    }
    target.setProperty(QString::fromLatin1(name), value);
}
void composerDraftCall(const ComposerDraftFrame& frame, const QJSValue& source, const char* name) {
    const auto method = composerDraftRead(frame, source, name);
    if (!frame.live()) return;
    const QJSManagedValue function(method, frame.engine.data());
    const QJSManagedValue receiver(source, frame.engine.data());
    if (function.engine() != frame.engine.data() || receiver.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Composer value belongs to another engine"));
        return;
    }
    function.callWithInstance(source);
}
struct ComposerDraftLiteral { QJSValue value, prototype; };
ComposerDraftLiteral composerDraftLiteral(const ComposerDraftFrame& frame) {
    ComposerDraftLiteral literal;
    if (!frame.live()) return literal;
    literal.value = frame.engine->newObject();
    QJSManagedValue object(literal.value, frame.engine.data());
    literal.prototype = object.prototype().toJSValue();
    const QJSManagedValue none(QJSValue(QJSValue::NullValue), frame.engine.data());
    // Object literals define own data fields without inherited setters (ADR-0056).
    object.setPrototype(none);
    return literal;
}
QJSValue completeComposerDraftLiteral(const ComposerDraftFrame& frame, const ComposerDraftLiteral& literal) {
    if (!frame.live()) return {};
    QJSManagedValue object(literal.value, frame.engine.data());
    const QJSManagedValue prototype(literal.prototype, frame.engine.data());
    object.setPrototype(prototype);
    return frame.live() ? literal.value : QJSValue();
}
void captureComposerDraft(const ComposerDraftFrame& frame, const char* property, const char* key, const QString& identity) {
    if (!frame.live()) return;
    const auto literal = composerDraftLiteral(frame);
    composerDraftWrite(frame, literal.value, key, QJSValue(identity));
    const auto text = composerDraftRead(frame, frame.edit, "text");
    if (!frame.live()) return;
    composerDraftWrite(frame, literal.value, "text", text);
    const auto revision = composerDraftRead(frame, frame.view, "textRevision");
    if (!frame.live()) return;
    composerDraftWrite(frame, literal.value, "revision", revision);
    const auto value = completeComposerDraftLiteral(frame, literal);
    if (frame.live()) composerDraftWrite(frame, frame.view, property, value);
}
bool composerDraftEditorIdle(const ComposerDraftFrame& frame) {
    const auto composing = composerDraftRead(frame, frame.edit, "inputMethodComposing");
    if (!frame.live() || composing.toBool()) return false;
    const auto preedit = composerDraftRead(frame, frame.edit, "preeditText");
    if (!frame.live()) return false;
    const auto length = composerDraftRead(frame, preedit, "length");
    return frame.live() && !length.toBool();
}
bool composerDraftFieldEqual(const ComposerDraftFrame& frame, const QJSValue& captured, const char* field,
                            const QJSValue& current, const char* currentField) {
    const auto before = composerDraftRead(frame, captured, field);
    if (!frame.live()) return false;
    const auto after = composerDraftRead(frame, current, currentField);
    return frame.live() && before.strictlyEquals(after);
}
void publishComposerDraft(const ComposerDraftFrame& frame) {
    const auto owner = composerDraftRead(frame, frame.view, "assistant");
    if (!frame.live()) return;
    const auto text = composerDraftRead(frame, frame.edit, "text");
    if (frame.live()) composerDraftWrite(frame, owner, "sessionDraft", text);
}
void incrementComposerDraftRevision(const ComposerDraftFrame& frame, const char* property) {
    const auto revision = composerDraftRead(frame, frame.view, property);
    if (!frame.live()) return;
    const QJSManagedValue number(revision, frame.engine.data());
    if (number.engine() != frame.engine.data()) {
        frame.engine->throwError(QJSValue::TypeError, QStringLiteral("Composer value belongs to another engine"));
        return;
    }
    const double next = number.toNumber() + 1;
    if (frame.live()) composerDraftWrite(frame, frame.view, property, QJSValue(next));
}
} // namespace

void ApplicationInfo::composerSessionSelectionStarted(QObject* composer, QObject* editor, const QString& threadId) const {
    const auto frame = composerDraftFrame(composer, editor);
    if (frame) captureComposerDraft(*frame, "sessionDraftIntent", "id", threadId);
}
void ApplicationInfo::composerSessionDraftRestored(QObject* composer, QObject* editor,
                                                     const QString& threadId, const QString& text) const {
    const auto frame = composerDraftFrame(composer, editor);
    if (!frame) return;
    const auto original = composerDraftRead(*frame, frame->view, "sessionDraftIntent");
    if (!frame->live()) return;
    composerDraftWrite(*frame, frame->view, "sessionDraftIntent", QJSValue(QJSValue::NullValue));
    if (!frame->live()) return;
    bool restore = !original.toBool();
    if (!restore) {
        const auto id = composerDraftRead(*frame, original, "id");
        if (!frame->live()) return;
        restore = id.strictlyEquals(QJSValue(threadId)) &&
            composerDraftFieldEqual(*frame, original, "text", frame->edit, "text") &&
            composerDraftFieldEqual(*frame, original, "revision", frame->view, "textRevision");
    }
    if (restore && composerDraftEditorIdle(*frame)) composerDraftWrite(*frame, frame->edit, "text", QJSValue(text));
    if (frame->live()) publishComposerDraft(*frame);
}
void ApplicationInfo::composerConversationClearRequested(QObject* composer, QObject* editor, const QString& intent) const {
    const auto frame = composerDraftFrame(composer, editor);
    if (frame) captureComposerDraft(*frame, "clearDraft", "intent", intent);
}
void ApplicationInfo::composerConversationClearCommitted(QObject* composer, QObject* editor, const QString& intent) const {
    const auto frame = composerDraftFrame(composer, editor);
    if (!frame) return;
    const auto original = composerDraftRead(*frame, frame->view, "clearDraft");
    if (!frame->live() || !original.toBool()) return;
    const auto key = composerDraftRead(*frame, original, "intent");
    if (!frame->live() || !key.strictlyEquals(QJSValue(intent))) return;
    composerDraftWrite(*frame, frame->view, "clearDraft", QJSValue(QJSValue::NullValue));
    if (composerDraftFieldEqual(*frame, original, "revision", frame->view, "textRevision") &&
        composerDraftFieldEqual(*frame, original, "text", frame->edit, "text") && composerDraftEditorIdle(*frame))
        composerDraftCall(*frame, frame->edit, "clear");
}
void ApplicationInfo::composerConversationRetired(QObject* composer) const {
    const auto frame = composerDraftFrame(composer);
    if (!frame) return;
    incrementComposerDraftRevision(*frame, "draftOwnerRevision");
    if (!frame->live()) return;
    composerDraftWrite(*frame, frame->view, "submittedDrafts", frame->engine->newArray());
    if (frame->live()) composerDraftWrite(*frame, frame->view, "workReportDraft", QJSValue(QJSValue::NullValue));
}
void ApplicationInfo::composerDraftEdited(QObject* composer, QObject* editor, bool publishText) const {
    const auto frame = composerDraftFrame(composer, editor);
    if (!frame) return;
    incrementComposerDraftRevision(*frame, "textRevision");
    if (publishText && frame->live()) publishComposerDraft(*frame);
}

void ApplicationInfo::composerRefreshFilePresentation(QObject* composer, bool advanceRevision) const {
    const auto frame = composerDraftFrame(composer);
    if (!frame) return;
    if (advanceRevision) incrementComposerDraftRevision(*frame, "consentFileRevision");
    double pending = 0;
    for (double index = 0; frame->live(); index += 1) {
        const auto owner = composerDraftRead(*frame, frame->view, "assistant");
        const auto files = composerDraftRead(*frame, owner, "selectedFiles");
        const auto count = composerDraftRead(*frame, files, "count");
        if (!frame->live()) return;
        const QJSManagedValue numericCount(count, frame->engine.data());
        if (numericCount.engine() != frame->engine.data()) {
            frame->engine->throwError(QJSValue::TypeError, QStringLiteral("Composer value belongs to another engine"));
            return;
        }
        const double limit = numericCount.toNumber();
        if (!frame->live()) return;
        if (!(index < limit)) break;
        const auto currentOwner = composerDraftRead(*frame, frame->view, "assistant");
        const auto currentFiles = composerDraftRead(*frame, currentOwner, "selectedFiles");
        const auto text = composerDraftRead(*frame, currentFiles, "text");
        if (!frame->live()) return;
        const auto marker = messageScriptCall(frame->engine, text, currentFiles,
                                             {QJSValue(index), QJSValue(QStringLiteral("pending"))});
        if (!frame->live()) return;
        if (!marker.strictlyEquals(QJSValue(QStringLiteral("false")))) pending += 1;
    }
    if (frame->live()) composerDraftWrite(*frame, frame->view, "pendingFileCount", QJSValue(pending));
}

bool ApplicationInfo::engineThreadsSelectable() const {
    return std::string_view(edi::engine_threading().backend) != "serial";
}

int ApplicationInfo::engineThreadsMaximum() const { return std::clamp(2 * QThread::idealThreadCount(), 16, 64); }

void ApplicationInfo::setEngineThreads(int count) const { edi::set_engine_threads(count); }

void ApplicationInfo::storeSettings() const { edi_app::store_settings_now(); }

void ApplicationInfo::assistantToolbarActivated(const QJSValue& window, const QJSValue& toggle,
                                                const QJSValue& panel, const QJSValue& session,
                                                const QJSValue& preferences, const QJSValue& desktopOnlyDialog) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine)) return;
    const auto read = [&](const QJSValue& source, const char* name) {
        return messageScriptProperty(engine, source, QString::fromLatin1(name));
    };
    const auto write = [&](const QJSValue& target, const char* name, const QJSValue& value) {
        messageScriptWrite(engine, target, QString::fromLatin1(name), value);
        return messageScriptReady(engine);
    };
    const auto call = [&](const QJSValue& target, const char* name, const QJSValueList& arguments = QJSValueList()) {
        const auto method = read(target, name);
        return messageScriptCall(engine, method, target, arguments);
    };
    if (!assistantAvailable()) {
        call(desktopOnlyDialog, "open");
        return;
    }
    const auto enabled = read(toggle, "enabled");
    if (!messageScriptReady(engine) || !enabled.toBool()) return;
    const auto shown = read(panel, "shown");
    if (!messageScriptReady(engine)) return;
    const bool show = !shown.toBool();
    if (!show) {
        const auto owner = read(session, "assistant");
        call(owner, "dismissChatReveal");
        if (!messageScriptReady(engine)) return;
    }
    if (show) {
        const auto owner = read(session, "assistant");
        const auto accepted = call(owner, "requestAssistantPane", {toggle});
        if (!messageScriptReady(engine) || !accepted.toBool()) return;
    }
    if (show) {
        const auto takeover = read(window, "assistantManualTakeover");
        if (!messageScriptReady(engine)) return;
        if (takeover.toBool()) {
            if (!write(window, "assistantManualTakeoverProject", QJSValue(QJSValue::NullValue))) return;
            if (!write(window, "assistantEmptyManualTakeover", QJSValue(false))) return;
        }
        const auto epoch = read(window, "assistantFocusEpoch");
        if (!messageScriptReady(engine)) return;
        if (!write(window, "assistantFocusEpoch", QJSValue(epoch.toNumber() + 1))) return;
        const auto focus = read(window, "activeFocusItem");
        if (!messageScriptReady(engine) || !write(window, "assistantPreviousFocus", focus)) return;
        const auto page = read(window, "assistantCurrentPage");
        if (!messageScriptReady(engine) || !write(window, "assistantPreviousPage", page)) return;
        const auto host = read(window, "activeAssistantHost");
        if (!messageScriptReady(engine) || !write(window, "assistantPreviousHost", host)) return;
        const auto project = read(session, "project");
        if (!messageScriptReady(engine) || !write(window, "assistantPreviousProject", project)) return;
    }
    bool manualPane = false;
    if (show) {
        const auto owner = read(session, "assistant");
        const auto actions = read(owner, "showingActions");
        if (!messageScriptReady(engine)) return;
        manualPane = actions.toBool();
    }
    if (!write(window, "assistantManualPane", QJSValue(manualPane))) return;
    write(preferences, "assistantShown", QJSValue(show));
}
