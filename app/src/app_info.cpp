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

#include <private/qjsengine_p.h>
#include <private/qjsvalue_p.h>
#include <private/qqmlcontextdata_p.h>
#include <private/qqmlcontext_p.h>
#include <private/qqmlimport_p.h>
#include <private/qqmltypenamecache_p.h>
#include <private/qqmllistwrapper_p.h>
#include <private/qqmltypewrapper_p.h>
#include <private/qv4compileddata_p.h>
#include <private/qv4function_p.h>
#include <private/qv4memberdata_p.h>
#include <private/qmetaobject_p.h>
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

#ifdef _OPENMP
#include <omp.h>
#endif
#ifdef Q_OS_WASM
#include <emscripten/val.h>
#endif

namespace QV4 {
namespace Heap {
#define AssistantPanelCallbackMembers(class, Member) \
    Member(class, Pointer, QmlContext*, context) \
    Member(class, Pointer, MemberData*, captures) \
    Member(class, NoMark, uint, operation)
DECLARE_HEAP_OBJECT(AssistantPanelCallback, FunctionObject) {
    DECLARE_MARKOBJECTS(AssistantPanelCallback)
    QV4QPointer<QObject> panel;
    void init(QV4::ExecutionEngine* engine, QV4::QmlContext* captured, uint kind, QObject* owner, QV4::MemberData* values = nullptr) {
        FunctionObject::init(engine, QString());
        context.set(engine, captured ? captured->d() : nullptr);
        captures.set(engine, values ? values->d() : nullptr);
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

namespace QV4 {
namespace Heap {
#define ApplicationProjectCallbackMembers(class, Member) \
    Member(class, Pointer, QmlContext*, context) \
    Member(class, NoMark, uint, operation)
DECLARE_HEAP_OBJECT(ApplicationProjectCallback, JavaScriptFunctionObject) {
    DECLARE_MARKOBJECTS(ApplicationProjectCallback)
    void init(QV4::ExecutionEngine* engine, QV4::QmlContext* captured, uint kind) {
        FunctionObject::init(engine, QString());
        scope.set(engine, captured ? captured->d() : engine->rootContext()->d());
        function = nullptr;
        context.set(engine, captured ? captured->d() : nullptr);
        operation = kind;
    }
};
}
struct ApplicationProjectCallback : JavaScriptFunctionObject {
    V4_OBJECT2(ApplicationProjectCallback, JavaScriptFunctionObject)
    V4_NEEDS_DESTROY
    static ReturnedValue virtualCall(const FunctionObject*, const Value*, const Value*, int);
};
DEFINE_OBJECT_VTABLE(ApplicationProjectCallback);
}


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

namespace {
bool panelUsageTruth(const QJSValue& value) {
    if (const auto* text = QJSValuePrivate::asQString(&value)) return !text->isEmpty();
    return QV4::Value::fromReturnedValue(QJSValuePrivate::asReturnedValue(&value)).toBoolean();
}
struct PanelUsageFrame {
    QPointer<QJSEngine> pointer;
    QQmlRefPointer<QQmlContextData> context;
    QV4::Heap::QmlContext* qmlScope = nullptr;
    mutable bool interrupted = false;
    explicit PanelUsageFrame(QJSEngine* engine = nullptr,
                             QQmlRefPointer<QQmlContextData> captured = {}, QV4::Heap::QmlContext* scope = nullptr)
        : pointer(engine), context(std::move(captured)), qmlScope(scope) {
        if (pointer) {
            auto* vm = QJSEnginePrivate::get(pointer.data())->v4Engine.get();
            if (!context) context = vm->callingQmlContext();
            if (!qmlScope) qmlScope = vm->qmlContext();
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
QJSValue viewProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&);
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
QJSValue panelUsageMemberCall(const PanelUsageFrame&, const QJSValue&, const char*, const QJSValueList&);
QV4::ReturnedValue panelUsageResolveContext(const PanelUsageFrame& frame, QV4::String* name,
                                           QV4::Value* base, bool forCall = false) {
    auto* vm = frame.vm();
    QV4::Scope scope(vm);
    QV4::Scoped<QV4::QmlContext> qml(scope, frame.qmlScope);
    auto context = frame.context;
    if (!qml) {
        bool found = false;
        const auto value = vm->globalObject->get(name, &found);
        return found ? value : vm->throwReferenceError(name->toQString());
    }
    QV4::Scoped<QV4::QQmlContextWrapper> resource(scope, qml->d()->qml());
    if (!context) return QV4::Encode::undefined();
    const auto expressionContext = context;
    const bool isJSContext = context->isJSContext();
    bool hasProperty = false;
    if (isJSContext) {
        QV4::ScopedValue value(scope, QV4::Object::virtualGet(resource, name->toPropertyKey(), nullptr, &hasProperty));
        if (hasProperty) return value->asReturnedValue();
    }
    auto* ep = QQmlEnginePrivate::get(vm->qmlEngine());
    QObject* scopeObject = resource->getScopeObject();
    const auto* meta = scopeObject ? reinterpret_cast<const QMetaObjectPrivate*>(scopeObject->metaObject()->d.data) : nullptr;
    if (meta && (meta->flags & DynamicMetaObject)) {
        QV4::ScopedValue value(scope, vm->globalObject->get(name, &hasProperty));
        if (hasProperty) return value->asReturnedValue();
    }
    const auto contextProperty = [&](const QQmlRefPointer<QQmlContextData>& source, bool* found) -> QV4::ReturnedValue {
        const int index = source->propertyIndex(name);
        if (index < 0) return QV4::Encode::undefined();
        *found = true;
        if (index < source->numIdValues()) {
            if (ep->propertyCapture) ep->propertyCapture->captureProperty(source->idValueBindings(index));
            return QV4::QObjectWrapper::wrap(vm, source->idValue(index));
        }
        auto* cp = source->asQQmlContextPrivate();
        if (ep->propertyCapture)
            ep->propertyCapture->captureProperty(source->asQQmlContext(), -1, index + cp->notifyIndex());
        const auto& value = cp->propertyValue(index);
        if (value.userType() == qMetaTypeId<QList<QObject*>>()) {
            QQmlListProperty<QObject> list(source->asQQmlContext(), reinterpret_cast<void*>(qintptr(index)),
                QQmlContextPrivate::context_count, QQmlContextPrivate::context_at);
            return QV4::QmlListWrapper::create(vm, list, QMetaType::fromType<QQmlListProperty<QObject>>());
        }
        return vm->fromVariant(value);
    };
    if (context && context->imports() && (name->startsWithUpper() || context->valueTypesAreAddressable())) {
        const auto imported = context->imports()->query<QQmlImport::AllowRecursion>(name, vm->typeLoader());
        if (imported.isValid()) {
            if (imported.scriptIndex != -1) {
                QV4::ScopedObject scripts(scope, context->importedScripts());
                return scripts ? scripts->get(imported.scriptIndex) : QV4::Encode::null();
            }
            if (imported.type.isValid()) return QV4::QQmlTypeWrapper::create(vm, scopeObject, imported.type);
            if (imported.importNamespace)
                return QV4::QQmlTypeWrapper::create(vm, scopeObject, context->imports(), imported.importNamespace);
        }
    }
    if (scopeObject == context->contextObject()) scopeObject = nullptr;
    auto outer = context;
    bool calling = forCall;
    while (context) {
        if (outer == context) {
            bool found = false;
            auto value = contextProperty(context, &found);
            if (found) return value;
            outer = outer->parent();
            if (const auto unit = context->typeCompilationUnit(); unit && unit->componentsAreBound()) {
                while (outer && outer->typeCompilationUnit() == unit) {
                    value = contextProperty(outer, &found);
                    if (found) return value;
                    outer = outer->parent();
                }
            }
        }
        for (QObject* object : {scopeObject, context->contextObject()}) {
            if (!object) continue;
            QV4::ScopedObject wrapper(scope, QV4::QObjectWrapper::wrap(vm, object));
            bool found = false;
            const auto flags = QV4::QObjectWrapper::Flags(QV4::QObjectWrapper::CheckRevision
                | (calling ? QV4::QObjectWrapper::NoFlag : QV4::QObjectWrapper::AttachMethods));
            const auto value = QV4::QObjectWrapper::getQmlProperty(vm, context, wrapper->d(), object, name, flags, &found);
            if (found) {
                if (base) *base = wrapper;
                return value;
            }
            if (object == context->contextObject()) break;
        }
        scopeObject = nullptr;
        context = context->parent();
        calling = false;
    }
    if (!isJSContext) {
        QV4::ScopedValue value(scope, QV4::Object::virtualGet(resource, name->toPropertyKey(), nullptr, &hasProperty));
        if (hasProperty) return value->asReturnedValue();
    }
    bool found = false;
    const auto result = vm->globalObject->get(name, &found);
    if (found) return result;
    expressionContext->setUnresolvedNames(true);
    return vm->throwReferenceError(name->toQString());
}
QJSValue panelUsageContextRead(const PanelUsageFrame& frame, const char* name) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedValue result(scope, panelUsageResolveContext(frame, key, nullptr));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
void panelUsageContextWrite(const PanelUsageFrame& frame, const char* name, const QJSValue& value) {
    if (!panelUsageReady(frame)) return;
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::QmlContext> qml(scope, frame.qmlScope);
    if (!qml) { frame.vm()->throwReferenceError(QString::fromLatin1(name)); return; }
    QV4::Scoped<QV4::QQmlContextWrapper> wrapper(scope, qml->d()->qml());
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedValue actual(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), value));
    wrapper->put(key, actual);
    frame.checked();
}
QJSValue panelUsageClosure(const PanelUsageFrame& frame, uint operation, const QJSValueList& values) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::MemberData> captures(scope, QV4::MemberData::allocate(frame.vm(), values.size()));
    captures->d()->values.size = values.size();
    for (qsizetype i = 0; i < values.size(); ++i)
        captures->set(frame.vm(), i, QV4::Value::fromReturnedValue(QJSValuePrivate::convertToReturnedValue(frame.vm(), values[i])));
    QV4::Scoped<QV4::QmlContext> context(scope, frame.qmlScope);
    QV4::Scoped<QV4::AssistantPanelCallback> callback(scope,
        frame.vm()->memoryManager->allocate<QV4::AssistantPanelCallback>(frame.vm(), context.getPointer(), operation, nullptr, captures.getPointer()));
    callback->defineReadonlyConfigurableProperty(frame.vm()->id_length(), QV4::Value::fromInt32(0));
    return QJSValuePrivate::fromReturnedValue(callback->asReturnedValue());
}
void panelUsageCallLater(const PanelUsageFrame& frame, const QJSValue& callback) {
    const auto qt = panelUsageContextRead(frame, "Qt");
    panelUsageMemberCall(frame, qt, "callLater", {callback});
}

QJSValue panelUsageGlobalCall(const PanelUsageFrame& frame, const char* name, const QJSValueList& arguments) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::JSCallArguments call(scope, static_cast<int>(arguments.size()));
    *call.thisObject = QV4::Encode::undefined();
    for (qsizetype i = 0; i < arguments.size(); ++i)
        call.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), arguments[i]);
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    QV4::ScopedValue callable(scope, panelUsageResolveContext(frame, key, call.thisObject, true));
    QV4::ScopedValue result(scope);
    if (const auto* function = callable->as<QV4::FunctionObject>()) result = function->call(call);
    else result = frame.vm()->throwTypeError(QStringLiteral("Property '%1' of object %2 is not a function").arg(key->toQString(), call.thisObject->toQStringNoThrow()));
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
        result = frame.vm()->throwTypeError(QStringLiteral("Cannot read property '%1' of %2")
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
    return !panelUsageReady(engine) ? QJSValue() : panelUsageTruth(value) ? value : engine->newArray();
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
            if (duration.strictlyEquals(minutes) && (!panelUsageTruth(selected) || panelUsageGreater(engine, window, selected))) selected = window;
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
    const auto math = panelUsageContextRead(engine, "Math");
    const auto value = argument();
    return panelUsageMemberCall(engine, math, operation, {value});
}
QJSValue panelUsageNow(const PanelUsageFrame& engine) {
    const auto date = panelUsageContextRead(engine, "Date");
    return panelUsageMemberCall(engine, date, "now");
}
QJSValue panelUsageCallback(const PanelUsageFrame& frame, uint operation, QObject* panel = nullptr) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::QmlContext> context(scope, frame.qmlScope);
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
    if (!panelUsageTruth(length)) return QJSValue(QString());
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
    if (!panelUsageTruth(name)) name = panelUsageRead(engine, bucket, "limitId");
    if (!panelUsageReady(engine)) return {};
    if (!panelUsageTruth(name)) name = panelUsageRead(engine, bucket, "id");
    if (!panelUsageReady(engine)) return {};
    if (!panelUsageTruth(name)) name = QJSValue(QString());
    const auto length = panelUsageRead(engine, name, "length");
    if (!panelUsageReady(engine)) return {};
    return panelUsageTruth(length) ? panelUsageAdd(engine, panelUsageAdd(engine, name, QJSValue(QStringLiteral(" · "))), label) : label;
}
} // namespace

namespace {
void assistantMemberWrite(const PanelUsageFrame& frame, const QJSValue& receiver,
                          const char* property, const QJSValue& value) {
    if (!panelUsageReady(frame)) return;
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), receiver));
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(property)));
    QV4::ScopedValue actual(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), value));
    QV4::Runtime::StoreElement::call(frame.vm(), *object, *key, *actual);
    frame.checked();
}
QJSValue assistantContextField(const PanelUsageFrame& frame, const char* object, const char* name) {
    const auto owner = panelUsageContextRead(frame, object);
    return panelUsageRead(frame, owner, name);
}
bool assistantRelation(const PanelUsageFrame& frame, const QJSValue& left, const QJSValue& right, int operation) {
    if (!panelUsageReady(frame)) return false;
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), left));
    QV4::ScopedValue b(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), right));
    bool result = false;
    if (operation == 0) result = bool(QV4::Runtime::CompareLessThan::call(*a, *b));
    else if (operation == 1) result = bool(QV4::Runtime::CompareGreaterThan::call(*a, *b));
    else if (operation == 2) result = bool(QV4::Runtime::CompareGreaterEqual::call(*a, *b));
    else result = bool(QV4::Runtime::CompareLessEqual::call(*a, *b));
    frame.checked();
    return result;
}
bool assistantSameName(const PanelUsageFrame& frame, const QJSValue& value, const char* name) {
    const auto actual = panelUsageContextRead(frame, name);
    return panelUsageReady(frame) && value.strictlyEquals(actual);
}
bool assistantEditorIdle(const PanelUsageFrame& frame) {
    const auto composing = assistantContextField(frame, "editor", "inputMethodComposing");
    if (!panelUsageReady(frame) || panelUsageTruth(composing)) return false;
    const auto preedit = assistantContextField(frame, "editor", "preeditText");
    const auto length = panelUsageRead(frame, preedit, "length");
    return panelUsageReady(frame) && length.strictlyEquals(QJSValue(0));
}
bool assistantDraftMatchesEditor(const PanelUsageFrame& frame, const QJSValue& draft) {
    const auto revision = panelUsageRead(frame, draft, "revision");
    if (!assistantSameName(frame, revision, "textRevision")) return false;
    const auto text = panelUsageRead(frame, draft, "text");
    const auto current = assistantContextField(frame, "editor", "text");
    return panelUsageReady(frame) && text.strictlyEquals(current) && assistantEditorIdle(frame);
}
QJSValue assistantMessageText(const PanelUsageFrame& frame, double index, const char* role) {
    const auto messages = assistantContextField(frame, "assistant", "messages");
    return panelUsageMemberCall(frame, messages, "text", {QJSValue(index), QJSValue(QString::fromLatin1(role))});
}
bool assistantContains(const PanelUsageFrame& frame, const QJSValue& ancestor, const QJSValue& item) {
    for (QJSValue current = item; panelUsageReady(frame) && panelUsageTruth(current);
         current = panelUsageRead(frame, current, "parent")) {
        if (current.strictlyEquals(ancestor)) return true;
    }
    return false;
}
bool assistantContainsCall(const PanelUsageFrame& frame, const QJSValue& ancestor, const QJSValue& item) {
    return panelUsageTruth(panelUsageGlobalCall(frame, "containsAssistantItem", {ancestor, item}));
}
void assistantIncrementEpoch(const PanelUsageFrame& frame) {
    const auto value = panelUsageContextRead(frame, "assistantFocusEpoch");
    const auto number = panelUsageNumber(frame, value);
    if (number) panelUsageContextWrite(frame, "assistantFocusEpoch", QJSValue(*number + 1));
}
void assistantFocusOpener(const PanelUsageFrame& frame) {
    const auto enabled = assistantContextField(frame, "assistantToggle", "enabled");
    if (!panelUsageReady(frame)) return;
    if (panelUsageTruth(enabled)) {
        const auto toggle = panelUsageContextRead(frame, "assistantToggle");
        panelUsageMemberCall(frame, toggle, "forceActiveFocus");
    } else {
        const auto item = assistantContextField(frame, "appBarCentralTabs", "currentItem");
        if (panelUsageReady(frame) && panelUsageTruth(item)) {
            const auto current = assistantContextField(frame, "appBarCentralTabs", "currentItem");
            panelUsageMemberCall(frame, current, "forceActiveFocus");
        }
    }
}
QJSValue assistantGeometryArray(const PanelUsageFrame& frame, const QJSValueList& entries) {
    const auto literal = panelUsageLiteral(frame, static_cast<int>(entries.size()));
    if (!panelUsageReady(frame)) return {};
    QJSManagedValue array(literal.value, frame.data());
    for (qsizetype index = 0; index < entries.size(); ++index) {
        array.setProperty(static_cast<quint32>(index), entries[index]);
        frame.checked();
        if (!panelUsageReady(frame)) return {};
    }
    return panelUsageComplete(frame, literal);
}
bool assistantGeometryFinite(const PanelUsageFrame& frame, const QJSValue& values) {
    const auto number = panelUsageContextRead(frame, "Number");
    const auto predicate = panelUsageRead(frame, number, "isFinite");
    return panelUsageTruth(panelUsageMemberCall(frame, values, "every", {predicate}));
}
void mainAssistantDelayed(const PanelUsageFrame& frame, uint operation,
                          const std::function<QJSValue(uint)>& captured) {
    if (operation == 2) {
        const auto epoch = captured(0), host = captured(1), project = captured(2), previous = captured(3);
        if (!assistantSameName(frame, epoch, "assistantFocusEpoch") || !assistantSameName(frame, host, "activeAssistantHost")) return;
        const auto currentProject = assistantContextField(frame, "Session", "project");
        if (!panelUsageReady(frame) || !project.strictlyEquals(currentProject)) return;
        const auto visible = assistantContextField(frame, "assistantPanel", "visible");
        if (!panelUsageReady(frame) || !panelUsageTruth(visible)) return;
        const auto shown = assistantContextField(frame, "assistantPanel", "shown");
        if (!panelUsageReady(frame) || !panelUsageTruth(shown) || !panelUsageTruth(previous)) return;
        const auto previousVisible = panelUsageRead(frame, previous, "visible");
        if (!panelUsageReady(frame) || !panelUsageTruth(previousVisible)) return;
        const auto enabled = panelUsageRead(frame, previous, "enabled");
        if (!panelUsageReady(frame) || !panelUsageTruth(enabled)) return;
        const auto content = assistantContextField(frame, "assistantPanel", "contentItem");
        if (assistantContainsCall(frame, content, previous)) panelUsageMemberCall(frame, previous, "forceActiveFocus");
        return;
    }
    const auto previous = captured(0), page = captured(1), host = captured(2), project = captured(3), epoch = captured(4);
    if (!assistantSameName(frame, epoch, "assistantFocusEpoch")) return;
    const auto shown = assistantContextField(frame, "assistantPanel", "shown");
    if (!panelUsageReady(frame) || panelUsageTruth(shown)) return;
    const auto visible = assistantContextField(frame, "assistantPanel", "visible");
    if (!panelUsageReady(frame) || panelUsageTruth(visible)) return;
    bool restore = assistantSameName(frame, page, "assistantCurrentPage") && assistantSameName(frame, host, "activeAssistantHost");
    if (restore) {
        const auto currentProject = assistantContextField(frame, "Session", "project");
        restore = panelUsageReady(frame) && project.strictlyEquals(currentProject) && panelUsageTruth(previous);
    }
    if (restore) {
        const auto previousVisible = panelUsageRead(frame, previous, "visible");
        restore = panelUsageReady(frame) && panelUsageTruth(previousVisible);
    }
    if (restore) {
        const auto enabled = panelUsageRead(frame, previous, "enabled");
        restore = panelUsageReady(frame) && panelUsageTruth(enabled);
    }
    if (restore) {
        restore = assistantContainsCall(frame, page, previous);
        if (panelUsageReady(frame) && !restore) restore = assistantSameName(frame, previous, "assistantToggle");
    }
    if (!panelUsageReady(frame)) return;
    if (restore) panelUsageMemberCall(frame, previous, "forceActiveFocus");
    else panelUsageGlobalCall(frame, "focusAssistantOpener", {});
}
}

namespace {
bool consentQtObject(const PanelUsageFrame& f, const QJSValue& value) {
    const auto qt = panelUsageContextRead(f, "Qt");
    return panelUsageReady(f) && panelUsageTruth(panelUsageMemberCall(f, qt, "isQtObject", {value}));
}
bool consentOwner(const PanelUsageFrame& f, const QJSValue& component, const QJSValue& owner) {
    if (!consentQtObject(f, component) || !consentQtObject(f, owner)) return false;
    const auto actual = panelUsageRead(f, component, "assistant");
    return panelUsageReady(f) && owner.strictlyEquals(actual);
}
bool consentPanelOwner(const PanelUsageFrame& f, const QJSValue& component, const QJSValue& draft, const QJSValue& owner) {
    if (!consentQtObject(f, component) || !consentQtObject(f, draft) || !consentQtObject(f, owner)) return false;
    const auto actual = panelUsageRead(f, component, "assistant");
    return panelUsageReady(f) && owner.strictlyEquals(actual);
}
bool consentFieldEquals(const PanelUsageFrame& f, const QJSValue& source, const char* key, const QJSValue& expected) {
    const auto actual = panelUsageRead(f, source, key);
    return panelUsageReady(f) && actual.strictlyEquals(expected);
}
bool consentFieldsEqual(const PanelUsageFrame& f, const QJSValue& left, const char* leftKey,
                        const QJSValue& right, const char* rightKey) {
    const auto a = panelUsageRead(f, left, leftKey);
    const auto b = panelUsageRead(f, right, rightKey);
    return panelUsageReady(f) && a.strictlyEquals(b);
}
QJSValue consentStatus(const PanelUsageFrame& f, const char* status) {
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "status", QJSValue(QString::fromLatin1(status)));
    return panelUsageComplete(f, literal);
}
QJSValue consentNull() { return QJSValue(QJSValue::NullValue); }
void consentClear(const PanelUsageFrame& f, const QJSValue& object, const char* field) {
    assistantMemberWrite(f, object, field, consentNull());
}
bool connectionOwnerCurrent(const PanelUsageFrame& f, const std::function<QJSValue(uint)>& v) {
    const auto dialog = panelUsageContextRead(f, "dialog");
    if (!consentQtObject(f, dialog) || !consentQtObject(f, v(0))) return false;
    const auto currentDialog = panelUsageContextRead(f, "dialog");
    if (!consentFieldEquals(f, currentDialog, "assistant", v(0))) return false;
    const auto approvalDialog = panelUsageContextRead(f, "dialog");
    if (!consentFieldEquals(f, approvalDialog, "approvalOwner", v(7))) return false;
    const auto project = assistantContextField(f, "Session", "project");
    if (!panelUsageReady(f) || !project.strictlyEquals(v(1))) return false;
    if (!consentFieldEquals(f, v(0), "selectedModel", v(2)) || !consentFieldEquals(f, v(0), "selectedEffort", v(3))) return false;
    if (panelUsageTruth(v(4))) {
        const auto account = panelUsageRead(f, v(0), "account");
        if (!consentFieldEquals(f, account, "email", v(5))) return false;
        const auto accountAgain = panelUsageRead(f, v(0), "account");
        if (!consentFieldEquals(f, accountAgain, "planType", v(6))) return false;
    }
    const auto blocked = panelUsageRead(f, v(0), "contextApprovalBlocked");
    if (!panelUsageReady(f) || panelUsageTruth(blocked)) return false;
    const auto callback = panelUsageRead(f, v(7), "currentDraft");
    if (!panelUsageReady(f)) return false;
    return !callback.isCallable() || panelUsageTruth(panelUsageMemberCall(f, v(7), "currentDraft"));
}
QJSValue connectionCurrent(const PanelUsageFrame& f, const std::function<QJSValue(uint)>& v) {
    if (!connectionOwnerCurrent(f, v)) return QJSValue(false);
    const auto context = panelUsageRead(f, v(0), "contextConsentIdentity");
    if (!connectionOwnerCurrent(f, v)) return QJSValue(false);
    const auto offered = v(8);
    const auto length = panelUsageRead(f, offered, "length");
    if (!assistantRelation(f, length, QJSValue(0), 1)) return QJSValue(false);
    const auto identity = assistantContextField(f, "dialog", "disclosedContextIdentity");
    return QJSValue(panelUsageReady(f) && identity.strictlyEquals(offered) && context.strictlyEquals(offered));
}
}

#ifndef Q_OS_WASM
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
    const auto outer = panelUsageContextRead(engine, "JSON");
    const auto inner = panelUsageContextRead(engine, "JSON");
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
            if (!panelUsageTruth(selected) || panelUsageGreater(engine, window, selected)) {
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
    if (panelUsageTruth(primary)) return panelUsageField(engine, view, "accountData", "planType");
    const auto known = engine->newArray();
    const auto buckets = panelUsageBuckets(engine, view);
    panelUsageEach(engine, buckets, [&](const QJSValue& bucket) {
        const auto offered = panelUsageRead(engine, bucket, "planType");
        if (!panelUsageReady(engine)) return false;
        if (!panelUsageTruth(offered)) return true;
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
    if (!panelUsageTruth(offered)) return QJSValue(QString());
    const auto array = panelUsageContextRead(engine, "Array");
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
    if (panelUsageTruth(selected)) {
        const auto text = panelUsageText(engine, QT_TRANSLATE_NOOP("AssistantPanel", "%1 · %2% used"));
        const auto first = panelUsageArg(engine, text, [&] { return panelUsageField(engine, view, "usageWindow", "label"); });
        return panelUsageArg(engine, first, [&] { return panelUsageField(engine, view, "usageWindow", "usedPercent"); });
    }
    const auto status = panelUsageField(engine, view, "usageData", "statusText");
    return !panelUsageReady(engine) ? QJSValue() : panelUsageTruth(status) ? status :
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
    const auto date = panelUsageContextRead(engine, "Date");
    if (!panelUsageReady(engine)) return {};
    const double milliseconds = value.toNumber() * 1000;
    const auto instance = panelUsageConstruct(engine, date, {QJSValue(milliseconds)});
    const auto time = panelUsageMemberCall(engine, instance, "getTime");
    const auto valid = panelUsageGlobalCall(engine, "isFinite", {time});
    if (!panelUsageReady(engine)) return {};
    if (!panelUsageTruth(valid)) return unavailable();
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
    if (!panelUsageReady(engine) || panelUsageTruth(connected)) return;
    const auto target = panelUsageView(engine, dialog);
    panelUsageMemberCall(engine, target, "close");
}


 // namespace

void ApplicationInfo::composerAcknowledgeVisiblePrompt() const {
    const auto frame = panelUsageEngine(this);
    const auto original = panelUsageContextRead(frame, "submittedDrafts");
    const auto ownerRevision = panelUsageContextRead(frame, "draftOwnerRevision");
    if (!panelUsageReady(frame)) return;
    const auto pending = frame->newArray();
    QJSValue acknowledged(QJSValue::NullValue);
    panelUsageEach(frame, original, [&](const QJSValue& draft) {
        QJSValue status(QString{});
        for (double index = 0; panelUsageReady(frame); ++index) {
            const auto messages = assistantContextField(frame, "assistant", "messages");
            const auto count = panelUsageRead(frame, messages, "count");
            if (!assistantRelation(frame, QJSValue(index), count, 0)) break;
            const auto id = assistantMessageText(frame, index, "id");
            const auto draftId = panelUsageRead(frame, draft, "id");
            if (!panelUsageReady(frame)) return false;
            if (!id.strictlyEquals(draftId)) continue;
            const auto kind = assistantMessageText(frame, index, "kind");
            if (!panelUsageReady(frame)) return false;
            if (kind.strictlyEquals(QJSValue(QStringLiteral("user")))) {
                status = assistantMessageText(frame, index, "status");
                break;
            }
        }
        if (!panelUsageReady(frame)) return false;
        if (status.strictlyEquals(QJSValue(QStringLiteral("completed")))) {
            if (assistantDraftMatchesEditor(frame, draft)) acknowledged = draft;
        } else if (!status.strictlyEquals(QJSValue(QStringLiteral("refused")))
                   && !status.strictlyEquals(QJSValue(QStringLiteral("interrupted")))) {
            panelUsageMemberCall(frame, pending, "push", {draft});
        }
        return panelUsageReady(frame);
    });
    if (!panelUsageReady(frame) || !assistantSameName(frame, original, "submittedDrafts")
        || !assistantSameName(frame, ownerRevision, "draftOwnerRevision")) return;
    panelUsageContextWrite(frame, "submittedDrafts", pending);
    if (!panelUsageReady(frame) || !panelUsageTruth(acknowledged) || !assistantSameName(frame, ownerRevision, "draftOwnerRevision")) return;
    // Final checks intentionally read the current editor before clearing it.
    const auto revision = panelUsageContextRead(frame, "textRevision");
    const auto acknowledgedRevision = panelUsageRead(frame, acknowledged, "revision");
    if (!panelUsageReady(frame) || !revision.strictlyEquals(acknowledgedRevision)) return;
    const auto text = assistantContextField(frame, "editor", "text");
    const auto acknowledgedText = panelUsageRead(frame, acknowledged, "text");
    if (!panelUsageReady(frame) || !text.strictlyEquals(acknowledgedText) || !assistantEditorIdle(frame)) return;
    const auto editor = panelUsageContextRead(frame, "editor");
    panelUsageMemberCall(frame, editor, "clear");
}
bool ApplicationInfo::assistantContainsItem(const QJSValue& ancestor, const QJSValue& item) const {
    return assistantContains(panelUsageEngine(this), ancestor, item);
}
QJSValue ApplicationInfo::assistantWorkflowPage() const {
    const auto frame = panelUsageEngine(this);
    QJSValueList loaders;
    for (const char* name : {"projectLoader", "structureLoader", "experimentLoader", "analysisLoader", "reportLoader"})
        loaders.append(panelUsageContextRead(frame, name));
    const auto current = assistantContextField(frame, "appBarCentralTabs", "currentIndex");
    const auto number = panelUsageNumber(frame, current);
    if (!number) return {};
    const auto index = *number - 1;
    if (!(index >= 0 && index < loaders.size())) return QJSValue(QJSValue::NullValue);
    const auto array = assistantGeometryArray(frame, loaders);
    const auto loader = panelUsageIndex(frame, array, static_cast<quint32>(index));
    return panelUsageRead(frame, loader, "item");
}
void ApplicationInfo::rehostAssistant() const {
    const auto frame = panelUsageEngine(this);
    assistantIncrementEpoch(frame);
    const auto active = panelUsageContextRead(frame, "activeAssistantHost");
    if (!panelUsageReady(frame) || !panelUsageTruth(active)) return;
    const auto panel = panelUsageContextRead(frame, "assistantPanel");
    if (!panelUsageReady(frame) || !panelUsageTruth(panel)) return;
    const auto previous = panelUsageContextRead(frame, "activeFocusItem");
    const auto content = assistantContextField(frame, "assistantPanel", "contentItem");
    const auto restore = assistantContainsCall(frame, content, previous);
    const auto actualPanel = panelUsageContextRead(frame, "assistantPanel");
    const auto fallback = panelUsageContextRead(frame, "assistantFallbackHost");
    assistantMemberWrite(frame, actualPanel, "parent", fallback);
    const auto epoch = panelUsageContextRead(frame, "assistantFocusEpoch");
    const auto host = panelUsageContextRead(frame, "activeAssistantHost");
    const auto project = assistantContextField(frame, "Session", "project");
    if (panelUsageReady(frame) && restore) panelUsageCallLater(frame, panelUsageClosure(frame, 2, {epoch, host, project, previous}));
}
void ApplicationInfo::focusAssistantOpener() const { assistantFocusOpener(panelUsageEngine(this)); }
void ApplicationInfo::retireAssistantFocus() const {
    const auto frame = panelUsageEngine(this);
    assistantIncrementEpoch(frame);
    panelUsageGlobalCall(frame, "focusAssistantOpener", {});
}
void ApplicationInfo::restoreAssistantFocus() const {
    const auto frame = panelUsageEngine(this);
    const auto previous = panelUsageContextRead(frame, "assistantPreviousFocus");
    const auto page = panelUsageContextRead(frame, "assistantPreviousPage");
    const auto host = panelUsageContextRead(frame, "assistantPreviousHost");
    const auto project = panelUsageContextRead(frame, "assistantPreviousProject");
    const auto epoch = panelUsageContextRead(frame, "assistantFocusEpoch");
    for (const char* name : {"assistantPreviousFocus", "assistantPreviousPage", "assistantPreviousHost", "assistantPreviousProject"})
        panelUsageContextWrite(frame, name, QJSValue(QJSValue::NullValue));
    const auto takeover = panelUsageContextRead(frame, "assistantManualTakeover");
    if (!panelUsageReady(frame) || panelUsageTruth(takeover)) return;
    panelUsageCallLater(frame, panelUsageClosure(frame, 3, {previous, page, host, project, epoch}));
}
bool ApplicationInfo::assistantHomeFocusCovered() const {
    const auto frame = panelUsageEngine(this);
    const auto item = panelUsageContextRead(frame, "activeFocusItem");
    const auto panel = panelUsageContextRead(frame, "assistantPanel");
    if (!panelUsageReady(frame) || !panelUsageTruth(panel)) return false;
    const auto visible = assistantContextField(frame, "assistantPanel", "visible");
    if (!panelUsageReady(frame) || !panelUsageTruth(visible) || !panelUsageTruth(item)) return false;
    const auto page = panelUsageContextRead(frame, "assistantCurrentPage");
    if (!assistantContainsCall(frame, page, item)) return false;
    for (QJSValue current = item; panelUsageReady(frame) && panelUsageTruth(current); current = panelUsageRead(frame, current, "parent")) {
        QJSValueList values;
        for (const char* name : {"x", "y", "width", "height", "scale", "rotation"}) values.append(panelUsageRead(frame, current, name));
        const auto geometry = assistantGeometryArray(frame, values);
        if (!assistantGeometryFinite(frame, geometry)) return false;
    }
    QJSValueList strip;
    for (const char* name : {"x", "y"}) strip.append(assistantContextField(frame, "assistantPanel", name));
    for (const char* name : {"x", "y", "width", "height"}) strip.append(assistantContextField(frame, "activeAssistantHost", name));
    for (const char* name : {"width", "height"}) strip.append(assistantContextField(frame, "window", name));
    if (!assistantGeometryFinite(frame, assistantGeometryArray(frame, strip))) return false;
    const auto content = assistantContextField(frame, "assistantPanel", "contentItem");
    const auto width = panelUsageRead(frame, item, "width");
    const auto height = panelUsageRead(frame, item, "height");
    const auto rectangle = panelUsageMemberCall(frame, item, "mapToItem", {content, QJSValue(0), QJSValue(0), width, height});
    const auto greaterZero = [&](const char* field) { return assistantRelation(frame, panelUsageRead(frame, rectangle, field), QJSValue(0), 1); };
    const auto nonnegative = [&](const char* field) { return assistantRelation(frame, panelUsageRead(frame, rectangle, field), QJSValue(0), 2); };
    if (!greaterZero("width") || !greaterZero("height") || !nonnegative("x") || !nonnegative("y")) return false;
    for (const auto& pair : {std::pair{"x", "width"}, std::pair{"y", "height"}}) {
        const auto position = panelUsageRead(frame, rectangle, pair.first);
        const auto extent = panelUsageRead(frame, rectangle, pair.second);
        const auto end = panelUsageAdd(frame, position, extent);
        const auto currentContent = assistantContextField(frame, "assistantPanel", "contentItem");
        const auto available = panelUsageRead(frame, currentContent, pair.second);
        if (!assistantRelation(frame, end, available, 3)) return false;
    }
    return panelUsageReady(frame);
}
void ApplicationInfo::enforceAssistantHomeFocus() const {
    const auto frame = panelUsageEngine(this);
    const auto takeover = panelUsageContextRead(frame, "assistantManualTakeover");
    if (!panelUsageReady(frame) || panelUsageTruth(takeover)) return;
    const auto covered = panelUsageContextRead(frame, "assistantHomeFocusCovered");
    if (!panelUsageReady(frame) || !panelUsageTruth(covered)) return;
    const auto shown = assistantContextField(frame, "assistantPanel", "shown");
    if (!panelUsageReady(frame)) return;
    if (panelUsageTruth(shown)) {
        const auto panel = panelUsageContextRead(frame, "assistantPanel");
        panelUsageMemberCall(frame, panel, "focusComposer");
    } else panelUsageGlobalCall(frame, "focusAssistantOpener", {});
}

 // namespace

QJSValue ApplicationInfo::composerCaptureConsentDraft() const {
    const auto f = panelUsageEngine(this);
    const auto composing = assistantContextField(f, "editor", "inputMethodComposing");
    if (!panelUsageReady(f) || panelUsageTruth(composing)) return consentNull();
    const auto preedit = assistantContextField(f, "editor", "preeditText");
    const auto length = panelUsageRead(f, preedit, "length");
    if (!panelUsageReady(f) || panelUsageTruth(length)) return consentNull();
    const auto component = panelUsageContextRead(f, "composer");
    const auto draft = panelUsageLiteral(f);
    panelUsageWrite(f, draft.value, "owner", panelUsageContextRead(f, "assistant"));
    panelUsageWrite(f, draft.value, "text", assistantContextField(f, "editor", "text"));
    for (const auto& field : {std::pair{"revision", "textRevision"}, std::pair{"ownerRevision", "draftOwnerRevision"}, std::pair{"files", "consentFileRevision"}})
        panelUsageWrite(f, draft.value, field.first, panelUsageContextRead(f, field.second));
    panelUsageWrite(f, draft.value, "project", assistantContextField(f, "Session", "project"));
    panelUsageWrite(f, draft.value, "model", assistantContextField(f, "assistant", "selectedModel"));
    panelUsageWrite(f, draft.value, "effort", assistantContextField(f, "assistant", "selectedEffort"));
    auto account = assistantContextField(f, "assistant", "account");
    panelUsageWrite(f, draft.value, "email", panelUsageRead(f, account, "email"));
    account = assistantContextField(f, "assistant", "account");
    panelUsageWrite(f, draft.value, "plan", panelUsageRead(f, account, "planType"));
    const auto actual = panelUsageComplete(f, draft);
    const auto owner = panelUsageRead(f, actual, "owner");
    const auto context = panelUsageRead(f, owner, "contextConsentIdentity");
    const auto currentOwner = [&] {
        if (!consentQtObject(f, component)) return false;
        const auto captured = panelUsageRead(f, actual, "owner");
        if (!consentQtObject(f, captured)) return false;
        return consentFieldsEqual(f, actual, "owner", component, "assistant");
    };
    if (!currentOwner()) return consentNull();
    assistantMemberWrite(f, actual, "context", context);
    const auto owned = panelUsageMemberCall(f, component, "ownsConsentDraft", {actual});
    if (!currentOwner()) return consentNull();
    return panelUsageTruth(owned) ? actual : consentNull();
}
bool ApplicationInfo::composerOwnsConsentDraft(const QJSValue& draft) const {
    const auto f = panelUsageEngine(this);
    if (draft.isNull()) return false;
    const auto owner = panelUsageRead(f, draft, "owner");
    if (!assistantSameName(f, owner, "assistant")) return false;
    const auto original = panelUsageContextRead(f, "assistant");
    const auto context = panelUsageRead(f, original, "contextConsentIdentity");
    const auto composer = panelUsageContextRead(f, "composer");
    if (!consentQtObject(f, composer) || !consentQtObject(f, original) || !assistantSameName(f, original, "assistant")) return false;
    if (!consentFieldEquals(f, draft, "owner", original)) return false;
    const auto text = panelUsageRead(f, draft, "text");
    const auto editorText = assistantContextField(f, "editor", "text");
    if (!panelUsageReady(f) || !text.strictlyEquals(editorText)) return false;
    for (const auto& field : {std::pair{"revision", "textRevision"}, std::pair{"ownerRevision", "draftOwnerRevision"}, std::pair{"files", "consentFileRevision"}}) {
        const auto value = panelUsageRead(f, draft, field.first);
        if (!assistantSameName(f, value, field.second)) return false;
    }
    const auto project = panelUsageRead(f, draft, "project");
    const auto currentProject = assistantContextField(f, "Session", "project");
    if (!panelUsageReady(f) || !project.strictlyEquals(currentProject)) return false;
    const auto offered = panelUsageRead(f, draft, "context");
    const auto length = panelUsageRead(f, offered, "length");
    if (!assistantRelation(f, length, QJSValue(0), 1) || !consentFieldEquals(f, draft, "context", context)) return false;
    for (const auto& field : {std::pair{"model", "selectedModel"}, std::pair{"effort", "selectedEffort"}}) {
        const auto value = panelUsageRead(f, draft, field.first);
        const auto selected = assistantContextField(f, "assistant", field.second);
        if (!panelUsageReady(f) || !value.strictlyEquals(selected)) return false;
    }
    for (const auto& field : {std::pair{"email", "email"}, std::pair{"plan", "planType"}}) {
        const auto value = panelUsageRead(f, draft, field.first);
        const auto account = assistantContextField(f, "assistant", "account");
        const auto selected = panelUsageRead(f, account, field.second);
        if (!panelUsageReady(f) || !value.strictlyEquals(selected)) return false;
    }
    return assistantEditorIdle(f);
}
QJSValue ApplicationInfo::composerSubmitApprovedDraft(const QJSValue& draft) const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "composer");
    const auto original = panelUsageContextRead(f, "assistant");
    const auto owned = panelUsageMemberCall(f, component, "ownsConsentDraft", {draft});
    const auto retired = QJSValue(QStringLiteral("retired"));
    const auto waiting = QJSValue(QStringLiteral("waiting"));
    if (!consentOwner(f, component, original) || !panelUsageTruth(owned)) return retired;
    const auto connected = panelUsageRead(f, original, "connected");
    if (!panelUsageReady(f) || !panelUsageTruth(connected)) return waiting;
    const auto required = panelUsageRead(f, original, "contextConsentRequired");
    if (!consentOwner(f, component, original)) return retired;
    const auto stillOwned = panelUsageMemberCall(f, component, "ownsConsentDraft", {draft});
    if (!consentOwner(f, component, original) || !panelUsageTruth(stillOwned)) return retired;
    if (panelUsageTruth(required)) return waiting;
    const auto state = panelUsageRead(f, original, "state");
    if (!panelUsageReady(f) || !state.strictlyEquals(QJSValue(QStringLiteral("idle")))) return waiting;
    const auto canCancel = panelUsageRead(f, original, "canCancel");
    if (!panelUsageReady(f) || panelUsageTruth(canCancel)) return waiting;
    const auto result = panelUsageMemberCall(f, component, "submit", {draft});
    return panelUsageReady(f) && panelUsageTruth(result) ? panelUsageRead(f, result, "status") : retired;
}
bool ApplicationInfo::composerExplainBlockedSubmission() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "composer");
    const auto original = panelUsageContextRead(f, "assistant");
    const auto blocked = panelUsageRead(f, original, "contextApprovalBlocked");
    if (!consentOwner(f, component, original)) return true;
    if (!panelUsageTruth(blocked)) return false;
    const auto connected = panelUsageRead(f, original, "connected");
    if (!panelUsageReady(f) || !panelUsageTruth(connected)) return true;
    const auto hasDraft = panelUsageRead(f, component, "hasDraft");
    if (!panelUsageReady(f) || !panelUsageTruth(hasDraft)) return true;
    const auto composing = assistantContextField(f, "editor", "inputMethodComposing");
    if (!panelUsageReady(f) || panelUsageTruth(composing)) return true;
    const auto preedit = assistantContextField(f, "editor", "preeditText");
    if (panelUsageTruth(panelUsageRead(f, preedit, "length")) || !panelUsageReady(f)) return true;
    const auto text = assistantContextField(f, "editor", "text");
    const auto revision = panelUsageContextRead(f, "textRevision");
    const auto ownerRevision = panelUsageContextRead(f, "draftOwnerRevision");
    const auto files = panelUsageContextRead(f, "consentFileRevision");
    const auto project = assistantContextField(f, "Session", "project");
    const auto model = panelUsageRead(f, original, "selectedModel");
    const auto effort = panelUsageRead(f, original, "selectedEffort");
    auto account = panelUsageRead(f, original, "account");
    const auto email = panelUsageRead(f, account, "email");
    account = panelUsageRead(f, original, "account");
    const auto plan = panelUsageRead(f, account, "planType");
    panelUsageMemberCall(f, original, "submitDraft", {text});
    if (!consentOwner(f, component, original) || !consentFieldEquals(f, component, "textRevision", revision)
        || !consentFieldEquals(f, component, "draftOwnerRevision", ownerRevision)) return true;
    const auto currentText = assistantContextField(f, "editor", "text");
    if (!panelUsageReady(f) || !text.strictlyEquals(currentText) || !consentFieldEquals(f, component, "consentFileRevision", files)) return true;
    const auto currentProject = assistantContextField(f, "Session", "project");
    if (!panelUsageReady(f) || !project.strictlyEquals(currentProject) || !consentFieldEquals(f, original, "selectedModel", model)
        || !consentFieldEquals(f, original, "selectedEffort", effort)) return true;
    account = panelUsageRead(f, original, "account");
    if (!consentFieldEquals(f, account, "email", email)) return true;
    account = panelUsageRead(f, original, "account");
    if (!consentFieldEquals(f, account, "planType", plan)) return true;
    const auto stillBlocked = panelUsageRead(f, original, "contextApprovalBlocked");
    if (panelUsageReady(f) && panelUsageTruth(stillBlocked)) panelUsageMemberCall(f, component, "submissionBlocked");
    return true;
}
QJSValue ApplicationInfo::composerSubmit(const QJSValue& approved) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(approved)) {
        const auto local = panelUsageContextRead(f, "localWorkReport");
        if (!panelUsageReady(f)) return {};
        if (panelUsageTruth(local)) { panelUsageGlobalCall(f, "submitWorkReport", {}); return {}; }
    }
    const auto component = panelUsageContextRead(f, "composer");
    const auto original = panelUsageContextRead(f, "assistant");
    if (!panelUsageTruth(approved)) {
        const auto blocked = panelUsageMemberCall(f, component, "explainBlockedSubmission");
        if (!panelUsageReady(f) || panelUsageTruth(blocked)) return {};
    }
    if (!consentOwner(f, component, original)) return {};
    const auto requested = panelUsageTruth(approved) ? approved : panelUsageMemberCall(f, component, "captureConsentDraft");
    if (!consentOwner(f, component, original) || !panelUsageTruth(requested)) return {};
    if (!panelUsageTruth(approved)) {
        panelUsageMemberCall(f, component, "submissionRequested", {requested});
        if (!consentOwner(f, component, original)) return {};
    }
    const auto owned = panelUsageMemberCall(f, component, "ownsConsentDraft", {requested});
    if (!consentOwner(f, component, original) || !panelUsageTruth(owned)) return {};
    const auto hasDraft = panelUsageContextRead(f, "hasDraft");
    if (!panelUsageReady(f) || !panelUsageTruth(hasDraft)) return {};
    const auto connected = panelUsageRead(f, original, "connected");
    bool waiting = !panelUsageTruth(connected);
    if (!waiting) {
        const auto cancel = panelUsageRead(f, original, "canCancel");
        if (panelUsageTruth(cancel)) waiting = !panelUsageTruth(panelUsageContextRead(f, "canSteer"));
    }
    if (!panelUsageReady(f)) return {};
    if (waiting) return panelUsageTruth(approved) ? consentStatus(f, "waiting") : consentNull();
    const auto required = panelUsageRead(f, original, "contextConsentRequired");
    if (!consentOwner(f, component, original)) return {};
    const auto stillOwned = panelUsageMemberCall(f, component, "ownsConsentDraft", {requested});
    if (!consentOwner(f, component, original) || !panelUsageTruth(stillOwned)) return {};
    if (panelUsageTruth(required)) {
        if (panelUsageTruth(approved)) return consentStatus(f, "waiting");
        const auto blocked = panelUsageRead(f, original, "contextApprovalBlocked");
        if (panelUsageTruth(blocked)) { panelUsageMemberCall(f, component, "explainBlockedSubmission"); return {}; }
        const auto text = panelUsageRead(f, requested, "text");
        panelUsageMemberCall(f, component, "contextApprovalRequested", {text});
        return {};
    }
    const auto text = assistantContextField(f, "editor", "text");
    const auto revision = panelUsageContextRead(f, "textRevision");
    const auto ownerRevision = panelUsageContextRead(f, "draftOwnerRevision");
    if (panelUsageTruth(approved)) {
        const auto state = panelUsageRead(f, original, "state");
        if (!state.strictlyEquals(QJSValue(QStringLiteral("idle")))) return consentStatus(f, "waiting");
        if (panelUsageTruth(panelUsageRead(f, original, "canCancel"))) return consentStatus(f, "waiting");
    }
    const auto admission = panelUsageTruth(approved) ? panelUsageMemberCall(f, original, "submitDraftAdmission", {text}) : consentNull();
    const auto rowId = panelUsageTruth(approved) ? (panelUsageTruth(admission) ? panelUsageRead(f, admission, "row_id") : QJSValue(QString{}))
                                       : panelUsageMemberCall(f, original, "submitDraft", {text});
    if (!consentOwner(f, component, original)) return {};
    const auto length = panelUsageRead(f, rowId, "length");
    if (panelUsageTruth(length) && assistantSameName(f, ownerRevision, "draftOwnerRevision")) {
        const auto submitted = panelUsageContextRead(f, "submittedDrafts");
        const auto pending = panelUsageMemberCall(f, submitted, "slice");
        const auto literal = panelUsageLiteral(f);
        panelUsageWrite(f, literal.value, "id", rowId);
        panelUsageWrite(f, literal.value, "text", text);
        panelUsageWrite(f, literal.value, "revision", revision);
        panelUsageMemberCall(f, pending, "push", {panelUsageComplete(f, literal)});
        panelUsageContextWrite(f, "submittedDrafts", pending);
        panelUsageGlobalCall(f, "acknowledgeVisiblePrompt", {});
    }
    return admission;
}

void ApplicationInfo::panelRetireConsentSend() const { panelUsageContextWrite(panelUsageEngine(this), "consentSend", consentNull()); }
bool ApplicationInfo::panelOwnsConsentSend(const QJSValue& intent) const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto draft = panelUsageContextRead(f, "composer");
    const auto dialog = panelUsageContextRead(f, "connectionDialog");
    if (!consentQtObject(f, dialog) || intent.isNull() || !assistantSameName(f, intent, "consentSend")
        || !consentFieldEquals(f, intent, "owner", original) || !consentFieldsEqual(f, intent, "offer", dialog, "approvalOwner")) return false;
    auto value = panelUsageRead(f, intent, "draft");
    const auto owned = panelUsageMemberCall(f, draft, "ownsConsentDraft", {value});
    if (!consentPanelOwner(f, component, draft, original) || !panelUsageTruth(owned) || !consentQtObject(f, dialog)
        || !consentFieldsEqual(f, intent, "offer", dialog, "approvalOwner")) return false;
    const auto context = panelUsageRead(f, original, "contextConsentIdentity");
    if (!consentPanelOwner(f, component, draft, original) || !consentQtObject(f, dialog)
        || !consentFieldEquals(f, component, "consentSend", intent) || !consentFieldEquals(f, intent, "owner", original)
        || !consentFieldsEqual(f, intent, "offer", dialog, "approvalOwner")) return false;
    value = panelUsageRead(f, intent, "project");
    const auto project = assistantContextField(f, "Session", "project");
    if (!panelUsageReady(f) || !value.strictlyEquals(project)) return false;
    if (!panelUsageTruth(panelUsageRead(f, context, "length")) || !panelUsageReady(f) || !consentFieldEquals(f, intent, "context", context)) return false;
    if (!consentFieldsEqual(f, original, "selectedModel", intent, "model") || !consentFieldsEqual(f, original, "selectedEffort", intent, "effort")) return false;
    value = panelUsageRead(f, intent, "draft");
    const auto stillOwned = panelUsageMemberCall(f, draft, "ownsConsentDraft", {value});
    return consentPanelOwner(f, component, draft, original) && panelUsageTruth(stillOwned)
        && consentFieldEquals(f, component, "consentSend", intent) && consentQtObject(f, dialog)
        && consentFieldsEqual(f, intent, "offer", dialog, "approvalOwner");
}
void ApplicationInfo::panelResumeConsentSend() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto draft = panelUsageContextRead(f, "composer");
    const auto intent = panelUsageRead(f, component, "consentSend");
    if (!panelUsageReady(f) || !panelUsageTruth(intent) || panelUsageTruth(panelUsageRead(f, intent, "submitting"))) return;
    const auto owned = panelUsageMemberCall(f, component, "ownsConsentSend", {intent});
    if (!consentPanelOwner(f, component, draft, original)) return;
    if (!panelUsageTruth(owned)) {
        if (consentFieldEquals(f, component, "consentSend", intent)) panelUsageMemberCall(f, component, "retireConsentSend");
        return;
    }
    if (!panelUsageTruth(panelUsageRead(f, intent, "approved")) || !panelUsageReady(f)) return;
    const auto required = panelUsageRead(f, original, "contextConsentRequired");
    if (!consentPanelOwner(f, component, draft, original)) return;
    const auto stillOwned = panelUsageMemberCall(f, component, "ownsConsentSend", {intent});
    if (!consentPanelOwner(f, component, draft, original) || !panelUsageTruth(stillOwned)) return;
    if (!panelUsageTruth(panelUsageRead(f, original, "connected")) || panelUsageTruth(required)
        || !panelUsageTruth(panelUsageRead(f, original, "draftAdmissionReady"))
        || !consentFieldEquals(f, original, "state", QJSValue(QStringLiteral("idle")))
        || panelUsageTruth(panelUsageRead(f, original, "canCancel")) || !panelUsageReady(f)) return;
    assistantMemberWrite(f, intent, "submitting", QJSValue(true));
    const auto requested = panelUsageRead(f, intent, "draft");
    const auto result = panelUsageMemberCall(f, draft, "submitApprovedDraft", {requested});
    if (!consentPanelOwner(f, component, draft, original) || !consentFieldEquals(f, component, "consentSend", intent)) return;
    assistantMemberWrite(f, intent, "submitting", QJSValue(false));
    if (!result.strictlyEquals(QJSValue(QStringLiteral("waiting")))) panelUsageMemberCall(f, component, "retireConsentSend");
}
void ApplicationInfo::panelConsentContextChanged() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto intent = panelUsageRead(f, component, "consentSend");
    const auto owned = panelUsageTruth(intent) ? panelUsageMemberCall(f, component, "ownsConsentSend", {intent}) : QJSValue(true);
    if (!consentOwner(f, component, original)) return;
    if (!panelUsageTruth(owned)) {
        if (consentFieldEquals(f, component, "consentSend", intent)) panelUsageMemberCall(f, component, "retireConsentSend");
    } else if (consentFieldEquals(f, component, "consentSend", intent)) panelUsageMemberCall(f, component, "scheduleConsentSend");
}
void ApplicationInfo::panelContextApproved(const QJSValue& offer) const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto dialog = panelUsageContextRead(f, "connectionDialog");
    const auto intent = panelUsageRead(f, component, "consentSend");
    if (!panelUsageReady(f) || !panelUsageTruth(intent) || !consentQtObject(f, dialog)
        || !consentFieldEquals(f, intent, "offer", offer) || !consentFieldEquals(f, dialog, "approvalOwner", offer)) return;
    const auto owned = panelUsageMemberCall(f, component, "ownsConsentSend", {intent});
    if (!consentOwner(f, component, original)) return;
    if (!panelUsageTruth(owned)) {
        if (consentFieldEquals(f, component, "consentSend", intent)) panelUsageMemberCall(f, component, "retireConsentSend");
        return;
    }
    if (!consentQtObject(f, dialog) || !consentFieldEquals(f, component, "consentSend", intent)
        || !consentFieldEquals(f, intent, "offer", offer) || !consentFieldEquals(f, dialog, "approvalOwner", offer)) return;
    assistantMemberWrite(f, intent, "approved", QJSValue(true));
    panelUsageMemberCall(f, component, "scheduleConsentSend");
}
void ApplicationInfo::panelScheduleConsentSend() const {
    const auto f = panelUsageEngine(this);
    const auto qt = panelUsageContextRead(f, "Qt");
    const auto callback = panelUsageContextRead(f, "resumeConsentSend");
    panelUsageMemberCall(f, qt, "callLater", {callback});
}

QJSValue ApplicationInfo::connectionBeginOffer() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageReady(f)) return {};
    const auto offer = f->newObject();
    panelUsageContextWrite(f, "acceptedOffer", consentNull());
    panelUsageContextWrite(f, "approvalOwner", offer);
    return offer;
}
void ApplicationInfo::connectionPresentOffer(const QJSValue& offer) const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "dialog");
    const auto original = assistantContextField(f, "dialog", "assistant");
    const auto token = offer.isUndefined() ? panelUsageMemberCall(f, component, "beginOffer") : offer;
    if (!consentOwner(f, component, original) || token.isNull() || !consentFieldEquals(f, component, "approvalOwner", token)) return;
    panelUsageMemberCall(f, component, "open");
}
void ApplicationInfo::connectionResumeAcceptedOffer() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "dialog");
    const auto accepted = panelUsageRead(f, component, "acceptedOffer");
    if (!panelUsageReady(f) || !panelUsageTruth(accepted) || panelUsageTruth(panelUsageRead(f, accepted, "submitting"))) return;
    const auto original = panelUsageRead(f, accepted, "owner");
    const auto current = panelUsageMemberCall(f, accepted, "current");
    bool retired = !panelUsageTruth(current) || !consentQtObject(f, component) || !consentQtObject(f, original)
        || !consentFieldEquals(f, component, "acceptedOffer", accepted);
    if (!retired) retired = !panelUsageTruth(panelUsageRead(f, original, "connected"));
    if (!panelUsageReady(f)) return;
    if (retired) {
        if (consentQtObject(f, component) && consentFieldEquals(f, component, "acceptedOffer", accepted)) consentClear(f, component, "acceptedOffer");
        return;
    }
    const auto ready = panelUsageRead(f, original, "draftAdmissionReady");
    if (!consentQtObject(f, component) || !consentQtObject(f, original) || !consentFieldEquals(f, component, "acceptedOffer", accepted)
        || !panelUsageTruth(panelUsageMemberCall(f, accepted, "current")) || !panelUsageTruth(ready) || !panelUsageReady(f)) return;
    assistantMemberWrite(f, accepted, "submitting", QJSValue(true));
    const auto context = panelUsageRead(f, accepted, "context");
    const auto result = panelUsageMemberCall(f, original, "acceptConnectionOffer", {context});
    if (!consentQtObject(f, component) || !consentQtObject(f, original) || !consentFieldEquals(f, component, "acceptedOffer", accepted)) return;
    assistantMemberWrite(f, accepted, "submitting", QJSValue(false));
    if (result.strictlyEquals(QJSValue(QStringLiteral("waiting"))) && panelUsageTruth(panelUsageMemberCall(f, accepted, "current"))) return;
    consentClear(f, component, "acceptedOffer");
    if (result.strictlyEquals(QJSValue(QStringLiteral("approved"))) && panelUsageTruth(panelUsageMemberCall(f, accepted, "current"))) {
        const auto approval = panelUsageRead(f, accepted, "approval");
        panelUsageMemberCall(f, component, "contextApproved", {approval});
    }
}
void ApplicationInfo::connectionScheduleAcceptedOffer() const {
    const auto f = panelUsageEngine(this);
    const auto qt = panelUsageContextRead(f, "Qt");
    const auto callback = panelUsageContextRead(f, "resumeAcceptedOffer");
    panelUsageMemberCall(f, qt, "callLater", {callback});
}
void ApplicationInfo::connectionShowFailure() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "connectionAttempt")) || !panelUsageReady(f)) return;
    if (assistantContextField(f, "assistant", "state").strictlyEquals(QJSValue(QStringLiteral("connecting")))) return;
    panelUsageContextWrite(f, "connectionAttempt", QJSValue(false));
    if (panelUsageTruth(assistantContextField(f, "assistant", "connected")) || !panelUsageReady(f)) return;
    const auto error = assistantContextField(f, "assistant", "lastError");
    if (!assistantRelation(f, panelUsageRead(f, error, "length"), QJSValue(0), 1)) return;
    const auto failure = panelUsageContextRead(f, "connectionFailure");
    const auto message = assistantContextField(f, "assistant", "lastError");
    assistantMemberWrite(f, failure, "message", message);
    const auto actual = panelUsageContextRead(f, "connectionFailure");
    panelUsageMemberCall(f, actual, "open");
}
void ApplicationInfo::connectionRefreshContext() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "dialog");
    const auto original = assistantContextField(f, "dialog", "assistant");
    if (!consentQtObject(f, component) || !consentQtObject(f, original)) return;
    const auto request = f->newObject();
    assistantMemberWrite(f, component, "contextPresentation", request);
    const auto current = [&] { return consentOwner(f, component, original) && consentFieldEquals(f, component, "contextPresentation", request); };
    if (!current()) return;
    const auto identity = panelUsageRead(f, original, "contextConsentIdentity");
    const bool firstCurrent = panelUsageReady(f) && current();
    if (panelUsageReady(f) && !firstCurrent) return;
    if (panelUsageReady(f)) {
        const auto exact = panelUsageRead(f, original, "contextPreview");
        const bool secondCurrent = panelUsageReady(f) && current();
        if (panelUsageReady(f) && !secondCurrent) return;
        if (panelUsageReady(f)) {
            const auto actual = panelUsageRead(f, original, "contextConsentIdentity");
            if (panelUsageReady(f) && current() && panelUsageTruth(panelUsageRead(f, identity, "length")) && identity.strictlyEquals(actual)) {
                assistantMemberWrite(f, component, "disclosedContextText", exact);
                if (current()) assistantMemberWrite(f, component, "disclosedContextIdentity", identity);
            }
        }
    }
    if (!f || !f->hasError()) return;
    f->catchError();
    if (!current()) return;
    assistantMemberWrite(f, component, "disclosedContextText", QJSValue(QString{}));
    if (current()) assistantMemberWrite(f, component, "disclosedContextIdentity", QJSValue(QString{}));
    if (current()) assistantMemberWrite(f, component, "approvalOwner", f->newObject());
}
QJSValue ApplicationInfo::connectionDisclosedContext() const {
    const auto f = panelUsageEngine(this);
    const auto json = panelUsageContextRead(f, "JSON");
    const auto text = panelUsageContextRead(f, "disclosedContextText");
    const auto result = panelUsageMemberCall(f, json, "parse", {text});
    if (panelUsageReady(f)) return result;
    if (!f || !f->hasError()) return {};
    f->catchError();
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "error", QJSValue(true));
    return panelUsageComplete(f, literal);
}
void ApplicationInfo::connectionAccepted() const {
    const auto f = panelUsageEngine(this);
    const auto original = panelUsageContextRead(f, "assistant");
    const auto project = assistantContextField(f, "Session", "project");
    const auto model = panelUsageRead(f, original, "selectedModel");
    const auto effort = panelUsageRead(f, original, "selectedEffort");
    const auto connected = panelUsageRead(f, original, "connected");
    auto account = panelUsageRead(f, original, "account");
    const auto email = panelUsageRead(f, account, "email");
    account = panelUsageRead(f, original, "account");
    const auto plan = panelUsageRead(f, account, "planType");
    const auto approval = assistantContextField(f, "dialog", "approvalOwner");
    QJSValueList values{original, project, model, effort, connected, email, plan, approval};
    const auto get = [&](uint index) { return values[index]; };
    if (!connectionOwnerCurrent(f, get)) return;
    const auto offered = assistantContextField(f, "dialog", "disclosedContextIdentity");
    if (!connectionOwnerCurrent(f, get)) return;
    values.append(offered);
    const auto current = [&] { return panelUsageTruth(connectionCurrent(f, get)); };
    if (!current()) return;
    const auto failure = panelUsageContextRead(f, "connectionFailure");
    panelUsageMemberCall(f, failure, "close");
    if (!current()) return;
    panelUsageContextWrite(f, "connectionAttempt", QJSValue(!panelUsageTruth(connected)));
    const auto result = panelUsageMemberCall(f, original, "acceptConnectionOffer", {offered});
    if (!current()) return;
    if (result.strictlyEquals(QJSValue(QStringLiteral("waiting")))) {
        const auto dialog = panelUsageContextRead(f, "dialog");
        const auto accepted = panelUsageLiteral(f);
        panelUsageWrite(f, accepted.value, "owner", original);
        panelUsageWrite(f, accepted.value, "approval", approval);
        panelUsageWrite(f, accepted.value, "context", offered);
        panelUsageWrite(f, accepted.value, "current", panelUsageClosure(f, 10, values));
        panelUsageWrite(f, accepted.value, "submitting", QJSValue(false));
        assistantMemberWrite(f, dialog, "acceptedOffer", panelUsageComplete(f, accepted));
        const auto actual = panelUsageContextRead(f, "dialog");
        panelUsageMemberCall(f, actual, "scheduleAcceptedOffer");
        return;
    }
    panelUsageGlobalCall(f, "showConnectionFailureIfFinished", {});
    if (result.strictlyEquals(QJSValue(QStringLiteral("approved"))) && current()) panelUsageGlobalCall(f, "contextApproved", {approval});
}

void ApplicationInfo::panelSubmissionRequested(const QJSValue& draft) const {
    const auto f = panelUsageEngine(this);
    const auto intent = assistantContextField(f, "panel", "consentSend");
    if (!panelUsageReady(f) || !panelUsageTruth(intent) || !panelUsageTruth(draft)) return;
    for (const char* field : {"owner", "revision", "ownerRevision", "files", "project"}) {
        const auto captured = panelUsageRead(f, intent, "draft");
        if (!consentFieldsEqual(f, captured, field, draft, field)) return;
    }
    const auto panel = panelUsageContextRead(f, "panel");
    panelUsageMemberCall(f, panel, "retireConsentSend");
}
void ApplicationInfo::panelContextApprovalRequested(const QJSValue& text) const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto draft = panelUsageContextRead(f, "composer");
    const auto dialog = panelUsageContextRead(f, "connectionDialog");
    const auto previous = panelUsageRead(f, component, "consentSend");
    const auto offer = panelUsageMemberCall(f, dialog, "beginOffer");
    if (!consentQtObject(f, component) || !consentQtObject(f, draft) || !consentQtObject(f, original)
        || !consentQtObject(f, dialog) || !consentFieldEquals(f, component, "assistant", original)
        || !consentFieldEquals(f, dialog, "assistant", original) || !consentFieldEquals(f, dialog, "approvalOwner", offer)
        || !consentFieldEquals(f, component, "consentSend", previous)) return;
    const auto captured = panelUsageMemberCall(f, draft, "captureConsentDraft");
    const auto ownedComponents = [&] {
        return consentPanelOwner(f, component, draft, original) && consentQtObject(f, dialog)
            && consentFieldEquals(f, dialog, "assistant", original) && consentFieldEquals(f, dialog, "approvalOwner", offer);
    };
    if (!ownedComponents() || !panelUsageTruth(captured) || !consentFieldEquals(f, captured, "text", text)
        || !consentFieldEquals(f, captured, "owner", original)) return;
    const auto owned = panelUsageMemberCall(f, draft, "ownsConsentDraft", {captured});
    if (!ownedComponents() || !panelUsageTruth(owned) || !consentFieldEquals(f, component, "consentSend", previous)) return;
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "owner", original);
    panelUsageWrite(f, literal.value, "project", panelUsageRead(f, captured, "project"));
    panelUsageWrite(f, literal.value, "draft", captured);
    for (const char* field : {"context", "model", "effort"}) panelUsageWrite(f, literal.value, field, panelUsageRead(f, captured, field));
    panelUsageWrite(f, literal.value, "offer", offer);
    panelUsageWrite(f, literal.value, "approved", QJSValue(false));
    panelUsageWrite(f, literal.value, "submitting", QJSValue(false));
    const auto intent = panelUsageComplete(f, literal);
    assistantMemberWrite(f, component, "consentSend", intent);
    assistantMemberWrite(f, offer, "currentDraft", panelUsageClosure(f, 11, {component, intent}));
    if (!consentPanelOwner(f, component, draft, original) || !consentQtObject(f, dialog)
        || !consentFieldEquals(f, dialog, "approvalOwner", offer) || !consentFieldEquals(f, component, "consentSend", intent)) return;
    const auto stillOwned = panelUsageMemberCall(f, component, "ownsConsentSend", {intent});
    if (!consentPanelOwner(f, component, draft, original) || !consentQtObject(f, dialog)
        || !consentFieldEquals(f, dialog, "approvalOwner", offer) || !panelUsageTruth(stillOwned)) return;
    panelUsageMemberCall(f, dialog, "presentOffer", {offer});
}
void ApplicationInfo::connectionUpdateAcceptButton() const {
    const auto f = panelUsageEngine(this);
    const auto ok = assistantContextField(f, "Dialog", "Ok");
    const auto accept = panelUsageGlobalCall(f, "standardButton", {ok});
    if (!panelUsageReady(f)) return;
    if (panelUsageTruth(accept)) {
        auto connected = assistantContextField(f, "assistant", "connected");
        if (!panelUsageReady(f)) return;
        if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
        const auto text = QJSValue(QCoreApplication::translate("AssistantConnectionDialog", panelUsageTruth(connected)
            ? "Share project information" : "Connect ChatGPT"));
        assistantMemberWrite(f, accept, "text", text);
        connected = assistantContextField(f, "assistant", "connected");
        assistantMemberWrite(f, accept, "fontIcon", QJSValue(panelUsageTruth(connected) ? QStringLiteral("check") : QStringLiteral("comment-dots")));
        const auto blocked = assistantContextField(f, "assistant", "contextApprovalBlocked");
        assistantMemberWrite(f, accept, "enabled", QJSValue(!panelUsageTruth(blocked)));
    }
    const auto cancel = assistantContextField(f, "Dialog", "Cancel");
    const auto button = panelUsageGlobalCall(f, "standardButton", {cancel});
    if (panelUsageReady(f) && panelUsageTruth(button)) assistantMemberWrite(f, button, "fontIcon", QJSValue(QStringLiteral("times")));
}
void ApplicationInfo::connectionResetOffer(bool refresh, bool retired) const {
    const auto f = panelUsageEngine(this);
    if (refresh) {
        panelUsageContextWrite(f, "acceptedOffer", consentNull());
        if (panelUsageReady(f)) panelUsageContextWrite(f, "approvalOwner", f->newObject());
        panelUsageGlobalCall(f, "refreshDisclosedContext", {});
    } else {
        const auto dialog = panelUsageContextRead(f, "dialog");
        consentClear(f, dialog, "acceptedOffer");
        const auto actual = panelUsageContextRead(f, "dialog");
        if (panelUsageReady(f)) assistantMemberWrite(f, actual, "approvalOwner", f->newObject());
    }
    if (retired) {
        const auto current = panelUsageContextRead(f, "dialog");
        assistantMemberWrite(f, current, "connectionAttempt", QJSValue(false));
        const auto failure = panelUsageContextRead(f, "connectionFailure");
        panelUsageMemberCall(f, failure, "close");
    }
}


#else
namespace edi_app::assistant_panel_presentation {
QJSValue usageWindowLabel(QJSEngine*, const QJSValue&, const QJSValue&) { return QJSValue(QString()); }
QJSValue accountPlanWord(QJSEngine*, const QJSValue&) { return QJSValue(QString()); }
}
QJSValue ApplicationInfo::assistantUsageData(QObject*) const {
    const auto frame = panelUsageEngine(this);
    if (!panelUsageReady(frame)) return {};
    const auto literal = panelUsageLiteral(frame);
    panelUsageWrite(frame, literal.value, "available", QJSValue(false));
    panelUsageWrite(frame, literal.value, "stale", QJSValue(false));
    panelUsageWrite(frame, literal.value, "buckets", frame->newArray());
    return panelUsageComplete(frame, literal);
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
void ApplicationInfo::composerAcknowledgeVisiblePrompt() const {}
bool ApplicationInfo::assistantContainsItem(const QJSValue&, const QJSValue&) const { return false; }
QJSValue ApplicationInfo::assistantWorkflowPage() const { return QJSValue(QJSValue::NullValue); }
void ApplicationInfo::rehostAssistant() const {}
void ApplicationInfo::focusAssistantOpener() const {}
void ApplicationInfo::retireAssistantFocus() const {}
void ApplicationInfo::restoreAssistantFocus() const {}
bool ApplicationInfo::assistantHomeFocusCovered() const { return false; }
void ApplicationInfo::enforceAssistantHomeFocus() const {}
QJSValue ApplicationInfo::composerCaptureConsentDraft() const { return QJSValue(QJSValue::NullValue); }
bool ApplicationInfo::composerOwnsConsentDraft(const QJSValue&) const { return false; }
QJSValue ApplicationInfo::composerSubmitApprovedDraft(const QJSValue&) const { return QJSValue(QJSValue::NullValue); }
bool ApplicationInfo::composerExplainBlockedSubmission() const { return false; }
QJSValue ApplicationInfo::composerSubmit(const QJSValue&) const { return QJSValue(QJSValue::NullValue); }
void ApplicationInfo::panelRetireConsentSend() const {}
bool ApplicationInfo::panelOwnsConsentSend(const QJSValue&) const { return false; }
void ApplicationInfo::panelResumeConsentSend() const {}
void ApplicationInfo::panelConsentContextChanged() const {}
void ApplicationInfo::panelContextApproved(const QJSValue&) const {}
void ApplicationInfo::panelScheduleConsentSend() const {}
void ApplicationInfo::panelSubmissionRequested(const QJSValue&) const {}
void ApplicationInfo::panelContextApprovalRequested(const QJSValue&) const {}
QJSValue ApplicationInfo::connectionBeginOffer() const { return QJSValue(QJSValue::NullValue); }
void ApplicationInfo::connectionPresentOffer(const QJSValue&) const {}
void ApplicationInfo::connectionResumeAcceptedOffer() const {}
void ApplicationInfo::connectionScheduleAcceptedOffer() const {}
void ApplicationInfo::connectionShowFailure() const {}
void ApplicationInfo::connectionRefreshContext() const {}
QJSValue ApplicationInfo::connectionDisclosedContext() const { const auto frame = panelUsageEngine(this); if (!panelUsageReady(frame)) return {}; const auto literal = panelUsageLiteral(frame); panelUsageWrite(frame, literal.value, "error", QJSValue(true)); return panelUsageComplete(frame, literal); }
void ApplicationInfo::connectionAccepted() const {}
void ApplicationInfo::connectionUpdateAcceptButton() const {}
void ApplicationInfo::connectionResetOffer(bool, bool) const {}
#endif

namespace {
QJSValue projectGuardedClosure(const PanelUsageFrame& frame, uint operation) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::QmlContext> context(scope, frame.qmlScope);
    QV4::Scoped<QV4::ApplicationProjectCallback> callback(scope,
        frame.vm()->memoryManager->allocate<QV4::ApplicationProjectCallback>(frame.vm(), context.getPointer(), operation));
    callback->defineReadonlyConfigurableProperty(frame.vm()->id_length(), QV4::Value::fromInt32(0));
    return QJSValuePrivate::fromReturnedValue(callback->asReturnedValue());
}
QJSValue projectCall(const PanelUsageFrame& frame, const QJSValue& callback, const QJSValueList& values = {}) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue function(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), callback));
    QV4::JSCallArguments args(scope, static_cast<int>(values.size()));
    for (qsizetype index = 0; index < values.size(); ++index) args.args[index] = QJSValuePrivate::convertToReturnedValue(frame.vm(), values[index]);
    QV4::ScopedValue result(scope, QV4::Runtime::CallValue::call(frame.vm(), *function, args.args, static_cast<int>(values.size())));
    frame.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue projectInvoke(const PanelUsageFrame& frame, const char* object, const char* method, const QJSValueList& args = {}) {
    const auto owner = panelUsageContextRead(frame, object);
    return panelUsageMemberCall(frame, owner, method, args);
}
void projectWrite(const PanelUsageFrame& frame, const char* object, const char* property, const QJSValue& value) {
    const auto target = panelUsageContextRead(frame, object);
    assistantMemberWrite(frame, target, property, value);
}
bool projectFieldIs(const PanelUsageFrame& frame, const char* object, const char* field, const QJSValue& value) {
    const auto actual = assistantContextField(frame, object, field);
    return panelUsageReady(frame) && actual.strictlyEquals(value);
}
QJSValue projectPage(const PanelUsageFrame& frame, const char* name) {
    const auto pages = assistantContextField(frame, "AppState", "Page");
    return panelUsageRead(frame, pages, name);
}
bool projectCreationCurrent(const PanelUsageFrame& frame, const QJSValue& owner, const QJSValue& before, const QJSValue& intent) {
    const auto window = panelUsageContextRead(frame, "window");
    if (!consentQtObject(frame, window) || !consentQtObject(frame, owner)) return false;
    if (!projectFieldIs(frame, "Session", "assistant", owner) || !projectFieldIs(frame, "Session", "project", before)) return false;
    return panelUsageTruth(panelUsageMemberCall(frame, owner, "nativeProjectCreateCurrent", {intent}));
}
void projectCreationRelease(const PanelUsageFrame& frame, const QJSValue& token) {
    if (projectFieldIs(frame, "window", "assistantCreateGuard", token)) projectWrite(frame, "window", "assistantCreateGuard", consentNull());
}
QJSValue projectCallback(const PanelUsageFrame& frame, uint operation, const std::function<QJSValue(uint)>& captured) {
    if (operation == 20) {
        const auto session = panelUsageContextRead(frame, "Session");
        return panelUsageMemberCall(frame, session, "openProject", {captured(0)});
    }
    if (operation == 21 || operation == 22) {
        const auto owner = captured(0), before = captured(1), intent = captured(2), token = captured(3);
        projectCreationRelease(frame, token);
        if (operation == 22 || !projectCreationCurrent(frame, owner, before, intent)) {
            if (consentQtObject(frame, owner)) panelUsageMemberCall(frame, owner, "nativeProjectCreateReady", {intent, QJSValue(false)});
            return {};
        }
        const auto actions = panelUsageRead(frame, owner, "showActions");
        if (!panelUsageReady(frame)) return {};
        if (panelUsageTruth(actions)) projectInvoke(frame, "AppState", "open", {projectPage(frame, "Project")});
        else {
            const auto math = panelUsageContextRead(frame, "Math");
            const auto reached = assistantContextField(frame, "AppState", "reached");
            const auto page = projectPage(frame, "Project");
            const auto maximum = panelUsageMemberCall(frame, math, "max", {reached, page});
            projectWrite(frame, "AppState", "reached", maximum);
        }
        if (projectCreationCurrent(frame, owner, before, intent)) panelUsageMemberCall(frame, owner, "nativeProjectCreateReady", {intent, QJSValue(true)});
        return {};
    }
    if (operation == 23) {
        projectWrite(frame, "window", "quitting", QJSValue(true));
        return projectInvoke(frame, "window", "close");
    }
    if (operation == 24) return projectInvoke(frame, "AppState", "reset");
    // Session restoration keeps the original project/admission transaction owner.
    const auto owner = captured(0), before = captured(1), intent = captured(2);
    const auto abandon = [&] { if (consentQtObject(frame, owner)) panelUsageMemberCall(frame, owner, "cancelSessionSelection", {intent}); };
    if (operation == 26) { abandon(); return {}; }
    const auto panel = panelUsageContextRead(frame, "panel");
    if (!consentQtObject(frame, panel) || !consentQtObject(frame, owner)
        || !projectFieldIs(frame, "panel", "assistant", owner) || !consentFieldEquals(frame, owner, "sessionSelection", intent)
        || !projectFieldIs(frame, "Session", "project", before)) { abandon(); return {}; }
    if (!panelUsageTruth(panelUsageMemberCall(frame, owner, "beginSessionProjectRestore", {intent}))) { abandon(); return {}; }
    const auto opened = projectInvoke(frame, "Session", "openProject", {captured(3)});
    if (panelUsageTruth(opened) && consentQtObject(frame, owner) && projectFieldIs(frame, "panel", "assistant", owner)
        && consentFieldEquals(frame, owner, "sessionSelection", intent)) panelUsageMemberCall(frame, owner, "continueSessionRestore", {captured(4)});
    else if (!consentQtObject(frame, owner) || !panelUsageTruth(panelUsageMemberCall(frame, owner, "sessionProjectRestorePending", {intent}))) abandon();
    return {};
}
} // namespace

QV4::ReturnedValue QV4::ApplicationProjectCallback::virtualCall(const FunctionObject* function,
    const Value*, const Value*, int) {
    const auto* callback = static_cast<const ApplicationProjectCallback*>(function);
    QV4::Scope scope(function->engine());
    QV4::Scoped<QV4::QmlContext> context(scope, callback->d()->context);
    const PanelUsageFrame frame(function->engine()->jsEngine(),
        context ? context->qmlContext() : QQmlRefPointer<QQmlContextData>(), context ? context->d() : nullptr);
    if (!panelUsageReady(frame)) return QV4::Encode::undefined();
    const auto result = projectCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); });
    return QJSValuePrivate::convertToReturnedValue(frame.vm(), result);
}

void ApplicationInfo::afterProjectChanges(const QJSValue& action, const QJSValue& abandoned) const {
    const auto frame = panelUsageEngine(this);
    const auto project = assistantContextField(frame, "Session", "project");
    if (!panelUsageReady(frame)) return;
    if (!project.isNull()) {
        const auto modified = assistantContextField(frame, "Session", "project");
        if (panelUsageTruth(panelUsageRead(frame, modified, "modified"))) {
            panelUsageGlobalCall(frame, "changesQuestion", {action, abandoned});
            return;
        }
    }
    const auto qt = panelUsageContextRead(frame, "Qt");
    panelUsageMemberCall(frame, qt, "callLater", {action});
}
void ApplicationInfo::openWorkflowPage(const QJSValue& page) const {
    const auto frame = panelUsageEngine(this);
    const auto math = panelUsageContextRead(frame, "Math");
    const auto reached = panelUsageContextRead(frame, "reached");
    const auto maximum = panelUsageMemberCall(frame, math, "max", {reached, page});
    panelUsageContextWrite(frame, "reached", maximum);
    const auto globals = assistantContextField(frame, "EaGlobals", "Vars");
    assistantMemberWrite(frame, globals, "appBarCurrentIndex", page);
}
void ApplicationInfo::resetWorkflow() const {
    const auto frame = panelUsageEngine(this);
    projectInvoke(frame, "Session", "closeProject");
    const auto page = projectPage(frame, "Project");
    panelUsageContextWrite(frame, "reached", page);
    const auto globals = assistantContextField(frame, "EaGlobals", "Vars");
    const auto currentPage = projectPage(frame, "Project");
    assistantMemberWrite(frame, globals, "appBarCurrentIndex", currentPage);
}
void ApplicationInfo::saveCurrentProject() const {
    const auto frame = panelUsageEngine(this);
    if (assistantContextField(frame, "Session", "project").isNull() || !panelUsageReady(frame)) return;
    if (panelUsageTruth(assistantContextField(frame, "Session", "needsSaveAs"))) { projectInvoke(frame, "window", "saveProjectAs"); return; }
    const auto saved = projectInvoke(frame, "Session", "save");
    if (!panelUsageTruth(saved) && !projectFieldIs(frame, "Session", "lastError", QJSValue(QString{}))) projectInvoke(frame, "saveError", "open");
}
void ApplicationInfo::saveCurrentProjectAs(const QJSValue& intent) const {
    const auto frame = panelUsageEngine(this);
    if (assistantContextField(frame, "Session", "project").isNull() || !panelUsageReady(frame)) return;
    const auto previous = panelUsageContextRead(frame, "assistantSaveIntent");
    if (!previous.strictlyEquals(QJSValue(QString{}))) {
        const auto actual = panelUsageContextRead(frame, "assistantSaveIntent");
        if (!actual.strictlyEquals(intent)) projectInvoke(frame, "Session", "cancelAssistantSaveAs", {panelUsageContextRead(frame, "assistantSaveIntent")});
    }
    panelUsageContextWrite(frame, "assistantSaveIntent", intent);
    projectInvoke(frame, "saveAsChoice", "open");
}
QJSValue ApplicationInfo::finishProjectSaveAs(const QJSValue& target, const QJSValue& zip, const QJSValue& copy) const {
    const auto frame = panelUsageEngine(this);
    const auto intent = panelUsageContextRead(frame, "assistantSaveIntent");
    panelUsageContextWrite(frame, "assistantSaveIntent", QJSValue(QString{}));
    return intent.strictlyEquals(QJSValue(QString{})) ? projectInvoke(frame, "Session", "saveProjectAs", {target, zip, copy})
        : projectInvoke(frame, "Session", "completeAssistantSaveAs", {intent, target, zip, copy});
}
void ApplicationInfo::cancelProjectSaveAs() const {
    const auto frame = panelUsageEngine(this);
    const auto intent = panelUsageContextRead(frame, "assistantSaveIntent");
    panelUsageContextWrite(frame, "assistantSaveIntent", QJSValue(QString{}));
    if (!intent.strictlyEquals(QJSValue(QString{}))) projectInvoke(frame, "Session", "cancelAssistantSaveAs", {intent});
}
void ApplicationInfo::projectWindowClosing(const QJSValue& close) const {
    const auto frame = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageContextRead(frame, "quitting")) || !panelUsageReady(frame)) return;
    if (assistantContextField(frame, "Session", "project").isNull()) return;
    const auto project = assistantContextField(frame, "Session", "project");
    if (!panelUsageTruth(panelUsageRead(frame, project, "modified")) || !panelUsageReady(frame)) return;
    assistantMemberWrite(frame, close, "accepted", QJSValue(false));
    projectInvoke(frame, "AppState", "afterChanges", {projectGuardedClosure(frame, 23)});
}
void ApplicationInfo::projectChangesQuestion(const QJSValue& action, const QJSValue& abandoned) const {
    const auto frame = panelUsageEngine(this);
    const auto previous = assistantContextField(frame, "unsavedChanges", "abandoned");
    projectWrite(frame, "unsavedChanges", "abandoned", consentNull());
    if (panelUsageTruth(previous)) projectCall(frame, previous);
    projectWrite(frame, "unsavedChanges", "abandoned", abandoned);
    const auto token = assistantContextField(frame, "window", "assistantCreateGuard");
    QJSValue native = consentNull();
    if (!token.isNull() && consentFieldEquals(frame, token, "action", action)) native = token;
    projectWrite(frame, "unsavedChanges", "nativeCreation", native);
    projectWrite(frame, "unsavedChanges", "action", action);
    projectInvoke(frame, "unsavedChanges", "open");
}
void ApplicationInfo::unsavedProjectOpened() const {
    const auto frame = panelUsageEngine(this);
    const auto token = panelUsageContextRead(frame, "nativeCreation");
    if (token.isNull() || !projectFieldIs(frame, "window", "assistantCreateGuard", token)) return;
    const auto owner = panelUsageRead(frame, token, "assistant");
    if (!consentQtObject(frame, owner)) return;
    const auto actualOwner = panelUsageRead(frame, token, "assistant");
    const auto intent = panelUsageRead(frame, token, "intent");
    const auto dialog = panelUsageContextRead(frame, "unsavedChanges");
    const auto save = assistantContextField(frame, "Dialog", "Save");
    const auto button = panelUsageGlobalCall(frame, "standardButton", {save});
    panelUsageMemberCall(frame, actualOwner, "nativeProjectCreateSaveChoice", {intent, dialog, button});
}
void ApplicationInfo::abandonUnsavedProjectAction() const {
    const auto frame = panelUsageEngine(this);
    const auto callback = panelUsageContextRead(frame, "abandoned");
    panelUsageContextWrite(frame, "abandoned", consentNull());
    panelUsageContextWrite(frame, "action", consentNull());
    if (panelUsageTruth(callback)) projectCall(frame, callback);
}
void ApplicationInfo::acceptUnsavedProject() const {
    const auto frame = panelUsageEngine(this);
    const auto original = panelUsageContextRead(frame, "nativeCreation");
    const auto waiting = panelUsageContextRead(frame, "action");
    if (panelUsageTruth(assistantContextField(frame, "Session", "needsSaveAs"))) {
        panelUsageGlobalCall(frame, "abandonAction", {});
        const auto window = panelUsageContextRead(frame, "window");
        if (consentQtObject(frame, window)) projectInvoke(frame, "window", "saveProjectAs");
        return;
    }
    QJSValue saved;
    if (!original.isNull()) {
        const auto owner = panelUsageRead(frame, original, "assistant");
        bool current = consentQtObject(frame, owner);
        if (current) {
            const auto assistant = assistantContextField(frame, "Session", "assistant");
            current = consentFieldEquals(frame, original, "assistant", assistant);
        }
        if (current) {
            const auto project = assistantContextField(frame, "Session", "project");
            current = consentFieldEquals(frame, original, "project", project);
        }
        if (current) {
            const auto actual = panelUsageRead(frame, original, "assistant");
            const auto intent = panelUsageRead(frame, original, "intent");
            saved = panelUsageMemberCall(frame, actual, "nativeProjectCreateSave", {intent});
        } else saved = QJSValue(false);
    } else saved = projectInvoke(frame, "Session", "save");
    if (!original.isNull()) {
        if (!assistantSameName(frame, original, "nativeCreation") || !projectFieldIs(frame, "window", "assistantCreateGuard", original)
            || !assistantSameName(frame, waiting, "action")) return;
        const auto owner = panelUsageRead(frame, original, "assistant");
        if (!consentQtObject(frame, owner)) return;
        const auto assistant = assistantContextField(frame, "Session", "assistant");
        if (!consentFieldEquals(frame, original, "assistant", assistant)) return;
        const auto project = assistantContextField(frame, "Session", "project");
        if (!consentFieldEquals(frame, original, "project", project)) return;
    }
    if (panelUsageTruth(saved)) {
        if (panelUsageTruth(assistantContextField(frame, "WebFiles", "available"))) {
            const auto action = panelUsageContextRead(frame, "action");
            panelUsageContextWrite(frame, "afterSave", action);
            const auto abandoned = panelUsageContextRead(frame, "abandoned");
            panelUsageContextWrite(frame, "afterSaveAbandoned", abandoned);
            panelUsageContextWrite(frame, "abandoned", consentNull());
        } else {
            panelUsageContextWrite(frame, "abandoned", consentNull());
            panelUsageContextWrite(frame, "action", consentNull());
            panelUsageCallLater(frame, waiting);
        }
    } else {
        panelUsageGlobalCall(frame, "abandonAction", {});
        if (!projectFieldIs(frame, "Session", "lastError", QJSValue(QString{}))) projectInvoke(frame, "saveError", "open");
    }
}
void ApplicationInfo::projectWebSaveFinished(const QJSValue& saved) const {
    const auto frame = panelUsageEngine(this);
    const auto waiting = assistantContextField(frame, "unsavedChanges", "afterSave");
    const auto abandoned = assistantContextField(frame, "unsavedChanges", "afterSaveAbandoned");
    projectWrite(frame, "unsavedChanges", "afterSave", consentNull());
    projectWrite(frame, "unsavedChanges", "afterSaveAbandoned", consentNull());
    if (panelUsageTruth(saved) && !waiting.isNull()) projectInvoke(frame, "AppState", "afterChanges", {waiting, abandoned});
    else if (panelUsageTruth(abandoned)) projectCall(frame, abandoned);
}
void ApplicationInfo::discardUnsavedProject() const {
    const auto frame = panelUsageEngine(this);
    const auto waiting = panelUsageContextRead(frame, "action");
    panelUsageContextWrite(frame, "action", consentNull());
    panelUsageContextWrite(frame, "abandoned", consentNull());
    panelUsageGlobalCall(frame, "close", {});
    projectInvoke(frame, "Session", "discardKeptChanges");
    panelUsageCallLater(frame, waiting);
}
void ApplicationInfo::prepareProjectSaveChoice() const {
    const auto frame = panelUsageEngine(this);
    auto disk = panelUsageContextRead(frame, "diskWritable");
    panelUsageContextWrite(frame, "zip", QJSValue(!panelUsageTruth(disk)));
    disk = panelUsageContextRead(frame, "diskWritable");
    panelUsageContextWrite(frame, "copy", QJSValue(!panelUsageTruth(disk)));
}
void ApplicationInfo::acceptProjectSaveChoice() const {
    const auto frame = panelUsageEngine(this);
    const auto intent = assistantContextField(frame, "window", "assistantSaveIntent");
    if (!intent.strictlyEquals(QJSValue(QString{})) && !panelUsageTruth(assistantContextField(frame, "WebFiles", "available"))) {
        if (!panelUsageTruth(projectInvoke(frame, "Session", "assistantSaveAsCurrent", {intent}))) { projectInvoke(frame, "window", "cancelAssistantSaveAs"); return; }
        const auto zip = panelUsageContextRead(frame, "zip");
        const auto target = projectInvoke(frame, "Session", "assistantSaveAsTarget", {intent, zip});
        const auto actualZip = panelUsageContextRead(frame, "zip");
        const auto copy = panelUsageContextRead(frame, "copy");
        projectInvoke(frame, "window", "finishAssistantSaveAs", {target, actualZip, copy});
        return;
    }
    if (!panelUsageTruth(panelUsageContextRead(frame, "diskWritable"))) { projectInvoke(frame, "Session", "downloadWebProject"); return; }
    if (panelUsageTruth(assistantContextField(frame, "WebFiles", "available"))) {
        const auto zip = panelUsageContextRead(frame, "zip");
        const auto copy = panelUsageContextRead(frame, "copy");
        projectInvoke(frame, "Session", "saveWebProjectAs", {QJSValue(panelUsageTruth(zip) ? QStringLiteral("zip") : QStringLiteral("folder")), copy});
        return;
    }
    const bool zip = panelUsageTruth(panelUsageContextRead(frame, "zip"));
    const auto picker = panelUsageContextRead(frame, zip ? "saveZip" : "saveFolder");
    const auto actualIntent = assistantContextField(frame, "window", "assistantSaveIntent");
    const auto target = actualIntent.strictlyEquals(QJSValue(QString{})) ? projectInvoke(frame, "Session", "suggestedSaveTarget", {QJSValue(zip)})
        : projectInvoke(frame, "Session", "assistantSaveAsTarget", {assistantContextField(frame, "window", "assistantSaveIntent"), QJSValue(zip)});
    panelUsageMemberCall(frame, picker, "openAt", {target});
}
void ApplicationInfo::openProjectSavePicker(const QJSValue& target) const {
    const auto frame = panelUsageEngine(this);
    const auto text = panelUsageMemberCall(frame, target, "toString");
    const auto again = panelUsageMemberCall(frame, target, "toString");
    const auto slash = panelUsageMemberCall(frame, again, "lastIndexOf", {QJSValue(QStringLiteral("/"))});
    const auto folder = panelUsageMemberCall(frame, text, "substring", {QJSValue(0), slash});
    panelUsageContextWrite(frame, "currentFolder", folder);
    panelUsageContextWrite(frame, "selectedFile", target);
    panelUsageGlobalCall(frame, "open", {});
}
void ApplicationInfo::acceptProjectSavePicker(bool zip) const {
    const auto frame = panelUsageEngine(this);
    const auto selected = panelUsageContextRead(frame, "selectedFile");
    const auto copy = assistantContextField(frame, "saveAsChoice", "copy");
    if (!panelUsageTruth(projectInvoke(frame, "window", "finishAssistantSaveAs", {selected, QJSValue(zip), copy}))) projectInvoke(frame, "saveError", "open");
}
void ApplicationInfo::dropProject(const QJSValue& drop) const {
    const auto frame = panelUsageEngine(this);
    const auto hasUrls = panelUsageRead(frame, drop, "hasUrls");
    if (!panelUsageReady(frame) || !panelUsageTruth(hasUrls)) return;
    const auto urls = panelUsageRead(frame, drop, "urls");
    if (!assistantRelation(frame, panelUsageRead(frame, urls, "length"), QJSValue(0), 1)) return;
    panelUsageMemberCall(frame, drop, "accept");
    const auto actualUrls = panelUsageRead(frame, drop, "urls");
    const auto url = panelUsageIndex(frame, actualUrls, 0);
    const auto action = panelUsageClosure(frame, 20, {url});
    projectInvoke(frame, "AppState", "afterChanges", {action});
}

bool ApplicationInfo::prepareProjectCreation(const QJSValue& intent) const {
    const auto frame = panelUsageEngine(this);
    const auto original = assistantContextField(frame, "Session", "assistant");
    const auto before = assistantContextField(frame, "Session", "project");
    if (!panelUsageTruth(panelUsageMemberCall(frame, original, "nativeProjectCreateCurrent", {intent}))
        || !panelUsageContextRead(frame, "assistantCreateGuard").isNull() || !panelUsageReady(frame)) return false;
    const auto literal = panelUsageLiteral(frame);
    panelUsageWrite(frame, literal.value, "assistant", original);
    panelUsageWrite(frame, literal.value, "project", before);
    panelUsageWrite(frame, literal.value, "intent", intent);
    panelUsageWrite(frame, literal.value, "action", consentNull());
    const auto token = panelUsageComplete(frame, literal);
    const auto action = panelUsageClosure(frame, 21, {original, before, intent, token});
    assistantMemberWrite(frame, token, "action", action);
    panelUsageContextWrite(frame, "assistantCreateGuard", token);
    const auto actualAction = panelUsageRead(frame, token, "action");
    const auto abandon = panelUsageClosure(frame, 22, {original, before, intent, token});
    projectInvoke(frame, "AppState", "afterChanges", {actualAction, abandon});
    return true;
}
bool ApplicationInfo::projectCreationSaveCurrent(const QJSValue& intent, const QJSValue& control) const {
    const auto frame = panelUsageEngine(this);
    const auto token = panelUsageContextRead(frame, "assistantCreateGuard");
    if (token.isNull() || !consentFieldEquals(frame, token, "intent", intent)
        || !projectFieldIs(frame, "unsavedChanges", "nativeCreation", token)) return false;
    auto owner = panelUsageRead(frame, token, "assistant");
    if (!consentQtObject(frame, owner)) return false;
    const auto assistant = assistantContextField(frame, "Session", "assistant");
    if (!consentFieldEquals(frame, token, "assistant", assistant)) return false;
    const auto project = assistantContextField(frame, "Session", "project");
    if (!consentFieldEquals(frame, token, "project", project)) return false;
    owner = panelUsageRead(frame, token, "assistant");
    if (!panelUsageTruth(panelUsageMemberCall(frame, owner, "nativeProjectCreateCurrent", {intent}))
        || !panelUsageTruth(assistantContextField(frame, "unsavedChanges", "visible"))
        || !panelUsageTruth(assistantContextField(frame, "unsavedChanges", "opened")) || !panelUsageReady(frame)) return false;
    const auto dialog = panelUsageContextRead(frame, "unsavedChanges");
    const auto save = assistantContextField(frame, "Dialog", "Save");
    const auto button = panelUsageMemberCall(frame, dialog, "standardButton", {save});
    return panelUsageReady(frame) && button.strictlyEquals(control);
}
bool ApplicationInfo::chooseProjectCreationSave(const QJSValue& intent, const QJSValue& control) const {
    const auto frame = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(frame, "nativeProjectCreateSaveCurrent", {intent, control}))) return false;
    panelUsageMemberCall(frame, control, "click");
    return true;
}
void ApplicationInfo::finishProjectCreationGuard(const QJSValue& intent) const {
    const auto frame = panelUsageEngine(this);
    const auto token = panelUsageContextRead(frame, "assistantCreateGuard");
    if (token.isNull() || !consentFieldEquals(frame, token, "intent", intent)) return;
    panelUsageContextWrite(frame, "assistantCreateGuard", consentNull());
    if (!projectFieldIs(frame, "unsavedChanges", "nativeCreation", token)) return;
    projectWrite(frame, "unsavedChanges", "nativeCreation", consentNull());
    const auto action = assistantContextField(frame, "unsavedChanges", "action");
    if (!consentFieldEquals(frame, token, "action", action)) return;
    projectWrite(frame, "unsavedChanges", "action", consentNull());
    projectWrite(frame, "unsavedChanges", "abandoned", consentNull());
    projectInvoke(frame, "unsavedChanges", "close");
}
QJSValue ApplicationInfo::createProjectFromIntent(const QJSValue& values, const QJSValue& intent) const {
    const auto frame = panelUsageEngine(this);
    const auto owner = assistantContextField(frame, "Session", "assistant");
    bool blocked = !panelUsageTruth(panelUsageMemberCall(frame, owner, "nativeProjectCreateCurrent", {intent}));
    if (!blocked) {
        const auto project = assistantContextField(frame, "Session", "project");
        if (!project.isNull()) {
            const auto actual = assistantContextField(frame, "Session", "project");
            blocked = panelUsageTruth(panelUsageRead(frame, actual, "modified"));
        }
    }
    if (!panelUsageReady(frame)) return {};
    if (blocked) return frame->newObject();
    const auto session = panelUsageContextRead(frame, "Session");
    QJSValueList args;
    for (const char* name : {"name", "description", "location", "suRule", "title", "authors", "reportLibraries"}) args.append(panelUsageRead(frame, values, name));
    args.append(intent);
    return panelUsageMemberCall(frame, session, "createProjectWithOutcome", args);
}
bool ApplicationInfo::showProjectReport(const QJSValue& project) const {
    const auto frame = panelUsageEngine(this);
    if (project.isNull() || !projectFieldIs(frame, "Session", "project", project)
        || !panelUsageTruth(assistantContextField(frame, "reportTab", "enabled")) || !panelUsageReady(frame)) return false;
    projectInvoke(frame, "AppState", "open", {projectPage(frame, "Report")});
    if (!projectFieldIs(frame, "Session", "project", project) || !panelUsageTruth(assistantContextField(frame, "AppState", "reportPageEnabled"))) return false;
    const auto globals = assistantContextField(frame, "EaGlobals", "Vars");
    const auto index = panelUsageRead(frame, globals, "appBarCurrentIndex");
    const auto report = projectPage(frame, "Report");
    return panelUsageReady(frame) && index.strictlyEquals(report);
}
void ApplicationInfo::restoreSessionProject(const QJSValue& thread, const QJSValue& location, const QJSValue& intent) const {
    const auto frame = panelUsageEngine(this);
    const auto original = assistantContextField(frame, "panel", "assistant");
    const auto before = assistantContextField(frame, "Session", "project");
    const QJSValueList captures{original, before, intent, location, thread};
    const auto abandon = panelUsageClosure(frame, 26, captures);
    const auto action = panelUsageClosure(frame, 25, captures);
    projectInvoke(frame, "AppState", "afterChanges", {action, abandon});
}
void ApplicationInfo::resetProjectAfterChanges() const {
    const auto frame = panelUsageEngine(this);
    projectInvoke(frame, "AppState", "afterChanges", {projectGuardedClosure(frame, 24)});
}


QV4::ReturnedValue QV4::AssistantPanelCallback::virtualCall(const FunctionObject* function,
    const Value*, const Value* arguments, int count) {
    const auto* callback = static_cast<const AssistantPanelCallback*>(function);
    QV4::Scope scope(function->engine());
    QV4::Scoped<QV4::QmlContext> context(scope, callback->d()->context);
    const PanelUsageFrame frame(function->engine()->jsEngine(), context ? context->qmlContext() : QQmlRefPointer<QQmlContextData>(), context ? context->d() : nullptr);
    if (!panelUsageReady(frame)) return QV4::Encode::undefined();
    const QJSValue value = count ? QJSValuePrivate::fromReturnedValue(arguments[0].asReturnedValue()) : QJSValue();
    QJSValue result;
    if (callback->d()->operation >= 40) {
        const auto argument = [&](uint index) {
            return index < static_cast<uint>(count) ? QJSValuePrivate::fromReturnedValue(arguments[index].asReturnedValue()) : QJSValue();
        };
        result = viewProcedureCallback(frame, callback->d()->operation, argument);
    } else if (callback->d()->operation == 30) {
        result = panelUsageRead(frame, value, "free");
    } else if (callback->d()->operation == 0) {
        result = panelUsagePlanWord(frame, value);
    } else if (callback->d()->operation == 1) {
        const auto panel = panelUsageCapturedPanel(frame, callback->d()->panel);
        const auto minutes = panelUsageRead(frame, value, "minutes");
        const auto selected = panelUsageMemberCall(frame, panel, "allowanceWindow", {minutes});
        if (panelUsageReady(frame)) result = QJSValue(!selected.isNull());
    }
    else {
        QV4::Scoped<QV4::MemberData> captures(scope, callback->d()->captures);
        const auto captured = [&](uint index) {
            return QJSValuePrivate::fromReturnedValue((*captures)[index].asReturnedValue());
        };
        if (callback->d()->operation >= 20) result = projectCallback(frame, callback->d()->operation, captured);
        else if (callback->d()->operation < 10) mainAssistantDelayed(frame, callback->d()->operation, captured);
        else if (callback->d()->operation == 10) result = connectionCurrent(frame, captured);
        else {
            const auto component = captured(0), intent = captured(1);
            if (consentQtObject(frame, component) && consentFieldEquals(frame, component, "consentSend", intent))
                result = panelUsageMemberCall(frame, component, "ownsConsentSend", {intent});
            else result = QJSValue(false);
        }
    }
    return QJSValuePrivate::convertToReturnedValue(frame.vm(), result);
}

namespace {
struct EditorShape {
    const char* id;
    const char* translation;
    bool parameter;
    bool locked;
};
EditorShape editorShape(ApplicationInfo::EditorKind kind) {
    if (kind == ApplicationInfo::ParameterFieldEditor) return {"field", "ParameterField", true, false};
    if (kind == ApplicationInfo::ParameterCellEditor) return {"cell", "ParameterCell", true, true};
    return {"cell", "TextCell", false, true};
}
QJSValue editorGet(const PanelUsageFrame& f, const char* name) { return panelUsageContextRead(f, name); }
bool editorFlag(const PanelUsageFrame& f, const char* name) { return panelUsageTruth(editorGet(f, name)); }
bool editorNull(const PanelUsageFrame& f, const char* name) { return editorGet(f, name).isNull(); }
bool editorDraftIs(const PanelUsageFrame& f, const char* key, const QJSValue& expected) {
    return consentFieldEquals(f, editorGet(f, "draft"), key, expected);
}
QJSValue editorText(const PanelUsageFrame& f, const EditorShape& shape, const char* text) {
    if (!panelUsageReady(f)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
    return QJSValue(QCoreApplication::translate(shape.translation, text));
}
bool editorLife(const PanelUsageFrame& f, const QJSValue& life) { return panelUsageTruth(panelUsageRead(f, life, "alive")); }
bool editorOriginal(const PanelUsageFrame& f, const QJSValue& life, const QJSValue& original, const QJSValue& owner) {
    return editorLife(f, life) && assistantSameName(f, original, "draft") && assistantSameName(f, owner, "ownerToken");
}
QJSValue editorRecord(const PanelUsageFrame& f, bool parameter, const QJSValue& owner, const char* kind) {
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "owner", owner);
    if (parameter) panelUsageWrite(f, literal.value, "item", editorGet(f, "item"));
    panelUsageWrite(f, literal.value, "kind", QJSValue(QString::fromLatin1(kind)));
    return panelUsageComplete(f, literal);
}
// A JavaScript finally runs with the prior exception suspended, then restores
// that exact value and trace unless the finally body throws its replacement.
void editorFinally(const PanelUsageFrame& f, const std::function<void()>& body) {
    if (!f) return;
    QV4::Scope scope(f.vm());
    const bool pending = f.vm()->hasException;
    QV4::StackTrace trace;
    QV4::ScopedValue exception(scope);
    if (pending) exception = f.vm()->catchException(&trace);
    body();
    if (pending && !f.vm()->hasException) {
        f.vm()->throwError(*exception);
        f.vm()->exceptionStackTrace = std::move(trace);
    }
}
struct EditorFinally {
    const PanelUsageFrame& frame;
    std::function<void()> release;
    ~EditorFinally() { editorFinally(frame, release); }
};
} // namespace

void ApplicationInfo::editorRefreshCleanText() const {
    const auto f = panelUsageEngine(this);
    if (!editorNull(f, "draft") || !editorNull(f, "commitInProgress") || editorFlag(f, "inputMethodComposing")
        || editorFlag(f, "assistantEditing") || editorFlag(f, "assistantCommitReady") || !panelUsageReady(f)) return;
    const auto value = editorGet(f, editorFlag(f, "activeFocus") ? "editText" : "value");
    panelUsageContextWrite(f, "text", value);
}
void ApplicationInfo::editorRememberDraft(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    const auto shape = editorShape(kind);
    if (editorFlag(f, "assistantEditing") && !editorNull(f, "draft")
        && editorDraftIs(f, "kind", QJSValue(QStringLiteral("assistant")))) {
        const auto owner = panelUsageRead(f, editorGet(f, "draft"), "owner");
        if (assistantSameName(f, owner, "ownerToken")) return;
    }
    const auto life = editorGet(f, "editorLife");
    const auto context = editorGet(f, "ownerToken");
    const auto literal = panelUsageLiteral(f);
    const auto owner = !editorNull(f, "draft") ? panelUsageRead(f, editorGet(f, "draft"), "owner") : editorGet(f, "ownerToken");
    panelUsageWrite(f, literal.value, "owner", owner);
    if (shape.parameter) {
        const auto item = !editorNull(f, "draft") ? panelUsageRead(f, editorGet(f, "draft"), "item") : editorGet(f, "item");
        panelUsageWrite(f, literal.value, "item", item);
    }
    panelUsageWrite(f, literal.value, "kind", QJSValue(QStringLiteral("manual")));
    const auto original = panelUsageComplete(f, literal);
    panelUsageContextWrite(f, "draft", original);
    if (!editorOriginal(f, life, original, context)) return;
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
    if (!editorOriginal(f, life, original, context)) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
}
void ApplicationInfo::editorBeginAssistantEdit(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    if (!editorNull(f, "commitInProgress") || !editorNull(f, "draft") || editorFlag(f, "assistantManualDraft") || !panelUsageReady(f)) return;
    const auto life = editorGet(f, "editorLife");
    const auto owner = editorGet(f, "ownerToken");
    const auto original = editorRecord(f, editorShape(kind).parameter, owner, "assistant");
    panelUsageContextWrite(f, "draft", original);
    const auto current = [&] { return editorLife(f, life) && assistantSameName(f, owner, "ownerToken") && assistantSameName(f, original, "draft"); };
    if (!current()) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(true));
    if (!current()) return;
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
}
void ApplicationInfo::editorAllowAssistantCommit(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    if (!editorNull(f, "commitInProgress") || editorFlag(f, "inputMethodComposing") || editorNull(f, "draft")
        || !editorDraftIs(f, "kind", QJSValue(QStringLiteral("assistant")))) return;
    const auto owner = panelUsageRead(f, editorGet(f, "draft"), "owner");
    if (!assistantSameName(f, owner, "ownerToken")) return;
    if (editorShape(kind).parameter) {
        const auto item = panelUsageRead(f, editorGet(f, "draft"), "item");
        if (!assistantSameName(f, item, "item")) return;
    }
    const auto life = editorGet(f, "editorLife");
    const auto original = editorGet(f, "draft");
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(true));
    if (!editorLife(f, life) || !assistantSameName(f, original, "draft")) return;
    const auto currentOwner = panelUsageRead(f, original, "owner");
    if (!assistantSameName(f, currentOwner, "ownerToken")) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
}
void ApplicationInfo::parameterEditorReset() const {
    const auto f = panelUsageEngine(this);
    if (!editorNull(f, "commitInProgress") || editorFlag(f, "inputMethodComposing") || !panelUsageReady(f)) return;
    const auto life = editorGet(f, "editorLife");
    const auto original = editorGet(f, "draft");
    const auto context = editorGet(f, "ownerToken");
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
    if (!editorOriginal(f, life, original, context)) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
    if (!editorOriginal(f, life, original, context)) return;
    panelUsageContextWrite(f, "typedRefusal", QJSValue(QString{}));
    if (!editorOriginal(f, life, original, context)) return;
    panelUsageContextWrite(f, "draft", consentNull());
}
void ApplicationInfo::editorCancelAssistantEdit(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    const auto shape = editorShape(kind);
    if (!shape.parameter && editorFlag(f, "inputMethodComposing")) return;
    if (editorNull(f, "draft") || !editorDraftIs(f, "kind", QJSValue(QStringLiteral("assistant")))) return;
    const auto owner = panelUsageRead(f, editorGet(f, "draft"), "owner");
    if (!assistantSameName(f, owner, "ownerToken")) return;
    if (shape.parameter) {
        const auto item = panelUsageRead(f, editorGet(f, "draft"), "item");
        if (assistantSameName(f, item, "item")) panelUsageGlobalCall(f, "resetEditorText", {});
        return;
    }
    const auto life = editorGet(f, "editorLife");
    const auto original = editorGet(f, "draft");
    const auto current = [&] {
        if (!editorLife(f, life) || !assistantSameName(f, original, "draft")) return false;
        const auto actualOwner = panelUsageRead(f, original, "owner");
        return assistantSameName(f, actualOwner, "ownerToken");
    };
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
    if (!current()) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
    if (!current()) return;
    panelUsageContextWrite(f, "draft", consentNull());
}
void ApplicationInfo::editorEscape(EditorKind kind, const QJSValue& event) const {
    const auto f = panelUsageEngine(this);
    if (!editorNull(f, "commitInProgress") || editorFlag(f, "inputMethodComposing") || !panelUsageReady(f)) return;
    if (editorShape(kind).parameter) {
        assistantMemberWrite(f, event, "accepted", QJSValue(true));
        panelUsageGlobalCall(f, "resetEditorText", {});
        return;
    }
    const auto life = editorGet(f, "editorLife");
    const auto original = editorGet(f, "draft");
    const auto owner = editorGet(f, "ownerToken");
    assistantMemberWrite(f, event, "accepted", QJSValue(true));
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
    if (!editorOriginal(f, life, original, owner)) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
    if (!editorOriginal(f, life, original, owner)) return;
    panelUsageContextWrite(f, "refusal", QJSValue(QString{}));
    if (!editorOriginal(f, life, original, owner)) return;
    panelUsageContextWrite(f, "draft", consentNull());
}
void ApplicationInfo::editorCommit(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    const auto shape = editorShape(kind);
    if (!editorNull(f, "commitInProgress") || editorFlag(f, "inputMethodComposing")
        || (shape.locked && editorFlag(f, "locked")) || !panelUsageReady(f)) return;
    if (editorFlag(f, "assistantEditing")) { panelUsageGlobalCall(f, "cancelAssistantEdit", {}); return; }
    if (editorNull(f, "draft") && !editorFlag(f, "assistantCommitReady")) return;
    bool stale = editorNull(f, "draft");
    if (!stale) {
        const auto owner = panelUsageRead(f, editorGet(f, "draft"), "owner");
        stale = !assistantSameName(f, owner, "ownerToken");
    }
    if (!stale && shape.parameter) {
        const auto item = panelUsageRead(f, editorGet(f, "draft"), "item");
        stale = !assistantSameName(f, item, "item") || editorNull(f, "item");
    }
    if (stale) {
        const auto text = editorText(f, shape, shape.parameter
            ? "This draft no longer belongs to the displayed parameter. Escape cancels it."
            : "This draft belongs to a different row or project. Escape cancels it.");
        panelUsageContextWrite(f, shape.parameter ? "typedRefusal" : "refusal", text);
        return;
    }
    const auto life = editorGet(f, "editorLife");
    const auto owner = editorGet(f, "ownerToken");
    const auto project = editorGet(f, "editOwner");
    const auto draft = editorGet(f, "draft");
    const auto item = shape.parameter ? editorGet(f, "item") : QJSValue();
    const auto text = editorGet(f, "text");
    const auto accepts = !shape.parameter ? editorGet(f, "accepts") : QJSValue();
    if (!panelUsageReady(f)) return;
    const auto original = f->newObject();
    const auto current = [&](bool clearing) {
        if (!editorLife(f, life)) return false;
        const auto component = editorGet(f, shape.id);
        if (!consentFieldEquals(f, component, "ownerToken", owner)) return false;
        const auto actual = editorGet(f, shape.id);
        if (!consentFieldEquals(f, actual, "editOwner", project)) return false;
        if (shape.parameter) {
            const auto actualItem = editorGet(f, shape.id);
            if (!consentFieldEquals(f, actualItem, "item", item)) return false;
        }
        const auto actualDraft = editorGet(f, shape.id);
        if (!consentFieldEquals(f, actualDraft, "draft", clearing ? consentNull() : draft)) return false;
        const auto actualCommit = editorGet(f, shape.id);
        return consentFieldEquals(f, actualCommit, "commitInProgress", original);
    };
    panelUsageContextWrite(f, "commitInProgress", original);
    if (!panelUsageReady(f)) return;
    const EditorFinally release{f, [&] {
        if (!editorLife(f, life)) return;
        const auto component = editorGet(f, shape.id);
        if (consentFieldEquals(f, component, "commitInProgress", original)) {
            const auto actual = editorGet(f, shape.id);
            assistantMemberWrite(f, actual, "commitInProgress", consentNull());
        }
    }};
    if (!current(false)) return;
    QJSValue message(QString{});
    const auto shown = editorGet(f, shape.parameter ? "value" : "shown");
    bool changed = !text.strictlyEquals(shown);
    if (changed && shape.parameter) changed = !assistantSameName(f, text, "editText");
    if (!panelUsageReady(f)) return;
    if (changed) {
        const auto typed = editorGet(f, "TypedInput");
        message = panelUsageMemberCall(f, typed, "refusal", {text, shape.parameter ? QJSValue(QStringLiteral("number")) : accepts});
        if (!current(false)) return;
        if (message.strictlyEquals(QJSValue(QString{}))) {
            if (shape.parameter) {
                const auto number = panelUsageGlobalCall(f, "Number", {text});
                assistantMemberWrite(f, item, "value", number);
                if (!current(false)) return;
                message = panelUsageRead(f, item, "lastError");
            } else {
                panelUsageGlobalCall(f, "committed", {text});
                if (!current(false)) return;
                message = panelUsageTruth(project) ? panelUsageRead(f, project, "lastError") : QJSValue(QString{});
            }
            if (!current(false)) return;
        }
    }
    panelUsageContextWrite(f, "assistantCommitReady", QJSValue(false));
    if (!current(false)) return;
    panelUsageContextWrite(f, "assistantEditing", QJSValue(false));
    if (!current(false)) return;
    panelUsageContextWrite(f, "draft", consentNull());
    if (!current(true)) return;
    panelUsageContextWrite(f, shape.parameter ? "typedRefusal" : "refusal", message);
}
void ApplicationInfo::parameterEditorFocusChanged(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    if (editorFlag(f, "activeFocus")) { panelUsageGlobalCall(f, "refreshCleanText", {}); return; }
    const auto life = editorGet(f, "editorLife");
    const auto owner = editorGet(f, "ownerToken");
    const auto project = editorGet(f, "editOwner");
    const auto item = editorGet(f, "item");
    panelUsageGlobalCall(f, "commit", {});
    if (editorLife(f, life) && assistantSameName(f, owner, "ownerToken") && assistantSameName(f, project, "editOwner")
        && assistantSameName(f, item, "item") && !editorFlag(f, "activeFocus") && editorNull(f, "draft")
        && editorNull(f, "commitInProgress") && !editorFlag(f, "inputMethodComposing")) panelUsageContextWrite(f, "cursorPosition", QJSValue(0));
    Q_UNUSED(kind);
}
void ApplicationInfo::editorRetireOwner() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageReady(f)) panelUsageContextWrite(f, "ownerToken", f->newObject());
}
void ApplicationInfo::editorDestroyed() const {
    const auto f = panelUsageEngine(this);
    const auto life = editorGet(f, "editorLife");
    assistantMemberWrite(f, life, "alive", QJSValue(false));
}
void ApplicationInfo::parameterEditorItemChanged(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageReady(f)) return;
    panelUsageContextWrite(f, "ownerToken", f->newObject());
    if (!editorNull(f, "draft")) panelUsageContextWrite(f, "typedRefusal", editorText(f, editorShape(kind), "This draft belongs to a different parameter. Escape cancels it."));
    else panelUsageGlobalCall(f, "refreshCleanText", {});
}
void ApplicationInfo::editorValueChanged(EditorKind kind) const {
    const auto f = panelUsageEngine(this);
    if (editorNull(f, "draft") && editorNull(f, "commitInProgress") && !editorFlag(f, "inputMethodComposing"))
        panelUsageContextWrite(f, editorShape(kind).parameter ? "typedRefusal" : "refusal", QJSValue(QString{}));
}
void ApplicationInfo::parameterEditorFitToggled(const QJSValue& checked) const {
    const auto f = panelUsageEngine(this);
    if (editorNull(f, "item")) return;
    const auto item = editorGet(f, "item");
    assistantMemberWrite(f, item, "free", checked);
}
void ApplicationInfo::editorTextChanged() const {
    const auto f = panelUsageEngine(this);
    if (!editorFlag(f, "activeFocus")) panelUsageContextWrite(f, "cursorPosition", QJSValue(0));
}
void ApplicationInfo::editorCompositionChanged(EditorKind) const {
    const auto f = panelUsageEngine(this);
    if (editorFlag(f, "inputMethodComposing")) panelUsageGlobalCall(f, "rememberManualDraft", {});
}
void ApplicationInfo::parameterEditorCompleted() const {
    const auto f = panelUsageEngine(this);
    const auto titles = panelUsageContextRead(f, "FieldTitles");
    const auto field = panelUsageContextRead(f, "field");
    panelUsageMemberCall(f, titles, "align", {field});
    panelUsageContextWrite(f, "cursorPosition", QJSValue(0));
}

QJSValue ApplicationInfo::typedInputRefusal(const QString& text, const QString& accepts) const {
    const auto f = panelUsageEngine(this);
    if (accepts == QStringLiteral("text")) return QJSValue(QString{});
    const auto trimmed = panelUsageMemberCall(f, QJSValue(text), "trim");
    const auto number = trimmed.strictlyEquals(QJSValue(QString{})) ? QJSValue(qQNaN()) : panelUsageGlobalCall(f, "Number", {QJSValue(text)});
    const auto finite = panelUsageGlobalCall(f, "isFinite", {number});
    const auto translated = [&](const char* message) {
        if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
        const auto label = QJSValue(QCoreApplication::translate("TypedInput", message));
        return panelUsageMemberCall(f, label, "arg", {QJSValue(text)});
    };
    if (!panelUsageReady(f)) return {};
    if (!panelUsageTruth(finite)) return translated("'%1' is not a number");
    if (accepts == QStringLiteral("integer")) {
        const auto constructor = panelUsageContextRead(f, "Number");
        if (!panelUsageTruth(panelUsageMemberCall(f, constructor, "isInteger", {number}))) return translated("'%1' is not a whole number");
    }
    return QJSValue(QString{});
}
QJSValue ApplicationInfo::parameterFreeRows(bool fittable) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageReady(f)) return {};
    const auto rows = f->newArray();
    if (assistantContextField(f, "menu", "filter").isNull() || assistantContextField(f, "menu", "project").isNull()) return rows;
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto filter = assistantContextField(f, "menu", "filter");
        const auto count = panelUsageMemberCall(f, filter, "rowCount");
        if (!assistantRelation(f, QJSValue(index), count, 0)) break;
        const auto current = assistantContextField(f, "menu", "filter");
        const auto parameter = panelUsageMemberCall(f, current, "parameterAt", {QJSValue(index)});
        if (!parameter.isNull() && panelUsageTruth(panelUsageRead(f, parameter, fittable ? "fittable" : "free")))
            panelUsageMemberCall(f, rows, "push", {parameter});
    }
    return rows;
}
QJSValue ApplicationInfo::parameterFreeCount() const {
    const auto f = panelUsageEngine(this);
    const auto shown = panelUsageContextRead(f, "shown");
    const auto callback = panelUsageCallback(f, 30);
    const auto rows = panelUsageMemberCall(f, shown, "filter", {callback});
    return panelUsageRead(f, rows, "length");
}
void ApplicationInfo::applyParametersFree(const QJSValue& free) const {
    const auto f = panelUsageEngine(this);
    if (!assistantContextField(f, "menu", "project").isNull()) {
        const auto project = assistantContextField(f, "menu", "project");
        const auto rows = projectInvoke(f, "menu", panelUsageTruth(free) ? "fittableRows" : "freeRows");
        panelUsageMemberCall(f, project, "setParametersFree", {rows, free});
    }
    projectInvoke(f, "menu", "close");
}
void ApplicationInfo::parameterMenuMembershipChanged() const {
    const auto f = panelUsageEngine(this);
    const auto current = assistantContextField(f, "menu", "membership");
    const auto number = panelUsageNumber(f, current);
    if (number) projectWrite(f, "menu", "membership", QJSValue(*number + 1));
}
void ApplicationInfo::ensureParameterSelection() const {
    const auto f = panelUsageEngine(this);
    bool replace = assistantContextField(f, "group", "selected").isNull();
    if (!replace) {
        const auto filter = panelUsageContextRead(f, "parameterFilter");
        const auto selected = assistantContextField(f, "group", "selected");
        replace = !panelUsageTruth(panelUsageMemberCall(f, filter, "shows", {selected}));
    }
    if (replace) {
        const auto group = panelUsageContextRead(f, "group");
        const auto parameter = projectInvoke(f, "parameterFilter", "parameterAt", {QJSValue(0)});
        assistantMemberWrite(f, group, "selected", parameter);
    }
    const auto group = panelUsageContextRead(f, "group");
    const auto filter = panelUsageContextRead(f, "parameterFilter");
    const auto selected = assistantContextField(f, "group", "selected");
    const auto row = panelUsageMemberCall(f, filter, "rowOf", {selected});
    assistantMemberWrite(f, group, "selectedRow", row);
}
void ApplicationInfo::parameterSelectionChanged(bool projectChanged) const {
    const auto f = panelUsageEngine(this);
    if (projectChanged) {
        projectWrite(f, "group", "selected", consentNull());
        projectInvoke(f, "group", "ensureSelection");
    } else {
        const auto filter = panelUsageContextRead(f, "parameterFilter");
        const auto selected = panelUsageContextRead(f, "selected");
        panelUsageContextWrite(f, "selectedRow", panelUsageMemberCall(f, filter, "rowOf", {selected}));
    }
}
void ApplicationInfo::updateParameterSliderLimits() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "selected"))) {
        panelUsageContextWrite(f, "lower", QJSValue(0));
        panelUsageContextWrite(f, "upper", QJSValue(1));
        return;
    }
    const auto selected = panelUsageContextRead(f, "selected");
    const auto span = panelUsageMemberCall(f, selected, "sliderHalfWidth");
    const auto value = assistantContextField(f, "selected", "value");
    const auto a = panelUsageNumber(f, value), b = panelUsageNumber(f, span);
    if (!a || !b) return;
    panelUsageContextWrite(f, "lower", QJSValue(*a - *b));
    const auto actual = assistantContextField(f, "selected", "value");
    panelUsageContextWrite(f, "upper", panelUsageAdd(f, actual, span));
}
void ApplicationInfo::parameterSliderPressed(bool destroying) const {
    const auto f = panelUsageEngine(this);
    if (destroying) {
        if (panelUsageTruth(panelUsageContextRead(f, "pressed")) && panelUsageTruth(assistantContextField(f, "group", "project"))) {
            const auto project = assistantContextField(f, "group", "project");
            assistantMemberWrite(f, project, "adjusting", QJSValue(false));
        }
        return;
    }
    if (panelUsageTruth(assistantContextField(f, "group", "project"))) {
        const auto project = assistantContextField(f, "group", "project");
        const auto pressed = panelUsageContextRead(f, "pressed");
        assistantMemberWrite(f, project, "adjusting", pressed);
    }
    if (!panelUsageTruth(panelUsageContextRead(f, "pressed"))) projectInvoke(f, "sliderRow", "updateLimits");
}
QJSValue ApplicationInfo::parameterBound(const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    if (value.strictlyEquals(QJSValue(qInf()))) return QJSValue(QStringLiteral("inf"));
    if (value.strictlyEquals(QJSValue(-qInf()))) return QJSValue(QStringLiteral("-inf"));
    return panelUsageGlobalCall(f, "String", {value});
}
QJSValue ApplicationInfo::formShownValue(const QJSValue& uid, const QJSValue& value, bool omitNaN) const {
    const auto f = panelUsageEngine(this);
    if (value.isUndefined()) return QJSValue(QString{});
    if (omitNaN && panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {value}))) return QJSValue(QString{});
    return projectInvoke(f, "Session", "display", {uid, value});
}
QJSValue ApplicationInfo::measuredRangeIncrement(const QJSValue& summary) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(summary)) return QJSValue(QString{});
    auto item = assistantContextField(f, "group", "rangeItem");
    auto key = panelUsageAdd(f, item, QJSValue(QStringLiteral("_step")));
    auto value = panelUsageRead(f, summary, "stepMinimum");
    const auto smallest = projectInvoke(f, "Session", "display", {key, value});
    item = assistantContextField(f, "group", "rangeItem");
    key = panelUsageAdd(f, item, QJSValue(QStringLiteral("_step")));
    value = panelUsageRead(f, summary, "stepMaximum");
    const auto largest = projectInvoke(f, "Session", "display", {key, value});
    if (smallest.strictlyEquals(largest)) return panelUsageRead(f, summary, "step");
    return panelUsageAdd(f, panelUsageAdd(f, smallest, QJSValue(QStringLiteral("–"))), largest);
}
QJSValue ApplicationInfo::instrumentWavelengthBand(const QJSValue& low, const QJSValue& high) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {low})) || panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {high}))) return QJSValue(QString{});
    const auto first = projectInvoke(f, "Session", "display", {QJSValue(QStringLiteral("refln.wavelength")), low});
    if (low.strictlyEquals(high)) return first;
    const auto last = projectInvoke(f, "Session", "display", {QJSValue(QStringLiteral("refln.wavelength")), high});
    return panelUsageAdd(f, panelUsageAdd(f, first, QJSValue(QStringLiteral("–"))), last);
}
void ApplicationInfo::chooseExperimentType(const QJSValue& axis, const QJSValue& token) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "row", "project"))) return;
    const auto project = assistantContextField(f, "row", "project");
    const auto index = assistantContextField(f, "row", "experimentIndex");
    panelUsageMemberCall(f, project, "setExperimentType", {index, axis, token});
}
void ApplicationInfo::chooseBackgroundType(const QJSValue& token) const {
    const auto f = panelUsageEngine(this);
    const bool line = assistantContextField(f, "experiment", "backgroundType").strictlyEquals(QJSValue(QStringLiteral("line-segment")));
    const char* name = line ? "points" : "terms";
    const auto rows = panelUsageTruth(panelUsageContextRead(f, name)) ? assistantContextField(f, name, "count") : QJSValue(0);
    if (rows.strictlyEquals(QJSValue(0))) {
        projectWrite(f, "experiment", "backgroundType", token);
        return;
    }
    projectWrite(f, "typeQuestion", "token", token);
    projectWrite(f, "typeQuestion", "rows", rows);
    projectInvoke(f, "typeQuestion", "open");
}
void ApplicationInfo::applyGeneratedCategory(int row, const QString& name, const QString& value) const {
    const auto f = panelUsageEngine(this);
    const auto group = panelUsageContextRead(f, "group");
    QJSValue refusal(QString{});
    if (panelUsageTruth(assistantContextField(f, "Session", "project"))) {
        const auto project = assistantContextField(f, "Session", "project");
        const auto source = assistantContextField(f, "group", "source");
        const auto file = panelUsageRead(f, source, "file");
        const auto edited = projectInvoke(f, "data", "editedText", {QJSValue(row), QJSValue(name), QJSValue(value)});
        refusal = panelUsageMemberCall(f, project, "applyText", {file, edited});
    }
    assistantMemberWrite(f, group, "refusal", refusal);
}
QJSValue ApplicationInfo::parameterSegments(const QJSValue& entry, bool category) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageReady(f)) return {};
    if (!panelUsageTruth(entry)) return f->newArray();
    const auto title = panelUsageLiteral(f);
    panelUsageWrite(f, title.value, "text", panelUsageRead(f, entry, "title"));
    if (category) panelUsageWrite(f, title.value, "bold", panelUsageRead(f, entry, "datablock"));
    panelUsageWrite(f, title.value, "elides", QJSValue(true));
    const auto text = panelUsageComplete(f, title);
    const auto icon = panelUsageRead(f, entry, "icon");
    if (icon.strictlyEquals(QJSValue(QString{}))) return assistantGeometryArray(f, {text});
    const auto segment = panelUsageLiteral(f);
    panelUsageWrite(f, segment.value, "icon", panelUsageRead(f, entry, "icon"));
    QJSValue color;
    if (category) {
        const auto colors = assistantContextField(f, "EaStyle", "Colors");
        color = panelUsageRead(f, colors, "themeForegroundMinor");
    } else {
        const auto group = panelUsageContextRead(f, "group");
        const auto kind = panelUsageRead(f, entry, "blockKind");
        const auto name = panelUsageRead(f, entry, "blockName");
        color = panelUsageMemberCall(f, group, "datablockColor", {kind, name});
    }
    panelUsageWrite(f, segment.value, "color", color);
    return assistantGeometryArray(f, {panelUsageComplete(f, segment), text});
}
QJSValue ApplicationInfo::parameterDatablockColor(const QJSValue& kind, const QJSValue& name) const {
    const auto f = panelUsageEngine(this);
    QJSValue blocks = consentNull();
    if (panelUsageTruth(assistantContextField(f, "group", "project"))) {
        const auto project = assistantContextField(f, "group", "project");
        blocks = panelUsageRead(f, project, kind.strictlyEquals(QJSValue(QStringLiteral("structure"))) ? "structures" : "experiments");
    }
    double place = 0;
    for (double row = 0; panelUsageReady(f) && panelUsageTruth(blocks); ++row) {
        if (!assistantRelation(f, QJSValue(row), panelUsageRead(f, blocks, "count"), 0)) break;
        const auto actual = panelUsageMemberCall(f, blocks, "text", {QJSValue(row), QJSValue(QStringLiteral("name"))});
        if (actual.strictlyEquals(name)) { place = row; break; }
    }
    const auto colors = panelUsageContextRead(f, "AppColors");
    return panelUsageMemberCall(f, colors, kind.strictlyEquals(QJSValue(QStringLiteral("structure"))) ? "structure" : "experiment", {QJSValue(place)});
}
QJSValue ApplicationInfo::derivedBackgroundValue(const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {value})) || assistantRelation(f, value, QJSValue(0), 3)) return QJSValue(QString{});
    const auto math = panelUsageContextRead(f, "Math");
    const auto rounded = panelUsageMemberCall(f, math, "round", {value});
    return panelUsageGlobalCall(f, "String", {rounded});
}
void ApplicationInfo::parameterCellRefit() const {
    const auto f = panelUsageEngine(this);
    const auto math = panelUsageContextRead(f, "Math");
    const auto width = panelUsageNumber(f, panelUsageContextRead(f, "width"));
    const auto implicit = panelUsageNumber(f, panelUsageContextRead(f, "implicitWidth"));
    if (!width || !implicit) return;
    const auto absolute = panelUsageMemberCall(f, math, "abs", {QJSValue(*width - *implicit)});
    const auto sized = assistantRelation(f, absolute, QJSValue(0.5), 2);
    bool full = panelUsageTruth(panelUsageContextRead(f, "fitDigits")) || !sized;
    if (!full) full = panelUsageContextRead(f, "item").isNull();
    QJSValue shown;
    if (full) shown = panelUsageContextRead(f, "valueText");
    else {
        const auto formatter = panelUsageContextRead(f, "NumberText");
        QJSValueList args;
        for (const char* name : {"valueText", "room", "shownMetrics", "narrowText"}) args.append(panelUsageContextRead(f, name));
        shown = panelUsageMemberCall(f, formatter, "fitted", args);
    }
    panelUsageContextWrite(f, "shownValue", shown);
}
QJSValue ApplicationInfo::parameterCellScaledPixelSize() const {
    const auto f = panelUsageEngine(this);
    const auto sizes = assistantContextField(f, "EaStyle", "Sizes");
    const auto full = panelUsageRead(f, sizes, "fontPixelSize");
    if (!panelUsageTruth(panelUsageContextRead(f, "fitDigits")) || assistantRelation(f, panelUsageContextRead(f, "room"), QJSValue(0), 3)) return full;
    const auto metrics = panelUsageContextRead(f, "fullMetrics");
    const auto text = panelUsageContextRead(f, "fullText");
    const auto needed = panelUsageMemberCall(f, metrics, "advanceWidth", {text});
    if (!assistantRelation(f, needed, panelUsageContextRead(f, "room"), 1)) return full;
    const auto math = panelUsageContextRead(f, "Math");
    const auto floorMath = panelUsageContextRead(f, "Math");
    const auto a = panelUsageNumber(f, full);
    const auto b = panelUsageNumber(f, panelUsageContextRead(f, "room"));
    const auto c = panelUsageNumber(f, needed);
    if (!a || !b || !c) return {};
    const auto rounded = panelUsageMemberCall(f, floorMath, "floor", {QJSValue(*a * *b / *c)});
    return panelUsageMemberCall(f, math, "max", {QJSValue(1), rounded});
}

namespace {
QJSValue pickerRecord(const PanelUsageFrame& f, const QJSValue& project, const QJSValue& experiment = {}, bool data = false) {
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "project", project);
    if (data) panelUsageWrite(f, literal.value, "experiment", experiment);
    return panelUsageComplete(f, literal);
}
bool pickerSessionProject(const PanelUsageFrame& f, const QJSValue& original) {
    const auto session = assistantContextField(f, "Session", "project");
    const auto requested = panelUsageRead(f, original, "project");
    return panelUsageReady(f) && session.strictlyEquals(requested);
}
bool pickerProject(const PanelUsageFrame& f, const QJSValue& original) {
    if (!consentFieldsEqual(f, panelUsageContextRead(f, "group"), "project", original, "project")) return false;
    const auto project = assistantContextField(f, "Session", "project");
    return consentFieldEquals(f, original, "project", project);
}
} // namespace

void ApplicationInfo::loadFormFiles(bool experiments) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) {
        const auto group = panelUsageContextRead(f, "group");
        const auto project = assistantContextField(f, "group", "project");
        assistantMemberWrite(f, group, "webRequestProject", project);
        if (experiments) projectWrite(f, "group", "webDataExperiment", consentNull());
        const auto requestOwner = panelUsageContextRead(f, "group");
        const auto request = projectInvoke(f, "WebFiles", "openFiles", {QJSValue(QStringLiteral(".cif,.edi")), QJSValue(experiments)});
        assistantMemberWrite(f, requestOwner, "webRequest", request);
    } else projectInvoke(f, "loadDialog", "open");
}
bool ApplicationInfo::chooseStructureFile() const {
    const auto f = panelUsageEngine(this);
    const auto life = panelUsageContextRead(f, "pickerLife");
    const auto project = panelUsageContextRead(f, "project");
    if (!editorLife(f, life) || !assistantSameName(f, project, "project") || !projectFieldIs(f, "Session", "project", project)) return false;
    if (panelUsageContextRead(f, "project").isNull()) return false;
    const auto sessionProject = assistantContextField(f, "Session", "project");
    if (!assistantSameName(f, sessionProject, "project") || !panelUsageContextRead(f, "webIntent").isNull()
        || !assistantContextField(f, "loadDialog", "intent").isNull() || panelUsageTruth(assistantContextField(f, "loadDialog", "visible"))) return false;
    const auto original = pickerRecord(f, panelUsageContextRead(f, "project"));
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) {
        panelUsageContextWrite(f, "webIntent", original);
        if (!editorLife(f, life) || !assistantSameName(f, original, "webIntent")) return false;
        const auto actualProject = panelUsageContextRead(f, "project");
        if (!consentFieldEquals(f, original, "project", actualProject) || !pickerSessionProject(f, original)) {
            panelUsageContextWrite(f, "webIntent", consentNull()); return false;
        }
        const auto request = projectInvoke(f, "WebFiles", "openFiles", {QJSValue(QStringLiteral(".edi,.cif")), QJSValue(false)});
        if (!editorLife(f, life) || !assistantSameName(f, original, "webIntent")) return false;
        const auto currentProject = panelUsageContextRead(f, "project");
        if (request.strictlyEquals(QJSValue(0)) || !consentFieldEquals(f, original, "project", currentProject)
            || !pickerSessionProject(f, original)) {
            panelUsageContextWrite(f, "webIntent", consentNull()); return false;
        }
        panelUsageContextWrite(f, "webRequest", request);
    } else {
        projectWrite(f, "loadDialog", "intent", original);
        if (!editorLife(f, life) || !projectFieldIs(f, "loadDialog", "intent", original)) return false;
        const auto currentProject = panelUsageContextRead(f, "project");
        if (!consentFieldEquals(f, original, "project", currentProject)
            || !pickerSessionProject(f, original)) {
            projectWrite(f, "loadDialog", "intent", consentNull()); return false;
        }
        projectInvoke(f, "loadDialog", "open");
    }
    return true;
}
QJSValue ApplicationInfo::takeStructureWebIntent(const QJSValue& request) const {
    const auto f = panelUsageEngine(this);
    if (!assistantSameName(f, request, "webRequest") || panelUsageContextRead(f, "webIntent").isNull()) return consentNull();
    const auto life = panelUsageContextRead(f, "pickerLife");
    const auto original = panelUsageContextRead(f, "webIntent");
    panelUsageContextWrite(f, "webRequest", QJSValue(0));
    if (!editorLife(f, life) || !assistantSameName(f, original, "webIntent")) return consentNull();
    panelUsageContextWrite(f, "webIntent", consentNull());
    if (!editorLife(f, life) || !panelUsageContextRead(f, "webIntent").isNull()) return consentNull();
    const auto project = panelUsageContextRead(f, "project");
    if (!consentFieldEquals(f, original, "project", project)
        || !pickerSessionProject(f, original)) return consentNull();
    return original;
}
void ApplicationInfo::chooseExperimentData(const QJSValue& experiment) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) {
        projectWrite(f, "group", "webRequestProject", assistantContextField(f, "group", "project"));
        projectWrite(f, "group", "webDataExperiment", experiment);
        const auto group = panelUsageContextRead(f, "group");
        const auto filter = assistantContextField(f, "group", "dataFilter");
        const auto request = projectInvoke(f, "WebFiles", "openFiles", {filter, QJSValue(false)});
        assistantMemberWrite(f, group, "webRequest", request);
    } else {
        if (panelUsageTruth(assistantContextField(f, "dataDialog", "visible"))) return;
        const auto dialog = panelUsageContextRead(f, "dataDialog");
        const auto project = assistantContextField(f, "group", "project");
        assistantMemberWrite(f, dialog, "intent", pickerRecord(f, project, experiment, true));
        projectWrite(f, "dataDialog", "experiment", experiment);
        projectWrite(f, "dataDialog", "project", assistantContextField(f, "group", "project"));
        projectInvoke(f, "dataDialog", "open");
    }
}
void ApplicationInfo::formFilesOpened(const QJSValue& request, const QJSValue& files, bool experiments) const {
    const auto f = panelUsageEngine(this);
    if (!projectFieldIs(f, "group", "webRequest", request)) return;
    projectWrite(f, "group", "webRequest", QJSValue(0));
    QJSValue experiment;
    bool data = false;
    if (experiments) {
        experiment = assistantContextField(f, "group", "webDataExperiment");
        data = !experiment.isNull();
        projectWrite(f, "group", "webDataExperiment", consentNull());
    }
    if (assistantContextField(f, "group", "project").isNull()) return;
    const auto current = assistantContextField(f, "group", "project");
    if (!projectFieldIs(f, "group", "webRequestProject", current)) return;
    const auto project = assistantContextField(f, "group", "project");
    if (!experiments || data) {
        const auto first = panelUsageIndex(f, files, 0);
        panelUsageMemberCall(f, project, experiments ? "loadDataInto" : "loadStructure", experiments ? QJSValueList{experiment, first} : QJSValueList{first});
    } else panelUsageMemberCall(f, project, "loadExperiments", {files});
}
void ApplicationInfo::formFilesCancelled(const QJSValue& request, bool experiments) const {
    const auto f = panelUsageEngine(this);
    if (!projectFieldIs(f, "group", "webRequest", request)) return;
    projectWrite(f, "group", "webRequest", QJSValue(0));
    if (experiments) projectWrite(f, "group", "webDataExperiment", consentNull());
}
void ApplicationInfo::acceptExperimentDataFile() const {
    const auto f = panelUsageEngine(this);
    const auto life = assistantContextField(f, "group", "pickerLife");
    const auto original = panelUsageContextRead(f, "intent");
    const auto file = panelUsageContextRead(f, "selectedFile");
    panelUsageContextWrite(f, "intent", consentNull());
    if (!editorLife(f, life) || !panelUsageContextRead(f, "intent").isNull() || original.isNull()
        || panelUsageRead(f, original, "experiment").isNull() || !pickerProject(f, original)) return;
    const auto project = panelUsageRead(f, original, "project");
    const auto experiment = panelUsageRead(f, original, "experiment");
    panelUsageMemberCall(f, project, "loadDataInto", {experiment, file});
}
void ApplicationInfo::formPickerDestroyed() const {
    const auto f = panelUsageEngine(this);
    const auto life = panelUsageContextRead(f, "pickerLife");
    assistantMemberWrite(f, life, "alive", QJSValue(false));
}
bool ApplicationInfo::sameExperimentGesture(const QJSValue& point) const {
    const auto f = panelUsageEngine(this);
    const auto retained = assistantContextField(f, "assistantGesture", "current");
    if (retained.isNull()) return false;
    for (const auto& field : {std::pair{"device", "device"}, std::pair{"id", "id"}, std::pair{"press", "pressTimestamp"}})
        if (!consentFieldsEqual(f, retained, field.first, point, field.second)) return false;
    return panelUsageReady(f);
}
void ApplicationInfo::discardExperimentGesture(const QJSValue& point) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(f, "sameGesture", {point}))) return;
    auto current = assistantContextField(f, "assistantGesture", "current");
    assistantMemberWrite(f, current, "closed", QJSValue(true));
    current = assistantContextField(f, "assistantGesture", "current");
    assistantMemberWrite(f, current, "proof", consentNull());
}
void ApplicationInfo::experimentGrabChanged(const QJSValue& transition, const QJSValue& point) const {
    const auto f = panelUsageEngine(this);
    const auto passive = assistantContextField(f, "PointerDevice", "GrabPassive");
    bool grabbed = transition.strictlyEquals(passive);
    if (!grabbed) grabbed = transition.strictlyEquals(assistantContextField(f, "PointerDevice", "GrabExclusive"));
    if (grabbed) {
        if (panelUsageTruth(panelUsageGlobalCall(f, "sameGesture", {point}))) return;
        const auto state = panelUsageRead(f, point, "state");
        if (!state.strictlyEquals(assistantContextField(f, "EventPoint", "Pressed"))) return;
        const auto literal = panelUsageLiteral(f);
        for (const auto& field : {std::pair{"device", "device"}, std::pair{"id", "id"}, std::pair{"press", "pressTimestamp"}})
            panelUsageWrite(f, literal.value, field.first, panelUsageRead(f, point, field.second));
        panelUsageWrite(f, literal.value, "proof", consentNull());
        panelUsageWrite(f, literal.value, "closed", QJSValue(false));
        const auto original = panelUsageComplete(f, literal);
        const auto holder = panelUsageContextRead(f, "assistantGesture");
        assistantMemberWrite(f, holder, "current", original);
        const auto owner = assistantContextField(f, "Session", "assistant");
        const auto control = panelUsageContextRead(f, "loadData");
        const auto experiment = assistantContextField(f, "row", "experiment");
        const auto proof = panelUsageMemberCall(f, owner, "beginManualControlInput", {control, point, experiment});
        if (consentFieldEquals(f, holder, "current", original) && !panelUsageTruth(panelUsageRead(f, original, "closed"))) assistantMemberWrite(f, original, "proof", proof);
    } else {
        for (const char* name : {"UngrabPassive", "UngrabExclusive", "CancelGrabPassive", "CancelGrabExclusive"}) {
            if (transition.strictlyEquals(assistantContextField(f, "PointerDevice", name))) {
                panelUsageGlobalCall(f, "discardGesture", {point}); return;
            }
        }
    }
}
void ApplicationInfo::experimentGestureCancelled(const QJSValue& point) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageGlobalCall(f, "sameGesture", {point}))) panelUsageGlobalCall(f, "discardGesture", {point});
}
void ApplicationInfo::experimentGestureTapped(const QJSValue& point) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(f, "sameGesture", {point}))) return;
    const auto current = assistantContextField(f, "assistantGesture", "current");
    if (panelUsageTruth(panelUsageRead(f, current, "closed"))) return;
    const auto original = assistantContextField(f, "assistantGesture", "current");
    const auto proof = panelUsageRead(f, original, "proof");
    assistantMemberWrite(f, original, "closed", QJSValue(true));
    assistantMemberWrite(f, original, "proof", consentNull());
    const auto owner = assistantContextField(f, "Session", "assistant");
    const auto control = panelUsageContextRead(f, "loadData");
    const auto experiment = assistantContextField(f, "row", "experiment");
    if (panelUsageTruth(panelUsageMemberCall(f, owner, "completeManualControlInput", {control, point, experiment, proof}))) projectInvoke(f, "loadData", "clicked");
}
void ApplicationInfo::activateFormBlock(const QJSValue& row, bool structure) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "group", "project"))) return;
    const auto project = assistantContextField(f, "group", "project");
    assistantMemberWrite(f, project, structure ? "currentStructureIndex" : "currentExperimentIndex", row);
}
void ApplicationInfo::rejectExperimentDataFile() const { panelUsageContextWrite(panelUsageEngine(this), "intent", consentNull()); }

void ApplicationInfo::commitValueField(const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "editable"))) return;
    const auto text = panelUsageContextRead(f, "text");
    if (projectFieldIs(f, "field", "value", text)) return;
    QJSValue refusal;
    bool clear = panelUsageTruth(panelUsageContextRead(f, "clearable"));
    if (clear) clear = panelUsageContextRead(f, "text").strictlyEquals(QJSValue(QString{}));
    if (clear) refusal = QJSValue(QString{});
    else {
        const auto typed = panelUsageContextRead(f, "TypedInput");
        const auto actualText = panelUsageContextRead(f, "text");
        const auto accepts = panelUsageContextRead(f, "accepts");
        refusal = panelUsageMemberCall(f, typed, "refusal", {actualText, accepts});
    }
    panelUsageContextWrite(f, "refusal", refusal);
    if (panelUsageContextRead(f, "refusal").strictlyEquals(QJSValue(QString{})) && !panelUsageTruth(panelUsageContextRead(f, "typedAdmitted")))
        panelUsageContextWrite(f, "refusal", panelUsageContextRead(f, "admitsRule"));
    if (panelUsageContextRead(f, "refusal").strictlyEquals(QJSValue(QString{}))) {
        panelUsageGlobalCall(f, "committed", {panelUsageContextRead(f, "text")});
        QJSValue error(QString{});
        if (panelUsageTruth(assistantContextField(f, "Session", "project"))) {
            const auto project = assistantContextField(f, "Session", "project");
            error = panelUsageRead(f, project, "lastError");
        }
        panelUsageContextWrite(f, "refusal", error);
    }
    projectCall(f, restoreBinding);
}
void ApplicationInfo::activateSelector(const QJSValue& index, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this);
    const auto life = panelUsageContextRead(f, "editorLife");
    const auto owner = assistantContextField(f, "Session", "project");
    const auto options = panelUsageContextRead(f, "options");
    if (!panelUsageReady(f)) return;
    const auto original = f->newObject();
    panelUsageContextWrite(f, "activation", original);
    const auto current = [&] {
        return editorLife(f, life) && projectFieldIs(f, "selector", "activation", original)
            && projectFieldIs(f, "Session", "project", owner) && projectFieldIs(f, "selector", "options", options);
    };
    if (!current() || options.isNull()) return;
    const auto chosen = panelUsageMemberCall(f, options, "tokenAt", {index});
    if (!current()) return;
    if (!assistantSameName(f, chosen, "token")) {
        panelUsageGlobalCall(f, "selected", {chosen});
        if (!current()) return;
        const auto message = panelUsageTruth(owner) ? panelUsageRead(f, owner, "lastError") : QJSValue(QString{});
        if (!current()) return;
        panelUsageContextWrite(f, "refusal", message);
        if (!current()) return;
    }
    projectCall(f, restoreBinding);
}
void ApplicationInfo::resetPreferences() const {
    const auto f = panelUsageEngine(this);
    projectWrite(f, "preferences", "assistantWidth", assistantContextField(f, "AppSizes", "assistantDefaultWidth"));
    const std::pair<const char*, QJSValue> defaults[] = {
        {"toolTips", QJSValue(true)}, {"autoCollapse", QJSValue(true)}, {"sideBarSide", QJSValue(QStringLiteral("Right"))},
        {"engineThreads", QJSValue(0)}, {"scanPatternUpdates", QJSValue(2)}, {"analysisShowNotMeasured", QJSValue(true)},
        {"analysisShowBySymmetry", QJSValue(false)}, {"analysisShowByConstraint", QJSValue(false)}, {"analysisShowFixedSettings", QJSValue(false)},
        {"showFitResults", QJSValue(true)}, {"scanRenderer", QJSValue(QStringLiteral("auto"))}, {"newProjectSuRule", QJSValue(QStringLiteral("iucr_99"))},
        {"newReportLibraries", QJSValue(QStringLiteral("online"))}, {"colourScheme", QJSValue(QStringLiteral("earth"))}, {"patternYScale", QJSValue(QStringLiteral("linear"))},
        {"structureCurves", QJSValue(true)}, {"patternLegendShown", QJSValue(false)}, {"patternHoverShown", QJSValue(true)},
        {"patternMeasuredStyle", QJSValue(QStringLiteral("band"))}, {"patternPointerMode", QJSValue(QStringLiteral("zoom"))},
        {"scanStackedPalette", QJSValue(QString{})}, {"scanMapColours", QJSValue(QStringLiteral("blue-red"))}, {"scanMapSmooth", QJSValue(true)},
        {"scanStackedReversed", QJSValue(false)}, {"scanStackedLegendShown", QJSValue(false)}, {"chartIncludedOnly", QJSValue(false)},
        {"chartSubtractBackground", QJSValue(false)}, {"singleCrystalQuantity", QJSValue(QStringLiteral("f_squared"))},
        {"chartHighlightSelected", QJSValue(true)}, {"chartHiddenRange", QJSValue(QStringLiteral("keep"))}, {"textShow", QJSValue(QStringLiteral("editable"))}
    };
    for (const auto& [name, value] : defaults) projectWrite(f, "preferences", name, value);
}
void ApplicationInfo::applyPreferences() const {
    const auto f = panelUsageEngine(this);
    auto globals = assistantContextField(f, "EaGlobals", "Vars");
    assistantMemberWrite(f, globals, "showToolTips", assistantContextField(f, "preferences", "toolTips"));
    globals = assistantContextField(f, "EaGlobals", "Vars");
    assistantMemberWrite(f, globals, "autoCollapseSideBarGroups", assistantContextField(f, "preferences", "autoCollapse"));
    projectInvoke(f, "ApplicationInfo", "setEngineThreads", {assistantContextField(f, "preferences", "engineThreads")});
    globals = assistantContextField(f, "EaGlobals", "Vars");
    assistantMemberWrite(f, globals, "checkUpdateOnAppStart", QJSValue(false));
    const auto sizes = assistantContextField(f, "EaStyle", "Sizes");
    assistantMemberWrite(f, sizes, "defaultScale", QJSValue(100));
}
void ApplicationInfo::preferencesColourChanged() const {
    const auto f = panelUsageEngine(this);
    const auto value = panelUsageContextRead(f, "colourScheme");
    const auto offered = projectInvoke(f, "ApplicationInfo", "colourSchemeOrDefault", {value});
    if (!assistantSameName(f, offered, "colourScheme")) panelUsageContextWrite(f, "colourScheme", offered);
}
void ApplicationInfo::preferencesStackedPaletteChanged() const {
    const auto f = panelUsageEngine(this);
    auto array = panelUsageContextRead(f, "Array");
    auto values = assistantContextField(f, "ApplicationInfo", "colourSchemes");
    const auto first = panelUsageMemberCall(f, array, "from", {values});
    array = panelUsageContextRead(f, "Array");
    values = assistantContextField(f, "ApplicationInfo", "scanColourMaps");
    const auto second = panelUsageMemberCall(f, array, "from", {values});
    const auto offered = panelUsageMemberCall(f, first, "concat", {second});
    if (!panelUsageContextRead(f, "scanStackedPalette").strictlyEquals(QJSValue(QString{}))) {
        const auto chosen = panelUsageContextRead(f, "scanStackedPalette");
        const auto index = panelUsageMemberCall(f, offered, "indexOf", {chosen});
        if (assistantRelation(f, index, QJSValue(0), 0)) panelUsageContextWrite(f, "scanStackedPalette", QJSValue(QString{}));
    }
}
void ApplicationInfo::preferencesLegacyPaletteChanged() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageContextRead(f, "patternColourScheme").strictlyEquals(QJSValue(QString{}))) return;
    const auto original = panelUsageContextRead(f, "patternColourScheme");
    const auto offered = projectInvoke(f, "ApplicationInfo", "colourSchemeOrDefault", {original});
    panelUsageContextWrite(f, "colourScheme", offered);
    panelUsageContextWrite(f, "patternColourScheme", QJSValue(QString{}));
}
void ApplicationInfo::persistPreference(int kind) const {
    const auto f = panelUsageEngine(this);
    const char* settings = "developSettings";
    const char* key = "engineThreads";
    const char* property = "engineThreads";
    if (kind == 0) projectInvoke(f, "ApplicationInfo", "setEngineThreads", {panelUsageContextRead(f, "engineThreads")});
    else if (kind == 1) { settings = "chartSettings"; key = "includedOnly"; property = "chartIncludedOnly"; }
    else if (kind == 2) { settings = "scanViewSettings"; key = "renderer"; property = "scanRenderer"; }
    else { settings = "analysisSettings"; key = "scanPatternUpdates"; property = "scanPatternUpdates"; }
    const auto target = panelUsageContextRead(f, settings);
    const auto value = panelUsageContextRead(f, property);
    panelUsageMemberCall(f, target, "setValue", {QJSValue(QString::fromLatin1(key)), value});
    projectInvoke(f, settings, "sync");
    projectInvoke(f, "ApplicationInfo", "storeSettings");
}

namespace {
QJSValue viewArithmetic(const PanelUsageFrame& f, const QJSValue& left, const QJSValue& right, int operation) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm());
    QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), left));
    QV4::ScopedValue b(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), right));
    QV4::ScopedValue result(scope);
    if (operation == 0) result = QV4::Runtime::Sub::call(*a, *b);
    else if (operation == 1) result = QV4::Runtime::Mul::call(*a, *b);
    else result = QV4::Runtime::Div::call(*a, *b);
    f.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue viewCallback(const PanelUsageFrame& f, uint operation, int arity) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm());
    QV4::Scoped<QV4::QmlContext> context(scope, f.qmlScope);
    QV4::Scoped<QV4::AssistantPanelCallback> callback(scope,
        f.vm()->memoryManager->allocate<QV4::AssistantPanelCallback>(f.vm(), context.getPointer(), operation, nullptr));
    callback->defineReadonlyConfigurableProperty(f.vm()->id_length(), QV4::Value::fromInt32(arity));
    return QJSValuePrivate::fromReturnedValue(callback->asReturnedValue());
}
QJSValue viewProcedureCallback(const PanelUsageFrame& f, uint operation, const std::function<QJSValue(uint)>& arg) {
    if (operation == 40) {
        const auto item = arg(0);
        for (const char* name : {"rowLabel", "rowBox", "rowButton"})
            if (panelUsageRead(f, item, name).strictlyEquals(QJSValue(true))) return QJSValue(true);
        return QJSValue(false);
    }
    if (operation == 41) {
        const auto accumulated = arg(0), page = arg(1);
        const auto nested = panelUsageGlobalCall(f, "itemsUnder", {page, viewCallback(f, 40, 1)});
        return panelUsageMemberCall(f, accumulated, "concat", {nested});
    }
    const auto widest = arg(0), item = arg(1);
    if (operation == 42) {
        if (!panelUsageRead(f, item, "rowLabel").strictlyEquals(QJSValue(true))) return widest;
        const auto math = panelUsageContextRead(f, "Math");
        const auto width = panelUsageRead(f, item, "implicitWidth");
        return panelUsageMemberCall(f, math, "max", {widest, width});
    }
    const auto math = panelUsageContextRead(f, "Math");
    QJSValue needed;
    if (operation == 44) needed = panelUsageRead(f, item, "implicitHeight");
    else if (panelUsageRead(f, item, "rowBox").strictlyEquals(QJSValue(true))) needed = panelUsageGlobalCall(f, "boxNeed", {item});
    else if (panelUsageRead(f, item, "rowButton").strictlyEquals(QJSValue(true))) needed = panelUsageGlobalCall(f, "buttonNeed", {item});
    else needed = QJSValue(0);
    return panelUsageMemberCall(f, math, "max", {widest, needed});
}
void viewAnchor(const PanelUsageFrame& f, const QJSValue& object, const char* edge, const QJSValue& value) {
    const auto anchors = panelUsageRead(f, object, "anchors");
    assistantMemberWrite(f, anchors, edge, value);
}
} // namespace

QJSValue ApplicationInfo::preferenceItemsUnder(const QJSValue& item, const QJSValue& wanted) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageReady(f)) return {};
    QJSValue found = f->newArray();
    const auto children = panelUsageRead(f, item, "children");
    panelUsageEach(f, children, [&](const QJSValue& child) {
        if (panelUsageTruth(projectCall(f, wanted, {child}))) panelUsageMemberCall(f, found, "push", {child});
        const auto original = found;
        const auto nested = panelUsageGlobalCall(f, "itemsUnder", {child, wanted});
        found = panelUsageMemberCall(f, original, "concat", {nested});
        return panelUsageReady(f);
    });
    return found;
}
QJSValue ApplicationInfo::preferenceBoxNeed(const QJSValue& box) const {
    const auto f = panelUsageEngine(this);
    QJSValue widest(0);
    for (double index = 0; panelUsageReady(f); ++index) {
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, box, "count"), 0)) break;
        const auto math = panelUsageContextRead(f, "Math");
        const auto metrics = panelUsageContextRead(f, "boxMetrics");
        const auto text = panelUsageMemberCall(f, box, "textAt", {QJSValue(index)});
        const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {text});
        widest = panelUsageMemberCall(f, math, "max", {widest, width});
    }
    auto math = panelUsageContextRead(f, "Math");
    const auto content = panelUsageRead(f, box, "implicitContentWidth");
    const auto metrics = panelUsageContextRead(f, "boxMetrics");
    const auto displayed = panelUsageRead(f, box, "displayText");
    const auto textWidth = panelUsageMemberCall(f, metrics, "advanceWidth", {displayed});
    const auto difference = viewArithmetic(f, content, textWidth, 0);
    const auto insets = panelUsageMemberCall(f, math, "max", {QJSValue(0), difference});
    math = panelUsageContextRead(f, "Math");
    const auto padding = viewArithmetic(f, QJSValue(2), panelUsageRead(f, box, "padding"), 1);
    auto sum = panelUsageAdd(f, widest, padding);
    sum = panelUsageAdd(f, sum, panelUsageRead(f, box, "spacing"));
    const auto indicator = viewArithmetic(f, QJSValue(2), panelUsageRead(f, box, "implicitIndicatorWidth"), 1);
    sum = panelUsageAdd(f, sum, indicator);
    sum = panelUsageAdd(f, sum, insets);
    return panelUsageMemberCall(f, math, "ceil", {sum});
}
QJSValue ApplicationInfo::preferenceButtonNeed(const QJSValue& button) const {
    const auto f = panelUsageEngine(this);
    const auto math = panelUsageContextRead(f, "Math");
    const auto metrics = panelUsageContextRead(f, "boxMetrics");
    const auto text = panelUsageRead(f, button, "text");
    const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {text});
    const auto sizes = assistantContextField(f, "EaStyle", "Sizes");
    const auto inset = viewArithmetic(f, QJSValue(2), panelUsageRead(f, sizes, "fontPixelSize"), 1);
    return panelUsageMemberCall(f, math, "ceil", {panelUsageAdd(f, width, inset)});
}
QJSValue ApplicationInfo::preferenceRowItems() const {
    const auto f = panelUsageEngine(this);
    const auto children = assistantContextField(f, "pages", "contentChildren");
    const auto callback = viewCallback(f, 41, 2);
    if (!panelUsageReady(f)) return {};
    return panelUsageMemberCall(f, children, "reduce", {callback, f->newArray()});
}
QJSValue ApplicationInfo::preferenceRowWidth(bool controls) const {
    const auto f = panelUsageEngine(this);
    const auto rows = panelUsageContextRead(f, "rowItems");
    return panelUsageMemberCall(f, rows, "reduce", {viewCallback(f, controls ? 43 : 42, 2), QJSValue(0)});
}
QJSValue ApplicationInfo::preferenceContentHeight() const {
    const auto f = panelUsageEngine(this);
    auto height = assistantContextField(f, "bar", "implicitHeight");
    height = panelUsageAdd(f, height, assistantContextField(f, "pages", "topPadding"));
    height = panelUsageAdd(f, height, assistantContextField(f, "pages", "bottomPadding"));
    const auto pages = assistantContextField(f, "pages", "contentChildren");
    const auto maximum = panelUsageMemberCall(f, pages, "reduce", {viewCallback(f, 44, 2), QJSValue(0)});
    return panelUsageAdd(f, height, maximum);
}
void ApplicationInfo::alignFieldTitle(const QJSValue& field, const QJSValue& installMargin, const QJSValue& installWidth) const {
    const auto f = panelUsageEngine(this);
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto children = panelUsageRead(f, field, "children");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, children, "length"), 0)) return;
        const auto actual = panelUsageRead(f, field, "children");
        const auto child = panelUsageIndex(f, actual, static_cast<quint32>(index));
        if (panelUsageRead(f, child, "text").isUndefined() || panelUsageRead(f, child, "elide").isUndefined()) continue;
        const auto text = panelUsageRead(f, child, "text");
        if (!consentFieldEquals(f, field, "shortPrettyName", text)) continue;
        if (panelUsageRead(f, child, "text").strictlyEquals(QJSValue(QString{}))) continue;
        viewAnchor(f, child, "right", {});
        viewAnchor(f, child, "left", panelUsageRead(f, field, "left"));
        projectCall(f, installMargin, {child});
        assistantMemberWrite(f, child, "rightPadding", QJSValue(0));
        projectCall(f, installWidth, {child});
        const auto elide = assistantContextField(f, "Text", "ElideRight");
        assistantMemberWrite(f, child, "elide", elide);
        return;
    }
}
void ApplicationInfo::showWorkflowSidebarTab(const QJSValue& extra) const {
    const auto f = panelUsageEngine(this);
    const quint32 index = panelUsageTruth(extra) ? 1 : 0;
    const auto tabs = assistantContextField(f, "sideBar", "tabs");
    if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, tabs, "length"), 0)) return;
    const auto actual = assistantContextField(f, "sideBar", "tabs");
    const auto tab = panelUsageIndex(f, actual, index);
    if (!panelUsageTruth(panelUsageRead(f, tab, "enabled"))) return;
    const auto current = assistantContextField(f, "sideBar", "tabs");
    assistantMemberWrite(f, panelUsageIndex(f, current, index), "checked", QJSValue(true));
}
void ApplicationInfo::showWorkflowMainTab(const QJSValue& index) const {
    const auto f = panelUsageEngine(this);
    const auto children = assistantContextField(f, "mainContent", "children");
    const auto first = panelUsageIndex(f, children, 0);
    assistantMemberWrite(f, first, "currentIndex", index);
}
void ApplicationInfo::placeWorkflowSidebar() const {
    const auto f = panelUsageEngine(this);
    const auto main = assistantContextField(f, "mainContent", "parent");
    const auto side = assistantContextField(f, "sideBar", "parent");
    if (!panelUsageTruth(main) || !panelUsageTruth(side)) return;
    const auto left = assistantContextField(f, "Preferences", "sideBarOnLeft");
    viewAnchor(f, side, "left", {}); viewAnchor(f, side, "right", {});
    viewAnchor(f, main, "left", {}); viewAnchor(f, main, "right", {});
    if (panelUsageTruth(left)) {
        viewAnchor(f, side, "left", assistantContextField(f, "page", "left"));
        viewAnchor(f, main, "left", panelUsageRead(f, side, "right"));
        viewAnchor(f, main, "right", assistantContextField(f, "page", "right"));
    } else {
        viewAnchor(f, side, "right", assistantContextField(f, "page", "right"));
        viewAnchor(f, main, "left", assistantContextField(f, "page", "left"));
        viewAnchor(f, main, "right", panelUsageRead(f, side, "left"));
    }
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto children = panelUsageRead(f, side, "children");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, children, "length"), 0)) return;
        const auto actual = panelUsageRead(f, side, "children");
        const auto border = panelUsageIndex(f, actual, static_cast<quint32>(index));
        if (assistantSameName(f, border, "sideBar")) continue;
        const auto width = panelUsageRead(f, border, "width");
        const auto sizes = assistantContextField(f, "EaStyle", "Sizes");
        if (!consentFieldEquals(f, sizes, "borderThickness", width)) continue;
        viewAnchor(f, border, "left", {}); viewAnchor(f, border, "right", {});
        viewAnchor(f, border, panelUsageTruth(left) ? "right" : "left", panelUsageRead(f, side, panelUsageTruth(left) ? "right" : "left"));
    }
}
void ApplicationInfo::workflowCompleted(const QJSValue& installShadow, const QJSValue& installContinueMargin) const {
    const auto f = panelUsageEngine(this);
    const auto side = assistantContextField(f, "sideBar", "parent");
    auto name = panelUsageAdd(f, QJSValue(QStringLiteral("workflow.")), assistantContextField(f, "page", "pageName"));
    assistantMemberWrite(f, side, "objectName", panelUsageAdd(f, name, QJSValue(QStringLiteral(".sidebarHost"))));
    const auto main = assistantContextField(f, "mainContent", "parent");
    name = panelUsageAdd(f, QJSValue(QStringLiteral("workflow.")), assistantContextField(f, "page", "pageName"));
    assistantMemberWrite(f, main, "objectName", panelUsageAdd(f, name, QJSValue(QStringLiteral(".mainContent"))));
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto children = assistantContextField(f, "sideBar", "children");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, children, "length"), 0)) break;
        const auto actual = assistantContextField(f, "sideBar", "children");
        const auto child = panelUsageIndex(f, actual, static_cast<quint32>(index));
        if (panelUsageTruth(panelUsageRead(f, child, "gradient"))) projectCall(f, installShadow, {child});
    }
    projectInvoke(f, "page", "placeSideBar");
    projectCall(f, installContinueMargin);
}
void ApplicationInfo::workflowCurrentChanged() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageContextRead(f, "current"))) {
        const auto page = panelUsageContextRead(f, "page");
        const auto globals = assistantContextField(f, "EaGlobals", "Vars");
        assistantMemberWrite(f, page, "pageIndex", panelUsageRead(f, globals, "appBarCurrentIndex"));
    }
}
void ApplicationInfo::workflowDirtyChanged() const {
    const auto f = panelUsageEngine(this);
    const auto page = panelUsageContextRead(f, "page");
    const auto item = assistantContextField(f, "textLoader", "item");
    assistantMemberWrite(f, page, "textDirty", panelUsageRead(f, item, "dirty"));
}
void ApplicationInfo::workflowStayRequested() const {
    const auto f = panelUsageEngine(this);
    if (assistantRelation(f, assistantContextField(f, "page", "pageIndex"), QJSValue(0), 2)) {
        const auto globals = assistantContextField(f, "EaGlobals", "Vars");
        assistantMemberWrite(f, globals, "appBarCurrentIndex", assistantContextField(f, "page", "pageIndex"));
    }
    const auto tab = assistantContextField(f, "textTabButton", "TabBar");
    const auto bar = panelUsageRead(f, tab, "tabBar");
    const auto current = assistantContextField(f, "textTabButton", "TabBar");
    assistantMemberWrite(f, bar, "currentIndex", panelUsageRead(f, current, "index"));
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
