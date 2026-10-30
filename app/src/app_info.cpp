// SPDX-License-Identifier: BSD-3-Clause
#include "app_info.hpp"
#include "assistant_message_presentation.hpp"
#include "assistant_panel_presentation.hpp"
#include "assistant_view_model.hpp"
#include "web_files.hpp"

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
#include <functional>
#include <optional>
#include <string_view>

#ifndef Q_OS_WASM
#include <private/qjsengine_p.h>
#include <private/qjsvalue_p.h>
#include <private/qqmlcontextdata_p.h>
#include <private/qqmlengine_p.h>
#include <private/qqmljavascriptexpression_p.h>
#include <private/qv4functionobject_p.h>
#include <private/qv4jscall_p.h>
#include <private/qv4lookup_p.h>
#include <private/qv4mm_p.h>
#include <private/qv4proxy_p.h>
#include <private/qv4qmlcontext_p.h>
#include <private/qv4qobjectwrapper_p.h>
#include <private/qv4runtime_p.h>
#include <private/qv4runtimeapi_p.h>
#include <private/qv4scopedvalue_p.h>
#include <private/qv4stackframe_p.h>
#include <private/qv4string_p.h>
#include <private/qqmljsast_p.h>
#endif

#ifdef _OPENMP
#include <omp.h>
#endif
#ifdef Q_OS_WASM
#include <emscripten/val.h>
#endif

#ifndef Q_OS_WASM
namespace QV4 {
namespace Heap {
#define AssistantPanelCallbackMembers(class, Member) \
    Member(class, Pointer, QmlContext*, context) \
    Member(class, NoMark, uint, operation)
DECLARE_HEAP_OBJECT(AssistantPanelCallback, FunctionObject) {
    DECLARE_MARKOBJECTS(AssistantPanelCallback)
    QV4QPointer<QObject> panel;
    void init(QV4::ExecutionEngine* engine, QV4::QmlContext* captured, uint kind, QObject* owner) {
        FunctionObject::init(engine, QString());
        context.set(engine, captured ? captured->d() : nullptr);
        panel.init(owner);
        operation = kind;
    }
    void destroy() { panel.destroy(); Object::destroy(); }
};
}
struct AssistantPanelCallback : FunctionObject {
    V4_OBJECT2(AssistantPanelCallback, FunctionObject)
    V4_NEEDS_DESTROY
    static ReturnedValue virtualCall(const FunctionObject*, const Value*, const Value*, int);
};
DEFINE_OBJECT_VTABLE(AssistantPanelCallback);
}
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
        const auto file = files.isString() ? messageScriptIndex(engine, files, static_cast<quint32>(index))
                                           : messageScriptProperty(engine, files, QJSPrimitiveValue(index).toString());
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

#ifndef Q_OS_WASM
namespace {
struct PanelUsageFrame {
    QPointer<QJSEngine> pointer;
    QQmlRefPointer<QQmlContextData> context;
    mutable bool interrupted = false;
    explicit PanelUsageFrame(QJSEngine* engine = nullptr,
                             QQmlRefPointer<QQmlContextData> captured = {}) : pointer(engine), context(std::move(captured)) {
        if (pointer) {
            auto* vm = QJSEnginePrivate::get(pointer.data())->v4Engine.get();
            if (!context) context = vm->callingQmlContext();
            interrupted = vm->isInterrupted.loadRelaxed();
        }
    }
    QJSEngine* data() const { return pointer.data(); }
    QJSEngine* operator->() const { return pointer.data(); }
    operator const QPointer<QJSEngine>&() const { return pointer; }
    explicit operator bool() const { return !pointer.isNull(); }
    QV4::ExecutionEngine* vm() const { return pointer ? QJSEnginePrivate::get(pointer.data())->v4Engine.get() : nullptr; }
    void checked() const { if (pointer && vm()->isInterrupted.loadRelaxed()) interrupted = true; }
};
bool panelUsageReady(const PanelUsageFrame& frame) {
    return messageScriptReady(frame.pointer) && !frame.interrupted;
}
PanelUsageFrame panelUsageEngine(const ApplicationInfo* actor) {
    QJSEngine* engine = qjsEngine(actor);
    return PanelUsageFrame(engine && engine->thread() == QThread::currentThread() ? engine : nullptr);
}
QV4::ReturnedValue panelUsageGet(const PanelUsageFrame& frame, const QV4::Value& value,
                               QV4::String* name, bool forCall = false) {
    auto* vm = frame.vm();
    QV4::Scope scope(vm);
    if (value.isNullOrUndefined())
        return vm->throwTypeError(QStringLiteral("Cannot read property '%1' of %2")
            .arg(name->toQString(), value.toQStringNoThrow()));
    if (const auto* object = value.as<QV4::Object>()) {
        if (const auto* wrapper = object->as<QV4::QObjectWrapper>()) {
            const auto flags = QV4::QObjectWrapper::Flags(QV4::QObjectWrapper::IncludeImports
                | (forCall ? QV4::QObjectWrapper::NoFlag : QV4::QObjectWrapper::AttachMethods));
            return wrapper->getQmlProperty(frame.context, name, flags, nullptr);
        }
        if (!object->as<QV4::ProxyObject>()
            && object->vtable()->resolveLookupGetter == QV4::Object::virtualResolveLookupGetter) {
            const auto index = object->internalClass()->findValueOrGetter(name->toPropertyKey());
            if (index.isValid()) return QV4::Object::getValue(&value, *object->d()->propertyData(index.index), index.attrs);
            QV4::Lookup lookup{};
            lookup.resolveProtoGetter(name->toPropertyKey(), object->d()->prototype());
            if (lookup.call == QV4::Lookup::Call::GetterProto) return lookup.protoLookup.data->asReturnedValue();
            if (lookup.call == QV4::Lookup::Call::GetterProtoAccessor) {
                QV4::ScopedValue getter(scope, *lookup.protoLookup.data);
                const auto* function = getter->as<QV4::FunctionObject>();
                return function ? function->call(&value, nullptr, 0) : QV4::Encode::undefined();
            }
        }
        return object->get(name, nullptr, &value);
    }
    if (value.isString() && name->toQString() == QStringLiteral("length"))
        return QV4::Encode(int(value.toQStringNoThrow().size()));
    QV4::ScopedObject prototype(scope);
    if (value.isBoolean()) prototype = vm->booleanPrototype();
    else if (value.isNumber()) prototype = vm->numberPrototype();
    else prototype = static_cast<const QV4::Managed&>(value).internalClass()->prototype;
    QV4::Lookup lookup{};
    lookup.resolveProtoGetter(name->toPropertyKey(), prototype->d());
    if (lookup.call == QV4::Lookup::Call::GetterProto)
        return lookup.protoLookup.data->asReturnedValue();
    if (lookup.call == QV4::Lookup::Call::GetterProtoAccessor) {
        QV4::ScopedValue getter(scope, *lookup.protoLookup.data);
        const auto* function = getter->as<QV4::FunctionObject>();
        return function ? function->call(&value, nullptr, 0) : QV4::Encode::undefined();
    }
    QV4::ScopedObject boxed(scope, value.toObject(vm));
    return boxed ? boxed->get(name) : QV4::Encode::undefined();
}
QJSValue panelUsageRead(const PanelUsageFrame& frame, const QJSValue& source, const char* name) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), source));
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedValue result(scope, panelUsageGet(frame, *value, key));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue panelUsageIndex(const PanelUsageFrame& frame, const QJSValue& source, quint32 index) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), source));
    QV4::ScopedValue key(scope, QV4::Encode(index));
    QV4::ScopedValue result(scope, QV4::Runtime::LoadElement::call(frame.vm(), *value, *key));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}

QJSValue panelUsageConstruct(const PanelUsageFrame& frame, const QJSValue& constructor,
                            const QJSValueList& arguments) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue function(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), constructor));
    QV4::JSCallArguments call(scope, static_cast<int>(arguments.size()));
    for (qsizetype i = 0; i < arguments.size(); ++i)
        call.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), arguments[i]);
    QV4::ScopedValue result(scope, QV4::Runtime::Construct::call(frame.vm(), *function, *function,
        call.args, static_cast<int>(arguments.size())));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue panelUsageGlobalCall(const PanelUsageFrame& frame, const char* name, const QJSValueList& arguments) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::JSCallArguments call(scope, static_cast<int>(arguments.size()));
    *call.thisObject = QV4::Encode::undefined();
    for (qsizetype i = 0; i < arguments.size(); ++i)
        call.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), arguments[i]);
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedObject global(scope, frame.vm()->globalObject);
    QV4::ScopedValue callable(scope, panelUsageGet(frame, *global, key, true));
    QV4::ScopedValue result(scope);
    if (const auto* function = callable->as<QV4::FunctionObject>()) result = function->call(call);
    else result = frame.vm()->throwTypeError(QStringLiteral("Property '%1' of object undefined is not a function").arg(key->toQString()));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue panelUsageMemberCall(const PanelUsageFrame& frame, const QJSValue& receiver,
                             const char* name, const QJSValueList& arguments = {}) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::JSCallArguments call(scope, static_cast<int>(arguments.size()));
    *call.thisObject = QJSValuePrivate::convertToReturnedValue(frame.vm(), receiver);
    for (qsizetype i = 0; i < arguments.size(); ++i)
        call.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), arguments[i]);
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedValue result(scope);
    if (call.thisObject->isNullOrUndefined()) {
        result = frame.vm()->throwTypeError(QStringLiteral("Cannot call method '%1' of %2")
            .arg(key->toQString(), call.thisObject->toQStringNoThrow()));
    } else {
        QV4::ScopedValue callable(scope, panelUsageGet(frame, *call.thisObject, key, true));
        if (const auto* function = callable->as<QV4::FunctionObject>()) result = function->call(call);
        else if (const auto* handler = callable->as<QV4::QmlSignalHandler>())
            result = handler->call(call.thisObject, call.args, static_cast<int>(arguments.size()));
        else result = frame.vm()->throwTypeError(QStringLiteral("Property '%1' of object %2 is not a function")
            .arg(key->toQString(), call.thisObject->toQStringNoThrow()));
    }
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}

QJSValue panelUsageView(const PanelUsageFrame& engine, QObject* panel) {
    return panelUsageReady(engine) ? engine->newQObject(panel) : QJSValue();
}
QJSValue panelUsageField(const PanelUsageFrame& engine, const QJSValue& panel, const char* property, const char* field) {
    const auto source = panelUsageRead(engine, panel, property);
    return panelUsageReady(engine) ? panelUsageRead(engine, source, field) : QJSValue();
}
QJSValue panelUsageText(const PanelUsageFrame& engine, const char* text) {
    if (!panelUsageReady(engine)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(engine.data())) qml->markCurrentFunctionAsTranslationBinding();
    const auto result = QJSValue(QCoreApplication::translate("AssistantPanel", text));
    engine.checked();
    return result;
}
std::optional<double> panelUsageNumber(const PanelUsageFrame& engine, const QJSValue& value) {
    if (!panelUsageReady(engine)) return std::nullopt;
    const QJSManagedValue number(value, engine.data());
    if (number.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Usage value belongs to another engine"));
        return std::nullopt;
    }
    const double result = number.toNumber();
    engine.checked();
    return panelUsageReady(engine) ? std::optional<double>(result) : std::nullopt;
}
QJSValue panelUsageAdd(const PanelUsageFrame& frame, const QJSValue& left, const QJSValue& right) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), left));
    QV4::ScopedValue b(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), right));
    QV4::ScopedValue result(scope, QV4::Runtime::Add::call(frame.vm(), *a, *b));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
struct PanelUsageLiteral { QJSValue value, prototype; };
PanelUsageLiteral panelUsageLiteral(const PanelUsageFrame& engine, int arrayLength = -1) {
    PanelUsageLiteral literal;
    if (!panelUsageReady(engine)) return literal;
    literal.value = arrayLength < 0 ? engine->newObject() : engine->newArray(arrayLength);
    QJSManagedValue object(literal.value, engine.data());
    literal.prototype = object.prototype().toJSValue();
    const QJSManagedValue none(QJSValue(QJSValue::NullValue), engine.data());
    object.setPrototype(none); // Original literal fields bypass inherited setters (ADR-0056).
    return literal;
}
void panelUsageWrite(const PanelUsageFrame& engine, const QJSValue& object, const char* name, const QJSValue& value) {
    if (!panelUsageReady(engine)) return;
    QJSManagedValue target(object, engine.data());
    if (target.engine() != engine.data()) {
        engine->throwError(QJSValue::TypeError, QStringLiteral("Usage value belongs to another engine"));
        return;
    }
    target.setProperty(QString::fromLatin1(name), value);
    engine.checked();
}
QJSValue panelUsageComplete(const PanelUsageFrame& engine, const PanelUsageLiteral& literal) {
    if (!panelUsageReady(engine)) return {};
    QJSManagedValue object(literal.value, engine.data());
    const QJSManagedValue prototype(literal.prototype, engine.data());
    object.setPrototype(prototype);
    return panelUsageReady(engine) ? literal.value : QJSValue();
}
bool panelUsageEach(const PanelUsageFrame& frame, const QJSValue& input,
                    const std::function<bool(const QJSValue&)>& visit) {
    if (!panelUsageReady(frame)) return false;
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue original(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), input));
    QV4::ScopedValue iterator(scope, QV4::Runtime::GetIterator::call(frame.vm(), *original,
        static_cast<int>(QQmlJS::AST::ForEachType::Of)));
    frame.checked();
    if (!panelUsageReady(frame)) return false;
    QV4::ScopedValue value(scope);
    for (;;) {
        const auto done = QV4::Runtime::IteratorNext::call(frame.vm(), *iterator, value);
        if (QV4::Value::fromReturnedValue(done).toBoolean()) {
            frame.checked();
            return panelUsageReady(frame);
        }
        const auto current = QJSValuePrivate::fromReturnedValue(value->asReturnedValue());
        if (!visit(current)) {
            QV4::Runtime::IteratorClose::call(frame.vm(), *iterator);
            frame.checked();
            return false;
        }
    }
}
QJSValue panelUsageArrayOrEmpty(const PanelUsageFrame& engine, const QJSValue& value) {
    return !panelUsageReady(engine) ? QJSValue() : value.toBool() ? value : engine->newArray();
}
QJSValue panelUsageBuckets(const PanelUsageFrame& engine, const QJSValue& view) {
    return panelUsageArrayOrEmpty(engine, panelUsageField(engine, view, "usageData", "buckets"));
}
bool panelUsageGreater(const PanelUsageFrame& frame, const QJSValue& first, const QJSValue& second) {
    const auto left = panelUsageRead(frame, first, "usedPercent");
    if (!panelUsageReady(frame)) return false;
    const auto right = panelUsageRead(frame, second, "usedPercent");
    if (!panelUsageReady(frame)) return false;
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), left));
    QV4::ScopedValue b(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), right));
    const bool result = bool(QV4::Runtime::CompareGreaterThan::call(*a, *b));
    frame.checked();
    return result;
}
QJSValue panelAllowanceWindow(const PanelUsageFrame& engine, const QJSValue& view, const QJSValue& minutes) {
    QJSValue selected(QJSValue::NullValue);
    const auto buckets = panelUsageBuckets(engine, view);
    panelUsageEach(engine, buckets, [&](const QJSValue& bucket) {
        const auto windows = panelUsageArrayOrEmpty(engine, panelUsageRead(engine, bucket, "windows"));
        return panelUsageEach(engine, windows, [&](const QJSValue& window) {
            const auto duration = panelUsageRead(engine, window, "windowDurationMins");
            if (!panelUsageReady(engine)) return false;
            if (duration.strictlyEquals(minutes) && (!selected.toBool() || panelUsageGreater(engine, window, selected))) selected = window;
            return panelUsageReady(engine);
        });
    });
    return panelUsageReady(engine) ? selected : QJSValue();
}
QJSValue panelUsageArg(const PanelUsageFrame& engine, const QJSValue& text,
                      const std::function<QJSValue()>& argument) {
    if (!panelUsageReady(engine)) return {};
    const auto value = argument();
    return panelUsageMemberCall(engine, text, "arg", {value});
}
QJSValue panelUsageMath(const PanelUsageFrame& engine, const char* operation,
                       const std::function<QJSValue()>& argument) {
    if (!panelUsageReady(engine)) return {};
    const auto math = panelUsageRead(engine, engine->globalObject(), "Math");
    const auto value = argument();
    return panelUsageMemberCall(engine, math, operation, {value});
}
QJSValue panelUsageNow(const PanelUsageFrame& engine) {
    const auto date = panelUsageRead(engine, engine->globalObject(), "Date");
    return panelUsageMemberCall(engine, date, "now");
}
QJSValue panelUsageCallback(const PanelUsageFrame& frame, uint operation, QObject* panel = nullptr) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::QmlContext> context(scope, frame.vm()->qmlContext());
    QV4::Scoped<QV4::AssistantPanelCallback> callback(scope,
        frame.vm()->memoryManager->allocate<QV4::AssistantPanelCallback>(frame.vm(), context.getPointer(), operation, panel));
    callback->defineReadonlyConfigurableProperty(frame.vm()->id_length(), QV4::Value::fromInt32(1));
    return QJSValuePrivate::fromReturnedValue(callback->asReturnedValue());
}
QJSValue panelUsageCapturedPanel(const PanelUsageFrame& frame, QObject* owner) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedString name(scope, frame.vm()->newString(QStringLiteral("panel")));
    auto context = frame.context;
    while (context) {
        const int index = context->propertyIndex(name);
        if (index >= 0 && index < context->numIdValues() && context->idValue(index) == owner) {
            auto* qml = QQmlEnginePrivate::get(frame.vm()->qmlEngine());
            if (qml->propertyCapture) qml->propertyCapture->captureProperty(context->idValueBindings(index));
            break;
        }
        context = context->parent();
    }
    QV4::ScopedValue result(scope, QV4::QObjectWrapper::wrap(frame.vm(), owner));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}

QJSValue panelUsagePlanWord(const PanelUsageFrame& engine, const QJSValue& word) {
    const auto length = panelUsageRead(engine, word, "length");
    if (!panelUsageReady(engine)) return {};
    if (!length.toBool()) return QJSValue(QString());
    const auto first = panelUsageIndex(engine, word, 0);
    const auto head = panelUsageMemberCall(engine, first, "toUpperCase");
    const auto tail = panelUsageMemberCall(engine, word, "slice", {QJSValue(1)});
    return panelUsageAdd(engine, head, tail);
}

QJSValue panelUsageWindowLabel(const PanelUsageFrame& engine, const QJSValue& bucket, const QJSValue& window) {
    auto duration = panelUsageRead(engine, window, "windowDurationMins");
    if (!panelUsageReady(engine)) return {};
    QJSValue label;
    if (duration.strictlyEquals(QJSValue(300))) label = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Session limit"));
    else {
        duration = panelUsageRead(engine, window, "windowDurationMins");
        if (!panelUsageReady(engine)) return {};
        label = panelUsageText(engine, duration.strictlyEquals(QJSValue(10080)) ?
            QT_TRANSLATE_NOOP("AssistantPanel", "Weekly") : QT_TRANSLATE_NOOP("AssistantPanel", "Other allowance"));
    }
    auto name = panelUsageRead(engine, bucket, "limitName");
    if (!panelUsageReady(engine)) return {};
    if (!name.toBool()) name = panelUsageRead(engine, bucket, "limitId");
    if (!panelUsageReady(engine)) return {};
    if (!name.toBool()) name = panelUsageRead(engine, bucket, "id");
    if (!panelUsageReady(engine)) return {};
    if (!name.toBool()) name = QJSValue(QString());
    const auto length = panelUsageRead(engine, name, "length");
    if (!panelUsageReady(engine)) return {};
    return length.toBool() ? panelUsageAdd(engine, panelUsageAdd(engine, name, QJSValue(QStringLiteral(" · "))), label) : label;
}
} // namespace

namespace edi_app::assistant_panel_presentation {
QJSValue usageWindowLabel(QJSEngine* actualEngine, const QJSValue& bucket, const QJSValue& window) {
    return panelUsageWindowLabel(PanelUsageFrame(actualEngine), bucket, window);
}
QJSValue accountPlanWord(QJSEngine* actualEngine, const QJSValue& word) {
    return panelUsagePlanWord(PanelUsageFrame(actualEngine), word);
}
} // namespace edi_app::assistant_panel_presentation

QJSValue ApplicationInfo::assistantUsageData(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    if (!panelUsageReady(engine)) return {};
    const auto view = panelUsageView(engine, panel);
    const auto outer = panelUsageRead(engine, engine->globalObject(), "JSON");
    const auto inner = panelUsageRead(engine, engine->globalObject(), "JSON");
    const auto owner = panelUsageRead(engine, view, "assistant");
    const auto usage = panelUsageRead(engine, owner, "usage");
    const auto serialized = panelUsageMemberCall(engine, inner, "stringify", {usage});
    const auto projected = panelUsageMemberCall(engine, outer, "parse", {serialized});
    if (panelUsageReady(engine)) return projected;
    if (!engine || !engine->hasError()) return {};
    engine->catchError();
    const auto fallback = panelUsageLiteral(engine);
    panelUsageWrite(engine, fallback.value, "available", QJSValue(false));
    panelUsageWrite(engine, fallback.value, "stale", QJSValue(false));
    panelUsageWrite(engine, fallback.value, "buckets", engine->newArray());
    return panelUsageComplete(engine, fallback);
}
QJSValue ApplicationInfo::assistantUsageWindow(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    const auto view = panelUsageView(engine, panel);
    QJSValue selected(QJSValue::NullValue);
    const auto buckets = panelUsageBuckets(engine, view);
    panelUsageEach(engine, buckets, [&](const QJSValue& bucket) {
        const auto windows = panelUsageArrayOrEmpty(engine, panelUsageRead(engine, bucket, "windows"));
        return panelUsageEach(engine, windows, [&](const QJSValue& window) {
            if (!selected.toBool() || panelUsageGreater(engine, window, selected)) {
                const auto literal = panelUsageLiteral(engine);
                const auto percent = panelUsageRead(engine, window, "usedPercent");
                if (!panelUsageReady(engine)) return false;
                panelUsageWrite(engine, literal.value, "usedPercent", percent);
                const auto label = panelUsageWindowLabel(engine, bucket, window);
                panelUsageWrite(engine, literal.value, "label", label);
                selected = panelUsageComplete(engine, literal);
            }
            return panelUsageReady(engine);
        });
    });
    return panelUsageReady(engine) ? selected : QJSValue();
}
QJSValue ApplicationInfo::assistantAccountPlan(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    const auto view = panelUsageView(engine, panel);
    const auto primary = panelUsageField(engine, view, "accountData", "planType");
    if (!panelUsageReady(engine)) return {};
    if (primary.toBool()) return panelUsageField(engine, view, "accountData", "planType");
    const auto known = engine->newArray();
    const auto buckets = panelUsageBuckets(engine, view);
    panelUsageEach(engine, buckets, [&](const QJSValue& bucket) {
        const auto offered = panelUsageRead(engine, bucket, "planType");
        if (!panelUsageReady(engine)) return false;
        if (!offered.toBool()) return true;
        const auto plan = panelUsageRead(engine, bucket, "planType");
        const auto index = panelUsageMemberCall(engine, known, "indexOf", {plan});
        const auto measured = panelUsageNumber(engine, index);
        if (!measured) return false;
        if (*measured < 0) {
            const auto value = panelUsageRead(engine, bucket, "planType");
            panelUsageMemberCall(engine, known, "push", {value});
        }
        return panelUsageReady(engine);
    });
    return panelUsageMemberCall(engine, known, "join", {QJSValue(QStringLiteral(", "))});
}
QJSValue ApplicationInfo::assistantAccountInitial(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    const auto view = panelUsageView(engine, panel);
    const auto offered = panelUsageField(engine, view, "accountData", "email");
    if (!panelUsageReady(engine)) return {};
    if (!offered.toBool()) return QJSValue(QString());
    const auto array = panelUsageRead(engine, engine->globalObject(), "Array");
    const auto email = panelUsageField(engine, view, "accountData", "email");
    const auto characters = panelUsageMemberCall(engine, array, "from", {email});
    const auto first = panelUsageIndex(engine, characters, 0);
    return panelUsageMemberCall(engine, first, "toUpperCase");
}
QJSValue ApplicationInfo::assistantAccountPlanLabel(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    if (!panelUsageReady(engine)) return {};
    const auto view = panelUsageView(engine, panel);
    const auto plan = panelUsageRead(engine, view, "accountPlan");
    const auto separator = engine->toScriptValue(QRegularExpression(QStringLiteral("[_ -]+")));
    const auto words = panelUsageMemberCall(engine, plan, "split", {separator});
    const auto callback = panelUsageCallback(engine, 0);
    const auto mapped = panelUsageMemberCall(engine, words, "map", {callback});
    return panelUsageMemberCall(engine, mapped, "join", {QJSValue(QStringLiteral(" "))});
}
QJSValue ApplicationInfo::assistantAccountPlanWord(const QJSValue& word,
                                                  const QJSValue& /*index*/,
                                                  const QJSValue& /*array*/) const {
    const auto engine = panelUsageEngine(this);
    return edi_app::assistant_panel_presentation::accountPlanWord(engine.data(), word);
}
QJSValue ApplicationInfo::assistantUsageCaption(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    const auto view = panelUsageView(engine, panel);
    const auto selected = panelUsageRead(engine, view, "usageWindow");
    if (!panelUsageReady(engine)) return {};
    if (selected.toBool()) {
        const auto text = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "%1 · %2% used"));
        const auto first = panelUsageArg(engine, text, [&] { return panelUsageField(engine, view, "usageWindow", "label"); });
        return panelUsageArg(engine, first, [&] { return panelUsageField(engine, view, "usageWindow", "usedPercent"); });
    }
    const auto status = panelUsageField(engine, view, "usageData", "statusText");
    return !panelUsageReady(engine) ? QJSValue() : status.toBool() ? status :
        panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Usage unavailable"));
}
QJSValue ApplicationInfo::assistantAllowanceWindow(QObject* panel, const QJSValue& minutes) const {
    const auto engine = panelUsageEngine(this);
    return panelAllowanceWindow(engine, panelUsageView(engine, panel), minutes);
}
QJSValue ApplicationInfo::assistantUsageAllowances(QObject* panel) const {
    const auto engine = panelUsageEngine(this);
    if (!panelUsageReady(engine)) return {};
    const auto descriptors = panelUsageLiteral(engine, 2);
    const int minutes[] = {300, 10080};
    const char* keys[] = {"session", "weekly"};
    const char* titles[] = {QT_TRANSLATE_NOOP("AssistantPanel", "Session limit"), QT_TRANSLATE_NOOP("AssistantPanel", "Weekly")};
    for (int index = 0; index < 2; ++index) {
        const auto title = panelUsageText(engine, titles[index]);
        const auto row = panelUsageLiteral(engine);
        panelUsageWrite(engine, row.value, "title", title);
        panelUsageWrite(engine, row.value, "minutes", QJSValue(minutes[index]));
        panelUsageWrite(engine, row.value, "key", QJSValue(QString::fromLatin1(keys[index])));
        const auto value = panelUsageComplete(engine, row);
        if (!panelUsageReady(engine)) return {};
        panelUsageWrite(engine, descriptors.value, index == 0 ? "0" : "1", value);
    }
    const auto values = panelUsageComplete(engine, descriptors);
    const auto callback = panelUsageCallback(engine, 1, panel);
    return panelUsageMemberCall(engine, values, "filter", {callback});
}
QJSValue ApplicationInfo::assistantAllowanceColor(const QJSValue& remaining, const QJSValue& colors) const {
    const auto engine = panelUsageEngine(this);
    auto measured = panelUsageNumber(engine, remaining);
    if (!measured) return {};
    if (*measured >= 0) {
        measured = panelUsageNumber(engine, remaining);
        if (!measured) return {};
        if (*measured < 5) return panelUsageRead(engine, colors, "red");
    }
    measured = panelUsageNumber(engine, remaining);
    if (!measured) return {};
    if (*measured >= 0) {
        measured = panelUsageNumber(engine, remaining);
        if (!measured) return {};
        if (*measured < 25) return panelUsageRead(engine, colors, "orange");
    }
    return panelUsageRead(engine, colors, "themeForeground");
}
QJSValue ApplicationInfo::assistantUsageResetLabel(const QJSValue& value, const QJSValue& now) const {
    const auto engine = panelUsageEngine(this);
    if (!panelUsageReady(engine)) return {};
    const auto unavailable = [&] { return panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Reset unavailable")); };
    if (!value.isNumber()) return unavailable();
    const auto date = panelUsageRead(engine, engine->globalObject(), "Date");
    if (!panelUsageReady(engine)) return {};
    const double milliseconds = value.toNumber() * 1000;
    const auto instance = panelUsageConstruct(engine, date, {QJSValue(milliseconds)});
    const auto time = panelUsageMemberCall(engine, instance, "getTime");
    const auto valid = panelUsageGlobalCall(engine, "isFinite", {time});
    if (!panelUsageReady(engine)) return {};
    if (!valid.toBool()) return unavailable();
    const auto minutes = panelUsageMath(engine, "ceil", [&] {
        const auto current = panelUsageNumber(engine, now);
        return current ? QJSValue((milliseconds - *current) / 60000) : QJSValue();
    });
    auto measured = panelUsageNumber(engine, minutes);
    if (!measured) return {};
    if (*measured <= 0) return panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Reset time reached"));
    const auto days = panelUsageMath(engine, "floor", [&] {
        const auto amount = panelUsageNumber(engine, minutes);
        return amount ? QJSValue(*amount / 1440) : QJSValue();
    });
    const auto hours = panelUsageMath(engine, "floor", [&] {
        const auto amount = panelUsageNumber(engine, minutes);
        return amount ? QJSValue(std::fmod(*amount, 1440) / 60) : QJSValue();
    });
    measured = panelUsageNumber(engine, days);
    if (!measured) return {};
    if (*measured > 0) {
        const auto text = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Resets in %1d %2h"));
        const auto first = panelUsageArg(engine, text, [&] { return days; });
        return panelUsageArg(engine, first, [&] { return hours; });
    }
    measured = panelUsageNumber(engine, hours);
    if (!measured) return {};
    if (*measured > 0) {
        const auto text = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Resets in %1h %2 min"));
        const auto first = panelUsageArg(engine, text, [&] { return hours; });
        return panelUsageArg(engine, first, [&] {
            const auto amount = panelUsageNumber(engine, minutes);
            return amount ? QJSValue(std::fmod(*amount, 60)) : QJSValue();
        });
    }
    const auto text = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "Resets in %1 min"));
    return panelUsageArg(engine, text, [&] { return minutes; });
}
QJSValue ApplicationInfo::assistantUsageNow() const { return panelUsageNow(panelUsageEngine(this)); }
void ApplicationInfo::refreshAssistantUsageClock(QObject* dialog) const {
    const auto engine = panelUsageEngine(this);
    const auto target = panelUsageView(engine, dialog);
    const auto now = panelUsageNow(engine);
    panelUsageWrite(engine, target, "resetClock", now);
}
void ApplicationInfo::assistantAccountConnectionChanged(QObject* panel, QObject* dialog) const {
    const auto engine = panelUsageEngine(this);
    const auto view = panelUsageView(engine, panel);
    const auto owner = panelUsageRead(engine, view, "assistant");
    const auto connected = panelUsageRead(engine, owner, "connected");
    if (!panelUsageReady(engine) || connected.toBool()) return;
    const auto target = panelUsageView(engine, dialog);
    panelUsageMemberCall(engine, target, "close");
}


QV4::ReturnedValue QV4::AssistantPanelCallback::virtualCall(const FunctionObject* function,
    const Value*, const Value* arguments, int count) {
    const auto* callback = static_cast<const AssistantPanelCallback*>(function);
    QV4::Scope scope(function->engine());
    QV4::Scoped<QV4::QmlContext> context(scope, callback->d()->context);
    const PanelUsageFrame frame(function->engine()->jsEngine(), context ? context->qmlContext() : QQmlRefPointer<QQmlContextData>());
    if (!panelUsageReady(frame)) return QV4::Encode::undefined();
    const QJSValue value = count ? QJSValuePrivate::fromReturnedValue(arguments[0].asReturnedValue()) : QJSValue();
    QJSValue result;
    if (callback->d()->operation == 0) {
        result = panelUsagePlanWord(frame, value);
    } else {
        const auto panel = panelUsageCapturedPanel(frame, callback->d()->panel);
        const auto minutes = panelUsageRead(frame, value, "minutes");
        const auto selected = panelUsageMemberCall(frame, panel, "allowanceWindow", {minutes});
        if (panelUsageReady(frame)) result = QJSValue(!selected.isNull());
    }
    return QJSValuePrivate::convertToReturnedValue(frame.vm(), result);
}
#else
namespace edi_app::assistant_panel_presentation {
QJSValue usageWindowLabel(QJSEngine*, const QJSValue&, const QJSValue&) { return QJSValue(QString()); }
QJSValue accountPlanWord(QJSEngine*, const QJSValue&) { return QJSValue(QString()); }
}
QJSValue ApplicationInfo::assistantUsageData(QObject*) const {
    auto* engine = qjsEngine(this);
    if (!engine) return QJSValue(QJSValue::NullValue);
    auto value = engine->newObject();
    value.setProperty(QStringLiteral("available"), false);
    value.setProperty(QStringLiteral("stale"), false);
    value.setProperty(QStringLiteral("buckets"), engine->newArray());
    return value;
}
QJSValue ApplicationInfo::assistantUsageWindow(QObject*) const { return QJSValue(QJSValue::NullValue); }
QJSValue ApplicationInfo::assistantAllowanceWindow(QObject*, const QJSValue&) const { return QJSValue(QJSValue::NullValue); }
QJSValue ApplicationInfo::assistantUsageAllowances(QObject*) const {
    auto* engine = qjsEngine(this);
    return engine ? engine->newArray() : QJSValue(QJSValue::NullValue);
}
QJSValue ApplicationInfo::assistantAccountPlan(QObject*) const { return QJSValue(QString()); }
QJSValue ApplicationInfo::assistantAccountInitial(QObject*) const { return QJSValue(QString()); }
QJSValue ApplicationInfo::assistantAccountPlanLabel(QObject*) const { return QJSValue(QString()); }
QJSValue ApplicationInfo::assistantAccountPlanWord(const QJSValue&, const QJSValue&, const QJSValue&) const { return QJSValue(QString()); }
QJSValue ApplicationInfo::assistantUsageCaption(QObject*) const { return QJSValue(assistantUnavailableReason()); }
QJSValue ApplicationInfo::assistantAllowanceColor(const QJSValue&, const QJSValue& colors) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    return messageScriptProperty(engine, colors, QStringLiteral("themeForeground"));
}
QJSValue ApplicationInfo::assistantUsageResetLabel(const QJSValue&, const QJSValue&) const { return QJSValue(QString()); }
QJSValue ApplicationInfo::assistantUsageNow() const { return QJSValue(0); }
void ApplicationInfo::refreshAssistantUsageClock(QObject*) const {}
void ApplicationInfo::assistantAccountConnectionChanged(QObject*, QObject*) const {}
#endif

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

void ApplicationInfo::storeWindowGeometry(QObject* window, QObject* settings) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine) || engine->thread() != QThread::currentThread()) return;
    const auto view = engine->newQObject(window);
    const auto read = [&](const QJSValue& source, const char* name) {
        return messageScriptProperty(engine, source, QString::fromLatin1(name));
    };
    const auto restored = read(view, "geometryRestored");
    if (!messageScriptReady(engine) || !restored.toBool() || edi_app::WebFiles::available()) return;
    auto visibility = read(view, "visibility");
    if (!messageScriptReady(engine) || visibility.strictlyEquals(QJSValue(int(QWindow::Maximized)))) return;
    visibility = read(view, "visibility");
    if (!messageScriptReady(engine) || visibility.strictlyEquals(QJSValue(int(QWindow::FullScreen)))) return;
    const auto target = engine->newQObject(settings);
    for (const char* field : {"x", "y", "width", "height"}) {
        const auto value = read(view, field);
        if (!messageScriptReady(engine)) return;
        messageScriptWrite(engine, target, QString::fromLatin1(field), value);
        if (!messageScriptReady(engine)) return;
    }
}

void ApplicationInfo::restoreWindowGeometry(QObject* window, QObject* settings) const {
    const QPointer<QJSEngine> engine(qjsEngine(this));
    if (!messageScriptReady(engine) || engine->thread() != QThread::currentThread()) return;
    const auto view = engine->newQObject(window);
    const auto kept = engine->newQObject(settings);
    const auto read = [&](const QJSValue& source, const char* name) {
        return messageScriptProperty(engine, source, QString::fromLatin1(name));
    };
    bool defaults = edi_app::WebFiles::available();
    if (!defaults) {
        const auto width = read(kept, "width");
        if (!messageScriptReady(engine)) return;
        defaults = width.toNumber() <= 0;
        if (!defaults) {
            const auto height = read(kept, "height");
            if (!messageScriptReady(engine)) return;
            defaults = height.toNumber() <= 0;
        }
    }
    if (!messageScriptReady(engine)) return;
    if (!defaults) {
        for (const char* field : {"width", "height"}) {
            const auto value = read(kept, field);
            if (!messageScriptReady(engine)) return;
            messageScriptWrite(engine, view, QString::fromLatin1(field), value);
            if (!messageScriptReady(engine)) return;
        }
        const auto actor = engine->newQObject(const_cast<ApplicationInfo*>(this));
        const auto placement = read(actor, "onScreenPosition");
        if (!messageScriptReady(engine)) return;
        const auto x = read(kept, "x");
        if (!messageScriptReady(engine)) return;
        const auto y = read(kept, "y");
        if (!messageScriptReady(engine)) return;
        const auto width = read(view, "width");
        if (!messageScriptReady(engine)) return;
        const auto height = read(view, "height");
        if (!messageScriptReady(engine)) return;
        const auto position = messageScriptCall(engine, placement, actor, {x, y, width, height});
        if (!messageScriptReady(engine)) return;
        for (const char* field : {"x", "y"}) {
            const auto value = read(position, field);
            if (!messageScriptReady(engine)) return;
            messageScriptWrite(engine, view, QString::fromLatin1(field), value);
            if (!messageScriptReady(engine)) return;
        }
    }
    messageScriptWrite(engine, view, QStringLiteral("geometryRestored"), QJSValue(true));
    if (!messageScriptReady(engine)) return;
    const auto store = read(view, "storeGeometry");
    if (messageScriptReady(engine)) messageScriptCall(engine, store, view, {});
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
