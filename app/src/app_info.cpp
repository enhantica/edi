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
#include <array>
#include <cmath>
#include <functional>
#include <initializer_list>
#include <iterator>
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
#include <private/qv4arrayobject_p.h>
#include <private/qmetaobject_p.h>
#include <private/qqmlengine_p.h>
#include <private/qqmljavascriptexpression_p.h>
#include <private/qv4functionobject_p.h>
#include <private/qv4jscall_p.h>
#include <private/qv4lookup_p.h>
#include <private/qv4mm_p.h>
#include <private/qv4regexpobject_p.h>
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
    Member(class, Pointer, ArrayObject*, captures) \
    Member(class, NoMark, bool, strict) \
    Member(class, NoMark, uint, operation)
DECLARE_HEAP_OBJECT(AssistantPanelCallback, FunctionObject) {
    DECLARE_MARKOBJECTS(AssistantPanelCallback)
    QV4QPointer<QObject> panel;
    void init(QV4::ExecutionEngine* engine, QV4::QmlContext* captured, uint kind, QObject* owner, QV4::ArrayObject* values = nullptr) {
        FunctionObject::init(engine, QString());
        context.set(engine, captured ? captured->d() : nullptr);
        captures.set(engine, values ? values->d() : nullptr);
        panel.init(owner);
        strict = engine->currentStackFrame && engine->currentStackFrame->v4Function && engine->currentStackFrame->v4Function->isStrict();
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
    bool strict = false;
    explicit PanelUsageFrame(QJSEngine* engine = nullptr,
                             QQmlRefPointer<QQmlContextData> captured = {}, QV4::Heap::QmlContext* scope = nullptr)
        : pointer(engine), context(std::move(captured)), qmlScope(scope) {
        if (pointer) {
            auto* vm = QJSEnginePrivate::get(pointer.data())->v4Engine.get();
            if (!context) context = vm->callingQmlContext();
            if (!qmlScope) qmlScope = vm->qmlContext();
            interrupted = vm->isInterrupted.loadRelaxed();
            strict = vm->currentStackFrame && vm->currentStackFrame->v4Function && vm->currentStackFrame->v4Function->isStrict();
        }
    }
    QJSEngine* data() const { return pointer.data(); }
    QJSEngine* operator->() const { return pointer.data(); }
    operator const QPointer<QJSEngine>&() const { return pointer; }
    explicit operator bool() const { return !pointer.isNull(); }
    QV4::ExecutionEngine* vm() const { return pointer ? QJSEnginePrivate::get(pointer.data())->v4Engine.get() : nullptr; }
    void checked() const { if (pointer && vm()->isInterrupted.loadRelaxed()) interrupted = true; }
};
QJSValue lifecycleCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue presentationCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue formsProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue recentRowCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue scanProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue singleProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue evolutionProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue patternProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue sceneProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue reportProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&, const std::function<void(uint, const QJSValue&)>&);
QJSValue numberProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue controlProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue tableProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue assistantUiCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
QJSValue remainingProcedureCallback(const PanelUsageFrame&, uint, const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>&);
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
    name->toPropertyKey(); // Private QObject lookup requires an existing identifier key.
    if (value.isNullOrUndefined())
        return vm->throwTypeError(QStringLiteral("Cannot read property '%1' of %2")
            .arg(name->toQString(), value.toQStringNoThrow()));
    if (const auto* object = value.as<QV4::Object>()) {
        if (const auto* wrapper = object->as<QV4::QObjectWrapper>()) {
            const auto flags = QV4::QObjectWrapper::Flags(QV4::QObjectWrapper::IncludeImports
                | (forCall ? QV4::QObjectWrapper::NoFlag : QV4::QObjectWrapper::AttachMethods));
            return wrapper->getQmlProperty(frame.context, name, flags, nullptr);
        }
        return object->get(name, nullptr, &value);
    }
    if (value.isString() && name->toQString() == QStringLiteral("length"))
        return QV4::Encode(int(value.toQStringNoThrow().size()));
    QV4::ScopedObject prototype(scope);
    if (value.isBoolean()) prototype = vm->booleanPrototype();
    else if (value.isNumber()) prototype = vm->numberPrototype();
    else prototype = static_cast<const QV4::Managed&>(value).internalClass()->prototype;
    if (value.isString() && name->toPropertyKey().isArrayIndex()) {
        QV4::ScopedObject boxed(scope, value.toObject(vm));
        return boxed ? boxed->get(name, nullptr, &value) : QV4::Encode::undefined();
    }
    return prototype ? prototype->get(name, nullptr, &value) : QV4::Encode::undefined();
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
// Keep context-list wrappers live: each access reads the current property at its original index.
qsizetype panelUsageContextListCount(QQmlListProperty<QObject>* property) {
    auto* context = static_cast<QQmlContext*>(property->object);
    const auto value = QQmlContextPrivate::get(context)->propertyValue(static_cast<int>(quintptr(property->data)));
    return value.userType() == qMetaTypeId<QList<QObject*>>()
        ? static_cast<const QList<QObject*>*>(value.constData())->size() : 0;
}
QObject* panelUsageContextListAt(QQmlListProperty<QObject>* property, qsizetype index) {
    auto* context = static_cast<QQmlContext*>(property->object);
    const auto value = QQmlContextPrivate::get(context)->propertyValue(static_cast<int>(quintptr(property->data)));
    return value.userType() == qMetaTypeId<QList<QObject*>>()
        ? static_cast<const QList<QObject*>*>(value.constData())->at(index) : nullptr;
}
QV4::ReturnedValue panelUsageResolveContext(const PanelUsageFrame& frame, QV4::String* name,
                                           QV4::Value* base, bool forCall = false) {
    auto* vm = frame.vm();
    QV4::Scope scope(vm);
    name->toPropertyKey(); // Private QObject lookup requires an existing identifier key.
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
        QV4::ScopedValue value(scope, QV4::Object::staticVTable()->get(resource, name->toPropertyKey(), nullptr, &hasProperty));
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
                panelUsageContextListCount, panelUsageContextListAt);
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
        QV4::ScopedValue value(scope, QV4::Object::staticVTable()->get(resource, name->toPropertyKey(), nullptr, &hasProperty));
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
QJSValue panelUsageClosure(const PanelUsageFrame& frame, uint operation, const QJSValueList& values, int arity = 0) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::JSCallArguments retained(scope, static_cast<int>(values.size()));
    for (qsizetype i = 0; i < values.size(); ++i)
        retained.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), values[i]);
    QV4::ScopedArrayObject captures(scope, frame.vm()->newArrayObject(retained.args, static_cast<int>(values.size())));
    QV4::Scoped<QV4::QmlContext> context(scope, frame.qmlScope);
    QV4::Scoped<QV4::AssistantPanelCallback> callback(scope,
        frame.vm()->memoryManager->allocate<QV4::AssistantPanelCallback>(frame.vm(), context.getPointer(), operation, nullptr, captures.getPointer()));
    callback->defineReadonlyConfigurableProperty(frame.vm()->id_length(), QV4::Value::fromInt32(arity));
    return QJSValuePrivate::fromReturnedValue(callback->asReturnedValue());
}
void panelUsageCallLater(const PanelUsageFrame& frame, const QJSValue& callback) {
    const auto qt = panelUsageContextRead(frame, "Qt");
    panelUsageMemberCall(frame, qt, "callLater", {callback});
}

QJSValue panelUsageGlobalCall(const PanelUsageFrame& frame, const char* name, const QJSValueList& arguments = {}) {
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

QJSValue panelUsageDeferredMemberCall(const PanelUsageFrame& frame, const QJSValue& receiver,
    const char* name, const std::function<QJSValueList()>& arguments) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(frame.vm(), receiver));
    QV4::ScopedString key(scope, frame.vm()->newString(QString::fromLatin1(name)));
    const auto values = arguments();
    if (!panelUsageReady(frame)) return {};
    QV4::JSCallArguments call(scope, static_cast<int>(values.size()));
    *call.thisObject = *object;
    for (qsizetype i = 0; i < values.size(); ++i) call.args[i] = QJSValuePrivate::convertToReturnedValue(frame.vm(), values[i]);
    QV4::ScopedValue callable(scope, panelUsageGet(frame, *object, key, true));
    frame.checked();
    if (!panelUsageReady(frame)) return {};
    QV4::ScopedValue result(scope);
    if (const auto* function = callable->as<QV4::FunctionObject>()) result = function->call(call);
    else if (const auto* handler = callable->as<QV4::QmlSignalHandler>()) result = handler->call(call.thisObject, call.args, static_cast<int>(values.size()));
    else result = frame.vm()->throwTypeError(QStringLiteral("Property '%1' of object %2 is not a function")
        .arg(key->toQString(), call.thisObject->toQStringNoThrow()));
    frame.checked(); return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
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
    return panelUsageDeferredMemberCall(engine, text, "arg", [&] { return QJSValueList{argument()}; });
}
QJSValue panelUsageMath(const PanelUsageFrame& engine, const char* operation,
                       const std::function<QJSValue()>& argument) {
    if (!panelUsageReady(engine)) return {};
    const auto math = panelUsageContextRead(engine, "Math");
    return panelUsageDeferredMemberCall(engine, math, operation, [&] { return QJSValueList{argument()}; });
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
QJSValue projectGuardedClosure(const PanelUsageFrame& frame, uint operation, int arity = 0) {
    if (!panelUsageReady(frame)) return {};
    QV4::Scope scope(frame.vm());
    QV4::Scoped<QV4::QmlContext> context(scope, frame.qmlScope);
    QV4::Scoped<QV4::ApplicationProjectCallback> callback(scope,
        frame.vm()->memoryManager->allocate<QV4::ApplicationProjectCallback>(frame.vm(), context.getPointer(), operation));
    callback->defineReadonlyConfigurableProperty(frame.vm()->id_length(), QV4::Value::fromInt32(arity));
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
    const Value*, const Value* arguments, int count) {
    const auto* callback = static_cast<const ApplicationProjectCallback*>(function);
    QV4::Scope scope(function->engine());
    QV4::Scoped<QV4::QmlContext> context(scope, callback->d()->context);
    const PanelUsageFrame frame(function->engine()->jsEngine(),
        context ? context->qmlContext() : QQmlRefPointer<QQmlContextData>(), context ? context->d() : nullptr);
    if (!panelUsageReady(frame)) return QV4::Encode::undefined();
    const auto argument = [&](uint index) {
        return index < static_cast<uint>(count) ? QJSValuePrivate::fromReturnedValue(arguments[index].asReturnedValue()) : QJSValue();
    };
    const auto result = callback->d()->operation >= 380
        ? lifecycleCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 360
        ? presentationCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 340
        ? formsProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 320
        ? recentRowCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 300
        ? scanProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 280
        ? singleProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 260
        ? evolutionProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 240
        ? patternProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 220
        ? sceneProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 200
        ? reportProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument, [](uint, const QJSValue&) {})
        : callback->d()->operation >= 180
        ? numberProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 160
        ? controlProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 120
        ? tableProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 80
        ? assistantUiCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
        : callback->d()->operation >= 60
            ? remainingProcedureCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); }, argument)
            : projectCallback(frame, callback->d()->operation, [](uint) { return QJSValue(); });
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
    PanelUsageFrame frame(function->engine()->jsEngine(), context ? context->qmlContext() : QQmlRefPointer<QQmlContextData>(), context ? context->d() : nullptr);
    frame.strict = callback->d()->strict;
    if (!panelUsageReady(frame)) return QV4::Encode::undefined();
    const QJSValue value = count ? QJSValuePrivate::fromReturnedValue(arguments[0].asReturnedValue()) : QJSValue();
    QJSValue result;
    if (callback->d()->operation >= 60) {
        QV4::ScopedArrayObject captures(scope, callback->d()->captures);
        const auto retained = [&](uint index) { return QJSValuePrivate::fromReturnedValue(captures->arrayData()->get(index)); };
        const auto argument = [&](uint index) {
            return index < static_cast<uint>(count) ? QJSValuePrivate::fromReturnedValue(arguments[index].asReturnedValue()) : QJSValue();
        };
        const auto updateCapture = [&](uint index, const QJSValue& value) {
            if (panelUsageReady(frame)) captures->arrayData()->setArrayData(frame.vm(), index, QV4::Value::fromReturnedValue(QJSValuePrivate::convertToReturnedValue(frame.vm(), value)));
        };
        result = callback->d()->operation >= 380 ? lifecycleCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 360 ? presentationCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 340 ? formsProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 320 ? recentRowCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 300 ? scanProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 280 ? singleProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 260 ? evolutionProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 240 ? patternProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 220 ? sceneProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 200 ? reportProcedureCallback(frame, callback->d()->operation, retained, argument, updateCapture)
            : callback->d()->operation >= 180 ? numberProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 160 ? controlProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 120 ? tableProcedureCallback(frame, callback->d()->operation, retained, argument)
            : callback->d()->operation >= 80 ? assistantUiCallback(frame, callback->d()->operation, retained, argument)
            : remainingProcedureCallback(frame, callback->d()->operation, retained, argument);
    } else if (callback->d()->operation >= 40) {
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
        QV4::ScopedArrayObject captures(scope, callback->d()->captures);
        const auto captured = [&](uint index) {
            return QJSValuePrivate::fromReturnedValue(captures->arrayData()->get(index));
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
        const auto edited = projectInvoke(f, "categoryData", "editedText", {QJSValue(row), QJSValue(name), QJSValue(value)});
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

namespace {
QJSValue textIndex(const PanelUsageFrame& f, const QJSValue& source, const QJSValue& key) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm());
    QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), source));
    QV4::ScopedValue index(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), key));
    QV4::ScopedValue value(scope, QV4::Runtime::LoadElement::call(f.vm(), *object, *index));
    f.checked();
    return QJSValuePrivate::fromReturnedValue(value->asReturnedValue());
}
void textIndexWrite(const PanelUsageFrame& f, const QJSValue& source, const QJSValue& key, const QJSValue& value) {
    if (!panelUsageReady(f)) return;
    QV4::Scope scope(f.vm());
    QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), source));
    QV4::ScopedValue index(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), key));
    QV4::ScopedValue actual(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), value));
    QV4::Runtime::StoreElement::call(f.vm(), *object, *index, *actual);
    f.checked();
}
QJSValue textIndexDelete(const PanelUsageFrame& f, const QJSValue& source, const QJSValue& key) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm());
    QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), source));
    QV4::ScopedValue index(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), key));
    const bool removed = bool(QV4::Runtime::DeleteProperty_NoThrow::call(f.vm(), *object, *index));
    if (!removed && f.strict) f.vm()->throwTypeError();
    f.checked();
    return QJSValue(removed);
}
QJSValue remainingProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& captured, const std::function<QJSValue(uint)>& arg) {
    if (operation == 60) {
        if (!panelUsageTruth(captured(2))) return QJSValue(QString{});
        const auto tab = panelUsageContextRead(f, "tab");
        return panelUsageMemberCall(f, tab, "applyTo", {captured(2), captured(3)});
    }
    if (operation == 61) {
        const auto kept = assistantContextField(f, "tab", "keptEdits");
        return textIndexDelete(f, kept, captured(0));
    }
    if (operation == 62) {
        const auto refusal = arg(0);
        if (panelUsageTruth(refusal)) {
            const auto kept = assistantContextField(f, "tab", "keptRefusals");
            textIndexWrite(f, kept, captured(0), refusal);
        }
        return projectInvoke(f, "tab", "blockRequested", {captured(1)});
    }
    if (operation == 63) {
        const auto tab = panelUsageContextRead(f, "tab");
        const auto source = assistantContextField(f, "tab", "source");
        const auto text = assistantContextField(f, "textEdit", "text");
        return panelUsageMemberCall(f, tab, "applyTo", {source, text});
    }
    if (operation == 64) return projectInvoke(f, "tab", "showBlock");
    if (operation == 65) {
        const auto refusal = arg(0);
        projectWrite(f, "tab", "refusal", refusal.isNull() || refusal.isUndefined() ? QJSValue(QString{}) : refusal);
        return projectInvoke(f, "tab", "stayRequested");
    }
    if (operation == 66) {
        projectWrite(f, "tab", "edited", QJSValue(false));
        projectWrite(f, "Preferences", "textShow", captured(0));
        return projectInvoke(f, "tab", "showBlock");
    }
    const auto refusal = arg(0);
    projectWrite(f, "tab", "refusal", refusal.isNull() || refusal.isUndefined() ? QJSValue(QString{}) : refusal);
    return projectCall(f, captured(0));
}
} // namespace

void ApplicationInfo::textTabShowBlock() const {
    const auto f = panelUsageEngine(this);
    auto tab = panelUsageContextRead(f, "tab");
    assistantMemberWrite(f, tab, "shownSource", assistantContextField(f, "tab", "source"));
    tab = panelUsageContextRead(f, "tab");
    const auto source = assistantContextField(f, "tab", "source");
    const auto file = panelUsageTruth(source) ? assistantContextField(f, "tab", "source") : QJSValue();
    assistantMemberWrite(f, tab, "shownFile", panelUsageTruth(source) ? panelUsageRead(f, file, "file") : QJSValue(QString{}));
    tab = panelUsageContextRead(f, "tab");
    assistantMemberWrite(f, tab, "shownBlockIndex", assistantContextField(f, "tab", "blockIndex"));
    tab = panelUsageContextRead(f, "tab");
    const auto refusals = assistantContextField(f, "tab", "keptRefusals");
    auto shown = assistantContextField(f, "tab", "shownFile");
    const auto refusal = textIndex(f, refusals, shown);
    assistantMemberWrite(f, tab, "refusal", refusal.isNull() || refusal.isUndefined() ? QJSValue(QString{}) : refusal);
    const auto previousRefusals = assistantContextField(f, "tab", "keptRefusals");
    shown = assistantContextField(f, "tab", "shownFile");
    textIndexDelete(f, previousRefusals, shown);
    const auto edits = assistantContextField(f, "tab", "keptEdits");
    shown = assistantContextField(f, "tab", "shownFile");
    const auto kept = textIndex(f, edits, shown);
    const auto previousEdits = assistantContextField(f, "tab", "keptEdits");
    shown = assistantContextField(f, "tab", "shownFile");
    textIndexDelete(f, previousEdits, shown);
    projectWrite(f, "tab", "showing", QJSValue(true));
    const auto editor = panelUsageContextRead(f, "textEdit");
    assistantMemberWrite(f, editor, "text", !kept.isUndefined() ? kept : assistantContextField(f, "tab", "shownText"));
    projectWrite(f, "tab", "showing", QJSValue(false));
    projectWrite(f, "tab", "edited", QJSValue(!kept.isUndefined()));
}
QJSValue ApplicationInfo::textTabApplyTo(const QJSValue& source, const QString& text) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "Session", "project"))) {
        const auto project = assistantContextField(f, "Session", "project");
        const auto file = panelUsageRead(f, source, "file");
        const auto full = panelUsageMemberCall(f, source, "withOutputs", {QJSValue(text)});
        return panelUsageMemberCall(f, project, "applyText", {file, full});
    }
    if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
    return QJSValue(QCoreApplication::translate("TextTab", "No project"));
}
void ApplicationInfo::textTabApplyEdit() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "tab", "dirty")) || !panelUsageTruth(assistantContextField(f, "tab", "editable"))) return;
    const auto tab = panelUsageContextRead(f, "tab");
    const auto source = assistantContextField(f, "tab", "source");
    const auto text = assistantContextField(f, "textEdit", "text");
    const auto refusal = panelUsageMemberCall(f, tab, "applyTo", {source, text});
    projectWrite(f, "tab", "refusal", refusal);
    if (refusal.strictlyEquals(QJSValue(QString{}))) projectInvoke(f, "tab", "showBlock");
}
void ApplicationInfo::textTabAskLeave(const QJSValue& apply, const QJSValue& leave, const QJSValue& drop, const QJSValue& stay) const {
    const auto f = panelUsageEngine(this);
    const auto dialog = panelUsageContextRead(f, "discardDialog");
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "apply", apply); panelUsageWrite(f, literal.value, "leave", leave);
    panelUsageWrite(f, literal.value, "drop", drop); panelUsageWrite(f, literal.value, "stay", stay);
    assistantMemberWrite(f, dialog, "actions", panelUsageComplete(f, literal));
    projectInvoke(f, "discardDialog", "open");
}
void ApplicationInfo::textTabSourceChanged() const {
    const auto f = panelUsageEngine(this);
    bool leaving = panelUsageTruth(assistantContextField(f, "tab", "edited"));
    if (leaving) leaving = !assistantContextField(f, "tab", "shownFile").strictlyEquals(QJSValue(QString{}));
    if (leaving) {
        leaving = assistantContextField(f, "tab", "source").isNull();
        if (!leaving) {
            const auto source = assistantContextField(f, "tab", "source");
            const auto file = panelUsageRead(f, source, "file");
            leaving = !projectFieldIs(f, "tab", "shownFile", file);
        }
    }
    if (leaving) {
        const auto file = assistantContextField(f, "tab", "shownFile");
        const auto index = assistantContextField(f, "tab", "shownBlockIndex");
        const auto left = assistantContextField(f, "tab", "shownSource");
        const auto kept = assistantContextField(f, "textEdit", "text");
        const auto edits = assistantContextField(f, "tab", "keptEdits");
        textIndexWrite(f, edits, file, kept);
        const auto tab = panelUsageContextRead(f, "tab");
        const QJSValueList captures{file, index, left, kept};
        const auto apply = panelUsageClosure(f, 60, captures);
        const auto leave = panelUsageClosure(f, 61, captures);
        const auto drop = panelUsageClosure(f, 61, captures);
        const auto stay = panelUsageClosure(f, 62, captures, 1);
        panelUsageMemberCall(f, tab, "askLeave", {apply, leave, drop, stay});
    }
    projectInvoke(f, "tab", "showBlock");
}
void ApplicationInfo::textTabChanged(int cause) const {
    const auto f = panelUsageEngine(this);
    if (cause == 0) {
        if (!panelUsageTruth(assistantContextField(f, "tab", "dirty"))) projectInvoke(f, "tab", "showBlock");
    } else if (cause == 1) {
        if (!panelUsageTruth(assistantContextField(f, "tab", "edited"))) projectWrite(f, "tab", "shownBlockIndex", assistantContextField(f, "tab", "blockIndex"));
    } else if (cause == 2) {
        if (!panelUsageTruth(assistantContextField(f, "tab", "shown")) && panelUsageTruth(assistantContextField(f, "tab", "dirty"))) {
            const auto tab = panelUsageContextRead(f, "tab");
            const auto apply = projectGuardedClosure(f, 63);
            const auto leave = projectGuardedClosure(f, 64);
            const auto drop = projectGuardedClosure(f, 64);
            const auto stay = projectGuardedClosure(f, 65, 1);
            panelUsageMemberCall(f, tab, "askLeave", {apply, leave, drop, stay});
        }
    } else if (!panelUsageTruth(assistantContextField(f, "tab", "showing")) && !panelUsageTruth(panelUsageContextRead(f, "readOnly"))) projectWrite(f, "tab", "edited", QJSValue(true));
}
void ApplicationInfo::textTabShowChoice(const QJSValue& index, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this);
    const auto choices = panelUsageContextRead(f, "choices");
    const auto choice = textIndex(f, choices, index);
    if (!panelUsageTruth(assistantContextField(f, "tab", "dirty"))) { projectWrite(f, "Preferences", "textShow", choice); return; }
    const auto shown = panelUsageClosure(f, 66, {choice});
    const auto tab = panelUsageContextRead(f, "tab");
    const auto apply = panelUsageClosure(f, 63, {});
    const auto stay = panelUsageClosure(f, 67, {restoreBinding}, 1);
    panelUsageMemberCall(f, tab, "askLeave", {apply, shown, shown, stay});
}
void ApplicationInfo::textTabAnswer(const QString& name, const QJSValue& argument) const {
    const auto f = panelUsageEngine(this);
    const auto actions = assistantContextField(f, "discardDialog", "actions");
    const auto action = textIndex(f, actions, QJSValue(name));
    if (!panelUsageReady(f)) return;
    projectWrite(f, "discardDialog", "actions", f->newObject());
    if (panelUsageTruth(action)) projectCall(f, action, {argument});
}
void ApplicationInfo::textDiscardCompleted() const {
    const auto f = panelUsageEngine(this);
    const auto role = assistantContextField(f, "Dialog", "Discard");
    const auto button = panelUsageGlobalCall(f, "standardButton", {role});
    if (!panelUsageTruth(button)) return;
    if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
    assistantMemberWrite(f, button, "text", QJSValue(QCoreApplication::translate("TextTab", "Don't apply")));
}
void ApplicationInfo::textDiscardApplied() const {
    const auto f = panelUsageEngine(this);
    panelUsageGlobalCall(f, "close", {});
    const auto actions = assistantContextField(f, "discardDialog", "actions");
    const auto apply = textIndex(f, actions, QJSValue(QStringLiteral("apply")));
    const auto refusal = panelUsageTruth(apply) ? projectCall(f, apply) : QJSValue(QString{});
    projectInvoke(f, "discardDialog", "answer", {QJSValue(refusal.strictlyEquals(QJSValue(QString{})) ? QStringLiteral("leave") : QStringLiteral("stay")), refusal});
}
void ApplicationInfo::textDiscardDiscarded() const {
    const auto f = panelUsageEngine(this);
    panelUsageGlobalCall(f, "close", {});
    projectInvoke(f, "discardDialog", "answer", {QJSValue(QStringLiteral("drop"))});
}

namespace {
bool composerScopeOwner(const PanelUsageFrame& f, const QJSValue& owner) {
    const auto composer = panelUsageContextRead(f, "composer");
    return consentQtObject(f, composer) && consentQtObject(f, owner) && assistantSameName(f, owner, "assistant");
}
void composerReportDraft(const PanelUsageFrame& f, const QJSValue& receipt, const QJSValue& owner,
    const QJSValue& text, const QJSValue& revision, const QJSValue& ownerRevision, const QJSValue& binding) {
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "id", panelUsageRead(f, receipt, "id"));
    panelUsageWrite(f, literal.value, "owner", owner); panelUsageWrite(f, literal.value, "text", text);
    panelUsageWrite(f, literal.value, "revision", revision); panelUsageWrite(f, literal.value, "ownerRevision", ownerRevision);
    panelUsageWrite(f, literal.value, "binding", binding);
    panelUsageContextWrite(f, "workReportDraft", panelUsageComplete(f, literal));
}
} // namespace
void ApplicationInfo::composerRememberSelection() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "editor", "activeFocus"))) return;
    panelUsageContextWrite(f, "savedSelectionStart", assistantContextField(f, "editor", "selectionStart"));
    panelUsageContextWrite(f, "savedSelectionEnd", assistantContextField(f, "editor", "selectionEnd"));
    panelUsageContextWrite(f, "selectionRevision", panelUsageContextRead(f, "textRevision"));
}
void ApplicationInfo::composerFocusEditor() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "assistant", "connected"))) return;
    const auto selection = panelUsageContextRead(f, "selectionRevision");
    const auto text = panelUsageContextRead(f, "textRevision");
    const bool restore = selection.strictlyEquals(text);
    const auto start = panelUsageContextRead(f, "savedSelectionStart");
    const auto end = panelUsageContextRead(f, "savedSelectionEnd");
    projectInvoke(f, "editor", "forceActiveFocus");
    if (restore) projectInvoke(f, "editor", "select", {start, end});
}
void ApplicationInfo::composerFinishWorkReport(const QJSValue& receipt) const {
    const auto f = panelUsageEngine(this);
    const auto waiting = panelUsageContextRead(f, "workReportDraft");
    if (!panelUsageTruth(waiting) || !consentFieldsEqual(f, receipt, "id", waiting, "id")
        || !consentFieldEquals(f, receipt, "phase", QJSValue(QStringLiteral("terminal")))) return;
    panelUsageContextWrite(f, "workReportDraft", consentNull());
    bool saved = consentFieldEquals(f, receipt, "disposition", QJSValue(QStringLiteral("saved")));
    if (!saved) saved = consentFieldEquals(f, receipt, "disposition", QJSValue(QStringLiteral("saved_incomplete")));
    if (!saved || panelUsageTruth(panelUsageRead(f, receipt, "scope_retired"))) return;
    const auto owner = panelUsageContextRead(f, "assistant");
    if (!consentFieldEquals(f, waiting, "owner", owner)) return;
    const auto binding = panelUsageContextRead(f, "workReportBinding");
    if (!consentFieldEquals(f, waiting, "binding", binding)) return;
    const auto ownerRevision = panelUsageContextRead(f, "draftOwnerRevision");
    if (!consentFieldEquals(f, waiting, "ownerRevision", ownerRevision)) return;
    const auto revision = panelUsageContextRead(f, "textRevision");
    if (!consentFieldEquals(f, waiting, "revision", revision)) return;
    const auto text = assistantContextField(f, "editor", "text");
    if (!consentFieldEquals(f, waiting, "text", text) || !assistantEditorIdle(f)) return;
    projectInvoke(f, "editor", "clear");
}
void ApplicationInfo::composerSubmitWorkReport() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "localWorkReport")) || panelUsageTruth(assistantContextField(f, "editor", "inputMethodComposing"))) return;
    const auto preedit = assistantContextField(f, "editor", "preeditText");
    if (panelUsageTruth(panelUsageRead(f, preedit, "length"))) return;
    const auto owner = panelUsageContextRead(f, "assistant");
    const auto text = assistantContextField(f, "editor", "text");
    const auto revision = panelUsageContextRead(f, "textRevision");
    const auto ownerRevision = panelUsageContextRead(f, "draftOwnerRevision");
    const auto binding = panelUsageContextRead(f, "workReportBinding");
    const auto receipt = panelUsageMemberCall(f, owner, "captureWorkReport");
    if (!composerScopeOwner(f, owner) || !assistantSameName(f, ownerRevision, "draftOwnerRevision")
        || !assistantSameName(f, binding, "workReportBinding")) return;
    if (panelUsageTruth(panelUsageRead(f, receipt, "id")) && consentFieldEquals(f, receipt, "phase", QJSValue(QStringLiteral("accepted"))))
        composerReportDraft(f, receipt, owner, text, revision, ownerRevision, binding);
    else if (panelUsageTruth(panelUsageRead(f, receipt, "id"))) {
        composerReportDraft(f, receipt, owner, text, revision, ownerRevision, binding);
        panelUsageGlobalCall(f, "finishWorkReport", {receipt});
    }
}
void ApplicationInfo::composerChooseFiles() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available")) || !panelUsageTruth(assistantContextField(f, "assistant", "connected"))
        || panelUsageTruth(assistantContextField(f, "assistant", "canCancel"))) return;
    const auto active = assistantContextField(f, "nativeFiles", "requestId");
    if (panelUsageTruth(panelUsageRead(f, active, "length"))) return;
    const auto original = panelUsageContextRead(f, "assistant");
    const auto request = panelUsageMemberCall(f, original, "beginFileSelection", {QJSValue(true)});
    const auto composer = panelUsageContextRead(f, "composer");
    bool current = consentOwner(f, composer, original);
    if (current) current = panelUsageTruth(panelUsageRead(f, original, "connected"));
    if (current) current = panelUsageTruth(panelUsageRead(f, request, "length"));
    if (!current) {
        if (consentQtObject(f, original)) panelUsageMemberCall(f, original, "cancelFileSelection", {request});
        return;
    }
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "owner", original); panelUsageWrite(f, literal.value, "id", request);
    const auto intent = panelUsageComplete(f, literal);
    projectWrite(f, "nativeFiles", "selection", intent);
    auto files = panelUsageContextRead(f, "nativeFiles");
    if (consentQtObject(f, files) && projectFieldIs(f, "nativeFiles", "selection", intent)) projectInvoke(f, "nativeFiles", "open");
    else if (consentQtObject(f, original)) panelUsageMemberCall(f, original, "cancelFileSelection", {request});
}
void ApplicationInfo::composerAcceptFiles() const {
    const auto f = panelUsageEngine(this);
    const auto target = panelUsageContextRead(f, "original");
    const auto request = panelUsageContextRead(f, "requestId");
    const auto files = panelUsageContextRead(f, "selectedFiles");
    panelUsageContextWrite(f, "selection", consentNull());
    if (!consentQtObject(f, target)) return;
    const auto composer = panelUsageContextRead(f, "composer");
    if (consentQtObject(f, composer) && consentFieldEquals(f, composer, "assistant", target) && panelUsageTruth(panelUsageRead(f, target, "connected")))
        panelUsageMemberCall(f, target, "addSelectedFiles", {request, files});
    else panelUsageMemberCall(f, target, "cancelFileSelection", {request});
}
void ApplicationInfo::composerCancelFiles() const {
    const auto f = panelUsageEngine(this);
    const auto target = panelUsageContextRead(f, "original");
    const auto request = panelUsageContextRead(f, "requestId");
    panelUsageContextWrite(f, "selection", consentNull());
    if (consentQtObject(f, target)) panelUsageMemberCall(f, target, "cancelFileSelection", {request});
}
void ApplicationInfo::composerFileSelectionRetired(const QJSValue& request) const {
    const auto f = panelUsageEngine(this);
    if (!projectFieldIs(f, "nativeFiles", "requestId", request)) return;
    projectWrite(f, "nativeFiles", "selection", consentNull());
    const auto files = panelUsageContextRead(f, "nativeFiles");
    if (consentQtObject(f, files) && assistantContextField(f, "nativeFiles", "selection").isNull()) projectInvoke(f, "nativeFiles", "reject");
}
void ApplicationInfo::composerOwnerChanged() const {
    const auto f = panelUsageEngine(this);
    panelUsageGlobalCall(f, "closeChoices", {});
    if (panelUsageReady(f)) panelUsageContextWrite(f, "workReportBinding", f->newObject());
    panelUsageContextWrite(f, "workReportDraft", consentNull());
}
void ApplicationInfo::composerChoicesEnabledChanged() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "choicesEnabled"))) panelUsageGlobalCall(f, "closeChoices", {});
}
bool ApplicationInfo::composerLocalWorkReport() const {
    const auto f = panelUsageEngine(this);
    const auto text = assistantContextField(f, "editor", "text");
    const auto trimmed = panelUsageMemberCall(f, text, "trim");
    return panelUsageReady(f) && trimmed.strictlyEquals(QJSValue(QStringLiteral("/work-report")));
}
bool ApplicationInfo::composerHasDraft() const {
    const auto f = panelUsageEngine(this);
    const auto text = assistantContextField(f, "editor", "text");
    const auto trimmed = panelUsageMemberCall(f, text, "trim");
    if (assistantRelation(f, panelUsageRead(f, trimmed, "length"), QJSValue(0), 1)) return true;
    return assistantRelation(f, panelUsageContextRead(f, "pendingFileCount"), QJSValue(0), 1);
}

namespace {
QJSValue assistantUiCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& retained, const std::function<QJSValue(uint)>& arg);
QJSValue choiceText(const PanelUsageFrame& f, const char* text) {
    if (!panelUsageReady(f)) return {};
    if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
    return QJSValue(QCoreApplication::translate("AssistantComposer", text));
}
QJSValue choiceOwner(const PanelUsageFrame& f, const QJSValue& intent) { return panelUsageRead(f, intent, "owner"); }
bool choiceStillCurrent(const PanelUsageFrame& f, const QJSValue& intent) {
    const auto popup = panelUsageContextRead(f, "choicePopup");
    return consentQtObject(f, popup) && panelUsageTruth(projectInvoke(f, "choicePopup", "current", {intent}));
}
QJSValue choiceScrollCoordinate(const PanelUsageFrame& f, const QJSValue& point, const QJSValue& flick,
                               const QJSValue& row, bool vertical) {
    const char* axis = vertical ? "y" : "x";
    const char* content = vertical ? "contentY" : "contentX";
    const char* extent = vertical ? "height" : "width";
    const auto position = panelUsageRead(f, point, axis);
    const auto start = panelUsageRead(f, flick, content);
    if (assistantRelation(f, position, start, 0)) return panelUsageRead(f, point, axis);
    const auto math = panelUsageContextRead(f, "Math");
    const auto current = panelUsageRead(f, flick, content);
    const auto pointAgain = panelUsageRead(f, point, axis);
    const auto selector = panelUsageRead(f, row, "selector");
    const auto size = panelUsageRead(f, selector, extent);
    const auto end = panelUsageAdd(f, pointAgain, size);
    const auto viewport = panelUsageRead(f, flick, extent);
    return panelUsageMemberCall(f, math, "max", {current, viewArithmetic(f, end, viewport, 0)});
}
QJSValue choiceClampedScroll(const PanelUsageFrame& f, const QJSValue& position, const QJSValue& flick, bool vertical) {
    const auto math = panelUsageContextRead(f, "Math");
    const auto inner = panelUsageContextRead(f, "Math");
    const auto total = panelUsageRead(f, flick, vertical ? "contentHeight" : "contentWidth");
    const auto viewport = panelUsageRead(f, flick, vertical ? "height" : "width");
    const auto difference = viewArithmetic(f, total, viewport, 0);
    const auto minimum = panelUsageMemberCall(f, inner, "min", {position, difference});
    return panelUsageMemberCall(f, math, "max", {QJSValue(0), minimum});
}
void choiceDeferredFocus(const PanelUsageFrame& f, const QJSValue& table, const QJSValue& index, const QJSValue& original) {
    if (!choiceStillCurrent(f, original) || !consentQtObject(f, table)) return;
    const auto row = panelUsageMemberCall(f, table, "itemAtIndex", {index});
    if (!consentQtObject(f, row)) return;
    auto selector = panelUsageRead(f, row, "selector");
    if (!panelUsageTruth(panelUsageRead(f, selector, "enabled"))) return;
    const auto flick = assistantContextField(f, "choiceScroll", "contentItem");
    if (!consentQtObject(f, flick) || !consentQtObject(f, panelUsageRead(f, flick, "contentItem"))) return;
    selector = panelUsageRead(f, row, "selector");
    const auto content = panelUsageRead(f, flick, "contentItem");
    const auto point = panelUsageMemberCall(f, selector, "mapToItem", {content, QJSValue(0), QJSValue(0)});
    const auto horizontal = choiceScrollCoordinate(f, point, flick, row, false);
    const auto vertical = choiceScrollCoordinate(f, point, flick, row, true);
    assistantMemberWrite(f, flick, "contentX", choiceClampedScroll(f, horizontal, flick, false));
    if (!choiceStillCurrent(f, original) || !consentQtObject(f, row)) return;
    assistantMemberWrite(f, flick, "contentY", choiceClampedScroll(f, vertical, flick, true));
    if (!choiceStillCurrent(f, original) || !consentQtObject(f, row)) return;
    selector = panelUsageRead(f, row, "selector");
    if (!panelUsageTruth(panelUsageRead(f, selector, "enabled"))) return;
    selector = panelUsageRead(f, row, "selector");
    panelUsageMemberCall(f, selector, "forceActiveFocus");
}
} // namespace

QJSValue ApplicationInfo::assistantEffortRank(const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    QJSValueList values;
    for (const char* token : {"none", "low", "medium", "high", "xhigh", "max", "ultra"}) values.append(QJSValue(QString::fromLatin1(token)));
    return panelUsageMemberCall(f, assistantGeometryArray(f, values), "indexOf", {value});
}
QJSValue ApplicationInfo::assistantEffortLabel(const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    const std::pair<const char*, const char*> labels[] = {{"", "Auto"}, {"none", "None"}, {"low", "Low"}, {"medium", "Medium"},
        {"high", "High"}, {"xhigh", "Extra high"}, {"max", "Maximum"}, {"ultra", "Ultra"}};
    for (const auto& [token, label] : labels) if (value.strictlyEquals(QJSValue(QString::fromLatin1(token)))) return choiceText(f, label);
    return value;
}
QJSValue ApplicationInfo::assistantEffortChoices() const {
    const auto f = panelUsageEngine(this);
    const auto initial = assistantGeometryArray(f, {QJSValue(QString{})});
    const auto efforts = assistantContextField(f, "assistant", "availableEfforts");
    const auto copied = panelUsageMemberCall(f, efforts, "slice");
    const auto sort = projectGuardedClosure(f, 80, 2);
    const auto ordered = panelUsageMemberCall(f, copied, "sort", {sort});
    const auto joined = panelUsageMemberCall(f, initial, "concat", {ordered});
    return panelUsageMemberCall(f, joined, "map", {projectGuardedClosure(f, 81, 1)});
}
QJSValue ApplicationInfo::assistantSelectedModelRow() const {
    const auto f = panelUsageEngine(this);
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto models = assistantContextField(f, "assistant", "models");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, models, "count"), 0)) break;
        const auto actual = assistantContextField(f, "assistant", "models");
        const auto id = panelUsageMemberCall(f, actual, "text", {QJSValue(index), QJSValue(QStringLiteral("id"))});
        const auto selected = assistantContextField(f, "assistant", "selectedModel");
        if (id.strictlyEquals(selected)) return QJSValue(index);
    }
    return QJSValue(-1);
}
QJSValue ApplicationInfo::assistantSelectedEffortLabel() const {
    const auto f = panelUsageEngine(this);
    const auto choices = panelUsageContextRead(f, "effortChoices");
    if (!panelUsageTruth(panelUsageMemberCall(f, choices, "some", {projectGuardedClosure(f, 82, 1)}))) return choiceText(f, "Effort");
    const auto effort = assistantContextField(f, "assistant", "selectedEffort");
    return panelUsageGlobalCall(f, "effortLabel", {effort});
}
QJSValue ApplicationInfo::assistantSelectedEffortRow() const {
    const auto f = panelUsageEngine(this);
    const auto choices = assistantContextField(f, "composer", "effortChoices");
    return panelUsageMemberCall(f, choices, "findIndex", {projectGuardedClosure(f, 83, 1)});
}
void ApplicationInfo::assistantCloseChoices() const {
    const auto f = panelUsageEngine(this);
    if (consentQtObject(f, panelUsageContextRead(f, "choicePopup"))) projectInvoke(f, "choicePopup", "close");
}
void ApplicationInfo::assistantOpenChoices() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "choicesEnabled")) || !consentQtObject(f, panelUsageContextRead(f, "choicePopup"))
        || panelUsageTruth(assistantContextField(f, "choicePopup", "visible"))) return;
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "owner", panelUsageContextRead(f, "assistant"));
    const auto original = panelUsageComplete(f, literal);
    projectWrite(f, "choicePopup", "intent", original);
    if (!consentQtObject(f, panelUsageContextRead(f, "choicePopup")) || !projectFieldIs(f, "choicePopup", "intent", original)) return;
    if (!consentQtObject(f, choiceOwner(f, original))) return;
    const auto owner = choiceOwner(f, original);
    if (!projectFieldIs(f, "composer", "assistant", owner) || !panelUsageTruth(assistantContextField(f, "composer", "choicesEnabled"))) return;
    projectInvoke(f, "choicePopup", "open");
}
QJSValue ApplicationInfo::assistantChoiceCurrent(const QJSValue& original) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(original)) return original;
    if (!assistantSameName(f, original, "intent")) return QJSValue(false);
    const auto visible = panelUsageContextRead(f, "visible");
    if (!panelUsageTruth(visible)) return visible;
    if (!consentQtObject(f, panelUsageContextRead(f, "composer")) || !consentQtObject(f, choiceOwner(f, original))) return QJSValue(false);
    const auto owner = choiceOwner(f, original);
    if (!projectFieldIs(f, "composer", "assistant", owner)) return QJSValue(false);
    return assistantContextField(f, "composer", "choicesEnabled");
}
void ApplicationInfo::assistantChoiceFocusRow(const QJSValue& table, const QJSValue& index, const QJSValue& original) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(f, "current", {original})) || assistantRelation(f, index, QJSValue(0), 0)
        || assistantRelation(f, index, panelUsageRead(f, table, "count"), 2)) return;
    const auto contain = assistantContextField(f, "ListView", "Contain");
    panelUsageMemberCall(f, table, "positionViewAtIndex", {index, contain});
    const auto qt = panelUsageContextRead(f, "Qt");
    const auto callback = panelUsageClosure(f, 90, {table, index, original});
    panelUsageMemberCall(f, qt, "callLater", {callback});
}
bool ApplicationInfo::assistantModelAvailable(const QJSValue& model, const QJSValue& index) const {
    const auto f = panelUsageEngine(this);
    const auto value = panelUsageMemberCall(f, model, "text", {index, QJSValue(QStringLiteral("available"))});
    return panelUsageReady(f) && value.strictlyEquals(QJSValue(QStringLiteral("true")));
}
void ApplicationInfo::assistantChoiceReconcile(const QJSValue& group, const QJSValue& original) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(f, "current", {original}))) return;
    QJSValue actual = consentNull();
    panelUsageEach(f, panelUsageRead(f, group, "buttons"), [&](const QJSValue& button) {
        if (consentQtObject(f, button) && panelUsageTruth(panelUsageRead(f, button, "selectionCurrent"))) { actual = button; return false; }
        return panelUsageReady(f);
    });
    assistantMemberWrite(f, group, "checkedButton", actual);
}
void ApplicationInfo::assistantChoiceFocusModel(const QJSValue& start, const QJSValue& step, const QJSValue& original) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageGlobalCall(f, "current", {original}))) return;
    const auto owner = choiceOwner(f, original);
    const auto model = panelUsageRead(f, owner, "models");
    for (QJSValue index = start; panelUsageReady(f) && assistantRelation(f, index, QJSValue(0), 2)
         && assistantRelation(f, index, panelUsageRead(f, model, "count"), 0); index = panelUsageAdd(f, index, step)) {
        if (panelUsageTruth(panelUsageGlobalCall(f, "modelAvailable", {model, index}))) {
            const auto table = panelUsageContextRead(f, "modelTable");
            panelUsageGlobalCall(f, "focusRow", {table, index, original}); return;
        }
    }
    QJSValue destination(0);
    if (!assistantRelation(f, step, QJSValue(0), 1)) {
        const auto choices = assistantContextField(f, "composer", "effortChoices");
        destination = viewArithmetic(f, panelUsageRead(f, choices, "length"), QJSValue(1), 0);
    }
    panelUsageGlobalCall(f, "focusEffort", {destination, original});
}
void ApplicationInfo::assistantChoiceFocusEffort(const QJSValue& index, const QJSValue& original) const {
    const auto f = panelUsageEngine(this);
    const auto table = panelUsageContextRead(f, "effortTable");
    panelUsageGlobalCall(f, "focusRow", {table, index, original});
}
void ApplicationInfo::assistantChooseModel(const QJSValue& id) const {
    const auto f = panelUsageEngine(this);
    const auto original = panelUsageContextRead(f, "intent");
    if (!panelUsageTruth(panelUsageGlobalCall(f, "current", {original}))) return;
    bool offered = false;
    for (double index = 0; panelUsageReady(f); ++index) {
        auto owner = choiceOwner(f, original); auto models = panelUsageRead(f, owner, "models");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, models, "count"), 0)) break;
        owner = choiceOwner(f, original); models = panelUsageRead(f, owner, "models");
        const auto rowId = panelUsageMemberCall(f, models, "text", {QJSValue(index), QJSValue(QStringLiteral("id"))});
        if (!rowId.strictlyEquals(id)) continue;
        owner = choiceOwner(f, original); models = panelUsageRead(f, owner, "models");
        if (panelUsageTruth(panelUsageGlobalCall(f, "modelAvailable", {models, QJSValue(index)}))) { offered = true; break; }
    }
    if (!offered) { panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "modelSelection"), original}); return; }
    assistantMemberWrite(f, choiceOwner(f, original), "selectedModel", id);
    if (!choiceStillCurrent(f, original)) return;
    panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "modelSelection"), original});
    if (!choiceStillCurrent(f, original)) return;
    const auto choices = assistantContextField(f, "composer", "effortChoices");
    const auto selected = panelUsageMemberCall(f, choices, "findIndex", {panelUsageClosure(f, 84, {original}, 1)});
    const auto math = panelUsageContextRead(f, "Math");
    const auto first = panelUsageMemberCall(f, math, "max", {QJSValue(0), selected});
    panelUsageGlobalCall(f, "focusEffort", {first, original});
}
void ApplicationInfo::assistantChooseEffort(const QJSValue& token) const {
    const auto f = panelUsageEngine(this);
    const auto original = panelUsageContextRead(f, "intent");
    if (!panelUsageTruth(panelUsageGlobalCall(f, "current", {original}))) return;
    const auto choices = assistantContextField(f, "composer", "effortChoices");
    if (!panelUsageTruth(panelUsageMemberCall(f, choices, "some", {panelUsageClosure(f, 85, {token}, 1)}))) {
        panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "effortSelection"), original}); return;
    }
    assistantMemberWrite(f, choiceOwner(f, original), "selectedEffort", token);
    if (!choiceStillCurrent(f, original)) return;
    panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "effortSelection"), original});
    if (choiceStillCurrent(f, original)) panelUsageGlobalCall(f, "close", {});
}
void ApplicationInfo::assistantChoicesOpened() const {
    const auto f = panelUsageEngine(this);
    const auto original = panelUsageContextRead(f, "intent");
    panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "modelSelection"), original});
    if (!choiceStillCurrent(f, original)) return;
    panelUsageGlobalCall(f, "reconcile", {panelUsageContextRead(f, "effortSelection"), original});
    if (!choiceStillCurrent(f, original)) return;
    const auto math = panelUsageContextRead(f, "Math");
    const auto selected = assistantContextField(f, "composer", "selectedModelRow");
    const auto first = panelUsageMemberCall(f, math, "max", {QJSValue(0), selected});
    panelUsageGlobalCall(f, "focusModel", {first, QJSValue(1), original});
}
void ApplicationInfo::assistantChoicesClosed() const {
    const auto f = panelUsageEngine(this);
    const auto original = panelUsageContextRead(f, "intent");
    panelUsageContextWrite(f, "intent", consentNull());
    if (!consentQtObject(f, panelUsageContextRead(f, "choicePopup")) || !assistantContextField(f, "choicePopup", "intent").isNull()
        || !consentQtObject(f, panelUsageContextRead(f, "composer")) || !panelUsageTruth(original)) return;
    if (!projectFieldIs(f, "composer", "assistant", choiceOwner(f, original)) || !panelUsageTruth(assistantContextField(f, "composer", "choicesEnabled"))
        || !panelUsageTruth(assistantContextField(f, "modelEffortButton", "visible"))) return;
    projectInvoke(f, "modelEffortButton", "forceActiveFocus");
}
QJSValue ApplicationInfo::assistantChoiceLabelWidth() const {
    const auto f = panelUsageEngine(this);
    auto math = panelUsageContextRead(f, "Math");
    auto metrics = panelUsageContextRead(f, "choiceMetrics");
    const auto model = panelUsageMemberCall(f, metrics, "advanceWidth", {choiceText(f, "Model")});
    metrics = panelUsageContextRead(f, "choiceMetrics");
    const auto effort = panelUsageMemberCall(f, metrics, "advanceWidth", {choiceText(f, "Reasoning effort")});
    auto measured = panelUsageMemberCall(f, math, "max", {model, effort});
    for (double index = 0; panelUsageReady(f); ++index) {
        auto owner = assistantContextField(f, "composer", "assistant");
        auto models = panelUsageRead(f, owner, "models");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, models, "count"), 0)) break;
        math = panelUsageContextRead(f, "Math"); metrics = panelUsageContextRead(f, "choiceMetrics");
        owner = assistantContextField(f, "composer", "assistant"); models = panelUsageRead(f, owner, "models");
        const auto name = panelUsageMemberCall(f, models, "text", {QJSValue(index), QJSValue(QStringLiteral("displayName"))});
        const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {name});
        measured = panelUsageMemberCall(f, math, "max", {measured, width});
    }
    panelUsageEach(f, assistantContextField(f, "composer", "effortChoices"), [&](const QJSValue& row) {
        math = panelUsageContextRead(f, "Math"); metrics = panelUsageContextRead(f, "choiceMetrics");
        const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {panelUsageRead(f, row, "label")});
        measured = panelUsageMemberCall(f, math, "max", {measured, width});
        return panelUsageReady(f);
    });
    math = panelUsageContextRead(f, "Math");
    const auto rounded = panelUsageMemberCall(f, math, "ceil", {measured});
    const auto gap = assistantContextField(f, "AppSizes", "fieldSpacing");
    return panelUsageAdd(f, rounded, viewArithmetic(f, gap, QJSValue(2), 1));
}
void ApplicationInfo::assistantChoiceActivateKey(const QJSValue& value, const QJSValue& event, bool model) const {
    const auto f = panelUsageEngine(this);
    projectInvoke(f, "choicePopup", model ? "chooseModel" : "chooseEffort", {value});
    assistantMemberWrite(f, event, "accepted", QJSValue(true));
}
void ApplicationInfo::assistantChoiceModelNavigate(const QJSValue& index, int step, const QJSValue& event) const {
    const auto f = panelUsageEngine(this);
    const auto popup = panelUsageContextRead(f, "choicePopup");
    const auto next = step > 0 ? panelUsageAdd(f, index, QJSValue(1)) : viewArithmetic(f, index, QJSValue(1), 0);
    const auto intent = assistantContextField(f, "choicePopup", "intent");
    panelUsageMemberCall(f, popup, "focusModel", {next, QJSValue(step), intent});
    assistantMemberWrite(f, event, "accepted", QJSValue(true));
}
void ApplicationInfo::assistantChoiceEffortNavigate(const QJSValue& row, bool forward, bool wrap, const QJSValue& event) const {
    const auto f = panelUsageEngine(this);
    if (forward) {
        const auto index = panelUsageRead(f, row, "index");
        const auto next = panelUsageAdd(f, index, QJSValue(1));
        if (assistantRelation(f, next, assistantContextField(f, "effortTable", "count"), 0)) {
            const auto popup = panelUsageContextRead(f, "choicePopup");
            const auto actual = panelUsageAdd(f, panelUsageRead(f, row, "index"), QJSValue(1));
            const auto intent = assistantContextField(f, "choicePopup", "intent");
            panelUsageMemberCall(f, popup, "focusEffort", {actual, intent});
        } else if (wrap) {
            const auto popup = panelUsageContextRead(f, "choicePopup");
            const auto intent = assistantContextField(f, "choicePopup", "intent");
            panelUsageMemberCall(f, popup, "focusModel", {QJSValue(0), QJSValue(1), intent});
        }
    } else {
        if (assistantRelation(f, panelUsageRead(f, row, "index"), QJSValue(0), 1)) {
            const auto popup = panelUsageContextRead(f, "choicePopup");
            const auto previous = viewArithmetic(f, panelUsageRead(f, row, "index"), QJSValue(1), 0);
            const auto intent = assistantContextField(f, "choicePopup", "intent");
            panelUsageMemberCall(f, popup, "focusEffort", {previous, intent});
        } else if (wrap) {
            const auto popup = panelUsageContextRead(f, "choicePopup");
            const auto count = assistantContextField(f, "modelTable", "count");
            const auto last = viewArithmetic(f, count, QJSValue(1), 0);
            const auto intent = assistantContextField(f, "choicePopup", "intent");
            panelUsageMemberCall(f, popup, "focusModel", {last, QJSValue(-1), intent});
        }
    }
    assistantMemberWrite(f, event, "accepted", QJSValue(true));
}
void ApplicationInfo::composerReturnPressed(const QJSValue& event) const {
    const auto f = panelUsageEngine(this);
    const auto modifiers = panelUsageRead(f, event, "modifiers"); const auto shift = assistantContextField(f, "Qt", "ShiftModifier");
    if (!panelUsageReady(f)) return;
    QV4::Scope scope(f.vm());
    QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), modifiers));
    QV4::ScopedValue b(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), shift));
    QV4::ScopedValue result(scope, QV4::Runtime::BitAnd::call(*a, *b));
    f.checked();
    if (result->toBoolean()) assistantMemberWrite(f, event, "accepted", QJSValue(false));
    else { projectInvoke(f, "composer", "submit"); assistantMemberWrite(f, event, "accepted", QJSValue(true)); }
}
void ApplicationInfo::assistantChoicesKey(const QJSValue& event, bool released) const {
    const auto f = panelUsageEngine(this);
    auto key = panelUsageRead(f, event, "key");
    bool enter = key.strictlyEquals(assistantContextField(f, "Qt", "Key_Return"));
    if (!enter) { key = panelUsageRead(f, event, "key"); enter = key.strictlyEquals(assistantContextField(f, "Qt", "Key_Enter")); }
    assistantMemberWrite(f, event, "accepted", QJSValue(enter));
    if (!released && enter && !panelUsageTruth(panelUsageRead(f, event, "isAutoRepeat"))) projectInvoke(f, "composer", "openChoices");
}

namespace {
QJSValue panelMessages(const PanelUsageFrame& f) {
    const auto owner = assistantContextField(f, "panel", "assistant");
    return panelUsageRead(f, owner, "messages");
}
QJSValue panelMessageText(const PanelUsageFrame& f, const QJSValue& index, const char* role) {
    return panelUsageMemberCall(f, panelMessages(f), "text", {index, QJSValue(QString::fromLatin1(role))});
}
QJSValue assistantUiCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& retained, const std::function<QJSValue(uint)>& arg) {
    if (operation == 80) {
        const auto b = panelUsageGlobalCall(f, "effortRank", {arg(1)});
        const auto a = panelUsageGlobalCall(f, "effortRank", {arg(0)});
        return viewArithmetic(f, b, a, 0);
    }
    if (operation == 81) {
        const auto token = arg(0);
        const auto literal = panelUsageLiteral(f);
        panelUsageWrite(f, literal.value, "token", token);
        panelUsageWrite(f, literal.value, "label", panelUsageGlobalCall(f, "effortLabel", {token}));
        return panelUsageComplete(f, literal);
    }
    if (operation >= 82 && operation <= 85) {
        const auto token = panelUsageRead(f, arg(0), "token");
        QJSValue selected;
        if (operation == 82) selected = assistantContextField(f, "assistant", "selectedEffort");
        else if (operation == 83) {
            const auto owner = assistantContextField(f, "composer", "assistant");
            selected = panelUsageRead(f, owner, "selectedEffort");
        } else if (operation == 84) selected = panelUsageRead(f, choiceOwner(f, retained(0)), "selectedEffort");
        else selected = retained(0);
        return QJSValue(token.strictlyEquals(selected));
    }
    if (operation == 90) { choiceDeferredFocus(f, retained(0), retained(1), retained(2)); return {}; }
    if (operation == 91) {
        const auto panel = panelUsageContextRead(f, "panel");
        if (!consentQtObject(f, panel) || !consentQtObject(f, assistantContextField(f, "panel", "assistant"))) return {};
        const auto owner = assistantContextField(f, "panel", "assistant");
        return panelUsageMemberCall(f, owner, "restoreLastSession");
    }
    if (panelUsageTruth(assistantContextField(f, "historyScrollBar", "activeFocus"))) {
        const auto conversation = panelUsageContextRead(f, "conversation");
        assistantMemberWrite(f, conversation, "followsTail", assistantContextField(f, "conversation", "atYEnd"));
    }
    return {};
}
QJSValue panelRegex(const PanelUsageFrame& f, const QString& pattern, int flags = 0) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm());
    QV4::Scoped<QV4::RegExpObject> expression(scope, f.vm()->newRegExpObject(pattern, flags));
    f.checked();
    return QJSValuePrivate::fromReturnedValue(expression->asReturnedValue());
}
} // namespace
void ApplicationInfo::panelCaptureNotice() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel");
    const auto original = assistantContextField(f, "panel", "assistant");
    if (!consentQtObject(f, component) || !consentQtObject(f, original)) return;
    const auto previous = panelUsageRead(f, component, "noticeState");
    const auto message = panelUsageRead(f, original, "lastError");
    if (!consentOwner(f, component, original)) return;
    if (!panelUsageTruth(panelUsageRead(f, message, "length"))) {
        if (consentFieldEquals(f, component, "noticeState", previous)) consentClear(f, component, "noticeState");
        return;
    }
    if (panelUsageTruth(previous) && consentFieldEquals(f, previous, "owner", original) && consentFieldEquals(f, previous, "text", message)) return;
    const auto rows = panelUsageRead(f, original, "messages");
    const auto count = panelUsageRead(f, rows, "count");
    const auto anchor = assistantRelation(f, count, QJSValue(0), 1)
        ? panelUsageMemberCall(f, rows, "text", {viewArithmetic(f, count, QJSValue(1), 0), QJSValue(QStringLiteral("id"))}) : QJSValue(QString{});
    if (!consentOwner(f, component, original) || !consentFieldEquals(f, component, "noticeState", previous)
        || !consentFieldEquals(f, original, "lastError", message)) return;
    const auto literal = panelUsageLiteral(f);
    panelUsageWrite(f, literal.value, "owner", original); panelUsageWrite(f, literal.value, "text", message); panelUsageWrite(f, literal.value, "anchor", anchor);
    assistantMemberWrite(f, component, "noticeState", panelUsageComplete(f, literal));
}
bool ApplicationInfo::panelNoticeAnchorPresent() const {
    const auto f = panelUsageEngine(this);
    const auto revision = panelUsageContextRead(f, "noticeProjection");
    const auto notice = panelUsageContextRead(f, "noticeState");
    if (revision.isNull() || !panelUsageTruth(notice)) return false;
    const auto owner = panelUsageRead(f, notice, "owner");
    if (!assistantSameName(f, owner, "assistant")) return false;
    const auto anchor = panelUsageRead(f, notice, "anchor");
    if (!panelUsageTruth(panelUsageRead(f, anchor, "length"))) return false;
    for (double index = 0; panelUsageReady(f); ++index) {
        const auto messages = assistantContextField(f, "assistant", "messages");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, messages, "count"), 0)) break;
        const auto actual = assistantContextField(f, "assistant", "messages");
        const auto id = panelUsageMemberCall(f, actual, "text", {QJSValue(index), QJSValue(QStringLiteral("id"))});
        if (consentFieldEquals(f, notice, "anchor", id)) return true;
    }
    return false;
}
void ApplicationInfo::panelNoticeOwnerChanged(int cause) const {
    const auto f = panelUsageEngine(this);
    if (cause == 0) {
        panelUsageContextWrite(f, "noticeState", consentNull()); panelUsageGlobalCall(f, "captureNotice", {});
    } else {
        projectInvoke(f, "panel", cause == 1 ? "retireConsentSend" : "scheduleConsentSend");
        projectWrite(f, "panel", "noticeState", consentNull()); projectInvoke(f, "panel", "captureNotice");
    }
}
void ApplicationInfo::panelCompleted() const {
    const auto f = panelUsageEngine(this);
    panelUsageGlobalCall(f, "captureNotice", {});
    const auto qt = panelUsageContextRead(f, "Qt");
    const auto callback = projectGuardedClosure(f, 91);
    panelUsageMemberCall(f, qt, "callLater", {callback});
}
void ApplicationInfo::panelSessionConsentRequested() const {
    const auto f = panelUsageEngine(this);
    if (!consentQtObject(f, panelUsageContextRead(f, "panel")) || !consentQtObject(f, panelUsageContextRead(f, "connectionDialog"))) return;
    projectInvoke(f, "connectionDialog", "beginOffer"); projectInvoke(f, "connectionDialog", "open");
}
QJSValue ApplicationInfo::panelOpenReportLink(const QJSValue& sourceRowId, const QJSValue& link) const {
    const auto f = panelUsageEngine(this);
    if (link.isString()) {
        const auto url = panelRegex(f, QStringLiteral(R"(^https?:\/\/[^\s/?#\\]+(?:[/?#][^\s\\]*)?$)"), QV4::RegExpObject::RegExp_IgnoreCase);
        if (panelUsageTruth(panelUsageMemberCall(f, url, "test", {link}))) {
            const auto controls = panelRegex(f, QStringLiteral(R"([\u0000-\u001f\u007f])"));
            if (!panelUsageTruth(panelUsageMemberCall(f, controls, "test", {link}))) return projectInvoke(f, "Qt", "openUrlExternally", {link});
        }
    }
    if (link.strictlyEquals(QJSValue(QStringLiteral("edi:report")))) {
        if (!assistantContextField(f, "Session", "project").isNull() && panelUsageTruth(assistantContextField(f, "AppState", "reportPageEnabled"))) {
            projectInvoke(f, "AppState", "open", {projectPage(f, "Report")}); return QJSValue(true);
        }
        projectInvoke(f, "reportPageUnavailable", "open"); return QJSValue(false);
    }
    const auto owner = assistantContextField(f, "panel", "assistant");
    return panelUsageMemberCall(f, owner, "openReport", {sourceRowId, link});
}
void ApplicationInfo::panelShownChanged() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageContextRead(f, "shown"))) return;
    projectInvoke(f, "panel", "retireConsentSend"); projectInvoke(f, "connectionDialog", "close"); projectInvoke(f, "composer", "closeChoices");
}
void ApplicationInfo::panelFocusComposer() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "ApplicationInfo", "assistantAvailable")) || !panelUsageTruth(panelUsageContextRead(f, "visible"))
        || !panelUsageTruth(panelUsageContextRead(f, "shown"))) return;
    if (panelUsageTruth(panelUsageRead(f, assistantContextField(f, "panel", "assistant"), "connected"))) projectInvoke(f, "composer", "focusEditor");
    else projectInvoke(f, "connectionButton", "forceActiveFocus");
}
void ApplicationInfo::panelSubmissionBlocked() const {
    const auto f = panelUsageEngine(this);
    const auto component = panelUsageContextRead(f, "panel"); const auto view = panelUsageContextRead(f, "conversation");
    const auto original = assistantContextField(f, "panel", "assistant");
    panelUsageMemberCall(f, component, "captureNotice");
    if (consentQtObject(f, component) && consentQtObject(f, view) && consentQtObject(f, original)
        && consentFieldEquals(f, component, "assistant", original) && panelUsageTruth(panelUsageRead(f, original, "contextApprovalBlocked"))) panelUsageMemberCall(f, view, "revealCurrentNotice");
}
void ApplicationInfo::panelFilesEntered(const QJSValue& drag) const {
    const auto f = panelUsageEngine(this);
    const auto urls = panelUsageRead(f, drag, "hasUrls");
    const auto result = panelUsageTruth(urls) ? QJSValue(!panelUsageTruth(panelUsageRead(f, assistantContextField(f, "panel", "assistant"), "canCancel"))) : urls;
    assistantMemberWrite(f, drag, "accepted", result);
}
void ApplicationInfo::panelFilesDropped(const QJSValue& drop) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "chatFilesDrop", "enabled")) || !panelUsageTruth(panelUsageRead(f, drop, "hasUrls"))
        || panelUsageTruth(panelUsageRead(f, assistantContextField(f, "panel", "assistant"), "canCancel"))) {
        assistantMemberWrite(f, drop, "accepted", QJSValue(false)); return;
    }
    const auto original = assistantContextField(f, "panel", "assistant"); const auto files = panelUsageRead(f, drop, "urls");
    const auto request = panelUsageMemberCall(f, original, "beginFileSelection", {QJSValue(true)});
    if (!consentQtObject(f, panelUsageContextRead(f, "panel")) || !consentQtObject(f, original)
        || !projectFieldIs(f, "panel", "assistant", original) || !panelUsageTruth(panelUsageRead(f, original, "connected"))) {
        if (consentQtObject(f, original)) panelUsageMemberCall(f, original, "cancelFileSelection", {request});
        assistantMemberWrite(f, drop, "accepted", QJSValue(false)); return;
    }
    const bool admitted = assistantRelation(f, panelUsageRead(f, request, "length"), QJSValue(0), 1);
    const auto result = admitted ? panelUsageMemberCall(f, original, "addSelectedFiles", {request, files}) : QJSValue(false);
    assistantMemberWrite(f, drop, "accepted", result);
}
void ApplicationInfo::panelConnectionRejected() const {
    const auto f = panelUsageEngine(this);
    projectInvoke(f, "panel", "retireConsentSend");
    if (consentQtObject(f, assistantContextField(f, "panel", "assistant"))) {
        const auto owner = assistantContextField(f, "panel", "assistant"); panelUsageMemberCall(f, owner, "cancelSessionSelection");
    }
}
void ApplicationInfo::panelConnectionActivated() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "connectionButton", "pendingConnection"))) {
        const auto component = panelUsageContextRead(f, "panel"); const auto original = assistantContextField(f, "panel", "assistant");
        if (!consentOwner(f, component, original) || !consentFieldEquals(f, original, "state", QJSValue(QStringLiteral("connecting")))
            || !panelUsageTruth(panelUsageRead(f, original, "canCancel"))) return;
        panelUsageMemberCall(f, original, "cancel");
    } else if (panelUsageTruth(assistantContextField(f, "connectionButton", "accountView"))) projectInvoke(f, "accountDialog", "open");
    else {
        const auto owner = assistantContextField(f, "panel", "assistant");
        if (panelUsageTruth(panelUsageMemberCall(f, owner, "resumeConnection"))) return;
        const auto component = panelUsageContextRead(f, "panel"); const auto original = assistantContextField(f, "panel", "assistant");
        const auto dialog = panelUsageContextRead(f, "connectionDialog");
        const auto offer = panelUsageMemberCall(f, dialog, "beginOffer");
        const auto current = [&] { return consentQtObject(f, component) && consentQtObject(f, original) && consentQtObject(f, dialog)
            && consentFieldEquals(f, component, "assistant", original) && consentFieldEquals(f, dialog, "assistant", original)
            && consentFieldEquals(f, dialog, "approvalOwner", offer); };
        if (!current()) return;
        panelUsageMemberCall(f, component, "retireConsentSend");
        if (!current() || panelUsageTruth(panelUsageRead(f, original, "connected"))) return;
        panelUsageMemberCall(f, dialog, "presentOffer", {offer});
    }
}
void ApplicationInfo::conversationDetailsChanging() const {
    const auto f = panelUsageEngine(this);
    projectInvoke(f, "conversation", "cancelFlick"); projectWrite(f, "conversation", "followsTail", QJSValue(false));
    projectWrite(f, "conversation", "jumpedUserId", QJSValue(QString{}));
}
QJSValue ApplicationInfo::connectionNaturalButtonsWidth() const {
    const auto f = panelUsageEngine(this);
    QJSValue total(0);
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageContextRead(f, "count"), 0); ++index) {
        const auto button = panelUsageGlobalCall(f, "itemAt", {QJSValue(index)});
        if (panelUsageTruth(button)) total = panelUsageAdd(f, total, panelUsageRead(f, button, "implicitWidth"));
    }
    const auto math = panelUsageContextRead(f, "Math");
    const auto count = panelUsageContextRead(f, "count");
    const auto gapCount = panelUsageMemberCall(f, math, "max", {QJSValue(0), viewArithmetic(f, count, QJSValue(1), 0)});
    const auto spacing = panelUsageContextRead(f, "spacing");
    return panelUsageAdd(f, total, viewArithmetic(f, gapCount, spacing, 1));
}
void ApplicationInfo::connectionPresentationChanged(int cause) const {
    const auto f = panelUsageEngine(this);
    if (cause == 1) {
        if (panelUsageTruth(assistantContextField(f, "dialog", "visible"))) projectInvoke(f, "dialog", "updateAcceptButton");
        return;
    }
    if (cause == 3) { projectInvoke(f, "dialog", "showConnectionFailureIfFinished"); projectInvoke(f, "dialog", "scheduleAcceptedOffer"); return; }
    const auto component = panelUsageContextRead(f, "dialog"); const auto original = assistantContextField(f, "dialog", "assistant");
    if (cause == 0) panelUsageGlobalCall(f, "refreshDisclosedContext", {}); else panelUsageMemberCall(f, component, "refreshDisclosedContext");
    if (consentOwner(f, component, original) && (cause == 0 || panelUsageTruth(panelUsageRead(f, component, "visible")))) panelUsageMemberCall(f, component, "updateAcceptButton");
}

QJSValue ApplicationInfo::conversationUserTarget(const QJSValue& direction) const {
    const auto f = panelUsageEngine(this);
    const auto count = panelUsageRead(f, panelMessages(f), "count");
    const auto position = panelUsageContextRead(f, "contentY");
    const auto layout = panelUsageContextRead(f, "contentHeight");
    if (count.strictlyEquals(QJSValue(0)) || assistantRelation(f, layout, QJSValue(0), 3)) return QJSValue(-1);
    const auto cursor = panelUsageContextRead(f, "jumpedUserId");
    if (assistantRelation(f, panelUsageRead(f, cursor, "length"), QJSValue(0), 1)) {
        QJSValue current(-1);
        for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), count, 0); ++index) {
            const auto id = panelMessageText(f, QJSValue(index), "id");
            if (assistantSameName(f, id, "jumpedUserId")) { current = QJSValue(index); break; }
        }
        if (assistantRelation(f, current, QJSValue(0), 2)) {
            for (QJSValue index = panelUsageAdd(f, current, direction); panelUsageReady(f)
                 && assistantRelation(f, index, QJSValue(0), 2) && assistantRelation(f, index, count, 0);
                 index = panelUsageAdd(f, index, direction)) {
                if (panelMessageText(f, index, "kind").strictlyEquals(QJSValue(QStringLiteral("user")))) return index;
            }
            return QJSValue(-1);
        }
    }
    QJSValue first = panelUsageGlobalCall(f, "indexAt", {QJSValue(1), panelUsageAdd(f, position, QJSValue(1))});
    if (assistantRelation(f, first, QJSValue(0), 0)) {
        const auto gap = panelUsageContextRead(f, "spacing");
        const auto after = panelUsageAdd(f, panelUsageAdd(f, position, gap), QJSValue(2));
        first = panelUsageGlobalCall(f, "indexAt", {QJSValue(1), after});
    }
    if (assistantRelation(f, first, QJSValue(0), 0)) first = panelUsageTruth(panelUsageContextRead(f, "atYEnd")) ? viewArithmetic(f, count, QJSValue(1), 0) : QJSValue(0);
    QJSValue candidate(-1);
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), count, 0); ++index) {
        if (!panelMessageText(f, QJSValue(index), "kind").strictlyEquals(QJSValue(QStringLiteral("user")))) continue;
        const auto item = panelUsageGlobalCall(f, "itemAtIndex", {QJSValue(index)});
        bool before;
        if (panelUsageTruth(item)) {
            const auto y = panelUsageRead(f, item, "y");
            before = assistantRelation(f, y, viewArithmetic(f, position, QJSValue(0.5), 0), 0);
        } else before = assistantRelation(f, QJSValue(index), first, 0);
        bool after;
        if (panelUsageTruth(item)) {
            const auto y = panelUsageRead(f, item, "y");
            after = assistantRelation(f, y, panelUsageAdd(f, position, QJSValue(0.5)), 1);
        } else after = assistantRelation(f, QJSValue(index), first, 1);
        if (assistantRelation(f, direction, QJSValue(0), 0) && before) candidate = QJSValue(index);
        if (assistantRelation(f, direction, QJSValue(0), 1) && after) return QJSValue(index);
    }
    return assistantRelation(f, direction, QJSValue(0), 0) ? candidate : QJSValue(-1);
}
void ApplicationInfo::conversationJumpToUser(const QJSValue& direction) const {
    const auto f = panelUsageEngine(this);
    const auto target = panelUsageContextRead(f, assistantRelation(f, direction, QJSValue(0), 0) ? "previousUserIndex" : "nextUserIndex");
    if (assistantRelation(f, target, QJSValue(0), 0)) return;
    panelUsageContextWrite(f, "jumpedUserId", panelMessageText(f, target, "id"));
    panelUsageContextWrite(f, "followsTail", QJSValue(false));
    panelUsageGlobalCall(f, "cancelFlick", {});
    panelUsageGlobalCall(f, "positionViewAtIndex", {target, assistantContextField(f, "ListView", "Beginning")});
}
void ApplicationInfo::conversationObserveAdmission() const {
    const auto f = panelUsageEngine(this);
    QJSValue latest(QString{});
    const auto count = panelUsageRead(f, panelMessages(f), "count");
    for (QJSValue index = viewArithmetic(f, count, QJSValue(1), 0); panelUsageReady(f)
         && assistantRelation(f, index, QJSValue(0), 2); index = viewArithmetic(f, index, QJSValue(1), 0)) {
        if (panelMessageText(f, index, "kind").strictlyEquals(QJSValue(QStringLiteral("user")))) { latest = panelMessageText(f, index, "id"); break; }
    }
    if (assistantSameName(f, latest, "lastUserId")) return;
    if (assistantRelation(f, panelUsageRead(f, latest, "length"), QJSValue(0), 1)) {
        panelUsageContextWrite(f, "followsTail", QJSValue(true)); panelUsageContextWrite(f, "jumpedUserId", QJSValue(QString{}));
    }
    panelUsageContextWrite(f, "lastUserId", latest);
}
void ApplicationInfo::conversationRevealNotice() const {
    const auto f = panelUsageEngine(this);
    const auto original = assistantContextField(f, "panel", "assistant");
    const auto notice = assistantContextField(f, "panel", "noticeState");
    if (!panelUsageTruth(notice) || !consentFieldEquals(f, notice, "owner", original)) return;
    const auto text = panelUsageRead(f, notice, "text");
    if (!panelUsageTruth(panelUsageRead(f, text, "length"))) return;
    QJSValue anchor(-1);
    for (double index = 0; panelUsageReady(f); ++index) {
        auto rows = panelUsageRead(f, original, "messages");
        if (!assistantRelation(f, QJSValue(index), panelUsageRead(f, rows, "count"), 0)) break;
        rows = panelUsageRead(f, original, "messages");
        const auto id = panelUsageMemberCall(f, rows, "text", {QJSValue(index), QJSValue(QStringLiteral("id"))});
        if (consentFieldEquals(f, notice, "anchor", id)) { anchor = QJSValue(index); break; }
    }
    if (!consentQtObject(f, panelUsageContextRead(f, "panel")) || !consentQtObject(f, original)
        || !projectFieldIs(f, "panel", "assistant", original) || !projectFieldIs(f, "panel", "noticeState", notice)) return;
    panelUsageGlobalCall(f, "cancelFlick", {}); panelUsageContextWrite(f, "followsTail", QJSValue(false)); panelUsageContextWrite(f, "jumpedUserId", QJSValue(QString{}));
    if (assistantRelation(f, anchor, QJSValue(0), 2)) panelUsageGlobalCall(f, "positionViewAtIndex", {anchor, assistantContextField(f, "ListView", "End")});
    else panelUsageGlobalCall(f, "positionViewAtBeginning", {});
}
void ApplicationInfo::conversationPositionAtTail() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "followsTail")) || panelUsageTruth(panelUsageContextRead(f, "moving"))
        || panelUsageTruth(assistantContextField(f, "historyScrollBar", "pressed")) || assistantRelation(f, panelUsageContextRead(f, "height"), QJSValue(0), 3)) return;
    panelUsageGlobalCall(f, "forceLayout", {});
    if (panelUsageTruth(panelUsageContextRead(f, "followsTail")) && !panelUsageTruth(panelUsageContextRead(f, "moving"))
        && !panelUsageTruth(assistantContextField(f, "historyScrollBar", "pressed"))) panelUsageGlobalCall(f, "positionViewAtEnd", {});
}
void ApplicationInfo::conversationFollowOutput() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "followsTail"))) return;
    const auto qt = panelUsageContextRead(f, "Qt");
    const auto callback = panelUsageContextRead(f, "positionAtTail");
    panelUsageMemberCall(f, qt, "callLater", {callback});
}
void ApplicationInfo::conversationUpdated(bool modelData) const {
    const auto f = panelUsageEngine(this);
    if (modelData) {
        const auto panel = panelUsageContextRead(f, "panel");
        if (panelUsageReady(f)) assistantMemberWrite(f, panel, "noticeProjection", f->newObject());
        projectInvoke(f, "conversation", "observeUserAdmission"); projectInvoke(f, "conversation", "followOutput");
    } else { panelUsageGlobalCall(f, "observeUserAdmission", {}); panelUsageGlobalCall(f, "followOutput", {}); }
}
void ApplicationInfo::conversationContentYChanged() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageContextRead(f, "moving")) || panelUsageTruth(assistantContextField(f, "historyScrollBar", "pressed"))) {
        panelUsageContextWrite(f, "jumpedUserId", QJSValue(QString{})); panelUsageContextWrite(f, "followsTail", panelUsageContextRead(f, "atYEnd"));
    }
}
void ApplicationInfo::conversationMovementChanged(bool started) const {
    const auto f = panelUsageEngine(this);
    if (started) panelUsageContextWrite(f, "jumpedUserId", QJSValue(QString{}));
    else {
        const auto id = panelUsageContextRead(f, "jumpedUserId");
        if (panelUsageRead(f, id, "length").strictlyEquals(QJSValue(0))) panelUsageContextWrite(f, "followsTail", panelUsageContextRead(f, "atYEnd"));
    }
}
void ApplicationInfo::conversationScrollChanged(bool position) const {
    const auto f = panelUsageEngine(this);
    if (!position) {
        if (!panelUsageTruth(panelUsageContextRead(f, "pressed"))) projectWrite(f, "conversation", "followsTail", assistantContextField(f, "conversation", "atYEnd"));
    } else if (panelUsageTruth(panelUsageContextRead(f, "activeFocus"))) {
        const auto qt = panelUsageContextRead(f, "Qt");
        panelUsageMemberCall(f, qt, "callLater", {projectGuardedClosure(f, 92)});
    }
}
QJSValue ApplicationInfo::assistantMessageTableTone(const QJSValue& lift) const {
    const auto f = panelUsageEngine(this);
    const auto base = panelUsageContextRead(f, "chatBackgroundColor");
    const auto qt = panelUsageContextRead(f, "Qt");
    QJSValueList channels;
    for (const char* channel : {"r", "g", "b"}) {
        const auto math = panelUsageContextRead(f, "Math");
        const auto color = panelUsageRead(f, base, channel);
        const auto delta = viewArithmetic(f, lift, QJSValue(255), 2);
        const auto sum = panelUsageAdd(f, color, delta);
        channels.append(panelUsageMemberCall(f, math, "min", {QJSValue(1), sum}));
    }
    channels.append(panelUsageRead(f, base, "a"));
    return panelUsageMemberCall(f, qt, "rgba", channels);
}
QJSValue ApplicationInfo::assistantSentFileLabel(const QJSValue& file) const {
    const auto f = panelUsageEngine(this);
    if (auto* qml = qobject_cast<QQmlEngine*>(f.data())) qml->markCurrentFunctionAsTranslationBinding();
    const auto label = QJSValue(QCoreApplication::translate("AssistantMessage", "%1 (%2)%3"));
    auto text = panelUsageMemberCall(f, label, "arg", {panelUsageRead(f, file, "name")});
    const auto info = panelUsageContextRead(f, "ApplicationInfo");
    const auto size = panelUsageMemberCall(f, info, "fileSizeKilobytes", {panelUsageRead(f, file, "bytes")});
    text = panelUsageMemberCall(f, text, "arg", {size});
    const auto readable = panelUsageRead(f, file, "textReadable");
    const auto extra = QJSValue(panelUsageTruth(readable) ? QString{} : QCoreApplication::translate("AssistantMessage", " · text export required"));
    return panelUsageMemberCall(f, text, "arg", {extra});
}
QJSValue ApplicationInfo::assistantWidestSentFile() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageContextRead(f, "kind").strictlyEquals(QJSValue(QStringLiteral("user")))
        || !panelUsageContextRead(f, "status").strictlyEquals(QJSValue(QStringLiteral("completed")))) return QJSValue(0);
    const auto metricsFont = assistantContextField(f, "historyCopyMetrics", "font"); Q_UNUSED(metricsFont);
    QJSValue widest(0);
    panelUsageEach(f, panelUsageContextRead(f, "inputFiles"), [&](const QJSValue& file) {
        const auto math = panelUsageContextRead(f, "Math");
        const auto inner = panelUsageContextRead(f, "Math");
        const auto metrics = panelUsageContextRead(f, "historyCopyMetrics");
        const auto label = panelUsageGlobalCall(f, "sentFileLabel", {file});
        const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {label});
        const auto rounded = panelUsageMemberCall(f, inner, "ceil", {width});
        widest = panelUsageMemberCall(f, math, "max", {widest, rounded});
        return panelUsageReady(f);
    });
    return widest;
}
void ApplicationInfo::assistantMessageCopyKey(const QJSValue& event) const {
    const auto f = panelUsageEngine(this);
    const auto copy = assistantContextField(f, "StandardKey", "Copy");
    if (!panelUsageTruth(panelUsageMemberCall(f, event, "matches", {copy}))) return;
    const auto start = assistantContextField(f, "body", "selectionStart"); const auto end = assistantContextField(f, "body", "selectionEnd");
    if (start.strictlyEquals(end)) return;
    const auto info = panelUsageContextRead(f, "ApplicationInfo"); const auto markdown = panelUsageContextRead(f, "markdownPresentation");
    const auto actualStart = assistantContextField(f, "body", "selectionStart"); const auto actualEnd = assistantContextField(f, "body", "selectionEnd");
    const auto literal = panelUsageMemberCall(f, markdown, "selectedSource", {actualStart, actualEnd});
    panelUsageMemberCall(f, info, "copyText", {literal}); assistantMemberWrite(f, event, "accepted", QJSValue(true));
}

namespace {
QJSValue tableCallback(const PanelUsageFrame& f, uint operation, const QJSValueList& values, int arity) {
    return panelUsageClosure(f, operation, values, arity);
}
QJSValue tableNullish(const QJSValue& value, const QJSValue& fallback) { return value.isNull() || value.isUndefined() ? fallback : value; }
bool tableAlive(const PanelUsageFrame& f, const QJSValue& life) { return panelUsageTruth(life) && editorLife(f, life); }
QJSValue tableArrayFrom(const PanelUsageFrame& f, const QJSValue& value) {
    const auto array = panelUsageContextRead(f, "Array"); return panelUsageMemberCall(f, array, "from", {value});
}
bool tableHas(const PanelUsageFrame& f, const QJSValue& object, const char* property) {
    if (!panelUsageReady(f)) return false;
    QV4::Scope scope(f.vm());
    QV4::ScopedValue key(scope, f.vm()->newString(QString::fromLatin1(property)));
    QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), object));
    QV4::ScopedValue result(scope, QV4::Runtime::In::call(f.vm(), *key, *value)); f.checked(); return result->toBoolean();
}
QJSValue tableTypeof(const PanelUsageFrame& f, const QJSValue& input) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), input));
    QV4::ScopedValue result(scope, QV4::Runtime::TypeofValue::call(f.vm(), *value));
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
bool tableForIn(const PanelUsageFrame& f, const QJSValue& source, const std::function<bool(const QJSValue&)>& visit) {
    if (!panelUsageReady(f)) return false;
    QV4::Scope scope(f.vm()); QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), source));
    QV4::ScopedValue iterator(scope, QV4::Runtime::GetIterator::call(f.vm(), *object, static_cast<int>(QQmlJS::AST::ForEachType::In)));
    f.checked(); if (!panelUsageReady(f)) return false;
    QV4::ScopedValue value(scope);
    for (;;) {
        const auto done = QV4::Runtime::IteratorNext::call(f.vm(), *iterator, value);
        if (QV4::Value::fromReturnedValue(done).toBoolean()) { f.checked(); return panelUsageReady(f); }
        if (!visit(QJSValuePrivate::fromReturnedValue(value->asReturnedValue()))) return false;
    }
}
void tableIncrement(const PanelUsageFrame& f, const char* name, bool explicitTable = false) {
    const auto original = explicitTable ? assistantContextField(f, "table", name) : panelUsageContextRead(f, name);
    const auto number = panelUsageNumber(f, original); if (!number) return;
    if (explicitTable) projectWrite(f, "table", name, QJSValue(*number + 1)); else panelUsageContextWrite(f, name, QJSValue(*number + 1));
}
QJSValue tableCellsOf(const PanelUsageFrame& f, const QJSValue& row) {
    QJSValue first = consentNull();
    if (panelUsageTruth(row) && panelUsageTruth(panelUsageRead(f, row, "contentRowData"))) {
        const auto array = panelUsageContextRead(f, "Array");
        const auto children = panelUsageRead(f, row, "contentRowData");
        const auto cells = panelUsageMemberCall(f, array, "from", {children});
        first = panelUsageMemberCall(f, cells, "find", {tableCallback(f, 131, {}, 1)});
    }
    if (!panelUsageTruth(first) || !panelUsageTruth(panelUsageRead(f, first, "parent"))) return consentNull();
    const auto array = panelUsageContextRead(f, "Array"); const auto parent = panelUsageRead(f, first, "parent");
    return panelUsageMemberCall(f, array, "from", {panelUsageRead(f, parent, "children")});
}
QJSValue tableControlWidth(const PanelUsageFrame& f, const QJSValue& child) {
    return tableHas(f, child, "fittedWidth") ? panelUsageRead(f, child, "fittedWidth") : tableNullish(panelUsageRead(f, child, "implicitWidth"), QJSValue(0));
}
QJSValue tablePadded(const PanelUsageFrame& f, const QJSValue& cell, const QJSValue& width) {
    const auto left = tableNullish(panelUsageRead(f, cell, "leftPadding"), QJSValue(0));
    const auto first = panelUsageAdd(f, width, left);
    return panelUsageAdd(f, first, tableNullish(panelUsageRead(f, cell, "rightPadding"), QJSValue(0)));
}
QJSValue tableMeasure(const PanelUsageFrame& f, const QJSValue& cell) {
    if (tableHas(f, cell, "number")) {
        const auto metrics = panelUsageContextRead(f, "metrics");
        const auto width = panelUsageMemberCall(f, metrics, "advanceWidth", {panelUsageRead(f, cell, "number")});
        return tablePadded(f, cell, width);
    }
    if (tableHas(f, cell, "elide")) return panelUsageRead(f, cell, "implicitWidth");
    if (tableHas(f, cell, "contentWidth")) return tablePadded(f, cell, panelUsageRead(f, cell, "contentWidth"));
    const auto array = panelUsageContextRead(f, "Array");
    const auto children = panelUsageMemberCall(f, array, "from", {panelUsageRead(f, cell, "children")});
    const auto callback = tableCallback(f, 130, {}, 2);
    return panelUsageMemberCall(f, children, "reduce", {callback, panelUsageRead(f, cell, "implicitWidth")});
}
QJSValue tableProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    if (operation == 121) return QJSValue(false);
    if (operation == 120) {
        const auto life = saved(0), row = saved(1);
        if (!editorLife(f, life) || !consentQtObject(f, row) || !consentFieldEquals(f, row, "parent", saved(2))
            || !projectFieldIs(f, "table", "sourceModel", saved(3)) || !projectFieldIs(f, "table", "modelRevision", saved(4))) return QJSValue(false);
        const auto array = panelUsageContextRead(f, "Array"); const auto children = panelUsageRead(f, row, "children");
        const auto current = panelUsageMemberCall(f, array, "from", {children});
        if (!consentFieldsEqual(f, current, "length", saved(5), "length")) return QJSValue(false);
        return panelUsageMemberCall(f, saved(5), "every", {tableCallback(f, 122, {current, row}, 2)});
    }
    if (operation == 122) {
        const auto cell = arg(0), index = arg(1);
        if (!consentQtObject(f, cell)) return QJSValue(false);
        const auto current = textIndex(f, saved(0), index);
        return QJSValue(current.strictlyEquals(cell) && consentFieldEquals(f, cell, "parent", saved(1)));
    }
    if (operation == 123) return QJSValue(arg(0).strictlyEquals(QJSValue(-1)));
    if (operation == 124 || operation == 125) {
        const auto sum = arg(0), width = arg(1), index = arg(2); bool include;
        if (operation == 124) include = assistantRelation(f, width, QJSValue(0), 1) && !panelUsageTruth(textIndex(f, saved(0), index));
        else include = panelUsageTruth(textIndex(f, saved(0), index));
        return panelUsageAdd(f, sum, include ? width : QJSValue(0));
    }
    if (operation == 126) {
        const auto width = arg(0), index = arg(1);
        if (!panelUsageTruth(textIndex(f, saved(0), index))) return width;
        const auto math = panelUsageContextRead(f, "Math");
        const auto measured = textIndex(f, saved(1), index);
        auto sum = panelUsageAdd(f, viewArithmetic(f, measured, saved(2), 1), saved(3));
        const auto spreadColumns = panelUsageContextRead(f, "spreadColumns");
        const auto extra = panelUsageTruth(panelUsageMemberCall(f, spreadColumns, "includes", {index})) ? saved(4) : QJSValue(0);
        return panelUsageMemberCall(f, math, "floor", {panelUsageAdd(f, sum, extra)});
    }
    if (operation == 127) return panelUsageAdd(f, arg(0), arg(1));
    if (operation == 130) {
        const auto math = panelUsageContextRead(f, "Math"); const auto maximum = arg(0);
        return panelUsageMemberCall(f, math, "max", {maximum, tableControlWidth(f, arg(1))});
    }
    if (operation == 131) {
        const auto item = panelUsageContextRead(f, "Item");
        if (!panelUsageReady(f)) return {};
        QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), arg(0)));
        QV4::ScopedValue type(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), item));
        QV4::ScopedValue result(scope, QV4::Runtime::Instanceof::call(f.vm(), *value, *type)); f.checked();
        return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
    }
    if (operation == 132) return QJSValue(true);
    if (operation == 133) {
        const auto cell = arg(0), index = arg(1); const auto math = panelUsageContextRead(f, "Math");
        const auto width = panelUsageRead(f, cell, "implicitWidth"); QJSValue filler(0);
        if (assistantSameName(f, index, "fillerIndex")) {
            const auto paddings = panelUsageContextRead(f, "basePaddings");
            if (panelUsageTruth(panelUsageMemberCall(f, paddings, "has", {cell}))) filler = panelUsageContextRead(f, "fillerWidth");
        }
        return panelUsageMemberCall(f, math, "ceil", {viewArithmetic(f, width, filler, 0)});
    }
    if (operation == 134) {
        const auto index = arg(1), math = panelUsageContextRead(f, "Math");
        const auto header = tableNullish(textIndex(f, saved(0), index), QJSValue(0));
        QJSValue previous(0);
        if (!panelUsageTruth(panelUsageContextRead(f, "refitting"))) previous = tableNullish(textIndex(f, panelUsageContextRead(f, "fittedWidths"), index), QJSValue(0));
        return panelUsageMemberCall(f, math, "max", {header, previous});
    }
    if (operation == 135) return panelUsageGlobalCall(f, "kindOf", {arg(0)});
    if (operation == 142) {
        const auto math = panelUsageContextRead(f, "Math"); return panelUsageMemberCall(f, math, "max", {arg(0), arg(1)});
    }
    if (editorLife(f, saved(0))) {
        assistantMemberWrite(f, saved(0), "queued", QJSValue(false)); return projectInvoke(f, "table", "fitColumns");
    }
    return {};
}
} // namespace

QJSValue ApplicationInfo::tableColumnRowOwner(const QJSValue& row) const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife");
    if (!tableAlive(f, life) || !consentQtObject(f, row)) return tableCallback(f, 121, {}, 0);
    const auto parent = panelUsageRead(f, row, "parent"); const auto source = panelUsageContextRead(f, "sourceModel");
    const auto revision = panelUsageContextRead(f, "modelRevision"); const auto array = panelUsageContextRead(f, "Array");
    const auto cells = panelUsageMemberCall(f, array, "from", {panelUsageRead(f, row, "children")});
    return tableCallback(f, 120, {life, row, parent, source, revision, cells}, 0);
}
void ApplicationInfo::tableApplyWidths(const QJSValue& row) const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife");
    if (!tableAlive(f, life) || !consentQtObject(f, row)) return;
    const auto owns = panelUsageGlobalCall(f, "columnRowOwner", {row}); const auto array = panelUsageContextRead(f, "Array");
    const auto cells = panelUsageMemberCall(f, array, "from", {panelUsageRead(f, row, "children")});
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, cells, "length"), 0); ++index) {
        if (!panelUsageTruth(projectCall(f, owns))) return;
        const auto widths = panelUsageContextRead(f, "resolvedColumnWidths");
        if (assistantRelation(f, QJSValue(index), panelUsageRead(f, widths, "length"), 2)) return;
        const auto cell = textIndex(f, cells, QJSValue(index)); const auto width = textIndex(f, widths, QJSValue(index));
        if (!panelUsageTruth(projectCall(f, owns))) return; assistantMemberWrite(f, cell, "width", width);
    }
}
void ApplicationInfo::tablePadForFiller(const QJSValue& cell, const QJSValue& column) const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife");
    if (!tableAlive(f, life) || !consentQtObject(f, cell) || !tableHas(f, cell, "rightPadding") || tableHas(f, cell, "keepsAlignment")) return;
    const auto owns = panelUsageGlobalCall(f, "columnRowOwner", {panelUsageRead(f, cell, "parent")});
    if (!panelUsageTruth(projectCall(f, owns))) return;
    auto paddings = panelUsageContextRead(f, "basePaddings");
    if (!panelUsageTruth(panelUsageMemberCall(f, paddings, "has", {cell}))) {
        paddings = panelUsageContextRead(f, "basePaddings"); const auto literal = panelUsageLiteral(f);
        panelUsageWrite(f, literal.value, "left", panelUsageRead(f, cell, "leftPadding")); panelUsageWrite(f, literal.value, "right", panelUsageRead(f, cell, "rightPadding"));
        panelUsageMemberCall(f, paddings, "set", {cell, panelUsageComplete(f, literal)});
    }
    paddings = panelUsageContextRead(f, "basePaddings"); const auto base = panelUsageMemberCall(f, paddings, "get", {cell});
    const auto kinds = panelUsageContextRead(f, "cellKinds"); const auto kind = tableNullish(panelUsageMemberCall(f, kinds, "get", {cell}), QJSValue(QString{}));
    const auto gap = assistantContextField(f, "EaStyle", "Sizes"); const auto spacing = panelUsageRead(f, gap, "tableColumnSpacing");
    const auto left = panelUsageAdd(f, panelUsageRead(f, base, "left"), kind.strictlyEquals(QJSValue(QStringLiteral("text"))) ? spacing : QJSValue(0));
    auto right = panelUsageRead(f, base, "right");
    right = panelUsageAdd(f, right, kind.strictlyEquals(QJSValue(QStringLiteral("number"))) || kind.strictlyEquals(QJSValue(QStringLiteral("check"))) ? spacing : QJSValue(0));
    right = panelUsageAdd(f, right, assistantSameName(f, column, "fillerIndex") ? panelUsageContextRead(f, "fillerWidth") : QJSValue(0));
    if (!panelUsageTruth(projectCall(f, owns))) return; assistantMemberWrite(f, cell, "leftPadding", left);
    if (!panelUsageTruth(projectCall(f, owns))) return; assistantMemberWrite(f, cell, "rightPadding", right);
}
QJSValue ApplicationInfo::tableCellKind(const QJSValue& cell) const {
    const auto f = panelUsageEngine(this);
    if (tableHas(f, cell, "checked") && tableHas(f, cell, "horizontalAlignment")) return QJSValue(QStringLiteral("check"));
    if (tableHas(f, cell, "ring") || tableHas(f, cell, "fontIcon")) return QJSValue(QStringLiteral("icon"));
    if (tableHas(f, cell, "number") || tableHas(f, cell, "columnAlignment") || tableHas(f, cell, "item")
        || (tableHas(f, cell, "numeric") && panelUsageTruth(panelUsageRead(f, cell, "numeric")))) return QJSValue(QStringLiteral("number"));
    return QJSValue(QStringLiteral("text"));
}
void ApplicationInfo::tableAlignCell(const QJSValue& cell, const QJSValue& kind) const {
    const auto f = panelUsageEngine(this); if (tableHas(f, cell, "keepsAlignment")) return;
    const auto kinds = panelUsageContextRead(f, "cellKinds"); panelUsageMemberCall(f, kinds, "set", {cell, kind});
    const bool number = kind.strictlyEquals(QJSValue(QStringLiteral("number"))) || kind.strictlyEquals(QJSValue(QStringLiteral("check")));
    const auto alignment = assistantContextField(f, "Text", number ? "AlignRight" : kind.strictlyEquals(QJSValue(QStringLiteral("icon"))) ? "AlignHCenter" : "AlignLeft");
    if (tableHas(f, cell, "columnAlignment")) assistantMemberWrite(f, cell, "columnAlignment", alignment);
    else if (tableHas(f, cell, "horizontalAlignment")) assistantMemberWrite(f, cell, "horizontalAlignment", alignment);
}
void ApplicationInfo::tableScheduleFitColumns() const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife");
    if (!tableAlive(f, life) || panelUsageTruth(panelUsageRead(f, life, "queued"))) return;
    assistantMemberWrite(f, life, "queued", QJSValue(true));
    const auto qt = panelUsageContextRead(f, "Qt"); panelUsageMemberCall(f, qt, "callLater", {tableCallback(f, 144, {life}, 0)});
}
QJSValue ApplicationInfo::tableColumnWidths() const {
    const auto f = panelUsageEngine(this); const auto fitted = panelUsageContextRead(f, "fittedWidths");
    if (panelUsageTruth(panelUsageContextRead(f, "equalColumns"))) return panelUsageContextRead(f, "columns");
    const auto length = panelUsageRead(f, fitted, "length");
    if (!consentFieldEquals(f, panelUsageContextRead(f, "columns"), "length", length)) return panelUsageContextRead(f, "columns");
    auto columns = panelUsageContextRead(f, "columns");
    const auto fits = panelUsageMemberCall(f, columns, "map", {tableCallback(f, 123, {}, 1)});
    const auto filtered = panelUsageMemberCall(f, fits, "filter", {panelUsageContextRead(f, "Boolean")});
    const auto fitting = panelUsageRead(f, filtered, "length");
    columns = panelUsageContextRead(f, "columns");
    const auto fixed = panelUsageMemberCall(f, columns, "reduce", {tableCallback(f, 124, {fits}, 3), QJSValue(0)});
    const auto texts = panelUsageMemberCall(f, fitted, "reduce", {tableCallback(f, 125, {fits}, 3), QJSValue(0)});
    const auto gaps = viewArithmetic(f, panelUsageRead(f, panelUsageContextRead(f, "columns"), "length"), QJSValue(1), 0);
    auto room = viewArithmetic(f, panelUsageContextRead(f, "width"), fixed, 0);
    auto sizes = assistantContextField(f, "EaStyle", "Sizes");
    room = viewArithmetic(f, room, viewArithmetic(f, panelUsageRead(f, sizes, "tableColumnSpacing"), gaps, 1), 0);
    sizes = assistantContextField(f, "EaStyle", "Sizes");
    room = viewArithmetic(f, room, viewArithmetic(f, panelUsageRead(f, sizes, "borderThickness"), QJSValue(2), 1), 0);
    room = viewArithmetic(f, room, viewArithmetic(f, panelUsageContextRead(f, "rowPadding"), QJSValue(2), 1), 0);
    QJSValue margin(0);
    if (assistantRelation(f, fitting, QJSValue(0), 1)) {
        const auto math = panelUsageContextRead(f, "Math"), inner = panelUsageContextRead(f, "Math");
        const auto padding = panelUsageContextRead(f, "autoColumnPadding");
        const auto delta = viewArithmetic(f, room, texts, 0);
        const auto least = panelUsageMemberCall(f, inner, "min", {padding, viewArithmetic(f, delta, fitting, 2)});
        margin = panelUsageMemberCall(f, math, "max", {QJSValue(0), least});
    }
    QJSValue scale(1);
    if (assistantRelation(f, texts, room, 1) && assistantRelation(f, texts, QJSValue(0), 1)) {
        const auto math = panelUsageContextRead(f, "Math");
        const auto maximum = panelUsageMemberCall(f, math, "max", {QJSValue(0), room}); scale = viewArithmetic(f, maximum, texts, 2);
    }
    QJSValue spread(0);
    if (assistantRelation(f, panelUsageRead(f, panelUsageContextRead(f, "spreadColumns"), "length"), QJSValue(0), 1)) {
        const auto math = panelUsageContextRead(f, "Math"); auto delta = viewArithmetic(f, room, texts, 0);
        delta = viewArithmetic(f, delta, viewArithmetic(f, margin, fitting, 1), 0);
        const auto maximum = panelUsageMemberCall(f, math, "max", {QJSValue(0), delta});
        spread = viewArithmetic(f, maximum, panelUsageRead(f, panelUsageContextRead(f, "spreadColumns"), "length"), 2);
    }
    columns = panelUsageContextRead(f, "columns");
    const auto widths = panelUsageMemberCall(f, columns, "map", {tableCallback(f, 126, {fits, fitted, scale, margin, spread}, 2)});
    if (assistantRelation(f, panelUsageContextRead(f, "fillerIndex"), QJSValue(0), 2)) {
        const auto used = panelUsageMemberCall(f, widths, "reduce", {tableCallback(f, 127, {}, 2), QJSValue(0)});
        const auto math = panelUsageContextRead(f, "Math"); auto spare = panelUsageContextRead(f, "width");
        sizes = assistantContextField(f, "EaStyle", "Sizes");
        spare = viewArithmetic(f, spare, viewArithmetic(f, panelUsageRead(f, sizes, "tableColumnSpacing"), gaps, 1), 0);
        sizes = assistantContextField(f, "EaStyle", "Sizes");
        spare = viewArithmetic(f, spare, viewArithmetic(f, panelUsageRead(f, sizes, "borderThickness"), QJSValue(2), 1), 0);
        spare = viewArithmetic(f, spare, viewArithmetic(f, panelUsageContextRead(f, "rowPadding"), QJSValue(2), 1), 0);
        spare = panelUsageMemberCall(f, math, "max", {QJSValue(0), viewArithmetic(f, spare, used, 0)});
        const auto index = panelUsageContextRead(f, "fillerIndex"), previous = textIndex(f, widths, index);
        const auto floor = panelUsageContextRead(f, "Math"); const auto rounded = panelUsageMemberCall(f, floor, "floor", {spare});
        textIndexWrite(f, widths, index, panelUsageAdd(f, previous, rounded));
    }
    return widths;
}
void ApplicationInfo::tableFitColumns() const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife"); if (!tableAlive(f, life)) return;
    QJSValue header;
    if (panelUsageTruth(panelUsageContextRead(f, "headerItem")) && panelUsageTruth(assistantContextField(f, "headerItem", "implicitColumnWidths"))) {
        const auto widths = assistantContextField(f, "headerItem", "implicitColumnWidths"); header = panelUsageMemberCall(f, widths, "filter", {tableCallback(f, 132, {}, 2)});
    } else if (panelUsageReady(f)) header = f->newArray();
    const auto headerCells = tableCellsOf(f, panelUsageContextRead(f, "headerItem"));
    const auto headerWidths = panelUsageTruth(headerCells) ? panelUsageMemberCall(f, headerCells, "map", {tableCallback(f, 133, {}, 2)}) : header;
    const auto widths = panelUsageMemberCall(f, panelUsageContextRead(f, "columns"), "map", {tableCallback(f, 134, {headerWidths}, 2)});
    QJSValue kinds = consentNull(); bool complete = true;
    panelUsageEach(f, assistantContextField(f, "contentItem", "children"), [&](const QJSValue& item) {
        if (!editorLife(f, life)) { complete = false; return false; }
        const auto cells = tableCellsOf(f, item);
        if (!panelUsageTruth(cells) || panelUsageRead(f, cells, "length").strictlyEquals(QJSValue(0)) || assistantSameName(f, item, "headerItem")) return panelUsageReady(f);
        if (!editorLife(f, life)) { complete = false; return false; }
        const auto first = textIndex(f, cells, QJSValue(0)); const auto parent = panelUsageRead(f, first, "parent");
        const auto owns = panelUsageGlobalCall(f, "columnRowOwner", {parent});
        if (!panelUsageTruth(projectCall(f, owns))) { complete = false; return false; }
        if (kinds.isNull() || kinds.isUndefined()) kinds = panelUsageMemberCall(f, cells, "map", {tableCallback(f, 135, {}, 1)});
        for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, cells, "length"), 0)
             && assistantRelation(f, QJSValue(index), panelUsageRead(f, widths, "length"), 0); ++index) {
            if (!panelUsageTruth(projectCall(f, owns))) { complete = false; return false; }
            if (index > 0 && panelUsageTruth(textIndex(f, kinds, QJSValue(index)))) panelUsageGlobalCall(f, "alignCell", {textIndex(f, cells, QJSValue(index)), textIndex(f, kinds, QJSValue(index))});
            if (!panelUsageTruth(projectCall(f, owns))) { complete = false; return false; }
            panelUsageGlobalCall(f, "padForFiller", {textIndex(f, cells, QJSValue(index)), QJSValue(index)});
            if (!panelUsageTruth(projectCall(f, owns))) { complete = false; return false; }
            const auto math = panelUsageContextRead(f, "Math"), previous = textIndex(f, widths, QJSValue(index)), inner = panelUsageContextRead(f, "Math");
            const auto measured = tableMeasure(f, textIndex(f, cells, QJSValue(index)));
            const auto filler = assistantSameName(f, QJSValue(index), "fillerIndex") ? panelUsageContextRead(f, "fillerWidth") : QJSValue(0);
            const auto rounded = panelUsageMemberCall(f, inner, "ceil", {viewArithmetic(f, measured, filler, 0)});
            textIndexWrite(f, widths, QJSValue(index), panelUsageMemberCall(f, math, "max", {previous, rounded}));
        }
        return panelUsageReady(f);
    });
    if (!complete || !panelUsageReady(f)) return;
    if (panelUsageTruth(kinds) && panelUsageTruth(headerCells) && panelUsageTruth(panelUsageRead(f, headerCells, "length"))) {
        const auto first = textIndex(f, headerCells, QJSValue(0)); const auto owns = panelUsageGlobalCall(f, "columnRowOwner", {panelUsageRead(f, first, "parent")});
        for (double index = 1; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, headerCells, "length"), 0)
             && assistantRelation(f, QJSValue(index), panelUsageRead(f, kinds, "length"), 0); ++index) {
            if (!panelUsageTruth(projectCall(f, owns))) return;
            panelUsageGlobalCall(f, "alignCell", {textIndex(f, headerCells, QJSValue(index)), textIndex(f, kinds, QJSValue(index))});
            if (!panelUsageTruth(projectCall(f, owns))) return;
            panelUsageGlobalCall(f, "padForFiller", {textIndex(f, headerCells, QJSValue(index)), QJSValue(index)});
        }
    }
    if (!editorLife(f, life)) return; panelUsageContextWrite(f, "refitting", QJSValue(false)); if (!editorLife(f, life)) return;
    auto json = panelUsageContextRead(f, "JSON"); const auto before = panelUsageMemberCall(f, json, "stringify", {widths});
    json = panelUsageContextRead(f, "JSON"); const auto after = panelUsageMemberCall(f, json, "stringify", {panelUsageContextRead(f, "fittedWidths")});
    if (!before.strictlyEquals(after)) panelUsageContextWrite(f, "fittedWidths", widths);
}
void ApplicationInfo::tableRefit() const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife"); if (!tableAlive(f, life)) return;
    panelUsageContextWrite(f, "refitting", QJSValue(true)); if (editorLife(f, life)) panelUsageGlobalCall(f, "scheduleFitColumns", {});
}
void ApplicationInfo::tableColumnsChanged(bool widthsChanged) const {
    const auto f = panelUsageEngine(this);
    if (!widthsChanged) {
        if (panelUsageTruth(assistantContextField(f, "table", "columnFitLife")) && panelUsageTruth(panelUsageRead(f, assistantContextField(f, "table", "columnFitLife"), "alive"))) projectInvoke(f, "table", "refit");
        return;
    }
    const auto life = assistantContextField(f, "table", "columnFitLife"); if (!tableAlive(f, life)) return;
    QJSValue spare(0);
    if (assistantRelation(f, panelUsageContextRead(f, "fillerIndex"), QJSValue(0), 2)) {
        const auto fitted = panelUsageRead(f, panelUsageContextRead(f, "fittedWidths"), "length");
        if (consentFieldEquals(f, panelUsageContextRead(f, "columns"), "length", fitted)) {
            const auto math = panelUsageContextRead(f, "Math"), columns = panelUsageContextRead(f, "columnWidths"), index = panelUsageContextRead(f, "fillerIndex");
            const auto first = textIndex(f, columns, index), previous = panelUsageContextRead(f, "fittedWidths"), actualIndex = panelUsageContextRead(f, "fillerIndex");
            auto room = viewArithmetic(f, first, tableNullish(textIndex(f, previous, actualIndex), QJSValue(0)), 0);
            room = viewArithmetic(f, room, panelUsageContextRead(f, "autoColumnPadding"), 0); spare = panelUsageMemberCall(f, math, "max", {QJSValue(0), room});
        }
    }
    if (!assistantSameName(f, spare, "fillerWidth")) { panelUsageContextWrite(f, "fillerWidth", spare); if (editorLife(f, life)) panelUsageGlobalCall(f, "scheduleFitColumns", {}); }
}
void ApplicationInfo::tableDestroyed() const {
    const auto f = panelUsageEngine(this); const auto life = panelUsageContextRead(f, "columnFitLife"); assistantMemberWrite(f, life, "alive", QJSValue(false));
    const auto owner = panelUsageContextRead(f, "table");
    // Destruction retires existing connections; it must not enable pending QML bindings.
    const auto stored = [&](const QJSValue& source, const char* name) -> QJSValue {
        if (!panelUsageReady(f)) return {};
        QV4::Scope scope(f.vm());
        QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), source));
        const auto* wrapper = value->as<QV4::QObjectWrapper>();
        const QPointer<QObject> object(wrapper ? wrapper->object() : nullptr);
        if (!object || QQmlData::wasDeleted(object.data())) return {};
        const QVariant result = object->property(name);
        f.checked();
        if (!panelUsageReady(f)) return {};
        return QJSValuePrivate::fromReturnedValue(f.vm()->fromVariant(result));
    };
    const auto owns = [&](const QJSValue& row) {
        return consentQtObject(f, row) && stored(row, "listView").strictlyEquals(owner)
            && panelUsageReady(f);
    };
    const auto literal = panelUsageLiteral(f, 1); panelUsageWrite(f, literal.value, "0", stored(owner, "headerItem"));
    const auto array = panelUsageContextRead(f, "Array"); QJSValue children;
    if (panelUsageTruth(stored(owner, "contentItem"))) children = stored(stored(owner, "contentItem"), "children"); else if (panelUsageReady(f)) children = f->newArray();
    const auto additional = panelUsageMemberCall(f, array, "from", {children}); uint index = 1;
    panelUsageEach(f, additional, [&](const QJSValue& row) { panelUsageWrite(f, literal.value, qPrintable(QString::number(index++)), row); return panelUsageReady(f); });
    const auto rows = panelUsageComplete(f, literal);
    panelUsageEach(f, rows, [&](const QJSValue& row) {
        if (!owns(row)) return panelUsageReady(f);
        const auto arrayAgain = panelUsageContextRead(f, "Array"); const auto data = stored(row, "data");
        if (!panelUsageReady(f)) return false;
        const auto source = data.isNull() || data.isUndefined() ? f->newArray() : data;
        const auto childrenAgain = panelUsageMemberCall(f, arrayAgain, "from", {source});
        return panelUsageEach(f, childrenAgain, [&](const QJSValue& child) {
            if (consentQtObject(f, child) && tableHas(f, child, "ignoreUnknownSignals") && tableHas(f, child, "target") && stored(child, "target").strictlyEquals(owner)) assistantMemberWrite(f, child, "enabled", QJSValue(false));
            return panelUsageReady(f);
        });
    });
    panelUsageEach(f, rows, [&](const QJSValue& row) { if (owns(row)) assistantMemberWrite(f, row, "listView", consentNull()); return panelUsageReady(f); });
}
QJSValue ApplicationInfo::tableTextWidth(int row, const QString& role) const {
    const auto f = panelUsageEngine(this); QJSValue text(QString{});
    auto model = panelUsageContextRead(f, "model"); const auto method = panelUsageRead(f, model, "text");
    if (tableTypeof(f, method).strictlyEquals(QJSValue(QStringLiteral("function")))) {
        model = panelUsageContextRead(f, "model"); text = panelUsageMemberCall(f, model, "text", {QJSValue(row), QJSValue(role)});
    } else {
        model = panelUsageContextRead(f, "model");
        if (tableTypeof(f, panelUsageRead(f, model, "get")).strictlyEquals(QJSValue(QStringLiteral("function")))) {
            model = panelUsageContextRead(f, "model"); const auto object = panelUsageMemberCall(f, model, "get", {QJSValue(row)});
            const auto value = tableNullish(textIndex(f, object, QJSValue(role)), QJSValue(QString{})); text = panelUsageGlobalCall(f, "String", {value});
        }
    }
    return projectInvoke(f, "metrics", "advanceWidth", {text});
}
QJSValue ApplicationInfo::tableAdvance(const QString& text) const { return projectInvoke(panelUsageEngine(this), "metrics", "advanceWidth", {QJSValue(text)}); }
QJSValue ApplicationInfo::tableTextColumnWidth(const QString& role, const QString& title, bool natural) const {
    const auto f = panelUsageEngine(this);
    if (!natural) {
        const auto math = panelUsageContextRead(f, "Math"); const auto needed = panelUsageGlobalCall(f, "naturalTextColumnWidth", {QJSValue(role), QJSValue(title)});
        const auto width = panelUsageContextRead(f, "width"), share = panelUsageContextRead(f, "maximumTextColumnShare");
        return panelUsageMemberCall(f, math, "min", {needed, viewArithmetic(f, width, share, 1)});
    }
    const auto revision = panelUsageContextRead(f, "modelRevision"); Q_UNUSED(revision);
    QJSValue widths = textIndex(f, panelUsageContextRead(f, "rowWidths"), QJSValue(role));
    bool replace = !panelUsageTruth(widths);
    if (!replace) { const auto length = panelUsageRead(f, widths, "length"); replace = !assistantSameName(f, length, "count"); }
    if (replace) {
        if (!panelUsageReady(f)) return {}; widths = f->newArray();
        for (double row = 0; panelUsageReady(f) && panelUsageTruth(panelUsageContextRead(f, "model"))
             && assistantRelation(f, QJSValue(row), panelUsageContextRead(f, "count"), 0); ++row) {
            const auto measured = panelUsageGlobalCall(f, "textWidth", {QJSValue(row), QJSValue(role)}); panelUsageMemberCall(f, widths, "push", {measured});
        }
        textIndexWrite(f, panelUsageContextRead(f, "rowWidths"), QJSValue(role), widths);
    }
    const auto callback = projectGuardedClosure(f, 142, 2); const auto titleWidth = projectInvoke(f, "metrics", "advanceWidth", {QJSValue(title)});
    const auto result = panelUsageMemberCall(f, widths, "reduce", {callback, titleWidth}); const auto math = panelUsageContextRead(f, "Math");
    const auto rounded = panelUsageMemberCall(f, math, "ceil", {result}); const auto spacing = assistantContextField(f, "AppSizes", "fieldSpacing");
    return panelUsageAdd(f, rounded, viewArithmetic(f, spacing, QJSValue(2), 1));
}
void ApplicationInfo::tableForgetWidths() const {
    const auto f = panelUsageEngine(this); const auto source = panelUsageContextRead(f, "rowWidths");
    tableForIn(f, source, [&](const QJSValue& role) { textIndexDelete(f, panelUsageContextRead(f, "rowWidths"), role); return panelUsageReady(f); });
}
void ApplicationInfo::tableRemeasure() const {
    const auto f = panelUsageEngine(this); panelUsageGlobalCall(f, "forgetWidths", {}); tableIncrement(f, "modelRevision");
}
void ApplicationInfo::tableDataChanged(const QJSValue& topLeft, const QJSValue& bottomRight) const {
    const auto f = panelUsageEngine(this); if (!tableAlive(f, panelUsageContextRead(f, "ownerLife"))) return;
    projectInvoke(f, "table", "refit"); if (!editorLife(f, panelUsageContextRead(f, "ownerLife"))) return;
    bool changed = false; const auto source = assistantContextField(f, "table", "rowWidths");
    tableForIn(f, source, [&](const QJSValue& role) {
        const auto widths = textIndex(f, assistantContextField(f, "table", "rowWidths"), role);
        for (QJSValue row = panelUsageRead(f, topLeft, "row"); panelUsageReady(f)
             && assistantRelation(f, row, panelUsageRead(f, bottomRight, "row"), 3)
             && assistantRelation(f, row, panelUsageRead(f, widths, "length"), 0);) {
            const auto measured = projectInvoke(f, "table", "textWidth", {row, role});
            if (!measured.strictlyEquals(textIndex(f, widths, row))) { textIndexWrite(f, widths, row, measured); changed = true; }
            const auto number = panelUsageNumber(f, row); if (!number) return false; row = QJSValue(*number + 1);
        }
        return panelUsageReady(f);
    });
    if (changed) tableIncrement(f, "modelRevision", true);
}
void ApplicationInfo::tableOwnerCallback(int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 3) { panelUsageContextWrite(f, "ownerLife", assistantContextField(f, "table", "columnFitLife")); return; }
    if (!tableAlive(f, panelUsageContextRead(f, "ownerLife"))) return;
    if (kind == 0) { projectInvoke(f, "table", "scheduleFitColumns"); return; }
    if (kind == 2) { projectInvoke(f, "table", "remeasure"); return; }
    QJSValue first = consentNull();
    if (panelUsageTruth(assistantContextField(f, "table", "headerItem"))) {
        auto header = assistantContextField(f, "table", "headerItem");
        if (panelUsageTruth(panelUsageRead(f, header, "contentRowData"))) {
            const auto array = panelUsageContextRead(f, "Array"); header = assistantContextField(f, "table", "headerItem");
            const auto cells = panelUsageMemberCall(f, array, "from", {panelUsageRead(f, header, "contentRowData")});
            first = panelUsageMemberCall(f, cells, "find", {projectGuardedClosure(f, 131, 1)});
        }
    }
    if (!editorLife(f, panelUsageContextRead(f, "ownerLife"))) return;
    if (panelUsageTruth(first) && panelUsageTruth(panelUsageRead(f, first, "parent"))) projectInvoke(f, "table", "applyWidths", {panelUsageRead(f, first, "parent")});
    if (editorLife(f, panelUsageContextRead(f, "ownerLife"))) projectInvoke(f, "table", "scheduleFitColumns");
}
bool ApplicationInfo::tableRevealRow(int index) const {
    const auto f = panelUsageEngine(this);
    if (index < 0 || assistantRelation(f, QJSValue(index), panelUsageContextRead(f, "count"), 2)) return false;
    const auto original = panelUsageContextRead(f, "sourceModel");
    panelUsageGlobalCall(f, "positionViewAtIndex", {QJSValue(index), assistantContextField(f, "ListView", "Contain")}); panelUsageGlobalCall(f, "forceLayout", {});
    const auto row = panelUsageGlobalCall(f, "itemAtIndex", {QJSValue(index)});
    if (!assistantSameName(f, original, "sourceModel") || row.isNull() || !consentFieldEquals(f, row, "index", QJSValue(index))) return false;
    const auto table = panelUsageContextRead(f, "table"); const auto point = panelUsageMemberCall(f, row, "mapToItem", {table, QJSValue(0), QJSValue(0)});
    const auto top = panelUsageRead(f, point, "y");
    const auto header = panelUsageTruth(panelUsageContextRead(f, "headerItem")) ? assistantContextField(f, "headerItem", "height") : QJSValue(0);
    if (assistantRelation(f, top, header, 0)) {
        const auto before = panelUsageContextRead(f, "contentY"); panelUsageContextWrite(f, "contentY", viewArithmetic(f, before, viewArithmetic(f, header, top, 0), 0));
    } else {
        const auto end = panelUsageAdd(f, top, panelUsageRead(f, row, "height"));
        if (assistantRelation(f, end, panelUsageContextRead(f, "height"), 1)) {
            const auto before = panelUsageContextRead(f, "contentY"), actual = panelUsageAdd(f, top, panelUsageRead(f, row, "height"));
            const auto delta = viewArithmetic(f, actual, panelUsageContextRead(f, "height"), 0); panelUsageContextWrite(f, "contentY", panelUsageAdd(f, before, delta));
        }
    }
    panelUsageGlobalCall(f, "forceLayout", {});
    if (!assistantSameName(f, original, "sourceModel")) return false;
    const auto actual = panelUsageGlobalCall(f, "itemAtIndex", {QJSValue(index)});
    return actual.strictlyEquals(row) && consentFieldEquals(f, row, "index", QJSValue(index));
}
bool ApplicationInfo::tableRevealItem(const QJSValue& item) const {
    const auto f = panelUsageEngine(this); if (item.isNull()) return false; QJSValue row = item;
    while (panelUsageReady(f) && !row.isNull()) {
        const auto parent = panelUsageRead(f, row, "parent"); if (assistantSameName(f, parent, "contentItem")) break; row = panelUsageRead(f, row, "parent");
    }
    if (row.isNull() || !tableHas(f, row, "index")) return false;
    const auto first = panelUsageGlobalCall(f, "itemAtIndex", {panelUsageRead(f, row, "index")}); if (!first.strictlyEquals(row)) return false;
    const auto index = panelUsageRead(f, row, "index"), model = panelUsageContextRead(f, "sourceModel");
    if (!panelUsageTruth(panelUsageGlobalCall(f, "revealRow", {index})) || !assistantSameName(f, model, "sourceModel")) return false;
    return panelUsageGlobalCall(f, "itemAtIndex", {index}).strictlyEquals(row);
}
void ApplicationInfo::tableKeyPressed(const QJSValue& event) const {
    const auto f = panelUsageEngine(this); auto key = panelUsageRead(f, event, "key");
    if (!key.strictlyEquals(assistantContextField(f, "Qt", "Key_Up"))) {
        key = panelUsageRead(f, event, "key"); if (!key.strictlyEquals(assistantContextField(f, "Qt", "Key_Down"))) return;
    }
    if (assistantContextField(f, "table", "count").strictlyEquals(QJSValue(0))) return;
    if (!panelUsageTruth(assistantContextField(f, "table", "selectable")) && !panelUsageTruth(assistantContextField(f, "table", "marksCurrentRow"))) return;
    const auto window = assistantContextField(f, "table", "Window"); const auto focused = panelUsageRead(f, window, "activeFocusItem");
    if (!focused.isNull() && tableHas(f, focused, "cursorPosition")) return;
    const auto from = assistantContextField(f, "table", "markerRow"), math = panelUsageContextRead(f, "Math"), inner = panelUsageContextRead(f, "Math");
    const auto last = viewArithmetic(f, assistantContextField(f, "table", "count"), QJSValue(1), 0); QJSValue proposed(0);
    if (!assistantRelation(f, from, QJSValue(0), 0)) {
        key = panelUsageRead(f, event, "key"); const bool down = key.strictlyEquals(assistantContextField(f, "Qt", "Key_Down")); proposed = panelUsageAdd(f, from, QJSValue(down ? 1 : -1));
    }
    const auto minimum = panelUsageMemberCall(f, inner, "min", {last, proposed}); const auto row = panelUsageMemberCall(f, math, "max", {QJSValue(0), minimum});
    projectWrite(f, "table", "currentIndex", row); projectInvoke(f, "table", "positionViewAtIndex", {row, assistantContextField(f, "ListView", "Contain")});
    if (panelUsageTruth(assistantContextField(f, "table", "selectable"))) projectInvoke(f, "table", "selectWithModifiers", {row, assistantContextField(f, "Qt", "NoModifier")});
    projectInvoke(f, "table", "rowActivated", {row}); assistantMemberWrite(f, event, "accepted", QJSValue(true));
}

namespace {
QJSValue controlProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    const auto unit = arg(0);
    if (operation == 160 || operation == 174) return panelUsageRead(f, unit, operation == 160 ? "visible" : "shown");
    if (operation == 161) {
        const auto width = panelUsageRead(f, unit, "width");
        return panelUsageAdd(f, width, panelUsageGlobalCall(f, "groupOf", {unit}));
    }
    if (operation == 162 || operation == 163) {
        const auto first = panelUsageAdd(f, arg(0), panelUsageRead(f, arg(1), "width"));
        QJSValue gap(0);
        if (assistantRelation(f, arg(2), QJSValue(0), 1)) {
            if (operation == 162) gap = saved(0);
            else {
                const auto previous = textIndex(f, saved(0), viewArithmetic(f, arg(2), QJSValue(1), 0));
                gap = panelUsageGlobalCall(f, "boxGap", {previous, arg(1)});
            }
        }
        return panelUsageAdd(f, first, gap);
    }
    if (operation == 164 || operation == 165) {
        const auto result = panelUsageGlobalCall(f, "isComboBox", {unit});
        return operation == 164 ? result : QJSValue(!panelUsageTruth(result));
    }
    if (operation == 166) {
        if (!assistantRelation(f, arg(1), QJSValue(0), 1)) return QJSValue(0);
        const auto previous = textIndex(f, saved(0), viewArithmetic(f, arg(1), QJSValue(1), 0));
        return panelUsageGlobalCall(f, "boxGap", {previous, unit});
    }
    if (operation == 167 || operation == 168) {
        if (assistantRelation(f, arg(1), QJSValue(0), 1)) return panelUsageContextRead(f, "spacing");
        if (operation == 167 && assistantRelation(f, panelUsageRead(f, saved(0), "length"), QJSValue(0), 1))
            return panelUsageContextRead(f, "groupSpacing");
        return QJSValue(0);
    }
    if (operation == 169) {
        const auto first = panelUsageAdd(f, arg(0), panelUsageRead(f, arg(1), "width"));
        const auto gaps = panelUsageRead(f, saved(0), "gaps");
        return panelUsageAdd(f, first, textIndex(f, gaps, arg(2)));
    }
    if (operation == 170) return QJSValue(panelUsageRead(f, unit, "elides").strictlyEquals(QJSValue(true)));
    if (operation == 171) {
        const auto method = tableTypeof(f, panelUsageRead(f, unit, "itemAt"));
        if (!method.strictlyEquals(QJSValue(QStringLiteral("function")))) return QJSValue(false);
        return QJSValue(tableTypeof(f, panelUsageRead(f, unit, "count")).strictlyEquals(QJSValue(QStringLiteral("number"))));
    }
    if (operation == 172 || operation == 173) return panelUsageRead(f, unit, operation == 172 ? "labelledWidth" : "compactWidth");
    if (operation == 175) return panelUsageRead(f, unit, "valueText");
    if (operation == 177) return projectInvoke(f, "ApplicationInfo", "scanColourTitle", {unit});
    if (operation == 176) return QJSValue(!unit.strictlyEquals(QJSValue(QStringLiteral(""))));
    return {};
}
QJSValue controlEmptyArray(const PanelUsageFrame& f) { return assistantGeometryArray(f, {}); }
QJSValue controlStylePixel(const PanelUsageFrame& f) {
    const auto style = panelUsageContextRead(f, "EaStyle");
    return panelUsageRead(f, panelUsageRead(f, style, "Sizes"), "fontPixelSize");
}
QJSValue controlMath(const PanelUsageFrame& f, const char* name, const QJSValueList& arguments) {
    return panelUsageMemberCall(f, panelUsageContextRead(f, "Math"), name, arguments);
}
QJSValue controlRow(const PanelUsageFrame& f, const QJSValue& units, const QJSValue& gaps) {
    auto row = panelUsageLiteral(f); panelUsageWrite(f, row.value, "units", units); panelUsageWrite(f, row.value, "gaps", gaps);
    return panelUsageComplete(f, row);
}
} // namespace

QJSValue ApplicationInfo::toolbarUnits() const {
    const auto f = panelUsageEngine(this); const auto array = tableArrayFrom(f, panelUsageContextRead(f, "children"));
    return panelUsageMemberCall(f, array, "filter", {projectGuardedClosure(f, 160, 1)});
}
QJSValue ApplicationInfo::toolbarMeasure() const {
    const auto f = panelUsageEngine(this); QJSValueList values;
    for (const char* name : {"centre", "leftEdge", "rightEdge"}) values.append(panelUsageContextRead(f, name));
    const auto prefix = assistantGeometryArray(f, values);
    const auto units = panelUsageContextRead(f, "units");
    const auto widths = panelUsageMemberCall(f, units, "map", {projectGuardedClosure(f, 161, 1)});
    const auto measured = panelUsageMemberCall(f, prefix, "concat", {widths});
    return panelUsageMemberCall(f, measured, "join", {QJSValue(QStringLiteral(","))});
}
QJSValue ApplicationInfo::toolbarIsComboBox(const QJSValue& unit) const {
    const auto f = panelUsageEngine(this); return QJSValue(!panelUsageRead(f, unit, "closedTexts").isUndefined());
}
QJSValue ApplicationInfo::toolbarGroupOf(const QJSValue& unit) const {
    const auto f = panelUsageEngine(this); return tableNullish(panelUsageRead(f, unit, "toolbarGroup"), QJSValue(QStringLiteral("")));
}
QJSValue ApplicationInfo::toolbarBoxGap(const QJSValue& before, const QJSValue& unit) const {
    const auto f = panelUsageEngine(this); const auto first = panelUsageGlobalCall(f, "groupOf", {before});
    const auto second = panelUsageGlobalCall(f, "groupOf", {unit});
    return panelUsageContextRead(f, first.strictlyEquals(second) ? "spacing" : "groupSpacing");
}
QJSValue ApplicationInfo::toolbarRowWidth(const QJSValue& row, const QJSValue& gap, bool boxes) const {
    const auto f = panelUsageEngine(this);
    return panelUsageMemberCall(f, row, "reduce", {tableCallback(f, boxes ? 163 : 162, {boxes ? row : gap}, 3), QJSValue(0)});
}
void ApplicationInfo::toolbarLayout() const {
    const auto f = panelUsageEngine(this);
    const auto boxes = panelUsageMemberCall(f, panelUsageContextRead(f, "units"), "filter", {tableCallback(f, 164, {}, 1)});
    const auto buttons = panelUsageMemberCall(f, panelUsageContextRead(f, "units"), "filter", {tableCallback(f, 165, {}, 1)});
    const auto right = panelUsageContextRead(f, "rightEdge"), left = panelUsageContextRead(f, "leftEdge");
    const auto room = viewArithmetic(f, right, left, 0); const auto rows = controlEmptyArray(f);
    const auto boxesWidth = panelUsageGlobalCall(f, "boxesWidth", {boxes});
    const auto buttonsWidth = panelUsageGlobalCall(f, "widthOf", {buttons, panelUsageContextRead(f, "spacing")});
    const auto first = panelUsageAdd(f, boxesWidth, buttonsWidth);
    QJSValue gap(0);
    if (assistantRelation(f, panelUsageRead(f, boxes, "length"), QJSValue(0), 1)
        && assistantRelation(f, panelUsageRead(f, buttons, "length"), QJSValue(0), 1)) gap = panelUsageContextRead(f, "groupSpacing");
    const auto together = panelUsageAdd(f, first, gap);
    if (assistantRelation(f, together, room, 3)) {
        const auto units = panelUsageMemberCall(f, boxes, "concat", {buttons});
        const auto boxGaps = panelUsageMemberCall(f, boxes, "map", {tableCallback(f, 166, {boxes}, 2)});
        const auto buttonGaps = panelUsageMemberCall(f, buttons, "map", {tableCallback(f, 167, {boxes}, 2)});
        const auto gaps = panelUsageMemberCall(f, boxGaps, "concat", {buttonGaps});
        panelUsageMemberCall(f, rows, "push", {controlRow(f, units, gaps)});
    } else {
        QJSValue row = consentNull();
        panelUsageEach(f, boxes, [&](const QJSValue& box) {
            bool newRow = row.isNull();
            if (!newRow) {
                const auto units = panelUsageRead(f, row, "units");
                const auto extended = panelUsageMemberCall(f, units, "concat", {assistantGeometryArray(f, {box})});
                newRow = assistantRelation(f, panelUsageGlobalCall(f, "boxesWidth", {extended}), room, 1);
            }
            if (newRow) {
                const auto units = controlEmptyArray(f), gaps = controlEmptyArray(f); row = controlRow(f, units, gaps);
                panelUsageMemberCall(f, rows, "push", {row});
            }
            const auto gaps = panelUsageRead(f, row, "gaps"); QJSValue before(0);
            if (assistantRelation(f, panelUsageRead(f, panelUsageRead(f, row, "units"), "length"), QJSValue(0), 1)) {
                const auto units = panelUsageRead(f, row, "units");
                const auto length = panelUsageRead(f, panelUsageRead(f, row, "units"), "length");
                before = panelUsageGlobalCall(f, "boxGap", {textIndex(f, units, viewArithmetic(f, length, QJSValue(1), 0)), box});
            }
            panelUsageMemberCall(f, gaps, "push", {before});
            panelUsageMemberCall(f, panelUsageRead(f, row, "units"), "push", {box});
            return panelUsageReady(f);
        });
        if (assistantRelation(f, panelUsageRead(f, buttons, "length"), QJSValue(0), 1)) {
            const auto gaps = panelUsageMemberCall(f, buttons, "map", {tableCallback(f, 168, {}, 2)});
            panelUsageMemberCall(f, rows, "push", {controlRow(f, buttons, gaps)});
        }
    }
    QJSValue top(0);
    panelUsageEach(f, rows, [&](const QJSValue& each) {
        const auto widthNow = panelUsageMemberCall(f, panelUsageRead(f, each, "units"), "reduce", {tableCallback(f, 169, {each}, 3), QJSValue(0)});
        const auto rounding = panelUsageContextRead(f, "Math");
        const auto maximizing = panelUsageContextRead(f, "Math");
        const auto leftEdge = panelUsageContextRead(f, "leftEdge");
        const auto minimizing = panelUsageContextRead(f, "Math");
        const auto end = viewArithmetic(f, panelUsageContextRead(f, "rightEdge"), widthNow, 0);
        const auto middle = viewArithmetic(f, panelUsageContextRead(f, "centre"), viewArithmetic(f, widthNow, QJSValue(2), 2), 0);
        const auto minimum = panelUsageMemberCall(f, minimizing, "min", {end, middle});
        const auto maximum = panelUsageMemberCall(f, maximizing, "max", {leftEdge, minimum});
        auto x = panelUsageMemberCall(f, rounding, "round", {maximum});
        for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, panelUsageRead(f, each, "units"), "length"), 0); ++i) {
            x = panelUsageAdd(f, x, textIndex(f, panelUsageRead(f, each, "gaps"), QJSValue(i)));
            assistantMemberWrite(f, textIndex(f, panelUsageRead(f, each, "units"), QJSValue(i)), "x", x);
            assistantMemberWrite(f, textIndex(f, panelUsageRead(f, each, "units"), QJSValue(i)), "y", top);
            x = panelUsageAdd(f, x, panelUsageRead(f, textIndex(f, panelUsageRead(f, each, "units"), QJSValue(i)), "width"));
        }
        const auto control = assistantContextField(f, "AppSizes", "toolbarControlSize");
        const auto spacing = assistantContextField(f, "AppSizes", "toolbarSpacing");
        top = panelUsageAdd(f, top, panelUsageAdd(f, control, spacing)); return panelUsageReady(f);
    });
    panelUsageContextWrite(f, "lineCount", panelUsageRead(f, rows, "length"));
    const auto height = viewArithmetic(f, top, assistantContextField(f, "AppSizes", "toolbarSpacing"), 0);
    panelUsageContextWrite(f, "implicitHeight", controlMath(f, "max", {QJSValue(0), height}));
}
QJSValue ApplicationInfo::iconElidedIndex() const {
    const auto f = panelUsageEngine(this); const auto segments = panelUsageContextRead(f, "segments");
    const auto marked = panelUsageMemberCall(f, segments, "findIndex", {projectGuardedClosure(f, 170, 1)});
    return assistantRelation(f, marked, QJSValue(0), 2) ? marked : viewArithmetic(f, panelUsageRead(f, panelUsageContextRead(f, "segments"), "length"), QJSValue(1), 0);
}
QJSValue ApplicationInfo::iconNaturalWidth(const QJSValue& segment, const QJSValue& piece) const {
    const auto f = panelUsageEngine(this); const auto fixed = panelUsageGlobalCall(f, "fixedWidth", {segment});
    return !fixed.isUndefined() ? fixed : panelUsageRead(f, piece, "implicitWidth");
}
QJSValue ApplicationInfo::iconFixedWidth(const QJSValue& segment) const {
    const auto f = panelUsageEngine(this);
    const auto mark = panelUsageTruth(segment) ? tableNullish(panelUsageRead(f, segment, "mark"), QJSValue(QStringLiteral(""))) : QJSValue(QStringLiteral(""));
    if (panelUsageTruth(segment) && panelUsageTruth(panelUsageRead(f, segment, "slot"))) return viewArithmetic(f, panelUsageContextRead(f, "pixelSize"), QJSValue(1.15), 1);
    if (mark.strictlyEquals(QJSValue(QStringLiteral("dash")))) return viewArithmetic(f, panelUsageContextRead(f, "pixelSize"), QJSValue(1.2), 1);
    if (!mark.strictlyEquals(QJSValue(QStringLiteral("")))) return viewArithmetic(f, panelUsageContextRead(f, "pixelSize"), QJSValue(0.6), 1);
    return {};
}
QJSValue ApplicationInfo::iconOtherWidth() const {
    const auto f = panelUsageEngine(this); QJSValue width(0);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), assistantContextField(f, "pieces", "count"), 0); ++i) {
        const auto piece = projectInvoke(f, "pieces", "itemAt", {QJSValue(i)});
        if (!QJSValue(i).strictlyEquals(panelUsageContextRead(f, "elidedIndex"))) {
            QJSValue extra(0);
            if (panelUsageTruth(piece)) {
                const auto segments = panelUsageContextRead(f, "segments");
                const auto natural = projectInvoke(f, "line", "naturalWidth", {textIndex(f, segments, QJSValue(i)), piece});
                extra = panelUsageAdd(f, natural, panelUsageContextRead(f, "spacing"));
            }
            width = panelUsageAdd(f, width, extra);
        }
    }
    return width;
}
QJSValue ApplicationInfo::sidebarIsOpen(const QJSValue& key, const QJSValue& group) const {
    const auto f = panelUsageEngine(this);
    if (!textIndex(f, panelUsageContextRead(f, "openStates"), key).isUndefined())
        return QJSValue(textIndex(f, panelUsageContextRead(f, "openStates"), key).strictlyEquals(QJSValue(true)));
    return panelUsageGlobalCall(f, "defaultOpen", {group});
}
void ApplicationInfo::sidebarSetOpen(const QJSValue& key, const QJSValue& open, const QJSValue& group) const {
    const auto f = panelUsageEngine(this);
    if (textIndex(f, panelUsageContextRead(f, "openStates"), key).isUndefined() && !group.isUndefined()
        && open.strictlyEquals(panelUsageGlobalCall(f, "defaultOpen", {group}))) return;
    textIndexWrite(f, panelUsageContextRead(f, "openStates"), key, open);
}
QJSValue ApplicationInfo::sidebarEdge(const QJSValue& group, bool last) const {
    const auto f = panelUsageEngine(this); const auto shown = panelUsageGlobalCall(f, "shownGroups", {group});
    if (!assistantRelation(f, panelUsageRead(f, shown, "length"), QJSValue(0), 1)) return QJSValue(false);
    const auto index = last ? viewArithmetic(f, panelUsageRead(f, shown, "length"), QJSValue(1), 0) : QJSValue(0);
    return QJSValue(textIndex(f, shown, index).strictlyEquals(group));
}
QJSValue ApplicationInfo::sidebarOrderedChildren(const QJSValue& parent) const {
    const auto f = panelUsageEngine(this); const auto children = controlEmptyArray(f);
    for (double i = 0; panelUsageReady(f) && panelUsageTruth(parent)
        && assistantRelation(f, QJSValue(i), panelUsageRead(f, panelUsageRead(f, parent, "children"), "length"), 0); ++i)
        panelUsageMemberCall(f, children, "push", {textIndex(f, panelUsageRead(f, parent, "children"), QJSValue(i))});
    const auto repeaters = panelUsageMemberCall(f, children, "filter", {projectGuardedClosure(f, 171, 1)});
    const auto repeated = controlEmptyArray(f);
    panelUsageEach(f, repeaters, [&](const QJSValue& repeater) {
        for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, repeater, "count"), 0); ++i)
            panelUsageMemberCall(f, repeated, "push", {panelUsageMemberCall(f, repeater, "itemAt", {QJSValue(i)})});
        return panelUsageReady(f);
    });
    const auto ordered = controlEmptyArray(f);
    panelUsageEach(f, children, [&](const QJSValue& child) {
        if (panelUsageTruth(panelUsageMemberCall(f, repeaters, "includes", {child}))) {
            for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, child, "count"), 0); ++i) {
                if (!panelUsageMemberCall(f, child, "itemAt", {QJSValue(i)}).isNull())
                    panelUsageMemberCall(f, ordered, "push", {panelUsageMemberCall(f, child, "itemAt", {QJSValue(i)})});
            }
        } else if (!panelUsageTruth(panelUsageMemberCall(f, repeated, "includes", {child}))) panelUsageMemberCall(f, ordered, "push", {child});
        return panelUsageReady(f);
    });
    return ordered;
}
QJSValue ApplicationInfo::sidebarShownGroups(const QJSValue& group) const {
    const auto f = panelUsageEngine(this);
    const auto siblings = panelUsageGlobalCall(f, "orderedChildren", {panelUsageTruth(group) ? panelUsageRead(f, group, "parent") : consentNull()});
    const auto shown = controlEmptyArray(f);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, siblings, "length"), 0); ++i) {
        const auto sibling = textIndex(f, siblings, QJSValue(i));
        if (!tableTypeof(f, panelUsageRead(f, sibling, "collapsible")).strictlyEquals(QJSValue(QStringLiteral("undefined")))
            && (tableTypeof(f, panelUsageRead(f, sibling, "listed")).strictlyEquals(QJSValue(QStringLiteral("undefined")))
                || panelUsageTruth(panelUsageRead(f, sibling, "listed")))) panelUsageMemberCall(f, shown, "push", {sibling});
    }
    return shown;
}
QJSValue ApplicationInfo::statusKeysFit() const {
    const auto f = panelUsageEngine(this); QJSValue width(0); double shown = 0;
    panelUsageEach(f, panelUsageContextRead(f, "items"), [&](const QJSValue& item) {
        if (panelUsageTruth(panelUsageRead(f, item, "shown"))) { width = panelUsageAdd(f, width, panelUsageRead(f, item, "labelledWidth")); ++shown; }
        return panelUsageReady(f);
    });
    const auto spacing = viewArithmetic(f, controlStylePixel(f), QJSValue(1.2), 1); QJSValue fitWidth(0);
    if (panelUsageTruth(assistantContextField(f, "fitArea", "visible"))) fitWidth = panelUsageAdd(f, assistantContextField(f, "fitArea", "labelledWidth"), spacing);
    else if (panelUsageTruth(assistantContextField(f, "openingProgress", "visible"))) fitWidth = panelUsageAdd(f, assistantContextField(f, "openingProgress", "width"), spacing);
    const auto spaces = viewArithmetic(f, controlMath(f, "max", {QJSValue(0), QJSValue(shown - 1)}), spacing, 1);
    const auto first = panelUsageAdd(f, panelUsageAdd(f, width, spaces), fitWidth); QJSValue assistantWidth(0);
    if (panelUsageTruth(assistantContextField(f, "assistantGroup", "visible"))) assistantWidth = panelUsageAdd(f, assistantContextField(f, "assistantGroup", "width"), spacing);
    const auto total = panelUsageAdd(f, first, assistantWidth);
    const auto barWidth = assistantContextField(f, "bar", "width");
    const auto margin = viewArithmetic(f, QJSValue(2), controlStylePixel(f), 1);
    return QJSValue(assistantRelation(f, total, viewArithmetic(f, barWidth, margin, 0), 3));
}
QJSValue ApplicationInfo::statusRoomFor() const {
    const auto f = panelUsageEngine(this); const auto spacing = viewArithmetic(f, controlStylePixel(f), QJSValue(1.2), 1);
    const auto barWidth = assistantContextField(f, "bar", "width");
    const auto margin = viewArithmetic(f, QJSValue(2), controlStylePixel(f), 1); auto available = viewArithmetic(f, barWidth, margin, 0);
    QJSValue assistantWidth(0);
    if (panelUsageTruth(assistantContextField(f, "assistantGroup", "visible"))) assistantWidth = panelUsageAdd(f, assistantContextField(f, "assistantGroup", "width"), spacing);
    available = viewArithmetic(f, available, assistantWidth, 0); QJSValue fitWidth(0);
    if (panelUsageTruth(assistantContextField(f, "fitArea", "visible"))) fitWidth = panelUsageAdd(f, assistantContextField(f, "fitArea", "compactWidth"), spacing);
    else if (panelUsageTruth(assistantContextField(f, "openingProgress", "visible"))) fitWidth = panelUsageAdd(f, assistantContextField(f, "openingProgress", "width"), spacing);
    available = viewArithmetic(f, available, fitWidth, 0); QJSValue width(0);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, panelUsageContextRead(f, "items"), "length"), 0); ++i) {
        if (!panelUsageTruth(panelUsageRead(f, textIndex(f, panelUsageContextRead(f, "items"), QJSValue(i)), "shown"))) continue;
        const auto gap = assistantRelation(f, width, QJSValue(0), 1) ? spacing : QJSValue(0);
        const auto measured = panelUsageRead(f, textIndex(f, panelUsageContextRead(f, "items"), QJSValue(i)), "compactWidth");
        width = panelUsageAdd(f, width, panelUsageAdd(f, gap, measured));
        if (assistantRelation(f, width, available, 1)) return QJSValue(i);
    }
    return panelUsageRead(f, panelUsageContextRead(f, "items"), "length");
}
QJSValue ApplicationInfo::statusMeasuredWidth(bool compact) const {
    const auto f = panelUsageEngine(this);
    return panelUsageGlobalCall(f, "widthWith", {projectGuardedClosure(f, compact ? 173 : 172, 1)});
}
QJSValue ApplicationInfo::statusWidthWith(const QJSValue& itemWidth, bool buttons) const {
    const auto f = panelUsageEngine(this); QJSValue width = buttons ? QJSValue(0) : assistantContextField(f, "rule", "width");
    double shown = buttons ? 0 : 1;
    panelUsageEach(f, panelUsageContextRead(f, buttons ? "buttons" : "items"), [&](const QJSValue& item) {
        if (panelUsageTruth(panelUsageRead(f, item, "shown"))) {
            width = panelUsageAdd(f, width, projectCall(f, itemWidth, {item})); ++shown;
        }
        return panelUsageReady(f);
    });
    if (!buttons) {
        const auto showing = panelUsageContextRead(f, "showing"), progress = panelUsageContextRead(f, "progress");
        panelUsageEach(f, assistantGeometryArray(f, {showing, progress}), [&](const QJSValue& extra) {
            if (panelUsageTruth(panelUsageRead(f, extra, "visible"))) { width = panelUsageAdd(f, width, panelUsageRead(f, extra, "width")); ++shown; }
            return panelUsageReady(f);
        });
        if (panelUsageTruth(assistantContextField(f, "fitButtons", "visible"))) {
            width = panelUsageAdd(f, width, projectInvoke(f, "fitButtons", "widthWith", {itemWidth})); ++shown;
        }
    }
    const auto count = buttons ? controlMath(f, "max", {QJSValue(0), QJSValue(shown - 1)}) : QJSValue(shown - 1);
    const auto spaces = viewArithmetic(f, count, panelUsageContextRead(f, "spacing"), 1);
    return panelUsageAdd(f, width, spaces);
}
QJSValue ApplicationInfo::statusFitValues() const {
    const auto f = panelUsageEngine(this); const auto items = assistantContextField(f, "fitArea", "items");
    const auto tail = panelUsageMemberCall(f, items, "slice", {QJSValue(1)});
    const auto shown = panelUsageMemberCall(f, tail, "filter", {projectGuardedClosure(f, 174, 1)});
    const auto values = panelUsageMemberCall(f, shown, "map", {projectGuardedClosure(f, 175, 1)});
    return panelUsageMemberCall(f, values, "join", {QJSValue(QStringLiteral(" "))});
}
QJSValue ApplicationInfo::statusProgressText() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "fitArea", "scanning"))) return panelUsageRead(f, assistantContextField(f, "bar", "fit"), "scanText");
    const auto fitting = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("StatusBar", "fitting")))}); QJSValue iterations(QStringLiteral(""));
    if (panelUsageTruth(assistantContextField(f, "bar", "fit"))
        && !panelUsageRead(f, assistantContextField(f, "bar", "fit"), "iterations").strictlyEquals(QJSValue(QStringLiteral("")))) {
        const auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("StatusBar", "it %1")))});
        iterations = panelUsageMemberCall(f, format, "arg", {panelUsageRead(f, assistantContextField(f, "bar", "fit"), "iterations")});
    }
    const auto texts = assistantGeometryArray(f, {fitting, iterations});
    const auto parts = panelUsageMemberCall(f, texts, "filter", {projectGuardedClosure(f, 176, 1)});
    return panelUsageMemberCall(f, parts, "join", {assistantContextField(f, "FitOutcomes", "separator")});
}
QJSValue ApplicationInfo::colourMapTitles() const {
    const auto f = panelUsageEngine(this);
    return panelUsageMemberCall(f, panelUsageContextRead(f, "maps"), "map", {projectGuardedClosure(f, 177, 1)});
}

namespace {
QJSValue preferenceText(const PanelUsageFrame& f, const char* text) {
    return panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(text))});
}
} // namespace
void ApplicationInfo::preferencesClosed() const {
    const auto f = panelUsageEngine(this); projectWrite(f, "Preferences", "dialogShown", QJSValue(false));
    const auto intent = assistantContextField(f, "sourcesFolder", "selection");
    if (panelUsageTruth(intent)) {
        projectWrite(f, "sourcesFolder", "selection", consentNull());
        if (consentQtObject(f, panelUsageRead(f, intent, "owner"))) {
            const auto owner = panelUsageRead(f, intent, "owner");
            panelUsageMemberCall(f, owner, "cancelSkillSourceSelection", {panelUsageRead(f, intent, "id")});
        }
        if (consentQtObject(f, panelUsageContextRead(f, "sourcesFolder")) && assistantContextField(f, "sourcesFolder", "selection").isNull())
            projectInvoke(f, "sourcesFolder", "reject");
    }
}
void ApplicationInfo::preferenceAssistantChanged() const {
    const auto f = panelUsageEngine(this); panelUsageContextWrite(f, "copyError", QJSValue(QStringLiteral("")));
    if (panelUsageTruth(panelUsageContextRead(f, "copyWorkReport"))) projectWrite(f, "copyWorkReport", "copied", QJSValue(false));
    if (panelUsageTruth(panelUsageContextRead(f, "copyConnection"))) projectWrite(f, "copyConnection", "copied", QJSValue(false));
}
void ApplicationInfo::preferenceCopyDiagnostics(const QJSValue& button, const QJSValue& report) const {
    const auto f = panelUsageEngine(this); const auto page = panelUsageContextRead(f, "aiPage");
    const auto owner = assistantContextField(f, "Session", "assistant"), project = assistantContextField(f, "Session", "project");
    if (!panelUsageReady(f)) return;
    const auto current = [&] {
        return consentQtObject(f, page) && consentQtObject(f, button) && consentQtObject(f, owner)
            && assistantContextField(f, "Session", "assistant").strictlyEquals(owner) && consentFieldEquals(f, page, "original", owner)
            && assistantContextField(f, "Session", "project").strictlyEquals(project);
    };
    const auto body = [&] {
        if (!current()) return;
        assistantMemberWrite(f, page, "copyError", QJSValue(QStringLiteral(""))); QJSValue literal;
        if (panelUsageTruth(report)) literal = panelUsageMemberCall(f, owner, "workReportDocument");
        else {
            const auto json = panelUsageContextRead(f, "JSON"); auto details = panelUsageLiteral(f);
            for (const auto& field : {std::pair{"connection", "connectionLabel"}, {"state", "state"}, {"account", "account"},
                     {"model", "selectedModel"}, {"effort", "selectedEffort"}, {"error", "lastError"}, {"context", "contextPreview"}})
                panelUsageWrite(f, details.value, field.first, panelUsageRead(f, owner, field.second));
            literal = panelUsageMemberCall(f, json, "stringify", {panelUsageComplete(f, details), consentNull(), QJSValue(2)});
        }
        if (!current()) return;
        if (!literal.isString() || !panelUsageTruth(panelUsageRead(f, literal, "length"))) {
            assistantMemberWrite(f, page, "copyError", preferenceText(f, QT_TRANSLATE_NOOP("AppPreferencesDialog", "No report is available to copy yet."))); return;
        }
        projectInvoke(f, "ApplicationInfo", "copyText", {literal});
        if (!current()) return;
        assistantMemberWrite(f, button, "copied", QJSValue(true));
        projectInvoke(f, panelUsageTruth(report) ? "reportCopyFeedback" : "connectionCopyFeedback", "restart");
    };
    body();
    // This is the original explicit catch: discard only its caught exception,
    // then allow a failing currentness check or recovery write to propagate.
    if (f && f.vm()->hasException) {
        f.vm()->catchException();
        if (current()) {
            assistantMemberWrite(f, button, "copied", QJSValue(false));
            assistantMemberWrite(f, page, "copyError", preferenceText(f, QT_TRANSLATE_NOOP("AppPreferencesDialog", "The details could not be copied. Try again.")));
        }
    }
}
void ApplicationInfo::preferenceSourceRevision() const { const auto f = panelUsageEngine(this); tableIncrement(f, "presentation"); }
void ApplicationInfo::preferenceSourceGesture(bool remove, bool pressed) const {
    const auto f = panelUsageEngine(this);
    if (pressed) {
        auto gesture = panelUsageLiteral(f);
        panelUsageWrite(f, gesture.value, "owner", assistantContextField(f, "sourceRow", "original"));
        panelUsageWrite(f, gesture.value, "id", assistantContextField(f, "sourceRow", "sourceId"));
        panelUsageWrite(f, gesture.value, "revision", panelUsageRead(f, assistantContextField(f, "sourceRow", "original"), "skillSourceRevision"));
        panelUsageWrite(f, gesture.value, "presentation", assistantContextField(f, "sourceRow", "presentation"));
        if (!remove) panelUsageWrite(f, gesture.value, "enabled", QJSValue(!panelUsageTruth(panelUsageRead(f, assistantContextField(f, "sourceRow", "model"), "enabled"))));
        panelUsageContextWrite(f, "gesture", panelUsageComplete(f, gesture)); return;
    }
    const auto original = panelUsageContextRead(f, "gesture"); panelUsageContextWrite(f, "gesture", consentNull());
    if (!panelUsageTruth(original) || !consentQtObject(f, panelUsageRead(f, original, "owner"))
        || !panelUsageRead(f, original, "owner").strictlyEquals(assistantContextField(f, "aiPage", "original"))
        || !panelUsageRead(f, original, "id").strictlyEquals(assistantContextField(f, "sourceRow", "sourceId"))
        || !panelUsageRead(f, original, "presentation").strictlyEquals(assistantContextField(f, "sourceRow", "presentation"))) return;
    if (!remove && !panelUsageRead(f, original, "enabled").strictlyEquals(QJSValue(!panelUsageTruth(panelUsageRead(f, assistantContextField(f, "sourceRow", "model"), "enabled"))))) return;
    const auto owner = panelUsageRead(f, original, "owner"), id = panelUsageRead(f, original, "id");
    if (remove) panelUsageMemberCall(f, owner, "removeSkillSource", {id, panelUsageRead(f, original, "revision")});
    else {
        const auto enabled = panelUsageRead(f, original, "enabled"), revision = panelUsageRead(f, original, "revision");
        panelUsageMemberCall(f, owner, "setSkillSourceEnabled", {id, enabled, revision});
    }
}
void ApplicationInfo::preferenceBeginSourceSelection(bool web) const {
    const auto f = panelUsageEngine(this); const auto original = assistantContextField(f, "Session", "assistant");
    if (web && panelUsageTruth(panelUsageRead(f, original, "skillSourceImporting"))) { panelUsageMemberCall(f, original, "cancelWebSkillSourceImport"); return; }
    const auto token = panelUsageMemberCall(f, original, "beginSkillSourceSelection");
    bool refused = !consentQtObject(f, original);
    if (!refused) {
        if (web) refused = !assistantContextField(f, "Session", "assistant").strictlyEquals(original);
        else refused = !original.strictlyEquals(assistantContextField(f, "Session", "assistant"));
    }
    if (!refused) refused = !panelUsageTruth(panelUsageRead(f, token, "length"));
    if (!refused) refused = web ? !assistantContextField(f, "webSource", "selection").isNull() : panelUsageTruth(panelUsageRead(f, assistantContextField(f, "sourcesFolder", "intent"), "length"));
    if (refused) { if (consentQtObject(f, original)) panelUsageMemberCall(f, original, "cancelSkillSourceSelection", {token}); return; }
    auto record = panelUsageLiteral(f); panelUsageWrite(f, record.value, "owner", original); panelUsageWrite(f, record.value, "id", token);
    const auto intent = panelUsageComplete(f, record); projectWrite(f, web ? "webSource" : "sourcesFolder", "selection", intent);
    if (web) projectInvoke(f, "webSource", "open");
    else if (consentQtObject(f, panelUsageContextRead(f, "sourcesFolder")) && assistantContextField(f, "sourcesFolder", "selection").strictlyEquals(intent)) projectInvoke(f, "sourcesFolder", "open");
    else if (consentQtObject(f, original)) panelUsageMemberCall(f, original, "cancelSkillSourceSelection", {token});
}
void ApplicationInfo::preferenceCompleteSourceSelection(bool web, bool accepted) const {
    const auto f = panelUsageEngine(this); const auto target = panelUsageContextRead(f, "original"), token = panelUsageContextRead(f, "intent"); QJSValue value;
    if (accepted) value = web ? assistantContextField(f, "sourceUrl", "text") : panelUsageContextRead(f, "selectedFolder");
    panelUsageContextWrite(f, "selection", consentNull());
    if (consentQtObject(f, target)) {
        if (accepted) panelUsageMemberCall(f, target, web ? "addWebSkillSource" : "addSkillSource", {token, value});
        else panelUsageMemberCall(f, target, "cancelSkillSourceSelection", {token});
    }
}
void ApplicationInfo::preferenceRetireSourceSelection(const QJSValue& token, bool web) const {
    const auto f = panelUsageEngine(this); const char* dialog = web ? "webSource" : "sourcesFolder";
    if (!assistantContextField(f, dialog, "intent").strictlyEquals(token)) return;
    projectWrite(f, dialog, "selection", consentNull());
    if (web || (consentQtObject(f, panelUsageContextRead(f, "sourcesFolder")) && assistantContextField(f, "sourcesFolder", "selection").isNull()))
        projectInvoke(f, dialog, "reject");
}
QJSValue ApplicationInfo::preferenceColourTitles() const {
    const auto f = panelUsageEngine(this);
    return panelUsageMemberCall(f, panelUsageContextRead(f, "choices"), "map", {projectGuardedClosure(f, 177, 1)});
}
QJSValue ApplicationInfo::preferenceStackedChoices() const {
    const auto f = panelUsageEngine(this); const auto array = panelUsageContextRead(f, "Array");
    const auto schemes = panelUsageMemberCall(f, array, "from", {assistantContextField(f, "ApplicationInfo", "colourSchemes")});
    const auto second = panelUsageContextRead(f, "Array");
    const auto maps = panelUsageMemberCall(f, second, "from", {assistantContextField(f, "ApplicationInfo", "scanColourMaps")});
    return panelUsageMemberCall(f, schemes, "concat", {maps});
}
QJSValue ApplicationInfo::preferenceEngineThreads() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "ApplicationInfo", "engineThreadsSelectable")))
        return assistantGeometryArray(f, {preferenceText(f, QT_TRANSLATE_NOOP("AppPreferencesDialog", "1 (single-thread build)"))});
    const auto counts = assistantGeometryArray(f, {preferenceText(f, QT_TRANSLATE_NOOP("AppPreferencesDialog", "Auto"))});
    for (double count = 1; panelUsageReady(f) && assistantRelation(f, QJSValue(count), assistantContextField(f, "ApplicationInfo", "engineThreadsMaximum"), 3); ++count)
        panelUsageMemberCall(f, counts, "push", {panelUsageGlobalCall(f, "String", {QJSValue(count)})});
    return counts;
}
void ApplicationInfo::preferenceActivated(const QJSValue& index, int setting) const {
    const auto f = panelUsageEngine(this);
    if (setting == 0) {
        const auto colors = panelUsageRead(f, panelUsageContextRead(f, "EaStyle"), "Colors");
        const char* name = index.strictlyEquals(QJSValue(1)) ? "DarkTheme" : index.strictlyEquals(QJSValue(2)) ? "SystemTheme" : "LightTheme";
        const auto selected = panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "EaStyle"), "Colors"), name);
        assistantMemberWrite(f, colors, "theme", selected); return;
    }
    if (setting == 9) {
        if (panelUsageTruth(assistantContextField(f, "ApplicationInfo", "engineThreadsSelectable")))
            projectWrite(f, "Preferences", "engineThreads", index);
        return;
    }
    const auto preferences = panelUsageContextRead(f, "Preferences");
    if (setting == 6 || setting == 7 || setting == 8) {
        const bool alternate = index.strictlyEquals(QJSValue(setting == 6 ? 0 : 1));
        const char* property = setting == 6 ? "sideBarSide" : setting == 7 ? "newProjectSuRule" : "newReportLibraries";
        const char* text = setting == 6 ? (alternate ? "Left" : "Right") : setting == 7 ? (alternate ? "iucr_99" : "iucr_19") : (alternate ? "embedded" : "online");
        assistantMemberWrite(f, preferences, property, QJSValue(QString::fromLatin1(text))); return;
    }
    const char* property = setting == 1 ? "colourScheme" : setting == 2 ? "scanStackedPalette" : setting == 3 ? "scanMapColours"
        : setting == 4 ? "chartHiddenRange" : setting == 5 ? "textShow" : "scanRenderer";
    const char* source = setting == 1 ? "schemes" : setting == 10 ? "values" : "choices";
    assistantMemberWrite(f, preferences, property, textIndex(f, panelUsageContextRead(f, source), index));
}

namespace {
QJSValue numberMath(const PanelUsageFrame& f, const char* name, const std::function<QJSValueList()>& arguments) {
    const auto math = panelUsageContextRead(f, "Math");
    return panelUsageDeferredMemberCall(f, math, name, arguments);
}
QJSValue numberNegate(const PanelUsageFrame& f, const QJSValue& input) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), input));
    QV4::ScopedValue result(scope, QV4::Runtime::UMinus::call(*value)); f.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
bool numberFinite(const PanelUsageFrame& f, const QJSValue& value) { return panelUsageTruth(panelUsageGlobalCall(f, "isFinite", {value})); }
bool numberType(const PanelUsageFrame& f, const QJSValue& value) {
    return tableTypeof(f, value).strictlyEquals(QJSValue(QStringLiteral("number")));
}
QJSValue numberString(const PanelUsageFrame& f, const QJSValue& value) { return panelUsageGlobalCall(f, "String", {value}); }
QJSValue numberAbs(const PanelUsageFrame& f, const QJSValue& value) { return numberMath(f, "abs", [&] { return QJSValueList{value}; }); }
QJSValue numberPower(const PanelUsageFrame& f, const std::function<QJSValue()>& power) {
    return numberMath(f, "pow", [&] { return QJSValueList{QJSValue(10), power()}; });
}
QJSValue numberReplaceExponent(const PanelUsageFrame& f, const QJSValue& value) {
    return panelUsageMemberCall(f, value, "replace", {QJSValue(QStringLiteral("e+")), QJSValue(QStringLiteral("e"))});
}
QJSValue numberRegex(const PanelUsageFrame& f, const char* pattern) { return panelRegex(f, QString::fromLatin1(pattern)); }
QJSValue numberProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    const auto tick = arg(0), power = saved(0), decimals = saved(1);
    const auto divisor = numberPower(f, [&] { return power; });
    const auto mantissa = viewArithmetic(f, tick, divisor, 2);
    if (operation == 181) return panelUsageMemberCall(f, mantissa, "toFixed", {decimals});
    if (!numberFinite(f, mantissa)) return QJSValue(true);
    const auto distance = numberMath(f, "abs", [&] {
        const auto fixed = panelUsageMemberCall(f, mantissa, "toFixed", {decimals});
        const auto rounded = panelUsageGlobalCall(f, "Number", {fixed});
        return QJSValueList{viewArithmetic(f, mantissa, rounded, 0)};
    });
    const auto scale = numberMath(f, "max", [&] { return QJSValueList{QJSValue(1), numberAbs(f, mantissa)}; });
    return QJSValue(assistantRelation(f, distance, viewArithmetic(f, QJSValue(1e-9), scale, 1), 3));
}
} // namespace

QJSValue ApplicationInfo::numberPresentation(NumberOperation operation, const QJSValue& value, const QJSValue& second,
    const QJSValue& third, const QJSValue& fourth) const {
    const auto f = panelUsageEngine(this);
    const auto read = [&](const QJSValue& object, const char* name) { return panelUsageRead(f, object, name); };
    const auto call = [&](const QJSValue& object, const char* name, const QJSValueList& args = QJSValueList()) { return panelUsageMemberCall(f, object, name, args); };
    const auto named = [&](const char* name, const QJSValueList& args) { return panelUsageGlobalCall(f, name, args); };
    const auto add = [&](const QJSValue& a, const QJSValue& b) { return panelUsageAdd(f, a, b); };
    const auto sub = [&](const QJSValue& a, const QJSValue& b) { return viewArithmetic(f, a, b, 0); };
    const auto mul = [&](const QJSValue& a, const QJSValue& b) { return viewArithmetic(f, a, b, 1); };
    const auto div = [&](const QJSValue& a, const QJSValue& b) { return viewArithmetic(f, a, b, 2); };
    const auto relation = [&](const QJSValue& a, const QJSValue& b, int kind) { return assistantRelation(f, a, b, kind); };
    const QJSValue empty(QStringLiteral("")), zeroText(QStringLiteral("0")), dot(QStringLiteral(".")), e(QStringLiteral("e"));
    if (operation == NumberScientific) {
        if (!numberType(f, value) || !numberFinite(f, value) || value.strictlyEquals(QJSValue(0))) return QJSValue(false);
        return QJSValue(relation(numberAbs(f, value), QJSValue(1e6), 2) || relation(numberAbs(f, value), QJSValue(1e-4), 0));
    }
    if (operation == NumberScientificExponent) return named("exponentOf", {call(value, "toExponential", {QJSValue(3)})});
    if (operation == NumberExponentOf) {
        const auto start = add(call(value, "indexOf", {e}), QJSValue(1));
        return named("Number", {call(value, "slice", {start})});
    }
    if (operation == NumberFull) return numberString(f, value);
    if (operation == NumberPlainFull) {
        if (!numberType(f, value) || !numberFinite(f, value)) return numberString(f, value);
        const auto text = numberString(f, value);
        const auto parts = call(numberRegex(f, R"(^(-?)(\d)(?:\.(\d+))?e([+-]\d+)$)"), "exec", {text});
        if (!panelUsageTruth(parts)) return text;
        const auto first = textIndex(f, parts, QJSValue(2));
        const auto digits = add(first, tableNullish(textIndex(f, parts, QJSValue(3)), empty));
        const auto power = named("Number", {textIndex(f, parts, QJSValue(4))});
        if (relation(power, QJSValue(0), 0)) {
            const auto prefix = add(textIndex(f, parts, QJSValue(1)), QJSValue(QStringLiteral("0.")));
            const auto zeros = call(zeroText, "repeat", {sub(numberNegate(f, power), QJSValue(1))});
            return add(add(prefix, zeros), digits);
        }
        const auto point = add(power, QJSValue(1)); const auto sign = textIndex(f, parts, QJSValue(1)); QJSValue rest;
        if (relation(read(digits, "length"), point, 3)) {
            const auto zeros = call(zeroText, "repeat", {sub(point, read(digits, "length"))}); rest = add(digits, zeros);
        } else {
            const auto prefix = add(call(digits, "slice", {QJSValue(0), point}), dot);
            rest = add(prefix, call(digits, "slice", {point}));
        }
        return add(sign, rest);
    }
    if (operation == NumberParameter) {
        if (panelUsageTruth(named("scientific", {value}))) return numberReplaceExponent(f, call(value, "toExponential", {QJSValue(3)}));
        const auto text = named("ruled", {value, second});
        return panelUsageTruth(text) ? read(text, "value") : named("rounded", {value, second, panelUsageContextRead(f, "Infinity"), third});
    }
    if (operation == NumberRuled) {
        const auto project = assistantContextField(f, "Session", "project");
        if (!panelUsageTruth(project) || read(project, "suRule").strictlyEquals(empty) || !numberType(f, value) || !numberFinite(f, value)
            || !numberType(f, second) || !numberFinite(f, second) || relation(second, QJSValue(0), 3)) return consentNull();
        const auto text = call(project, "suText", {value, second});
        return !read(text, "value").strictlyEquals(empty) ? text : consentNull();
    }
    if (operation == NumberRounded) {
        if (!numberType(f, value)) return numberString(f, value);
        if (!numberFinite(f, value)) return numberString(f, value);
        const auto room = relation(third, QJSValue(0), 1) ? third : QJSValue(8);
        const bool known = numberType(f, second) && numberFinite(f, second) && relation(second, QJSValue(0), 1);
        const auto most = relation(fourth, QJSValue(0), 1) ? fourth : QJSValue(6); auto significant = most; QJSValue text;
        if (known) {
            const auto place = named("exponentOf", {call(second, "toExponential", {QJSValue(0)})});
            const auto digits = numberMath(f, "round", [&] { return QJSValueList{div(value, numberPower(f, [&] { return place; }))}; });
            significant = value.strictlyEquals(QJSValue(0)) ? QJSValue(1) : numberMath(f, "max", [&] {
                const auto floor = numberMath(f, "floor", [&] {
                    return QJSValueList{numberMath(f, "log10", [&] { return QJSValueList{numberAbs(f, value)}; })};
                });
                return QJSValueList{QJSValue(1), add(sub(floor, place), QJSValue(1))};
            });
            if (relation(place, QJSValue(0), 0)) text = call(value, "toFixed", {numberMath(f, "min", [&] { return QJSValueList{numberNegate(f, place), QJSValue(100)}; })});
            else if (relation(numberAbs(f, digits), QJSValue(1e21), 0)) {
                if (digits.strictlyEquals(QJSValue(0))) text = zeroText;
                else { const auto prefix = numberString(f, digits); text = add(prefix, call(zeroText, "repeat", {place})); }
            } else text = named("exponent", {value, significant});
        } else {
            const auto precise = call(value, "toPrecision", {most}); text = numberString(f, named("Number", {precise}));
        }
        if (relation(read(text, "length"), room, 3)) return text;
        const auto digits = numberMath(f, "min", [&] {
            return QJSValueList{significant, numberMath(f, "max", [&] { return QJSValueList{QJSValue(1), sub(room, QJSValue(5))}; })};
        });
        return named("exponent", {value, digits});
    }
    if (operation == NumberError) {
        if (!numberType(f, value) || !numberFinite(f, value) || relation(value, QJSValue(0), 3)) return empty;
        if (panelUsageTruth(named("scientific", {third}))) {
            const auto power = named("scientificExponent", {third});
            const auto mantissa = mul(value, numberPower(f, [&] { return numberNegate(f, power); }));
            if (numberFinite(f, mantissa) && relation(mantissa, QJSValue(1e21), 0)) return add(add(call(mantissa, "toFixed", {QJSValue(3)}), e), power);
            return add(add(named("sharedExponent", {value, power}), e), power);
        }
        const auto room = relation(second, QJSValue(0), 1) ? second : QJSValue(6);
        const auto text = named("ruled", {third, value}); if (panelUsageTruth(text)) return read(text, "su");
        const auto plain = numberString(f, named("Number", {call(value, "toPrecision", {QJSValue(1)})}));
        return relation(read(plain, "length"), room, 3) ? plain : named("exponent", {value, QJSValue(1)});
    }
    if (operation == NumberSharedExponent) {
        const auto shift = sub(named("exponentOf", {call(value, "toExponential")}), second); QJSValue thousandths;
        if (relation(add(shift, QJSValue(3)), QJSValue(0), 0)) {
            const auto rounded = numberMath(f, "round", [&] {
                const auto exponential = call(value, "toExponential");
                const auto parts = call(exponential, "split", {e});
                const auto mantissa = named("Number", {textIndex(f, parts, QJSValue(0))});
                return QJSValueList{mul(mantissa, numberPower(f, [&] { return add(shift, QJSValue(3)); }))};
            });
            thousandths = numberString(f, rounded);
        } else {
            const auto count = numberMath(f, "min", [&] { return QJSValueList{add(shift, QJSValue(3)), QJSValue(14)}; });
            const auto text = call(value, "toExponential", {count});
            const auto at = call(text, "indexOf", {e});
            const auto digits = call(call(text, "slice", {QJSValue(0), at}), "replace", {dot, empty});
            const auto padding = numberMath(f, "max", [&] {
                const auto exponent = named("exponentOf", {text});
                const auto first = sub(exponent, sub(second, QJSValue(3)));
                return QJSValueList{QJSValue(0), sub(first, sub(read(digits, "length"), QJSValue(1)))};
            });
            thousandths = add(digits, call(zeroText, "repeat", {padding}));
        }
        const auto padded = call(thousandths, "padStart", {QJSValue(4), zeroText});
        const auto prefix = add(call(padded, "slice", {QJSValue(0), QJSValue(-3)}), dot);
        return add(prefix, call(padded, "slice", {QJSValue(-3)}));
    }
    if (operation == NumberPlain) return named("rounded", {value, QJSValue(0), second});
    if (operation == NumberAxisFormat) {
        QJSValue largest(0);
        panelUsageEach(f, value, [&](const QJSValue& tick) {
            if (numberFinite(f, tick)) largest = numberMath(f, "max", [&] { return QJSValueList{largest, numberAbs(f, tick)}; });
            return panelUsageReady(f);
        });
        QJSValue power(0);
        if (panelUsageTruth(second) && panelUsageTruth(named("scientific", {largest}))) power = named("scientificExponent", {largest});
        auto literal = panelUsageLiteral(f); panelUsageWrite(f, literal.value, "shared", second); panelUsageWrite(f, literal.value, "power", power);
        panelUsageWrite(f, literal.value, "decimals", QJSValue(0)); const auto format = panelUsageComplete(f, literal);
        if (!panelUsageTruth(second)) return format;
        const QJSValue most(power.strictlyEquals(QJSValue(0)) ? 6 : 3);
        const auto exact = [&](const QJSValue& decimals) {
            return call(value, "every", {panelUsageClosure(f, 180, {power, decimals}, 1)});
        };
        const auto distinct = [&](const QJSValue& decimals) {
            const auto constructor = panelUsageContextRead(f, "Set");
            const auto texts = call(value, "map", {panelUsageClosure(f, 181, {power, decimals}, 1)});
            const auto set = panelUsageConstruct(f, constructor, {texts});
            const auto size = read(set, "size"); return size.strictlyEquals(read(value, "length"));
        };
        assistantMemberWrite(f, format, "decimals", QJSValue(0));
        while (panelUsageReady(f) && relation(read(format, "decimals"), most, 0) && !panelUsageTruth(exact(read(format, "decimals")))) {
            const auto decimals = panelUsageNumber(f, read(format, "decimals")); if (!decimals) return {};
            assistantMemberWrite(f, format, "decimals", QJSValue(*decimals + 1));
        }
        while (panelUsageReady(f) && relation(read(format, "decimals"), QJSValue(12), 0) && !distinct(read(format, "decimals"))) {
            const auto decimals = panelUsageNumber(f, read(format, "decimals")); if (!decimals) return {};
            assistantMemberWrite(f, format, "decimals", QJSValue(*decimals + 1));
        }
        return format;
    }
    if (operation == NumberAxisTick) {
        if (!numberType(f, value) || !numberFinite(f, value)) return numberString(f, value);
        if (!panelUsageTruth(read(second, "shared"))) {
            if (panelUsageTruth(named("scientific", {value}))) return numberReplaceExponent(f, named("exponent", {value, QJSValue(4)}));
            return numberString(f, named("Number", {call(value, "toPrecision", {QJSValue(6)})}));
        }
        const auto scaled = div(value, numberPower(f, [&] { return read(second, "power"); }));
        const auto text = call(scaled, "toFixed", {read(second, "decimals")});
        if (named("Number", {text}).strictlyEquals(QJSValue(0)))
            return !read(second, "power").strictlyEquals(QJSValue(0)) ? zeroText : call(QJSValue(0), "toFixed", {read(second, "decimals")});
        if (!read(second, "power").strictlyEquals(QJSValue(0))) { const auto prefix = add(text, e); return add(prefix, read(second, "power")); }
        return text;
    }
    if (operation == NumberDecimal) {
        const auto expression = numberRegex(f, R"(^([+-]?)(\d*)(?:\.(\d*))?$)");
        const auto parts = call(expression, "exec", {numberString(f, value)});
        if (!panelUsageTruth(parts) || (textIndex(f, parts, QJSValue(2)).strictlyEquals(empty)
            && tableNullish(textIndex(f, parts, QJSValue(3)), empty).strictlyEquals(empty))) return consentNull();
        const auto whole = call(textIndex(f, parts, QJSValue(2)), "replace", {numberRegex(f, "^0+"), empty});
        const auto fraction = tableNullish(textIndex(f, parts, QJSValue(3)), empty);
        if (!whole.strictlyEquals(empty)) {
            auto result = panelUsageLiteral(f); panelUsageWrite(f, result.value, "sign", textIndex(f, parts, QJSValue(1)));
            panelUsageWrite(f, result.value, "digits", add(whole, fraction));
            panelUsageWrite(f, result.value, "power", sub(read(whole, "length"), QJSValue(1)));
            panelUsageWrite(f, result.value, "whole", QJSValue(textIndex(f, parts, QJSValue(3)).isUndefined()));
            return panelUsageComplete(f, result);
        } else {
            const auto first = call(fraction, "search", {numberRegex(f, "[1-9]")});
            if (relation(first, QJSValue(0), 0)) return consentNull();
            auto result = panelUsageLiteral(f); panelUsageWrite(f, result.value, "sign", textIndex(f, parts, QJSValue(1)));
            panelUsageWrite(f, result.value, "digits", call(fraction, "slice", {first}));
            panelUsageWrite(f, result.value, "power", numberNegate(f, add(first, QJSValue(1))));
            panelUsageWrite(f, result.value, "whole", QJSValue(false));
            return panelUsageComplete(f, result);
        }
    }
    if (operation == NumberCompact) {
        const auto number = named("decimal", {value}); if (number.isNull()) return numberString(f, value);
        auto digits = read(number, "digits");
        if (relation(second, QJSValue(0), 1)) digits = call(call(digits, "slice", {QJSValue(0), second}), "padEnd", {second, zeroText});
        else if (panelUsageTruth(read(number, "whole"))) {
            digits = call(digits, "replace", {numberRegex(f, "0+$"), empty}); if (!panelUsageTruth(digits)) digits = zeroText;
        }
        const auto sign = read(number, "sign"), firstDigit = textIndex(f, digits, QJSValue(0));
        const auto first = add(sign, firstDigit);
        const auto fraction = relation(read(digits, "length"), QJSValue(1), 1) ? add(dot, call(digits, "slice", {QJSValue(1)})) : empty;
        const auto prefix = add(add(first, fraction), e); return add(prefix, read(number, "power"));
    }
    if (operation == NumberSuDigits) {
        const auto project = assistantContextField(f, "Session", "project");
        const auto expression = numberRegex(f, "[1-9]"); const auto first = call(expression, "exec", {numberString(f, value)});
        const bool two = (panelUsageTruth(project) && read(project, "suRule").strictlyEquals(QJSValue(QStringLiteral("iucr_99"))))
            || (!first.isNull() && textIndex(f, first, QJSValue(0)).strictlyEquals(QJSValue(QStringLiteral("1"))));
        return QJSValue(two ? 2 : 1);
    }
    if (operation == NumberRuledDigits) {
        const auto number = named("decimal", {value}), uncertainty = named("decimal", {second});
        if (number.isNull() || uncertainty.isNull()) return QJSValue(0);
        const auto count = named("suDigits", {second});
        const auto numberPower = read(number, "power");
        const auto uncertaintyPower = read(uncertainty, "power");
        const auto digits = add(sub(numberPower, add(sub(uncertaintyPower, count), QJSValue(1))), QJSValue(1));
        return relation(digits, QJSValue(1), 2) ? digits : count;
    }
    if (operation == NumberNarrowParameter) {
        const auto text = named("parameter", {value, second, third}); if (panelUsageTruth(named("scientific", {value}))) return text;
        const auto rule = named("ruled", {value, second});
        if (panelUsageTruth(rule)) {
            const auto ruleValue = read(rule, "value"), su = read(rule, "su");
            return named("compact", {text, named("ruledDigits", {ruleValue, su})});
        }
        const auto number = named("decimal", {text});
        if (number.isNull() || !numberType(f, second) || !numberFinite(f, second) || relation(second, QJSValue(0), 3)) return named("compact", {text});
        const auto digits = numberMath(f, "max", [&] {
            const auto power = read(number, "power"); const auto place = named("exponentOf", {call(second, "toExponential", {QJSValue(0)})});
            return QJSValueList{QJSValue(1), add(sub(power, place), QJSValue(1))};
        });
        return named("compact", {text, digits});
    }
    if (operation == NumberFitted) {
        if (!relation(second, QJSValue(0), 1) || relation(call(third, "advanceWidth", {value}), second, 3)) return value;
        return fourth.isNull() || fourth.isUndefined() ? named("compact", {value}) : fourth;
    }
    if (operation == NumberOwnUncertainty) {
        if (!numberType(f, value) || !numberFinite(f, value) || relation(value, QJSValue(0), 3)) return empty;
        const auto text = named("ruled", {second, value});
        const auto written = panelUsageTruth(text) ? read(text, "su") : numberString(f, named("Number", {call(value, "toPrecision", {QJSValue(1)})}));
        if (panelUsageTruth(call(numberRegex(f, "e"), "test", {written}))) return numberReplaceExponent(f, written);
        return named("compact", {written, panelUsageTruth(text) ? named("suDigits", {written}) : QJSValue(1)});
    }
    if (operation == NumberExponent) {
        const auto count = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), sub(second, QJSValue(1))}; });
        const auto text = call(value, "toExponential", {count}), at = call(text, "indexOf", {e});
        auto mantissa = call(text, "slice", {QJSValue(0), at});
        if (relation(call(mantissa, "indexOf", {dot}), QJSValue(0), 2)) {
            mantissa = call(mantissa, "replace", {numberRegex(f, "0+$"), empty});
            mantissa = call(mantissa, "replace", {numberRegex(f, R"(\.$)"), empty});
        }
        return add(mantissa, call(text, "slice", {at}));
    }
    return {};
}

namespace {
QJSValue reportProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg,
    const std::function<void(uint, const QJSValue&)>& writeCapture) {
    if (operation == 200) {
        EditorFinally release{f, [&] { projectWrite(f, "group", "saving", QJSValue(false)); }};
        const auto style = panelUsageContextRead(f, "EaStyle");
        const auto font = panelUsageRead(f, panelUsageRead(f, style, "Fonts"), "fontFamily");
        panelUsageMemberCall(f, saved(0), "saveReport", {font});
        const auto refusal = projectInvoke(f, "Session", "writeBackReports");
        if (!refusal.strictlyEquals(QJSValue(QStringLiteral("")))) {
            projectWrite(f, "saveError", "message", refusal); projectInvoke(f, "saveError", "open");
        }
        return {};
    }
    if (operation == 201) {
        const auto figures = arg(0);
        tableForIn(f, figures, [&](const QJSValue& name) {
            panelUsageMemberCall(f, saved(0), "setFigure", {name, textIndex(f, figures, name)}); return panelUsageReady(f);
        });
        return projectCall(f, saved(1));
    }
    if (operation == 202) {
        const auto figures = saved(0), job = saved(1);
        const auto name = panelUsageRead(f, job, "name"), image = panelUsageRead(f, arg(0), "image");
        textIndexWrite(f, figures, name, image); return projectCall(f, saved(2));
    }
    if (operation == 203) {
        const auto previous = panelUsageNumber(f, saved(3)); if (!previous || !panelUsageReady(f)) return {};
        const QJSValue left(*previous - 1); writeCapture(3, left);
        if (assistantRelation(f, left, QJSValue(0), 1)) return {};
        panelUsageEach(f, saved(0), [&](const QJSValue& job) {
            panelUsageMemberCall(f, panelUsageRead(f, job, "item"), "destroy"); return panelUsageReady(f);
        });
        return projectCall(f, saved(1), {saved(2)});
    }
    if (operation == 204) {
        if (!panelUsageRead(f, arg(0), "key").strictlyEquals(QJSValue(QStringLiteral("charts")))) return QJSValue(false);
        return panelUsageRead(f, arg(0), "included");
    }
    if (operation == 205) {
        const auto row = arg(0), label = panelUsageRead(f, row, "label"); QJSValue text;
        if (!panelUsageTruth(panelUsageRead(f, row, "units"))) text = panelUsageRead(f, row, "text");
        else {
            const auto prefix = panelUsageAdd(f, panelUsageRead(f, row, "text"), QJSValue(QStringLiteral(" ")));
            text = panelUsageAdd(f, prefix, panelUsageRead(f, row, "units"));
        }
        return assistantGeometryArray(f, {label, text});
    }
    if (operation == 206) return panelUsageAdd(f, arg(0), panelUsageRead(f, arg(1), "width"));
    return {};
}
QJSValue reportTemplateString(const PanelUsageFrame& f, const QJSValue& input) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), input));
    QV4::ScopedString text(scope, value->toString(f.vm())); f.checked();
    return text ? QJSValuePrivate::fromReturnedValue(text->asReturnedValue()) : QJSValue();
}
QJSValue reportWindow(const PanelUsageFrame& f, bool named) {
    const auto attached = named ? assistantContextField(f, "printFigures", "Window") : panelUsageContextRead(f, "Window");
    return panelUsageRead(f, attached, "window");
}
QJSValueList reportTriple(const PanelUsageFrame& f, const QJSValue& input) {
    QJSValueList values;
    panelUsageEach(f, input, [&](const QJSValue& value) { values.append(value); return values.size() < 3; });
    while (values.size() < 3) values.append(QJSValue());
    return values;
}
QJSValue reportColourChannel(const PanelUsageFrame& f, const QJSValue& background, const QJSValue& end,
    const QJSValue& share, const char* channel) {
    const auto first = panelUsageRead(f, background, channel), finish = panelUsageRead(f, end, channel), start = panelUsageRead(f, background, channel);
    const auto distance = viewArithmetic(f, finish, start, 0);
    return panelUsageAdd(f, first, viewArithmetic(f, distance, share, 1));
}
} // namespace

void ApplicationInfo::saveReportPreview() const {
    const auto f = panelUsageEngine(this); const auto report = assistantContextField(f, "group", "report");
    if (!panelUsageTruth(assistantContextField(f, "group", "inBrowser")) && panelUsageTruth(assistantContextField(f, "Session", "needsSaveAs"))) {
        projectWrite(f, "group", "afterSaveAs", QJSValue(true)); projectInvoke(f, "AppState", "saveAsRequested"); return;
    }
    if (panelUsageTruth(panelUsageRead(f, report, "calculating"))) { projectWrite(f, "group", "savePending", QJSValue(true)); return; }
    projectWrite(f, "group", "saving", QJSValue(true)); projectWrite(f, "group", "savePending", QJSValue(false));
    const auto write = panelUsageClosure(f, 200, {report}, 0);
    if (panelUsageTruth(panelUsageRead(f, report, "writesPdf"))) {
        const auto preview = assistantContextField(f, "group", "preview");
        panelUsageMemberCall(f, preview, "grabFigures", {panelUsageClosure(f, 201, {report, write}, 1)});
    } else projectCall(f, write);
}
QJSValue ApplicationInfo::savedReportRow(const QJSValue& format) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "group", "report")) || !panelUsageTruth(assistantContextField(f, "group", "shown"))) return consentNull();
    const auto stem = panelUsageRead(f, assistantContextField(f, "group", "report"), "fileStem");
    const auto prefix = panelUsageAdd(f, stem, QJSValue(QStringLiteral("."))), name = panelUsageAdd(f, prefix, format);
    QJSValue selected = consentNull();
    panelUsageEach(f, panelUsageRead(f, assistantContextField(f, "group", "report"), "savedReports"), [&](const QJSValue& row) {
        if (consentFieldEquals(f, row, "name", name) && consentFieldEquals(f, row, "format", format)) { selected = row; return false; }
        return panelUsageReady(f);
    });
    return selected;
}
void ApplicationInfo::reportExportFailure(const QJSValue& message) const {
    const auto f = panelUsageEngine(this); projectWrite(f, "saveError", "message", message); projectInvoke(f, "saveError", "open");
}
void ApplicationInfo::reportExportChanged(int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 1) { projectWrite(f, "group", "afterSaveAs", QJSValue(false)); return; }
    if (event == 0) {
        if (panelUsageTruth(assistantContextField(f, "group", "afterSaveAs")) && !panelUsageTruth(assistantContextField(f, "Session", "needsSaveAs"))) {
            projectWrite(f, "group", "afterSaveAs", QJSValue(false)); projectInvoke(f, "group", "saveReport");
        }
    } else if (panelUsageTruth(assistantContextField(f, "group", "savePending")) && !panelUsageTruth(panelUsageRead(f, assistantContextField(f, "group", "report"), "calculating")))
        projectInvoke(f, "group", "saveReport");
}
QJSValue ApplicationInfo::reportChartsIncluded() const {
    const auto f = panelUsageEngine(this); const auto model = panelUsageContextRead(f, "model");
    const auto original = panelUsageRead(f, model, "contents");
    const auto contents = original.isNull() || original.isUndefined() ? controlEmptyArray(f) : original;
    return panelUsageMemberCall(f, contents, "some", {projectGuardedClosure(f, 204, 1)});
}
QJSValue ApplicationInfo::reportSection(const QJSValue& name, bool numbered) const {
    const auto f = panelUsageEngine(this); const auto index = panelUsageMemberCall(f, panelUsageContextRead(f, "sections"), "indexOf", {name});
    return numbered ? panelUsageAdd(f, index, QJSValue(1)) : QJSValue(assistantRelation(f, index, QJSValue(0), 2));
}
QJSValue ApplicationInfo::reportKeyValues(const QJSValue& rows) const {
    const auto f = panelUsageEngine(this); const auto input = rows.isNull() || rows.isUndefined() ? controlEmptyArray(f) : rows;
    return panelUsageMemberCall(f, input, "map", {projectGuardedClosure(f, 205, 1)});
}
void ApplicationInfo::reportGrabFigures(const QJSValue& done) const {
    const auto f = panelUsageEngine(this); const auto jobs = controlEmptyArray(f); QJSValueList groups;
    for (const auto& group : {std::array<const char*, 3>{"structureRecords", "structure", "printStructure"}, {"experimentRecords", "pattern", "printPattern"}, {"evolutionRecords", "evolution", "printEvolution"}}) {
        const auto records = panelUsageContextRead(f, group[0]); const QJSValue kind(QString::fromLatin1(group[1]));
        const auto component = panelUsageContextRead(f, group[2]); groups.append(assistantGeometryArray(f, {records, kind, component}));
    }
    const auto source = assistantGeometryArray(f, groups);
    panelUsageEach(f, source, [&](const QJSValue& input) {
        const auto fields = reportTriple(f, input); const auto records = fields[0], kind = fields[1], component = fields[2];
        for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, records, "count"), 0); ++i) {
            const auto record = panelUsageMemberCall(f, records, "itemAt", {QJSValue(i)}); QJSValue shown = consentNull();
            if (panelUsageTruth(record)) shown = kind.strictlyEquals(QJSValue(QStringLiteral("evolution"))) ? record : panelUsageRead(f, record, "figureItem");
            if (!panelUsageTruth(shown) || assistantRelation(f, panelUsageRead(f, shown, "width"), QJSValue(0), 3)
                || assistantRelation(f, panelUsageRead(f, shown, "height"), QJSValue(0), 3)) continue;
            auto literal = panelUsageLiteral(f); panelUsageWrite(f, literal.value, "width", panelUsageRead(f, shown, "width"));
            panelUsageWrite(f, literal.value, "height", panelUsageRead(f, shown, "height")); const auto properties = panelUsageComplete(f, literal);
            QJSValue crystal = consentNull();
            if (kind.strictlyEquals(QJSValue(QStringLiteral("pattern")))) crystal = tableNullish(panelUsageRead(f, panelUsageRead(f, record, "modelData"), "single_crystal"), consentNull());
            if (kind.strictlyEquals(QJSValue(QStringLiteral("evolution")))) {
                assistantMemberWrite(f, properties, "reportSeries", panelUsageRead(f, record, "reportSeries"));
                const auto styles = panelUsageRead(f, assistantContextField(f, "preview", "model"), "pattern_styles");
                assistantMemberWrite(f, properties, "reportStyles", styles.isNull() || styles.isUndefined() ? controlEmptyArray(f) : styles);
            } else if (panelUsageTruth(crystal)) assistantMemberWrite(f, properties, "reportData", crystal);
            else assistantMemberWrite(f, properties, "report", assistantContextField(f, "preview", "report"));
            if (!kind.strictlyEquals(QJSValue(QStringLiteral("evolution"))) && !panelUsageTruth(crystal)) {
                const QJSValue key(QString::fromLatin1(kind.strictlyEquals(QJSValue(QStringLiteral("structure"))) ? "reportStructure" : "reportExperiment"));
                textIndexWrite(f, properties, key, panelUsageRead(f, panelUsageRead(f, record, "modelData"), "id"));
            }
            const auto factory = panelUsageTruth(crystal) ? panelUsageContextRead(f, "printSingleCrystal") : component;
            const auto copy = panelUsageMemberCall(f, factory, "createObject", {panelUsageContextRead(f, "printFigures"), properties});
            if (panelUsageTruth(copy)) {
                auto job = panelUsageLiteral(f); panelUsageWrite(f, job.value, "item", copy);
                const auto kindText = reportTemplateString(f, kind); const auto prefix = panelUsageAdd(f, kindText, QJSValue(QStringLiteral("-")));
                panelUsageWrite(f, job.value, "name", panelUsageAdd(f, prefix, reportTemplateString(f, QJSValue(i))));
                panelUsageMemberCall(f, jobs, "push", {panelUsageComplete(f, job)});
            }
        }
        return panelUsageReady(f);
    });
    projectInvoke(f, "printFigures", "start", {jobs, done});
}
void ApplicationInfo::reportCaptureStart(const QJSValue& jobs, const QJSValue& done) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageRead(f, jobs, "length").strictlyEquals(QJSValue(0))) { projectCall(f, done, {panelUsageComplete(f, panelUsageLiteral(f))}); return; }
    projectWrite(f, "printFigures", "jobs", jobs); projectWrite(f, "printFigures", "done", done); projectWrite(f, "printFigures", "frames", QJSValue(0));
    panelUsageMemberCall(f, reportWindow(f, false), "update");
}
void ApplicationInfo::reportCaptureAll() const {
    const auto f = panelUsageEngine(this); const auto jobs = assistantContextField(f, "printFigures", "jobs"), done = assistantContextField(f, "printFigures", "done");
    projectWrite(f, "printFigures", "jobs", controlEmptyArray(f)); const auto figures = panelUsageComplete(f, panelUsageLiteral(f));
    const auto left = panelUsageRead(f, jobs, "length");
    // The original shared lexical counter lives in this closure's marked capture,
    // shared by all per-image callbacks, rather than in a new view or controller.
    const auto finish = panelUsageClosure(f, 203, {jobs, done, figures, left}, 0);
    panelUsageEach(f, jobs, [&](const QJSValue& job) {
        const auto item = panelUsageRead(f, job, "item"); const auto callback = panelUsageClosure(f, 202, {figures, job, finish}, 1);
        const auto qt = panelUsageContextRead(f, "Qt");
        const auto width = viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, job, "item"), "width"), QJSValue(2), 1);
        const auto height = viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, job, "item"), "height"), QJSValue(2), 1);
        const auto size = panelUsageMemberCall(f, qt, "size", {width, height});
        const auto asked = panelUsageMemberCall(f, item, "grabToImage", {callback, size});
        if (!panelUsageTruth(asked)) projectCall(f, finish); return panelUsageReady(f);
    });
}
void ApplicationInfo::reportCaptureFrame() const {
    const auto f = panelUsageEngine(this); const auto previous = panelUsageNumber(f, assistantContextField(f, "printFigures", "frames"));
    if (!previous) return; const QJSValue frames(*previous + 1); projectWrite(f, "printFigures", "frames", frames);
    if (assistantRelation(f, frames, QJSValue(3), 0)) panelUsageMemberCall(f, reportWindow(f, true), "update");
    else projectInvoke(f, "printFigures", "grabAll");
}
QJSValue ApplicationInfo::reportTableDotWidth() const {
    const auto f = panelUsageEngine(this); const auto font = assistantContextField(f, "metrics", "font"); Q_UNUSED(font)
    return numberMath(f, "ceil", [&] { return QJSValueList{projectInvoke(f, "metrics", "advanceWidth", {QJSValue(QStringLiteral("."))})}; });
}
QJSValue ApplicationInfo::reportTableSplit(const QJSValue& text) const {
    const auto f = panelUsageEngine(this);
    const auto expression = panelRegex(f, QString::fromUtf8(R"(^([-−+]?[0-9]*)(\.?)([0-9]*(?:\([0-9]+\))?(?:[eE][-+]?[0-9]+)?(?: [^ 0-9].*)?)$)"));
    const auto match = panelUsageMemberCall(f, expression, "exec", {text});
    if (!panelUsageTruth(match)) return consentNull();
    const auto digits = panelRegex(f, QStringLiteral("[0-9]")); const auto first = textIndex(f, match, QJSValue(1)), last = textIndex(f, match, QJSValue(3));
    if (!panelUsageTruth(panelUsageMemberCall(f, digits, "test", {panelUsageAdd(f, first, last)}))) return consentNull();
    auto result = panelUsageLiteral(f); panelUsageWrite(f, result.value, "left", textIndex(f, match, QJSValue(1)));
    panelUsageWrite(f, result.value, "dot", QJSValue(!textIndex(f, match, QJSValue(2)).strictlyEquals(QJSValue(QStringLiteral("")))));
    panelUsageWrite(f, result.value, "right", textIndex(f, match, QJSValue(3))); return panelUsageComplete(f, result);
}
QJSValue ApplicationInfo::reportTableLayout() const {
    const auto f = panelUsageEngine(this); const auto font = assistantContextField(f, "metrics", "font"); Q_UNUSED(font)
    const auto out = controlEmptyArray(f);
    for (double column = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(column), panelUsageContextRead(f, "columnCount"), 0); ++column) {
        double numbers = 0, others = 0; QJSValue left(0), right(0), plain(0);
        panelUsageEach(f, panelUsageContextRead(f, "rows"), [&](const QJSValue& row) {
            const auto text = tableNullish(textIndex(f, row, QJSValue(column)), QJSValue(QStringLiteral("")));
            if (text.strictlyEquals(QJSValue(QStringLiteral("")))) return panelUsageReady(f);
            const auto parts = projectInvoke(f, "table", "split", {text});
            if (panelUsageTruth(parts)) {
                ++numbers;
                left = numberMath(f, "max", [&] { return QJSValueList{left, projectInvoke(f, "metrics", "advanceWidth", {panelUsageRead(f, parts, "left")})}; });
                right = numberMath(f, "max", [&] { return QJSValueList{right, projectInvoke(f, "metrics", "advanceWidth", {panelUsageRead(f, parts, "right")})}; });
            } else ++others;
            plain = numberMath(f, "max", [&] { return QJSValueList{plain, projectInvoke(f, "metrics", "advanceWidth", {text})}; }); return panelUsageReady(f);
        });
        const bool numeric = numbers > 0 && others == 0; QJSValue header(0);
        if (!panelUsageTruth(panelUsageContextRead(f, "keyValue"))) header = projectInvoke(f, "metrics", "advanceWidth", {textIndex(f, panelUsageContextRead(f, "columns"), QJSValue(column))});
        QJSValue content;
        if (numeric) {
            const auto leading = numberMath(f, "ceil", [&] { return QJSValueList{left}; });
            const auto prefix = panelUsageAdd(f, leading, panelUsageContextRead(f, "dotWidth"));
            content = panelUsageAdd(f, prefix, numberMath(f, "ceil", [&] { return QJSValueList{right}; }));
        } else content = numberMath(f, "ceil", [&] { return QJSValueList{plain}; });
        auto entry = panelUsageLiteral(f); panelUsageWrite(f, entry.value, "numeric", QJSValue(numeric));
        panelUsageWrite(f, entry.value, "left", numberMath(f, "ceil", [&] { return QJSValueList{left}; }));
        panelUsageWrite(f, entry.value, "right", numberMath(f, "ceil", [&] { return QJSValueList{right}; }));
        const auto maximum = numberMath(f, "max", [&] { return QJSValueList{content, numberMath(f, "ceil", [&] { return QJSValueList{header}; })}; });
        const auto padded = panelUsageAdd(f, maximum, viewArithmetic(f, QJSValue(2), panelUsageContextRead(f, "padding"), 1)); QJSValue extra(0);
        if (panelUsageTruth(panelUsageContextRead(f, "keyValue")) && column == 0) extra = panelUsageContextRead(f, "keyGap");
        panelUsageWrite(f, entry.value, "width", panelUsageAdd(f, padded, extra)); panelUsageMemberCall(f, out, "push", {panelUsageComplete(f, entry)});
    }
    return out;
}
QJSValue ApplicationInfo::reportTableWidth() const {
    const auto f = panelUsageEngine(this); const auto layout = panelUsageContextRead(f, "layout");
    const auto sum = panelUsageMemberCall(f, layout, "reduce", {projectGuardedClosure(f, 206, 2), QJSValue(0)});
    const auto gaps = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), viewArithmetic(f, panelUsageContextRead(f, "columnCount"), QJSValue(1), 0)}; });
    const auto style = panelUsageContextRead(f, "EaStyle"); const auto spacing = panelUsageRead(f, panelUsageRead(f, style, "Sizes"), "tableColumnSpacing");
    const auto spaced = panelUsageAdd(f, sum, viewArithmetic(f, gaps, spacing, 1));
    const auto bordered = panelUsageAdd(f, spaced, viewArithmetic(f, QJSValue(2), panelUsageContextRead(f, "border"), 1)); QJSValue extra(0);
    if (panelUsageTruth(panelUsageContextRead(f, "windowed"))) extra = controlStylePixel(f);
    return panelUsageAdd(f, bordered, extra);
}
void ApplicationInfo::reportTableRowsChanged() const {
    const auto f = panelUsageEngine(this);
    for (double row = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(row), panelUsageRead(f, panelUsageContextRead(f, "rows"), "length"), 0); ++row) {
        const auto cellsRow = textIndex(f, panelUsageContextRead(f, "rows"), QJSValue(row));
        const auto cells = panelUsageMemberCall(f, cellsRow, "join", {assistantContextField(f, "table", "cellSeparator")});
        if (assistantRelation(f, QJSValue(row), assistantContextField(f, "rowModel", "count"), 0)) projectInvoke(f, "rowModel", "setProperty", {QJSValue(row), QJSValue(QStringLiteral("cells")), cells});
        else {
            auto item = panelUsageLiteral(f); panelUsageWrite(f, item.value, "cells", cells); projectInvoke(f, "rowModel", "append", {panelUsageComplete(f, item)});
        }
    }
    const auto count = assistantContextField(f, "rowModel", "count"), length = panelUsageRead(f, panelUsageContextRead(f, "rows"), "length");
    if (assistantRelation(f, count, length, 1)) {
        const auto model = panelUsageContextRead(f, "rowModel"), at = panelUsageRead(f, panelUsageContextRead(f, "rows"), "length");
        const auto present = assistantContextField(f, "rowModel", "count"), wanted = panelUsageRead(f, panelUsageContextRead(f, "rows"), "length");
        panelUsageMemberCall(f, model, "remove", {at, viewArithmetic(f, present, wanted, 0)});
    }
}
QJSValue ApplicationInfo::reportCorrelationLabelWidth() const {
    const auto f = panelUsageEngine(this); const auto font = assistantContextField(f, "metrics", "font"); Q_UNUSED(font)
    QJSValue widest(0);
    panelUsageEach(f, panelUsageContextRead(f, "labels"), [&](const QJSValue& label) {
        widest = numberMath(f, "max", [&] {
            const auto metrics = panelUsageContextRead(f, "metrics");
            const auto index = panelUsageMemberCall(f, panelUsageContextRead(f, "labels"), "indexOf", {label});
            const auto number = panelUsageAdd(f, index, QJSValue(1)); const auto prefix = panelUsageAdd(f, number, QJSValue(QStringLiteral("  ")));
            return QJSValueList{widest, panelUsageMemberCall(f, metrics, "advanceWidth", {panelUsageAdd(f, prefix, label)})};
        });
        return panelUsageReady(f);
    });
    const auto measured = numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
    return panelUsageAdd(f, measured, controlStylePixel(f));
}
QJSValue ApplicationInfo::reportCorrelationColor(const QJSValue& value) const {
    const auto f = panelUsageEngine(this); const auto style = panelUsageContextRead(f, "EaStyle");
    const auto background = panelUsageRead(f, panelUsageRead(f, style, "Colors"), "chartBackground");
    const auto end = panelUsageContextRead(f, assistantRelation(f, value, QJSValue(0), 0) ? "negativeColor" : "positiveColor");
    const auto share = numberMath(f, "min", [&] { return QJSValueList{QJSValue(1), numberAbs(f, value)}; });
    const auto qt = panelUsageContextRead(f, "Qt");
    const QJSValueList channels{reportColourChannel(f, background, end, share, "r"), reportColourChannel(f, background, end, share, "g"), reportColourChannel(f, background, end, share, "b"), QJSValue(1)};
    return panelUsageMemberCall(f, qt, "rgba", channels);
}

namespace {
QJSValue chartBinary(const PanelUsageFrame& f, const QJSValue& left, const QJSValue& right, bool remainder) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue a(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), left)), b(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), right));
    QV4::ScopedValue value(scope, remainder ? QV4::Runtime::Mod::call(*a, *b) : QV4::Runtime::BitAnd::call(*a, *b)); f.checked();
    return QJSValuePrivate::fromReturnedValue(value->asReturnedValue());
}
QJSValue chartStyle(const PanelUsageFrame& f, const char* name) {
    return panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "EaStyle"), "Colors"), name);
}
QJSValue chartEscape(const PanelUsageFrame& f, const QJSValue& text) {
    const int flags = QV4::CompiledData::RegExp::RegExp_Global;
    auto out = panelUsageMemberCall(f, text, "replace", {panelRegex(f, QStringLiteral("&"), flags), QJSValue(QStringLiteral("&amp;"))});
    out = panelUsageMemberCall(f, out, "replace", {panelRegex(f, QStringLiteral("<"), flags), QJSValue(QStringLiteral("&lt;"))});
    return panelUsageMemberCall(f, out, "replace", {panelRegex(f, QStringLiteral(">"), flags), QJSValue(QStringLiteral("&gt;"))});
}
QJSValue chartRecord(const PanelUsageFrame& f, const std::initializer_list<std::pair<const char*, QJSValue>>& fields) {
    auto record = panelUsageLiteral(f); for (const auto& field : fields) panelUsageWrite(f, record.value, field.first, field.second);
    return panelUsageComplete(f, record);
}
QJSValue sceneProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    if (operation == 220) {
        const auto piece = arg(0); const auto text = chartEscape(f, numberString(f, panelUsageRead(f, piece, "text")));
        if (panelUsageTruth(assistantContextField(f, "legend", "labelInColor")) && panelUsageTruth(panelUsageRead(f, piece, "color"))) {
            const auto start = panelUsageAdd(f, QJSValue(QStringLiteral("<font color=\"")), panelUsageRead(f, piece, "color"));
            const auto prefix = panelUsageAdd(f, start, QJSValue(QStringLiteral("\">")));
            return panelUsageAdd(f, panelUsageAdd(f, prefix, text), QJSValue(QStringLiteral("</font>")));
        }
        return text;
    }
    if (operation == 221) {
        auto record = panelUsageLiteral(f); panelUsageWrite(f, record.value, "text", arg(0));
        const auto colors = assistantContextField(f, "entry", "labelColors");
        panelUsageWrite(f, record.value, "color", projectCall(f, saved(0), {textIndex(f, colors, arg(1))}));
        return panelUsageComplete(f, record);
    }
    if (operation == 222) {
        if (panelUsageTruth(assistantContextField(f, "entry", "hidden"))) return panelUsageRead(f, assistantContextField(f, "legend", "colors"), "themeForegroundDisabled");
        return arg(0);
    }
    if (operation == 223) {
        const auto project = saved(0); const auto number = panelUsageTruth(project) ? panelUsageMemberCall(f, project, "parameterNumber", {arg(0)}) : QJSValue(0);
        return assistantRelation(f, number, QJSValue(0), 1) ? numberString(f, number) : QJSValue(QStringLiteral(""));
    }
    return {};
}
} // namespace

QJSValue ApplicationInfo::legendToggleAt(const QJSValue& item, const QJSValue& x, const QJSValue& y) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(assistantContextField(f, "legend", "toggles")) || !panelUsageTruth(assistantContextField(f, "legend", "visible"))) return QJSValue(false);
    const auto at = panelUsageMemberCall(f, item, "mapToItem", {panelUsageContextRead(f, "column"), x, y});
    const auto column = panelUsageContextRead(f, "column"); const auto px = panelUsageRead(f, at, "x"), py = panelUsageRead(f, at, "y");
    const auto row = panelUsageMemberCall(f, column, "childAt", {px, py});
    if (row.isNull() || panelUsageRead(f, row, "key").isUndefined()) return QJSValue(false);
    projectInvoke(f, "legend", "toggled", {panelUsageRead(f, row, "key")}); return QJSValue(true);
}
QJSValue ApplicationInfo::legendRichLabel(const QJSValue& pieces) const {
    const auto f = panelUsageEngine(this); const auto texts = panelUsageMemberCall(f, pieces, "map", {projectGuardedClosure(f, 220, 1)});
    return panelUsageMemberCall(f, texts, "join", {QJSValue(QStringLiteral(""))});
}
QJSValue ApplicationInfo::legendMarkPiece(const QJSValue& mark, const QJSValue& width, const QJSValue& color) const {
    const auto f = panelUsageEngine(this);
    if (mark.strictlyEquals(QJSValue(QStringLiteral("atom")))) {
        auto record = panelUsageLiteral(f); panelUsageWrite(f, record.value, "icon", QJSValue(QStringLiteral("atom")));
        const auto colors = panelUsageContextRead(f, "AppColors");
        const auto background = panelUsageRead(f, assistantContextField(f, "legend", "colors"), "mainContentBackgroundHalfTransparent");
        panelUsageWrite(f, record.value, "color", panelUsageMemberCall(f, colors, "readable", {color, assistantGeometryArray(f, {background})}));
        return panelUsageComplete(f, record);
    }
    return chartRecord(f, {{"mark", mark}, {"width", width}, {"color", color}});
}
QJSValue ApplicationInfo::legendSegments() const {
    const auto f = panelUsageEngine(this); const auto ink = panelUsageClosure(f, 222, {}, 1);
    const auto legend = panelUsageContextRead(f, "legend");
    const auto kind = assistantContextField(f, "entry", "mark"), width = assistantContextField(f, "entry", "markWidth");
    const auto color = projectCall(f, ink, {assistantContextField(f, "entry", "color")});
    const auto mark = panelUsageMemberCall(f, legend, "markPiece", {kind, width, color});
    if (panelUsageTruth(assistantContextField(f, "entry", "bragg"))) {
        const auto title = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("ChartLegend", "Bragg peaks")))});
        const auto text = chartRecord(f, {{"text", title}}); auto icon = panelUsageLiteral(f); panelUsageWrite(f, icon.value, "icon", QJSValue(QStringLiteral("layer-group")));
        panelUsageWrite(f, icon.value, "color", projectCall(f, ink, {assistantContextField(f, "entry", "color")}));
        const auto last = chartRecord(f, {{"text", assistantContextField(f, "entry", "label")}});
        return assistantGeometryArray(f, {mark, text, panelUsageComplete(f, icon), last});
    }
    if (panelUsageTruth(assistantContextField(f, "entry", "selected"))) {
        auto label = panelUsageLiteral(f); panelUsageWrite(f, label.value, "text", assistantContextField(f, "entry", "label"));
        panelUsageWrite(f, label.value, "color", projectCall(f, ink, {assistantContextField(f, "entry", "color")})); panelUsageWrite(f, label.value, "bold", QJSValue(true));
        return assistantGeometryArray(f, {mark, panelUsageComplete(f, label)});
    }
    if (panelUsageTruth(assistantContextField(f, "entry", "hidden"))) {
        auto label = panelUsageLiteral(f); panelUsageWrite(f, label.value, "text", assistantContextField(f, "entry", "label"));
        panelUsageWrite(f, label.value, "color", projectCall(f, ink, {assistantContextField(f, "entry", "color")}));
        return assistantGeometryArray(f, {mark, panelUsageComplete(f, label)});
    }
    auto label = panelUsageLiteral(f); const auto receiver = panelUsageContextRead(f, "legend"); QJSValue pieces;
    if (assistantRelation(f, panelUsageRead(f, assistantContextField(f, "entry", "labelTexts"), "length"), QJSValue(0), 1))
        pieces = panelUsageMemberCall(f, assistantContextField(f, "entry", "labelTexts"), "map", {panelUsageClosure(f, 221, {ink}, 2)});
    else {
        auto piece = panelUsageLiteral(f); panelUsageWrite(f, piece.value, "text", assistantContextField(f, "entry", "label"));
        panelUsageWrite(f, piece.value, "color", projectCall(f, ink, {assistantContextField(f, "entry", "color")}));
        pieces = assistantGeometryArray(f, {panelUsageComplete(f, piece)});
    }
    panelUsageWrite(f, label.value, "text", panelUsageMemberCall(f, receiver, "richLabel", {pieces})); panelUsageWrite(f, label.value, "rich", QJSValue(true));
    panelUsageWrite(f, label.value, "color", projectCall(f, ink, {panelUsageRead(f, assistantContextField(f, "legend", "colors"), "themeForeground")}));
    return assistantGeometryArray(f, {mark, panelUsageComplete(f, label)});
}
QJSValue ApplicationInfo::factorPresentation(const QJSValue& value, bool rich) const {
    const auto f = panelUsageEngine(this); const auto text = value.isNull() || value.isUndefined() ? QJSValue(QStringLiteral("")) : value;
    if (!rich) {
        const auto pattern = panelRegex(f, QStringLiteral("\\b(c?)R_?(wp|p|exp|Bragg|F)\\b"));
        return panelUsageMemberCall(f, pattern, "test", {numberString(f, text)});
    }
    const auto escaped = chartEscape(f, numberString(f, text));
    return panelUsageMemberCall(f, escaped, "replace", {panelUsageContextRead(f, "pattern"), QJSValue(QStringLiteral("$1R<sub>$2</sub>"))});
}
QJSValue ApplicationInfo::fitOutcomePresentation(FitOutcomeOperation operation, const QJSValue& key, const QJSValue& neutral) const {
    const auto f = panelUsageEngine(this); const QJSValue empty(QStringLiteral(""));
    if (operation == FitRing) return QJSValue(key.strictlyEquals(empty));
    if (operation == FitTextColor) return panelUsageGlobalCall(f, "color", {key, chartStyle(f, "themeForeground")});
    const auto is = [&](const char* text) { return key.strictlyEquals(QJSValue(QString::fromLatin1(text))); };
    if (operation == FitIcon) {
        if (is("success")) return QJSValue(QStringLiteral("check-circle"));
        if (is("maxIterations") || is("noStep") || is("notConverged")) return QJSValue(QStringLiteral("exclamation-circle"));
        if (is("stopped")) return QJSValue(QStringLiteral("stop-circle"));
        if (is("superseded") || is("skipped")) return QJSValue(QStringLiteral("minus-circle"));
        if (is("failed") || is("refused")) return QJSValue(QStringLiteral("times-circle"));
        return empty;
    }
    if (operation == FitColor) {
        if (is("success")) return chartStyle(f, "green");
        if (is("maxIterations") || is("noStep") || is("notConverged")) return chartStyle(f, "orange");
        if (is("failed") || is("refused")) return chartStyle(f, "red");
        return !neutral.isUndefined() ? neutral : chartStyle(f, "themeForegroundMinor");
    }
    static const struct { const char* key; const char* word; const char* meaning; } rows[] = {
        {"", QT_TRANSLATE_NOOP("FitOutcomes", "Not fitted"), QT_TRANSLATE_NOOP("FitOutcomes", "Not fitted yet")},
        {"success", QT_TRANSLATE_NOOP("FitOutcomes", "Success"), QT_TRANSLATE_NOOP("FitOutcomes", "The fit converged")},
        {"maxIterations", QT_TRANSLATE_NOOP("FitOutcomes", "Max iterations"), QT_TRANSLATE_NOOP("FitOutcomes", "The iteration limit was reached; the result is kept")},
        {"noStep", QT_TRANSLATE_NOOP("FitOutcomes", "No step"), QT_TRANSLATE_NOOP("FitOutcomes", "No further improving step was found; the result is kept")},
        {"notConverged", QT_TRANSLATE_NOOP("FitOutcomes", "Not converged"), QT_TRANSLATE_NOOP("FitOutcomes", "The fit did not converge; why was not recorded with the result, which is kept")},
        {"stopped", QT_TRANSLATE_NOOP("FitOutcomes", "Stopped"), QT_TRANSLATE_NOOP("FitOutcomes", "Stop fitting was pressed; the result is kept")},
        {"superseded", QT_TRANSLATE_NOOP("FitOutcomes", "Superseded"), QT_TRANSLATE_NOOP("FitOutcomes", "An input changed during the fit; nothing was written")},
        {"skipped", QT_TRANSLATE_NOOP("FitOutcomes", "Skipped"), QT_TRANSLATE_NOOP("FitOutcomes", "The file has no intensity above zero, so it was not fitted")},
        {"refused", QT_TRANSLATE_NOOP("FitOutcomes", "Refused"), QT_TRANSLATE_NOOP("FitOutcomes", "The fit refused this file (analysis/scan-notes.csv says why); the scan went on")},
        {"failed", QT_TRANSLATE_NOOP("FitOutcomes", "Failed"), QT_TRANSLATE_NOOP("FitOutcomes", "The fit was refused or failed; nothing was written")}
    };
    for (const auto& row : rows) if (is(row.key)) return panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(operation == FitWord ? row.word : row.meaning))});
    return empty;
}
void ApplicationInfo::stepBlock(const QJSValue& offset) const {
    const auto f = panelUsageEngine(this); const auto next = panelUsageAdd(f, assistantContextField(f, "row", "blockIndex"), offset);
    if (assistantRelation(f, next, QJSValue(0), 2) && assistantRelation(f, next, assistantContextField(f, "selector", "count"), 0)) projectInvoke(f, "row", "blockActivated", {next});
}
QJSValue ApplicationInfo::blockSegments(const QJSValue& index, const QJSValue& name, const QJSValue& nameColor, const QJSValue& outcome, const QJSValue& isTemplate) const {
    const auto f = panelUsageEngine(this); if (assistantRelation(f, index, QJSValue(0), 0)) return controlEmptyArray(f);
    auto slot = panelUsageLiteral(f);
    panelUsageWrite(f, slot.value, "icon", projectInvoke(f, "FitOutcomes", "icon", {outcome}));
    panelUsageWrite(f, slot.value, "color", projectInvoke(f, "FitOutcomes", "color", {outcome}));
    panelUsageWrite(f, slot.value, "ring", projectInvoke(f, "FitOutcomes", "ring", {outcome})); panelUsageWrite(f, slot.value, "slot", QJSValue(true));
    auto number = panelUsageLiteral(f); panelUsageWrite(f, number.value, "text", numberString(f, panelUsageAdd(f, index, QJSValue(1))));
    panelUsageWrite(f, number.value, "color", chartStyle(f, "themeForegroundMinor"));
    auto icon = panelUsageLiteral(f); const auto names = panelUsageContextRead(f, "ParameterNames");
    panelUsageWrite(f, icon.value, "icon", panelUsageMemberCall(f, names, "blockIcon", {assistantContextField(f, "selector", "blockKind")}));
    const auto colors = panelUsageContextRead(f, "AppColors");
    panelUsageWrite(f, icon.value, "color", panelUsageMemberCall(f, colors, "block", {assistantContextField(f, "selector", "blockKind"), index}));
    const auto label = chartRecord(f, {{"text", name}, {"color", nameColor}, {"elides", QJSValue(true)}, {"factors", QJSValue(true)}});
    const bool hasSlot = !assistantContextField(f, "row", "outcomeRole").strictlyEquals(QJSValue(QStringLiteral("")));
    const auto numberValue = panelUsageComplete(f, number), iconValue = panelUsageComplete(f, icon), slotValue = panelUsageComplete(f, slot);
    const auto lead = hasSlot ? assistantGeometryArray(f, {numberValue, iconValue, slotValue}) : assistantGeometryArray(f, {numberValue, iconValue});
    auto tag = panelUsageLiteral(f); panelUsageWrite(f, tag.value, "text", projectInvoke(f, "Session", "label", {QJSValue(QStringLiteral("sequential_fit.template_file"))}));
    panelUsageWrite(f, tag.value, "color", chartStyle(f, "themeAccent")); const auto tagValue = panelUsageComplete(f, tag);
    const auto tail = panelUsageTruth(isTemplate) ? assistantGeometryArray(f, {label, tagValue}) : assistantGeometryArray(f, {label});
    return panelUsageMemberCall(f, lead, "concat", {tail});
}
void ApplicationInfo::activateBlock(const QJSValue& index, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this); projectInvoke(f, "row", "blockActivated", {index}); projectCall(f, restoreBinding);
}
QJSValue ApplicationInfo::correlationNumbers() const {
    const auto f = panelUsageEngine(this); const auto project = assistantContextField(f, "Session", "project");
    return panelUsageMemberCall(f, panelUsageContextRead(f, "labels"), "map", {panelUsageClosure(f, 223, {project}, 1)});
}
QJSValue ApplicationInfo::correlationEdgeText(const QJSValue& index) const {
    const auto f = panelUsageEngine(this); const auto source = panelUsageContextRead(f, panelUsageTruth(panelUsageContextRead(f, "namesShown")) ? "labels" : "numbers");
    return tableNullish(textIndex(f, source, index), QJSValue(QStringLiteral("")));
}
QJSValue ApplicationInfo::correlationValueAt(const QJSValue& index) const {
    const auto f = panelUsageEngine(this); if (assistantRelation(f, panelUsageContextRead(f, "count"), QJSValue(0), 3)) return panelUsageContextRead(f, "NaN");
    const auto row = numberMath(f, "floor", [&] { return QJSValueList{viewArithmetic(f, index, panelUsageContextRead(f, "count"), 2)}; });
    const auto column = chartBinary(f, index, panelUsageContextRead(f, "count"), true); auto source = index;
    if (panelUsageTruth(panelUsageContextRead(f, "fullMatrix")) && assistantRelation(f, column, row, 1))
        source = panelUsageAdd(f, viewArithmetic(f, column, panelUsageContextRead(f, "count"), 1), row);
    if (assistantRelation(f, source, QJSValue(0), 2) && assistantRelation(f, source, panelUsageRead(f, panelUsageContextRead(f, "values"), "length"), 0))
        return textIndex(f, panelUsageContextRead(f, "values"), source);
    return panelUsageContextRead(f, "NaN");
}
void ApplicationInfo::correlationCommit(const QJSValue& text, bool count) const {
    const auto f = panelUsageEngine(this); const auto value = panelUsageGlobalCall(f, count ? "parseInt" : "Number", {text});
    if (!panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {value}))) assistantMemberWrite(f, assistantContextField(f, "chart", "correlations"), count ? "maxParameters" : "level", value);
}
void ApplicationInfo::correlationNumberDone(const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this); const auto text = panelUsageContextRead(f, "text");
    if (!text.strictlyEquals(assistantContextField(f, "box", "shown"))) projectInvoke(f, "box", "committed", {panelUsageContextRead(f, "text")});
    projectCall(f, restoreBinding);
}
void ApplicationInfo::correlationToggle(bool full) const {
    const auto f = panelUsageEngine(this); const char* field = full ? "fullMatrix" : "namesShown";
    projectWrite(f, "chart", field, QJSValue(!panelUsageTruth(assistantContextField(f, "chart", field))));
}
QJSValue ApplicationInfo::correlationWidestLabel() const {
    const auto f = panelUsageEngine(this); QJSValue widest(0);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), assistantContextField(f, "chart", "count"), 0); ++i)
        widest = numberMath(f, "max", [&] {
            const auto metrics = panelUsageContextRead(f, "metrics");
            const auto text = projectInvoke(f, "chart", "edgeText", {QJSValue(i)});
            return QJSValueList{widest, panelUsageMemberCall(f, metrics, "advanceWidth", {text})};
        });
    return numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
}
QJSValue ApplicationInfo::structureHoverText(const QJSValue& result) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageRead(f, result, "objectHit").strictlyEquals(panelUsageContextRead(f, "spheresModel"))) {
        const auto controller = assistantContextField(f, "scene", "controller");
        return panelUsageMemberCall(f, controller, "hoverAtSphere", {panelUsageRead(f, result, "instanceIndex")});
    }
    if (panelUsageRead(f, result, "objectHit").strictlyEquals(panelUsageContextRead(f, "sharedModel"))) {
        const auto controller = assistantContextField(f, "scene", "controller");
        return panelUsageMemberCall(f, controller, "hoverAtShared", {panelUsageRead(f, panelUsageRead(f, result, "uvPosition"), "x")});
    }
    return QJSValue(QStringLiteral(""));
}
void ApplicationInfo::structurePointer(const QJSValue& event, int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 2) {
        if (panelUsageTruth(assistantContextField(f, "view", "report"))) assistantMemberWrite(f, event, "accepted", QJSValue(false));
        else {
            const auto controller = panelUsageContextRead(f, "controller");
            const QJSValueList args{panelUsageRead(f, event, "x"), panelUsageRead(f, event, "y"), panelUsageRead(f, panelUsageRead(f, event, "angleDelta"), "y")};
            panelUsageMemberCall(f, controller, "zoomAt", args);
        }
        return;
    }
    QJSValue dx, dy;
    if (kind == 1) {
        const auto x = panelUsageRead(f, event, "x"), previousX = panelUsageRead(f, assistantContextField(f, "pointer", "last"), "x"); dx = viewArithmetic(f, x, previousX, 0);
        const auto y = panelUsageRead(f, event, "y"), previousY = panelUsageRead(f, assistantContextField(f, "pointer", "last"), "y"); dy = viewArithmetic(f, y, previousY, 0);
    }
    const auto pointer = panelUsageContextRead(f, "pointer"), qt = panelUsageContextRead(f, "Qt");
    const QJSValueList coordinates{panelUsageRead(f, event, "x"), panelUsageRead(f, event, "y")};
    assistantMemberWrite(f, pointer, "last", panelUsageMemberCall(f, qt, "point", coordinates));
    if (kind == 0) { projectWrite(f, "hover", "text", QJSValue(QStringLiteral(""))); return; }
    const auto buttons = panelUsageRead(f, event, "buttons"), left = assistantContextField(f, "Qt", "LeftButton");
    if (panelUsageTruth(chartBinary(f, buttons, left, false))) projectInvoke(f, "controller", "rotateBy", {dx, dy});
    else {
        const auto other = panelUsageRead(f, event, "buttons"), right = assistantContextField(f, "Qt", "RightButton");
        if (panelUsageTruth(chartBinary(f, other, right, false))) projectInvoke(f, "controller", "panBy", {dx, dy});
        else {
            const auto hover = panelUsageContextRead(f, "hover");
            const QJSValueList args{panelUsageRead(f, event, "x"), panelUsageRead(f, event, "y")}; panelUsageMemberCall(f, hover, "show", args);
        }
    }
}
void ApplicationInfo::structureHoverShow(const QJSValue& x, const QJSValue& y) const {
    const auto f = panelUsageEngine(this); QJSValue result = consentNull();
    if (panelUsageTruth(assistantContextField(f, "view", "view3d"))) {
        const auto view = assistantContextField(f, "view", "view3d");
        const auto origin = projectInvoke(f, "controller", "pickOrigin", {x, y}), direction = projectInvoke(f, "controller", "pickDirection", {x, y});
        result = panelUsageMemberCall(f, view, "rayPick", {origin, direction});
    }
    const auto hover = panelUsageContextRead(f, "hover");
    assistantMemberWrite(f, hover, "text", panelUsageTruth(result) ? projectInvoke(f, "structureScene", "hoverText", {result}) : QJSValue(QStringLiteral("")));
    const auto horizontal = panelUsageContextRead(f, "hover");
    const auto atX = numberMath(f, "min", [&] {
        const auto first = panelUsageAdd(f, x, assistantContextField(f, "view", "margin"));
        const auto width = assistantContextField(f, "view", "width"), size = assistantContextField(f, "hover", "width");
        return QJSValueList{first, viewArithmetic(f, width, size, 0)};
    }); assistantMemberWrite(f, horizontal, "x", atX);
    const auto vertical = panelUsageContextRead(f, "hover");
    const auto atY = numberMath(f, "min", [&] {
        const auto first = panelUsageAdd(f, y, assistantContextField(f, "view", "margin"));
        const auto height = assistantContextField(f, "view", "height"), size = assistantContextField(f, "hover", "height");
        return QJSValueList{first, viewArithmetic(f, height, size, 0)};
    }); assistantMemberWrite(f, vertical, "y", atY);
}
void ApplicationInfo::structureColourChoice(const QJSValue& index) const {
    const auto f = panelUsageEngine(this); const auto options = assistantContextField(f, "view", "options");
    assistantMemberWrite(f, options, "colorScheme", QJSValue(index.strictlyEquals(QJSValue(1)) ? QStringLiteral("vesta") : QStringLiteral("jmol")));
}

namespace {
QJSValue chartAs(const PanelUsageFrame& f, const QJSValue& input, const char* name) {
    const auto type = panelUsageContextRead(f, name); if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), input)), target(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), type));
    QV4::ScopedValue result(scope, QV4::Runtime::As::call(f.vm(), *value, *target)); f.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue patternProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    if (operation == 240) return projectInvoke(f, "controller", "originalValue", {arg(0), saved(0)});
    if (operation == 241) {
        const auto axis = saved(0), low = panelUsageRead(f, axis, "min"); const auto numerator = viewArithmetic(f, arg(0), low, 0);
        const auto high = panelUsageRead(f, axis, "max"), lower = panelUsageRead(f, axis, "min");
        return viewArithmetic(f, numerator, viewArithmetic(f, high, lower, 0), 2);
    }
    const auto text = arg(0);
    if (operation == 242 && panelUsageTruth(panelUsageMemberCall(f, text, "startsWith", {QJSValue(QStringLiteral("x: "))}))) return text;
    const char* source = operation == 242 ? QT_TRANSLATE_NOOP("PatternChart", "x: %1") : QT_TRANSLATE_NOOP("PatternChart", "meas: %1");
    const auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(source))});
    return panelUsageMemberCall(f, format, "arg", {text});
}
QJSValue patternUnder(const PanelUsageFrame& f, const QJSValue& view) {
    const auto height = panelUsageRead(f, view, "height"), y = panelUsageRead(f, panelUsageRead(f, view, "plotArea"), "y");
    const auto first = viewArithmetic(f, height, y, 0);
    return viewArithmetic(f, first, panelUsageRead(f, panelUsageRead(f, view, "plotArea"), "height"), 0);
}
QJSValue patternAxisMargin(const PanelUsageFrame& f, const char* name) {
    const auto x = panelUsageRead(f, assistantContextField(f, name, "plotArea"), "x"), margin = assistantContextField(f, name, "marginLeft");
    return viewArithmetic(f, x, margin, 0);
}
void patternSetMargin(const PanelUsageFrame& f, const QJSValue& view, const QJSValue& margin) {
    const auto distance = numberMath(f, "abs", [&] { return QJSValueList{viewArithmetic(f, panelUsageRead(f, view, "marginLeft"), margin, 0)}; });
    if (assistantRelation(f, distance, QJSValue(0.5), 1)) assistantMemberWrite(f, view, "marginLeft", margin);
}
} // namespace

QJSValue ApplicationInfo::patternTickValues(const QJSValue& axis) const {
    const auto f = panelUsageEngine(this); const auto out = controlEmptyArray(f);
    const auto high = panelUsageRead(f, axis, "max"), low = panelUsageRead(f, axis, "min"); const auto span = viewArithmetic(f, high, low, 0);
    if (!assistantRelation(f, panelUsageRead(f, axis, "tickInterval"), QJSValue(0), 1) || !assistantRelation(f, span, QJSValue(0), 1)) return out;
    const auto first = numberMath(f, "ceil", [&] {
        const auto lower = panelUsageRead(f, axis, "min"), anchor = panelUsageRead(f, axis, "tickAnchor");
        const auto distance = viewArithmetic(f, lower, anchor, 0), interval = panelUsageRead(f, axis, "tickInterval");
        return QJSValueList{viewArithmetic(f, viewArithmetic(f, distance, interval, 2), QJSValue(1e-9), 0)};
    });
    auto index = first;
    while (panelUsageReady(f) && assistantRelation(f, panelUsageRead(f, out, "length"), QJSValue(64), 0)) {
        const auto anchor = panelUsageRead(f, axis, "tickAnchor"), interval = panelUsageRead(f, axis, "tickInterval");
        const auto value = panelUsageAdd(f, anchor, viewArithmetic(f, index, interval, 1));
        const auto fraction = viewArithmetic(f, viewArithmetic(f, value, panelUsageRead(f, axis, "min"), 0), span, 2);
        if (assistantRelation(f, fraction, QJSValue(1 + 1e-9), 1)) break;
        panelUsageMemberCall(f, out, "push", {value}); const auto number = panelUsageNumber(f, index); if (!number) return {};
        index = QJSValue(*number + 1);
    }
    return out;
}
QJSValue ApplicationInfo::patternYValues(const QJSValue& axis, const QJSValue& scale) const {
    const auto f = panelUsageEngine(this); const auto ticks = panelUsageGlobalCall(f, "tickValues", {axis});
    return panelUsageMemberCall(f, ticks, "map", {panelUsageClosure(f, 240, {scale}, 1)});
}
QJSValue ApplicationInfo::patternGridTicks(const QJSValue& axis) const {
    const auto f = panelUsageEngine(this); const auto ticks = projectInvoke(f, "chart", "tickValues", {axis});
    return panelUsageMemberCall(f, ticks, "map", {panelUsageClosure(f, 241, {axis}, 1)});
}
QJSValue ApplicationInfo::patternYLabelText(const QJSValue& text, const QJSValue& axis, const QJSValue& scale, const QJSValue& format) const {
    const auto f = panelUsageEngine(this); const auto shown = panelUsageGlobalCall(f, "Number", {text}); auto display = panelUsageContextRead(f, "NaN");
    panelUsageEach(f, panelUsageGlobalCall(f, "tickValues", {axis}), [&](const QJSValue& value) {
        bool nearer = panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {display}));
        if (!nearer) {
            const auto current = numberMath(f, "abs", [&] { return QJSValueList{viewArithmetic(f, value, shown, 0)}; });
            const auto previous = numberMath(f, "abs", [&] { return QJSValueList{viewArithmetic(f, display, shown, 0)}; });
            nearer = assistantRelation(f, current, previous, 0);
        }
        if (nearer) display = value; return panelUsageReady(f);
    });
    if (numberFinite(f, shown) && !panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {display}))) {
        const auto numbers = panelUsageContextRead(f, "NumberText"); const auto original = projectInvoke(f, "controller", "originalValue", {display, scale});
        return panelUsageMemberCall(f, numbers, "axisTick", {original, format});
    }
    return text;
}
QJSValue ApplicationInfo::patternYLabelsRoom() const {
    const auto f = panelUsageEngine(this); QJSValue widest(0);
    const auto measure = [&](const QJSValue& values, const char* format) {
        panelUsageEach(f, values, [&](const QJSValue& value) {
            widest = numberMath(f, "max", [&] {
                const auto metrics = panelUsageContextRead(f, "labelMetrics"), numbers = panelUsageContextRead(f, "NumberText");
                const auto text = panelUsageMemberCall(f, numbers, "axisTick", {value, panelUsageContextRead(f, format)});
                return QJSValueList{widest, panelUsageMemberCall(f, metrics, "advanceWidth", {text})};
            }); return panelUsageReady(f);
        });
    };
    const auto axis = panelUsageContextRead(f, "mainY"), scale = assistantContextField(f, "controller", "yScale");
    measure(panelUsageGlobalCall(f, "yValues", {axis, scale}), "mainYFormat");
    if (panelUsageTruth(assistantContextField(f, "controller", "hasResidual"))) {
        const auto residual = panelUsageContextRead(f, "residualY"), linear = assistantContextField(f, "PatternChartController", "Linear");
        measure(panelUsageGlobalCall(f, "yValues", {residual, linear}), "residualYFormat");
    }
    return numberMath(f, "ceil", [&] { return QJSValueList{panelUsageAdd(f, widest, viewArithmetic(f, panelUsageContextRead(f, "em"), QJSValue(0.5), 1))}; });
}
void ApplicationInfo::patternAlignPanes() const {
    const auto f = panelUsageEngine(this);
    if (assistantRelation(f, panelUsageRead(f, assistantContextField(f, "bottomView", "plotArea"), "height"), QJSValue(0), 1)) {
        const auto distance = numberMath(f, "abs", [&] {
            const auto height = panelUsageContextRead(f, "xLabelsHeight"); return QJSValueList{viewArithmetic(f, height, patternUnder(f, panelUsageContextRead(f, "bottomView")), 0)};
        });
        if (assistantRelation(f, distance, QJSValue(0.5), 1)) panelUsageContextWrite(f, "xLabelsHeight", patternUnder(f, panelUsageContextRead(f, "bottomView")));
    }
    const auto bottom = panelUsageContextRead(f, "bottomView"), main = panelUsageContextRead(f, "mainView");
    if (!bottom.strictlyEquals(main) && assistantRelation(f, panelUsageRead(f, assistantContextField(f, "mainView", "plotArea"), "height"), QJSValue(0), 1)) {
        const auto distance = numberMath(f, "abs", [&] {
            const auto height = panelUsageContextRead(f, "mainAxisHeight"); return QJSValueList{viewArithmetic(f, height, patternUnder(f, panelUsageContextRead(f, "mainView")), 0)};
        });
        if (assistantRelation(f, distance, QJSValue(0.5), 1)) panelUsageContextWrite(f, "mainAxisHeight", patternUnder(f, panelUsageContextRead(f, "mainView")));
    }
    const auto mainAxis = patternAxisMargin(f, "mainView");
    const auto residualAxis = panelUsageTruth(assistantContextField(f, "residualView", "visible")) ? patternAxisMargin(f, "residualView") : QJSValue(0);
    const auto edge = numberMath(f, "round", [&] {
        return QJSValueList{numberMath(f, "max", [&] {
            const auto side = panelUsageContextRead(f, "sideMargin"), gutter = panelUsageContextRead(f, "titleGutter"); const auto start = panelUsageAdd(f, side, gutter);
            const auto axis = numberMath(f, "max", [&] { return QJSValueList{mainAxis, residualAxis, panelUsageContextRead(f, "yLabelsRoom")}; });
            const auto first = panelUsageAdd(f, start, axis); const auto secondSide = panelUsageContextRead(f, "sideMargin"), labels = panelUsageContextRead(f, "braggLabelsRoom");
            const auto prefix = panelUsageAdd(f, secondSide, labels); const auto second = panelUsageAdd(f, prefix, panelUsageContextRead(f, "braggLabelGap"));
            return QJSValueList{first, second};
        })};
    });
    const auto mainView = panelUsageContextRead(f, "mainView"); patternSetMargin(f, mainView, viewArithmetic(f, edge, mainAxis, 0));
    const auto residualView = panelUsageContextRead(f, "residualView"); patternSetMargin(f, residualView, viewArithmetic(f, edge, residualAxis, 0));
    const auto bragg = panelUsageContextRead(f, "braggView"); patternSetMargin(f, bragg, viewArithmetic(f, edge, patternAxisMargin(f, "braggView"), 0));
}
QJSValue ApplicationInfo::patternClosedTexts(bool measured) const {
    const auto f = panelUsageEngine(this);
    return panelUsageMemberCall(f, panelUsageContextRead(f, "entries"), "map", {projectGuardedClosure(f, measured ? 243 : 242, 1)});
}
void ApplicationInfo::patternChoice(const QJSValue& index, int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) {
        if (assistantContextField(f, "chart", "settingsPage").strictlyEquals(QJSValue(QStringLiteral("pattern")))) {
            const auto preferences = panelUsageContextRead(f, "Preferences"); const auto tokens = assistantContextField(f, "chart", "scaleTokens");
            assistantMemberWrite(f, preferences, "patternYScale", textIndex(f, tokens, index));
        } else projectWrite(f, "controller", "yScale", index);
    } else if (kind == 1) {
        if (panelUsageTruth(assistantContextField(f, "chart", "axisProject"))) assistantMemberWrite(f, assistantContextField(f, "chart", "axisProject"), "patternDSpacing", QJSValue(index.strictlyEquals(QJSValue(1))));
        else projectWrite(f, "controller", "dSpacing", QJSValue(index.strictlyEquals(QJSValue(1))));
    } else {
        const auto preferences = panelUsageContextRead(f, "Preferences");
        assistantMemberWrite(f, preferences, "patternMeasuredStyle", textIndex(f, panelUsageContextRead(f, "tokens"), index));
    }
}
QJSValue ApplicationInfo::patternSameRanges(const QJSValue& a, const QJSValue& b) const {
    const auto f = panelUsageEngine(this); const auto aLength = panelUsageRead(f, a, "length"), bLength = panelUsageRead(f, b, "length");
    if (!aLength.strictlyEquals(bLength)) return QJSValue(false);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, a, "length"), 0); ++i) {
        const auto first = textIndex(f, a, QJSValue(i)), second = textIndex(f, b, QJSValue(i));
        if (!first.strictlyEquals(second) && !(panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {textIndex(f, a, QJSValue(i))}))
            && panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {textIndex(f, b, QJSValue(i))})))) return QJSValue(false);
    }
    return QJSValue(true);
}
void ApplicationInfo::patternViewChanged(int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        const auto ranges = assistantContextField(f, "controller", "viewRanges"), shared = assistantContextField(f, "AppState", "patternViewRanges");
        if (!panelUsageTruth(panelUsageGlobalCall(f, "sameRanges", {ranges, shared}))) {
            const auto state = panelUsageContextRead(f, "AppState"); assistantMemberWrite(f, state, "patternViewAxis", assistantContextField(f, "controller", "viewRangesAxis"));
            const auto next = panelUsageContextRead(f, "AppState"); assistantMemberWrite(f, next, "patternViewRanges", assistantContextField(f, "controller", "viewRanges"));
        }
    } else if (event == 4) {
        const auto chart = panelUsageContextRead(f, "chart"); const auto curveSlots = numberMath(f, "max", [&] {
            const auto previous = assistantContextField(f, "chart", "structureCurveSlots");
            return QJSValueList{previous, panelUsageRead(f, assistantContextField(f, "controller", "structureCurveColors"), "length")};
        }); assistantMemberWrite(f, chart, "structureCurveSlots", curveSlots);
    } else {
        const char* source = event == 1 ? "legendShown" : event == 2 ? "hoverShown" : "pointerMode";
        const char* destination = event == 1 ? "patternLegendShown" : event == 2 ? "patternHoverShown" : "patternPointerMode";
        const auto preferences = panelUsageContextRead(f, "Preferences"); assistantMemberWrite(f, preferences, destination, assistantContextField(f, "toolbar", source));
    }
}
void ApplicationInfo::patternStructureReady() const {
    const auto f = panelUsageEngine(this); const auto main = panelUsageContextRead(f, "mainView");
    panelUsageMemberCall(f, main, "insertSeries", {QJSValue(0), assistantContextField(f, "area", "outline")});
    projectInvoke(f, "mainView", "insertSeries", {QJSValue(0), panelUsageContextRead(f, "area")});
    const auto controller = panelUsageContextRead(f, "controller");
    const QJSValueList values{assistantContextField(f, "area", "index"), assistantContextField(f, "area", "upperSeries"), assistantContextField(f, "area", "lowerSeries"), assistantContextField(f, "area", "outline")};
    panelUsageMemberCall(f, controller, "setStructureSeries", values);
}
void ApplicationInfo::patternBraggSeries(const QJSValue& index, const QJSValue& series, bool added) const {
    const auto f = panelUsageEngine(this);
    if (added) { projectInvoke(f, "braggView", "addSeries", {series}); projectInvoke(f, "controller", "setBraggSeries", {index, series}); return; }
    projectInvoke(f, "controller", "setBraggSeries", {index, consentNull()}); const auto ticks = chartAs(f, series, "LineSeries");
    panelUsageMemberCall(f, ticks, "clear"); const auto nan = panelUsageContextRead(f, "NaN"), second = panelUsageContextRead(f, "NaN");
    panelUsageMemberCall(f, ticks, "append", {nan, second}); projectInvoke(f, "braggView", "removeSeries", {ticks});
}
QJSValue ApplicationInfo::patternBraggLabelsRoom() const {
    const auto f = panelUsageEngine(this); QJSValue widest(0);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), assistantContextField(f, "braggLabelRepeater", "count"), 0); ++i) {
        const auto label = projectInvoke(f, "braggLabelRepeater", "itemAt", {QJSValue(i)});
        if (panelUsageTruth(label) && panelUsageTruth(panelUsageRead(f, label, "visible"))) widest = numberMath(f, "max", [&] { return QJSValueList{widest, panelUsageRead(f, label, "width")}; });
    }
    return numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
}
void ApplicationInfo::patternPointer(const QJSValue& mouse, int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) {
        const auto x = panelUsageRead(f, mouse, "x"); panelUsageContextWrite(f, "lastX", x); panelUsageContextWrite(f, "pressX", x);
        panelUsageContextWrite(f, "pressY", panelUsageRead(f, mouse, "y")); return;
    }
    if (kind == 1) {
        bool panning = panelUsageTruth(panelUsageContextRead(f, "pressed"));
        if (panning) { const auto buttons = panelUsageContextRead(f, "pressedButtons"), left = assistantContextField(f, "Qt", "LeftButton"); panning = panelUsageTruth(chartBinary(f, buttons, left, false)); }
        if (panning && assistantContextField(f, "toolbar", "pointerMode").strictlyEquals(QJSValue(QStringLiteral("pan")))) {
            const auto controller = panelUsageContextRead(f, "controller"), x = panelUsageRead(f, mouse, "x"), previous = panelUsageContextRead(f, "lastX");
            panelUsageMemberCall(f, controller, "panBy", {viewArithmetic(f, x, previous, 0)}); panelUsageContextWrite(f, "lastX", panelUsageRead(f, mouse, "x"));
        }
        if (panelUsageTruth(assistantContextField(f, "toolbar", "hoverShown")) && !panelUsageTruth(panelUsageContextRead(f, "pressed")))
            projectInvoke(f, "hoverLabel", "read", {QJSValue(0), panelUsageContextRead(f, "pointer"), mouse});
        else projectInvoke(f, "hoverLabel", "show", {QJSValue(QStringLiteral("")), QJSValue(0), QJSValue(0)});
        return;
    }
    const auto horizontal = numberMath(f, "abs", [&] { const auto x = panelUsageRead(f, mouse, "x"), before = panelUsageContextRead(f, "pressX"); return QJSValueList{viewArithmetic(f, x, before, 0)}; });
    const auto horizontalLimit = viewArithmetic(f, assistantContextField(f, "chart", "em"), QJSValue(0.3), 1); bool still = assistantRelation(f, horizontal, horizontalLimit, 0);
    if (still) {
        const auto vertical = numberMath(f, "abs", [&] { const auto y = panelUsageRead(f, mouse, "y"), before = panelUsageContextRead(f, "pressY"); return QJSValueList{viewArithmetic(f, y, before, 0)}; });
        const auto limit = viewArithmetic(f, assistantContextField(f, "chart", "em"), QJSValue(0.3), 1); still = assistantRelation(f, vertical, limit, 0);
    }
    const auto button = panelUsageRead(f, mouse, "button"), left = assistantContextField(f, "Qt", "LeftButton");
    if (button.strictlyEquals(left) && still) {
        const auto legend = panelUsageContextRead(f, "chartLegend"); const QJSValueList values{panelUsageContextRead(f, "pointer"), panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")};
        if (panelUsageTruth(panelUsageMemberCall(f, legend, "toggleAt", values))) return;
    }
    const auto released = panelUsageRead(f, mouse, "button"), right = assistantContextField(f, "Qt", "RightButton");
    if (released.strictlyEquals(right)) projectInvoke(f, "controller", "reset");
    else if (assistantContextField(f, "toolbar", "pointerMode").strictlyEquals(QJSValue(QStringLiteral("zoom")))) {
        const auto controller = panelUsageContextRead(f, "controller");
        const QJSValueList values{panelUsageContextRead(f, "pressX"), panelUsageRead(f, mouse, "x"), panelUsageContextRead(f, "pressY"), panelUsageRead(f, mouse, "y")};
        panelUsageMemberCall(f, controller, "zoomTo", values);
    }
}
void ApplicationInfo::patternHoverRead(const QJSValue& pane, const QJSValue& area, const QJSValue& mouse) const {
    const auto f = panelUsageEngine(this); const auto controller = panelUsageContextRead(f, "controller");
    const QJSValueList values{panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y"), pane, panelUsageRead(f, area, "height")};
    const auto at = panelUsageMemberCall(f, controller, "hoverPoint", values); QJSValue text(QStringLiteral(""));
    if (!assistantRelation(f, panelUsageRead(f, at, "x"), QJSValue(0), 0)) {
        const auto owner = panelUsageContextRead(f, "controller");
        const QJSValueList args{panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y"), pane, panelUsageRead(f, area, "height")}; text = panelUsageMemberCall(f, owner, "hoverReadout", args);
    }
    const auto x = panelUsageRead(f, area, "x"), atX = panelUsageRead(f, at, "x"); const auto horizontal = panelUsageAdd(f, x, atX);
    const auto y = panelUsageRead(f, area, "y"), atY = panelUsageRead(f, at, "y"); const auto vertical = panelUsageAdd(f, y, atY);
    panelUsageGlobalCall(f, "show", {text, horizontal, vertical});
}
namespace {
void chartHoverPosition(const PanelUsageFrame& f, const QJSValue& atX, const QJSValue& atY) {
    const auto first = panelUsageAdd(f, atX, assistantContextField(f, "chart", "em")), right = panelUsageAdd(f, first, panelUsageContextRead(f, "width"));
    QJSValue x;
    if (assistantRelation(f, right, assistantContextField(f, "chart", "width"), 3)) x = panelUsageAdd(f, atX, assistantContextField(f, "chart", "em"));
    else { const auto start = viewArithmetic(f, atX, assistantContextField(f, "chart", "em"), 0); x = viewArithmetic(f, start, panelUsageContextRead(f, "width"), 0); }
    panelUsageContextWrite(f, "x", x);
    const auto start = viewArithmetic(f, atY, panelUsageContextRead(f, "height"), 0), em = assistantContextField(f, "chart", "em");
    const auto top = viewArithmetic(f, start, viewArithmetic(f, em, QJSValue(0.5), 1), 0); QJSValue y;
    if (assistantRelation(f, top, QJSValue(0), 2)) {
        const auto before = viewArithmetic(f, atY, panelUsageContextRead(f, "height"), 0), currentEm = assistantContextField(f, "chart", "em");
        y = viewArithmetic(f, before, viewArithmetic(f, currentEm, QJSValue(0.5), 1), 0);
    } else y = panelUsageAdd(f, atY, assistantContextField(f, "chart", "em"));
    panelUsageContextWrite(f, "y", y);
}
} // namespace
void ApplicationInfo::patternHoverShow(const QJSValue& text, const QJSValue& atX, const QJSValue& atY) const {
    const auto f = panelUsageEngine(this); projectWrite(f, "hoverText", "text", text);
    chartHoverPosition(f, atX, atY);
}
void ApplicationInfo::chartToolbarAction(int action) const {
    const auto f = panelUsageEngine(this);
    if (action == 3 || action == 4) { projectWrite(f, "toolbar", "pointerMode", QJSValue(action == 3 ? QStringLiteral("pan") : QStringLiteral("zoom"))); return; }
    const bool preference = action == 2 || action == 5 || action == 6; const char* owner = preference ? "Preferences" : "toolbar";
    const char* field = action == 0 ? "legendShown" : action == 1 ? "hoverShown" : action == 2 ? "structureCurves" : action == 5 ? "chartIncludedOnly" : "chartSubtractBackground";
    const auto object = panelUsageContextRead(f, owner); assistantMemberWrite(f, object, field, QJSValue(!panelUsageTruth(assistantContextField(f, owner, field))));
}
void ApplicationInfo::renewPatternChart() const {
    const auto f = panelUsageEngine(this); const auto old = assistantContextField(f, "holder", "chart"), holder = panelUsageContextRead(f, "holder");
    const auto made = projectInvoke(f, "chartComponent", "createObject", {panelUsageContextRead(f, "holder")});
    assistantMemberWrite(f, holder, "chart", chartAs(f, made, "PatternChart"));
    if (panelUsageTruth(old)) { assistantMemberWrite(f, old, "visible", QJSValue(false)); panelUsageMemberCall(f, old, "destroy"); }
}

namespace {
QJSValue chartCapitalisedValue(const PanelUsageFrame& f, const QJSValue& value) {
        if (!assistantRelation(f, panelUsageRead(f, value, "length"), QJSValue(0), 1)) return value;
        const auto first = panelUsageMemberCall(f, value, "charAt", {QJSValue(0)});
        const auto upper = panelUsageMemberCall(f, first, "toUpperCase");
        return panelUsageAdd(f, upper, panelUsageMemberCall(f, value, "slice", {QJSValue(1)}));

}
QJSValue evolutionProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>& arg) {
    const auto value = arg(0);
    if (operation == 260) return QJSValue(panelUsageRead(f, value, "key").strictlyEquals(QJSValue(QStringLiteral("meas.0"))));
    if (operation == 261) return chartCapitalisedValue(f, value);
    if (operation == 262) {
        const auto text = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("EvolutionChart", "x: %1")))});
        return panelUsageMemberCall(f, text, "arg", {value});
    }
    if (operation == 263 || operation == 264) return panelUsageRead(f, value, operation == 263 ? "x" : "y");
    if (numberType(f, panelUsageRead(f, value, "su"))) return panelUsageRead(f, value, "su");
    return panelUsageContextRead(f, "NaN");
}
QJSValue chartSpan(const PanelUsageFrame& f, const char* axis) {
    const auto high = assistantContextField(f, axis, "max"), low = assistantContextField(f, axis, "min");
    return viewArithmetic(f, high, low, 0);
}
QJSValue chartCoordinateValue(const PanelUsageFrame& f, const std::function<QJSValue()>& position, bool vertical) {
    const char* axis = vertical ? "axisY" : "axisX";
    const auto start = assistantContextField(f, axis, vertical ? "max" : "min"), point = position();
    const auto fraction = viewArithmetic(f, point, panelUsageContextRead(f, vertical ? "height" : "width"), 2);
    const auto scaled = viewArithmetic(f, fraction, chartSpan(f, axis), 1);
    return vertical ? viewArithmetic(f, start, scaled, 0) : panelUsageAdd(f, start, scaled);
}
bool evolutionMovedIn(const PanelUsageFrame& f, const QJSValue& mouse, const char* coordinate, const char* pressed) {
    const auto distance = numberMath(f, "abs", [&] {
        const auto point = panelUsageRead(f, mouse, coordinate), before = panelUsageContextRead(f, pressed);
        return QJSValueList{viewArithmetic(f, point, before, 0)};
    });
    const auto limit = viewArithmetic(f, assistantContextField(f, "chart", "em"), QJSValue(0.3), 1);
    return assistantRelation(f, distance, limit, 1);
}
QJSValue evolutionWheelEnd(const PanelUsageFrame& f, const QJSValue& anchor, const QJSValue& factor, bool right) {
    const auto end = assistantContextField(f, "axisX", right ? "max" : "min");
    const auto difference = right ? viewArithmetic(f, end, anchor, 0) : viewArithmetic(f, anchor, end, 0);
    const auto scaled = viewArithmetic(f, difference, factor, 1);
    return right ? panelUsageAdd(f, anchor, scaled) : viewArithmetic(f, anchor, scaled, 0);
}
} // namespace

QJSValue ApplicationInfo::chartNiceStep(const QJSValue& span, const QJSValue& count) const {
    const auto f = panelUsageEngine(this); if (!assistantRelation(f, span, QJSValue(0), 1)) return QJSValue(1);
    const auto raw = viewArithmetic(f, span, count, 2);
    const auto power = numberPower(f, [&] {
        return numberMath(f, "floor", [&] { return QJSValueList{numberMath(f, "log10", [&] { return QJSValueList{raw}; })}; });
    });
    const auto scaled = viewArithmetic(f, raw, power, 2);
    const QJSValue step(assistantRelation(f, scaled, QJSValue(1.5), 0) ? 1 : assistantRelation(f, scaled, QJSValue(3.5), 0) ? 2 : assistantRelation(f, scaled, QJSValue(7.5), 0) ? 5 : 10);
    return viewArithmetic(f, step, power, 1);
}
QJSValue ApplicationInfo::chartGridShares(const QJSValue& axis) const {
    const auto f = panelUsageEngine(this); const auto out = controlEmptyArray(f);
    const auto high = panelUsageRead(f, axis, "max"), low = panelUsageRead(f, axis, "min"); const auto span = viewArithmetic(f, high, low, 0);
    if (!assistantRelation(f, panelUsageRead(f, axis, "tickInterval"), QJSValue(0), 1) || !assistantRelation(f, span, QJSValue(0), 1)) return out;
    auto index = numberMath(f, "ceil", [&] {
        const auto lower = panelUsageRead(f, axis, "min"), interval = panelUsageRead(f, axis, "tickInterval");
        return QJSValueList{viewArithmetic(f, viewArithmetic(f, lower, interval, 2), QJSValue(1e-9), 0)};
    });
    while (panelUsageReady(f) && assistantRelation(f, panelUsageRead(f, out, "length"), QJSValue(64), 0)) {
        const auto point = viewArithmetic(f, index, panelUsageRead(f, axis, "tickInterval"), 1);
        const auto share = viewArithmetic(f, viewArithmetic(f, point, panelUsageRead(f, axis, "min"), 0), span, 2);
        if (assistantRelation(f, share, QJSValue(1 + 1e-9), 1)) break;
        panelUsageMemberCall(f, out, "push", {share}); const auto current = panelUsageNumber(f, index); if (!current) return {};
        index = QJSValue(*current + 1);
    }
    return out;
}
QJSValue ApplicationInfo::chartCoordinate(const QJSValue& position, bool vertical) const {
    const auto f = panelUsageEngine(this); return chartCoordinateValue(f, [&] { return position; }, vertical);
}
QJSValue ApplicationInfo::evolutionMeasuredStyle() const {
    const auto f = panelUsageEngine(this); const auto original = panelUsageContextRead(f, "reportStyles");
    const auto styles = original.isNull() || original.isUndefined() ? controlEmptyArray(f) : original;
    return tableNullish(panelUsageMemberCall(f, styles, "find", {projectGuardedClosure(f, 260, 1)}), consentNull());
}
QJSValue ApplicationInfo::evolutionReportRange() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageRead(f, panelUsageContextRead(f, "reportPoints"), "length").strictlyEquals(QJSValue(0))) return assistantGeometryArray(f, {QJSValue(0), QJSValue(1), QJSValue(0), QJSValue(1)});
    auto xMin = panelUsageContextRead(f, "Infinity"), xMax = numberNegate(f, panelUsageContextRead(f, "Infinity"));
    auto yMin = panelUsageContextRead(f, "Infinity"), yMax = numberNegate(f, panelUsageContextRead(f, "Infinity"));
    panelUsageEach(f, panelUsageContextRead(f, "reportPoints"), [&](const QJSValue& point) {
        QJSValue su(0);
        if (numberType(f, panelUsageRead(f, point, "su")) && numberFinite(f, panelUsageRead(f, point, "su"))) su = panelUsageRead(f, point, "su");
        xMin = numberMath(f, "min", [&] { return QJSValueList{xMin, panelUsageRead(f, point, "x")}; });
        xMax = numberMath(f, "max", [&] { return QJSValueList{xMax, panelUsageRead(f, point, "x")}; });
        yMin = numberMath(f, "min", [&] { return QJSValueList{yMin, viewArithmetic(f, panelUsageRead(f, point, "y"), su, 0)}; });
        yMax = numberMath(f, "max", [&] { return QJSValueList{yMax, panelUsageAdd(f, panelUsageRead(f, point, "y"), su)}; });
        return panelUsageReady(f);
    });
    const auto xPad = numberMath(f, "max", [&] { return QJSValueList{viewArithmetic(f, viewArithmetic(f, xMax, xMin, 0), QJSValue(0.06), 1), QJSValue(0.5)}; });
    const auto yPad = numberMath(f, "max", [&] {
        const auto first = viewArithmetic(f, viewArithmetic(f, yMax, yMin, 0), QJSValue(0.16), 1);
        const auto second = panelUsageAdd(f, viewArithmetic(f, numberAbs(f, yMax), QJSValue(1e-6), 1), QJSValue(1e-12));
        return QJSValueList{first, second};
    });
    return assistantGeometryArray(f, {viewArithmetic(f, xMin, xPad, 0), panelUsageAdd(f, xMax, xPad), viewArithmetic(f, yMin, yPad, 0), panelUsageAdd(f, yMax, yPad)});
}
QJSValue ApplicationInfo::evolutionXEntries(bool closed) const {
    const auto f = panelUsageEngine(this);
    if (closed) return panelUsageMemberCall(f, panelUsageContextRead(f, "entries"), "map", {projectGuardedClosure(f, 262, 1)});
    if (!panelUsageTruth(assistantContextField(f, "chart", "evolution"))) return controlEmptyArray(f);
    const auto modes = panelUsageRead(f, assistantContextField(f, "chart", "evolution"), "xModes");
    return panelUsageMemberCall(f, modes, "map", {projectGuardedClosure(f, 261, 1)});
}
QJSValue ApplicationInfo::evolutionMoved(const QJSValue& mouse) const {
    const auto f = panelUsageEngine(this); return QJSValue(evolutionMovedIn(f, mouse, "x", "pressX") || evolutionMovedIn(f, mouse, "y", "pressY"));
}
void ApplicationInfo::evolutionPointer(const QJSValue& mouse, int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        panelUsageContextWrite(f, "pressX", panelUsageRead(f, mouse, "x")); panelUsageContextWrite(f, "pressY", panelUsageRead(f, mouse, "y"));
        const auto button = panelUsageRead(f, mouse, "button"), left = assistantContextField(f, "Qt", "LeftButton"); panelUsageContextWrite(f, "picking", QJSValue(button.strictlyEquals(left))); return;
    }
    if (event == 1) { if (panelUsageTruth(panelUsageGlobalCall(f, "moved", {mouse}))) panelUsageContextWrite(f, "picking", QJSValue(false)); return; }
    if (event == 2) {
        const auto button = panelUsageRead(f, mouse, "button"), right = assistantContextField(f, "Qt", "RightButton");
        if (button.strictlyEquals(right)) { panelUsageContextWrite(f, "picking", QJSValue(false)); projectWrite(f, "chart", "zoom", controlEmptyArray(f)); }
        else if (panelUsageTruth(panelUsageGlobalCall(f, "moved", {mouse}))) {
            panelUsageContextWrite(f, "picking", QJSValue(false)); QJSValueList ends;
            for (const auto& operation : {std::array<const char*, 3>{"min", "xAt", "pressX"}, {"max", "xAt", "pressX"}, {"min", "yAt", "pressY"}, {"max", "yAt", "pressY"}})
                ends.append(numberMath(f, operation[0], [&] {
                    const auto first = panelUsageGlobalCall(f, operation[1], {panelUsageContextRead(f, operation[2])});
                    const auto second = panelUsageGlobalCall(f, operation[1], {panelUsageRead(f, mouse, std::string_view(operation[1]) == "xAt" ? "x" : "y")});
                    return QJSValueList{first, second};
                }));
            const auto box = assistantGeometryArray(f, ends);
            bool valid = evolutionMovedIn(f, mouse, "x", "pressX") && evolutionMovedIn(f, mouse, "y", "pressY");
            if (valid) { const auto high = textIndex(f, box, QJSValue(1)), low = textIndex(f, box, QJSValue(0)); valid = assistantRelation(f, high, low, 1); }
            if (valid) { const auto high = textIndex(f, box, QJSValue(3)), low = textIndex(f, box, QJSValue(2)); valid = assistantRelation(f, high, low, 1); }
            if (valid) { const auto high = textIndex(f, box, QJSValue(1)), low = textIndex(f, box, QJSValue(0)); valid = numberFinite(f, viewArithmetic(f, high, low, 0)); }
            if (valid) { const auto high = textIndex(f, box, QJSValue(3)), low = textIndex(f, box, QJSValue(2)); valid = numberFinite(f, viewArithmetic(f, high, low, 0)); }
            if (valid) projectWrite(f, "chart", "zoom", box);
        }
        return;
    }
    if (event == 3) {
        if (assistantContextField(f, "chart", "evolution").isNull()) return;
        const auto reach = viewArithmetic(f, assistantContextField(f, "chart", "em"), QJSValue(0.6), 1), evolution = assistantContextField(f, "chart", "evolution");
        QJSValueList args;
        args.append(chartCoordinateValue(f, [&] { return panelUsageRead(f, mouse, "x"); }, false));
        args.append(chartCoordinateValue(f, [&] { return panelUsageRead(f, mouse, "y"); }, true));
        const auto xReach = viewArithmetic(f, reach, panelUsageContextRead(f, "width"), 2); args.append(viewArithmetic(f, xReach, chartSpan(f, "axisX"), 1));
        const auto yReach = viewArithmetic(f, reach, panelUsageContextRead(f, "height"), 2); args.append(viewArithmetic(f, yReach, chartSpan(f, "axisY"), 1));
        const auto dataset = panelUsageMemberCall(f, evolution, "datasetAt", args);
        if (assistantRelation(f, dataset, QJSValue(0), 2)) assistantMemberWrite(f, assistantContextField(f, "chart", "project"), "currentExperimentIndex", dataset); return;
    }
    if (panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y").strictlyEquals(QJSValue(0))) return;
    const auto anchor = panelUsageGlobalCall(f, "xAt", {panelUsageRead(f, mouse, "x")});
    const auto factor = numberMath(f, "pow", [&] { return QJSValueList{QJSValue(0.8), viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y"), QJSValue(120), 2)}; });
    const auto left = evolutionWheelEnd(f, anchor, factor, false), right = evolutionWheelEnd(f, anchor, factor, true);
    bool valid = numberFinite(f, left) && numberFinite(f, right) && assistantRelation(f, right, left, 1) && numberFinite(f, viewArithmetic(f, right, left, 0));
    if (valid) { const auto high = assistantContextField(f, "axisY", "max"), low = assistantContextField(f, "axisY", "min"); valid = assistantRelation(f, high, low, 1); }
    if (valid) valid = numberFinite(f, chartSpan(f, "axisY"));
    if (!valid) return;
    const auto chart = panelUsageContextRead(f, "chart"); const QJSValueList ends{evolutionWheelEnd(f, anchor, factor, false), evolutionWheelEnd(f, anchor, factor, true), assistantContextField(f, "axisY", "min"), assistantContextField(f, "axisY", "max")};
    assistantMemberWrite(f, chart, "zoom", assistantGeometryArray(f, ends));
}
void ApplicationInfo::evolutionResetZoom() const { const auto f = panelUsageEngine(this); projectWrite(f, "chart", "zoom", controlEmptyArray(f)); }
void ApplicationInfo::evolutionDrawReportPoints() const {
    const auto f = panelUsageEngine(this); const auto layer = panelUsageContextRead(f, "layer"); QJSValueList args;
    for (uint operation : {263u, 264u, 265u}) args.append(panelUsageMemberCall(f, panelUsageContextRead(f, "reportPoints"), "map", {projectGuardedClosure(f, operation, 1)}));
    panelUsageMemberCall(f, layer, "setPoints", args);
}
void ApplicationInfo::evolutionReportChanged() const {
    const auto f = panelUsageEngine(this); if (panelUsageTruth(panelUsageContextRead(f, "fromReport"))) panelUsageGlobalCall(f, "drawReportPoints");
}

namespace {
QJSValue chartSpreadCall(const PanelUsageFrame& f, const QJSValue& receiver, const char* name, const QJSValue& values) {
    if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue object(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), receiver));
    QV4::ScopedString key(scope, f.vm()->newString(QString::fromLatin1(name))); QV4::ScopedValue function(scope, panelUsageGet(f, *object, key, true));
    if (!panelUsageReady(f)) return {};
    QV4::Value* args = scope.constructUndefined(2); args[0].setEmpty(); args[1] = QJSValuePrivate::convertToReturnedValue(f.vm(), values);
    QV4::ScopedValue result(scope, QV4::Runtime::CallWithSpread::call(f.vm(), *function, *object, args, 2)); f.checked();
    return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
QJSValue singleNamedExperiments(const PanelUsageFrame& f, bool explicitChart) {
    const auto read = [&](const char* name) { return explicitChart ? assistantContextField(f, "chart", name) : panelUsageContextRead(f, name); };
    if (panelUsageTruth(read("stacked"))) return read("stackedExperiments");
    return panelUsageTruth(read("experiment")) ? assistantGeometryArray(f, {read("experiment")}) : controlEmptyArray(f);
}
QJSValue singleProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    const auto value = arg(0);
    if (operation == 280) {
        if (!panelUsageTruth(value)) return value;
        const auto model = panelUsageRead(f, value, "singleCrystalReflections"); if (!panelUsageTruth(model)) return model;
        const auto hidden = panelUsageContextRead(f, "hiddenRows"); return panelUsageMemberCall(f, hidden, "includes", {panelUsageRead(f, value, "name")});
    }
    if (operation == 281) return panelUsageRead(f, value, "singleCrystalReflections");
    if (operation == 282) return QJSValue(!panelUsageTruth(panelUsageMemberCall(f, panelUsageContextRead(f, "hiddenModels"), "includes", {value})));
    if (operation == 283) return panelUsageRead(f, value, "calculatedShown");
    if (operation == 284 || operation == 285) {
        const bool squared = panelUsageTruth(panelUsageContextRead(f, "squared"));
        return panelUsageRead(f, value, operation == 284 ? (squared ? "low" : "lowF") : (squared ? "high" : "highF"));
    }
    if (operation == 286) return panelUsageTruth(value) ? panelUsageRead(f, value, "name") : QJSValue(QStringLiteral(""));
    if (operation == 287) {
        const auto colors = panelUsageContextRead(f, "AppColors");
        const auto index = panelUsageTruth(assistantContextField(f, "chart", "stacked")) ? arg(1) : QJSValue(0);
        const auto dark = panelUsageRead(f, assistantContextField(f, "chart", "colors"), "isDarkPalette");
        return numberString(f, panelUsageMemberCall(f, colors, "experiment", {index, dark}));
    }
    if (operation == 288) return QJSValue(!value.strictlyEquals(saved(0)));
    return {};
}
void singleEmptyPoints(const PanelUsageFrame& f, const QJSValue& layer) {
    const QJSValueList values{controlEmptyArray(f), controlEmptyArray(f), controlEmptyArray(f)};
    panelUsageMemberCall(f, layer, "setPoints", values);
}
bool singleBoxIncreasing(const PanelUsageFrame& f, const QJSValue& box, bool spans) {
    auto high = textIndex(f, box, QJSValue(1)), low = textIndex(f, box, QJSValue(0)); if (!assistantRelation(f, high, low, 1)) return false;
    high = textIndex(f, box, QJSValue(3)); low = textIndex(f, box, QJSValue(2)); if (!assistantRelation(f, high, low, 1)) return false;
    if (spans) {
        high = textIndex(f, box, QJSValue(1)); low = textIndex(f, box, QJSValue(0)); if (!numberFinite(f, viewArithmetic(f, high, low, 0))) return false;
        high = textIndex(f, box, QJSValue(3)); low = textIndex(f, box, QJSValue(2)); if (!numberFinite(f, viewArithmetic(f, high, low, 0))) return false;
    }
    return panelUsageReady(f);
}
bool singleStillIn(const PanelUsageFrame& f, const QJSValue& mouse, const char* name, const char* pressed) {
    const auto distance = numberMath(f, "abs", [&] { const auto point = panelUsageRead(f, mouse, name), before = panelUsageContextRead(f, pressed); return QJSValueList{viewArithmetic(f, point, before, 0)}; });
    const auto limit = viewArithmetic(f, assistantContextField(f, "chart", "em"), QJSValue(0.3), 1);
    return assistantRelation(f, distance, limit, 0);
}
QJSValue singleWheelEnd(const PanelUsageFrame& f, const QJSValue& anchor, const QJSValue& factor, const char* axis, bool high) {
    const auto edge = assistantContextField(f, axis, high ? "max" : "min");
    const auto distance = high ? viewArithmetic(f, edge, anchor, 0) : viewArithmetic(f, anchor, edge, 0);
    const auto scaled = viewArithmetic(f, distance, factor, 1);
    return high ? panelUsageAdd(f, anchor, scaled) : viewArithmetic(f, anchor, scaled, 0);
}
} // namespace

QJSValue ApplicationInfo::singleModels() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "stacked"))) return panelUsageTruth(panelUsageContextRead(f, "reflections")) ? assistantGeometryArray(f, {panelUsageContextRead(f, "reflections")}) : controlEmptyArray(f);
    const auto out = controlEmptyArray(f);
    panelUsageEach(f, panelUsageContextRead(f, "stackedExperiments"), [&](const QJSValue& shown) {
        if (panelUsageTruth(shown) && panelUsageTruth(panelUsageRead(f, shown, "singleCrystalReflections"))) panelUsageMemberCall(f, out, "push", {panelUsageRead(f, shown, "singleCrystalReflections")});
        return panelUsageReady(f);
    }); return out;
}
QJSValue ApplicationInfo::singleHiddenModels() const {
    const auto f = panelUsageEngine(this); const auto named = singleNamedExperiments(f, false);
    const auto hidden = panelUsageMemberCall(f, named, "filter", {projectGuardedClosure(f, 280, 1)});
    return panelUsageMemberCall(f, hidden, "map", {projectGuardedClosure(f, 281, 1)});
}
QJSValue ApplicationInfo::singleRangeModels() const {
    const auto f = panelUsageEngine(this);
    if (!assistantContextField(f, "Preferences", "chartHiddenRange").strictlyEquals(QJSValue(QStringLiteral("fit")))) return panelUsageContextRead(f, "models");
    return panelUsageMemberCall(f, panelUsageContextRead(f, "models"), "filter", {projectGuardedClosure(f, 282, 1)});
}
QJSValue ApplicationInfo::singleCalculated() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(panelUsageContextRead(f, "reportMode"))) return QJSValue(assistantRelation(f, panelUsageRead(f, assistantContextField(f, "reportData", "calc"), "length"), QJSValue(0), 1));
    const auto revision = panelUsageContextRead(f, "revision"); Q_UNUSED(revision)
    return panelUsageMemberCall(f, panelUsageContextRead(f, "models"), "some", {projectGuardedClosure(f, 283, 1)});
}
QJSValue ApplicationInfo::singleReportRange() const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(panelUsageContextRead(f, "reportMode"))) return assistantGeometryArray(f, {QJSValue(0), QJSValue(1)});
    auto low = panelUsageContextRead(f, "Infinity"), high = numberNegate(f, panelUsageContextRead(f, "Infinity"));
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, assistantContextField(f, "reportData", "meas"), "length"), 0); ++i) {
        QJSValueList values;
        const auto first = textIndex(f, assistantContextField(f, "reportData", "meas"), QJSValue(i)), su = textIndex(f, assistantContextField(f, "reportData", "su"), QJSValue(i));
        values.append(viewArithmetic(f, first, su, 0));
        const auto second = textIndex(f, assistantContextField(f, "reportData", "meas"), QJSValue(i)), error = textIndex(f, assistantContextField(f, "reportData", "su"), QJSValue(i));
        values.append(panelUsageAdd(f, second, error)); values.append(textIndex(f, assistantContextField(f, "reportData", "calc"), QJSValue(i)));
        panelUsageEach(f, assistantGeometryArray(f, values), [&](const QJSValue& end) {
            if (numberFinite(f, end)) { low = numberMath(f, "min", [&] { return QJSValueList{low, end}; }); high = numberMath(f, "max", [&] { return QJSValueList{high, end}; }); }
            return panelUsageReady(f);
        });
    }
    if (!assistantRelation(f, high, low, 1)) return assistantGeometryArray(f, {QJSValue(0), QJSValue(1)});
    const auto pad = viewArithmetic(f, viewArithmetic(f, high, low, 0), QJSValue(0.05), 1);
    const QJSValueList ends{numberMath(f, "min", [&] { return QJSValueList{QJSValue(0), viewArithmetic(f, low, pad, 0)}; }), panelUsageAdd(f, high, pad)};
    return assistantGeometryArray(f, ends);
}
QJSValue ApplicationInfo::singleFullRange(bool high) const {
    const auto f = panelUsageEngine(this); if (panelUsageTruth(panelUsageContextRead(f, "reportMode"))) return textIndex(f, panelUsageContextRead(f, "reportRange"), QJSValue(high ? 1 : 0));
    const auto revision = panelUsageContextRead(f, "revision"); Q_UNUSED(revision)
    const auto shown = panelUsageMemberCall(f, panelUsageContextRead(f, "rangeModels"), "filter", {projectGuardedClosure(f, 283, 1)});
    const auto values = panelUsageMemberCall(f, shown, "map", {projectGuardedClosure(f, high ? 285 : 284, 1)});
    const auto finite = panelUsageMemberCall(f, values, "filter", {panelUsageContextRead(f, "isFinite")});
    if (assistantRelation(f, panelUsageRead(f, finite, "length"), QJSValue(0), 1)) return chartSpreadCall(f, panelUsageContextRead(f, "Math"), high ? "max" : "min", finite);
    return QJSValue(high ? 1 : 0);
}
void ApplicationInfo::singleUpdateLegend() const {
    const auto f = panelUsageEngine(this); const auto named = singleNamedExperiments(f, true), rows = panelUsageContextRead(f, "legendRows");
    QJSValueList args;
    args.append(panelUsageMemberCall(f, named, "map", {projectGuardedClosure(f, 286, 1)}));
    args.append(panelUsageMemberCall(f, named, "map", {projectGuardedClosure(f, 287, 2)}));
    QJSValue selected(-1);
    if (panelUsageTruth(assistantContextField(f, "chart", "stacked")) && !panelUsageTruth(assistantContextField(f, "Preferences", "chartHighlightSelected"))) selected = assistantContextField(f, "chart", "selectedIndex");
    args.append(selected); args.append(assistantContextField(f, "chart", "hiddenRows")); panelUsageMemberCall(f, rows, "setRows", args);
}
void ApplicationInfo::singleToggleRow(const QJSValue& key) const {
    const auto f = panelUsageEngine(this); const auto chart = panelUsageContextRead(f, "chart"); QJSValue rows;
    if (panelUsageTruth(panelUsageMemberCall(f, assistantContextField(f, "chart", "hiddenRows"), "includes", {key})))
        rows = panelUsageMemberCall(f, assistantContextField(f, "chart", "hiddenRows"), "filter", {panelUsageClosure(f, 288, {key}, 1)});
    else rows = panelUsageMemberCall(f, assistantContextField(f, "chart", "hiddenRows"), "concat", {assistantGeometryArray(f, {key})});
    assistantMemberWrite(f, chart, "hiddenRows", rows);
    if (assistantContextField(f, "Preferences", "chartHiddenRange").strictlyEquals(QJSValue(QStringLiteral("fit")))) projectWrite(f, "chart", "zoom", controlEmptyArray(f));
    projectInvoke(f, "chart", "updateLegend");
}
QJSValue ApplicationInfo::singlePart(const QJSValue& x, const QJSValue& y, const QJSValue& su, const QJSValue& used, const QJSValue& want) const {
    const auto f = panelUsageEngine(this); const QJSValueList empty{controlEmptyArray(f), controlEmptyArray(f), controlEmptyArray(f)}; const auto out = assistantGeometryArray(f, empty);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, x, "length"), 0); ++i) {
        QJSValue take(true);
        if (panelUsageTruth(used) && assistantRelation(f, QJSValue(i), panelUsageRead(f, used, "length"), 0)) take = textIndex(f, used, QJSValue(i));
        if (take.strictlyEquals(want)) for (int column = 0; column < 3; ++column) {
            const auto destination = textIndex(f, out, QJSValue(column)); const auto value = textIndex(f, column == 0 ? x : column == 1 ? y : su, QJSValue(i));
            panelUsageMemberCall(f, destination, "push", {value});
        }
    }
    return out;
}
void ApplicationInfo::singleDrawModel(const QJSValue& model, const QJSValue& usedLayer, const QJSValue& leftOutLayer) const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(model) || !panelUsageTruth(assistantContextField(f, "chart", "shown")) || !panelUsageTruth(panelUsageRead(f, model, "calculatedShown"))) { singleEmptyPoints(f, usedLayer); singleEmptyPoints(f, leftOutLayer); return; }
    const auto x = panelUsageRead(f, model, panelUsageTruth(assistantContextField(f, "chart", "squared")) ? "calculated" : "calculatedF");
    const auto y = panelUsageRead(f, model, panelUsageTruth(assistantContextField(f, "chart", "squared")) ? "measured" : "measuredF");
    const auto su = panelUsageRead(f, model, panelUsageTruth(assistantContextField(f, "chart", "squared")) ? "measuredSu" : "measuredFSu");
    const auto used = panelUsageGlobalCall(f, "part", {x, y, su, panelUsageRead(f, model, "used"), QJSValue(true)});
    const auto left = panelUsageGlobalCall(f, "part", {x, y, su, panelUsageRead(f, model, "used"), QJSValue(false)});
    const QJSValueList kept{textIndex(f, used, QJSValue(0)), textIndex(f, used, QJSValue(1)), textIndex(f, used, QJSValue(2))}; panelUsageMemberCall(f, usedLayer, "setPoints", kept);
    const QJSValueList dropped{textIndex(f, left, QJSValue(0)), textIndex(f, left, QJSValue(1)), textIndex(f, left, QJSValue(2))}; panelUsageMemberCall(f, leftOutLayer, "setPoints", dropped);
}
void ApplicationInfo::singleRedraw() const {
    const auto f = panelUsageEngine(this); projectInvoke(f, "chart", "updateLegend");
    if (panelUsageTruth(assistantContextField(f, "chart", "stacked"))) { projectInvoke(f, "chart", "redrawStacked"); return; }
    if (panelUsageTruth(assistantContextField(f, "chart", "reportMode"))) {
        if (panelUsageTruth(assistantContextField(f, "chart", "calculated"))) {
            const auto layer = panelUsageContextRead(f, "layer"); const QJSValueList args{panelUsageRead(f, assistantContextField(f, "chart", "reportData"), "calc"), panelUsageRead(f, assistantContextField(f, "chart", "reportData"), "meas"), panelUsageRead(f, assistantContextField(f, "chart", "reportData"), "su")}; panelUsageMemberCall(f, layer, "setPoints", args);
        } else singleEmptyPoints(f, panelUsageContextRead(f, "layer"));
        singleEmptyPoints(f, panelUsageContextRead(f, "leftOutLayer")); return;
    }
    if (!panelUsageTruth(assistantContextField(f, "chart", "reflections")) || !panelUsageTruth(assistantContextField(f, "chart", "shown"))) return;
    const auto chart = panelUsageContextRead(f, "chart"); const QJSValueList args{assistantContextField(f, "chart", "reflections"), panelUsageContextRead(f, "layer"), panelUsageContextRead(f, "leftOutLayer")}; panelUsageMemberCall(f, chart, "drawModel", args);
}
void ApplicationInfo::singleDrawDiagonal() const {
    const auto f = panelUsageEngine(this);
    const auto from = numberMath(f, "min", [&] { return QJSValueList{assistantContextField(f, "chart", "xLow"), assistantContextField(f, "chart", "yLow")}; });
    const auto to = numberMath(f, "max", [&] { return QJSValueList{assistantContextField(f, "chart", "xHigh"), assistantContextField(f, "chart", "yHigh")}; });
    projectInvoke(f, "diagonal", "clear"); projectInvoke(f, "diagonal", "append", {from, from}); projectInvoke(f, "diagonal", "append", {to, to});
}
void ApplicationInfo::singleStateChanged(int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) { panelUsageContextWrite(f, "zoom", controlEmptyArray(f)); panelUsageGlobalCall(f, "redraw"); }
    else if (event == 1) { panelUsageContextWrite(f, "hiddenRows", controlEmptyArray(f)); panelUsageGlobalCall(f, "updateLegend"); }
    else if (event == 2) { if (!panelUsageTruth(assistantContextField(f, "chart", "stacked"))) { const auto preferences = panelUsageContextRead(f, "Preferences"); assistantMemberWrite(f, preferences, "patternLegendShown", panelUsageContextRead(f, "legendShown")); } }
    else {
        const auto preferences = panelUsageContextRead(f, "Preferences"); assistantMemberWrite(f, preferences, "chartHighlightSelected", QJSValue(!panelUsageTruth(assistantContextField(f, "Preferences", "chartHighlightSelected"))));
    }
}
void ApplicationInfo::singleModelChanged(bool stacked) const {
    const auto f = panelUsageEngine(this); const auto chart = panelUsageContextRead(f, "chart"); const auto previous = panelUsageNumber(f, assistantContextField(f, "chart", "revision"));
    if (previous) assistantMemberWrite(f, chart, "revision", QJSValue(*previous + 1));
    projectInvoke(f, stacked ? "stackedLayer" : "chart", "redraw");
}
void ApplicationInfo::singleQuantityChoice(const QJSValue& index) const {
    const auto f = panelUsageEngine(this); projectWrite(f, "Preferences", "singleCrystalQuantity", QJSValue(index.strictlyEquals(QJSValue(0)) ? QStringLiteral("f_squared") : QStringLiteral("f")));
}
QJSValue ApplicationInfo::singleNearest(const QJSValue& px, const QJSValue& py) const {
    const auto f = panelUsageEngine(this); const auto span = chartSpan(f, "axisX"); double best = -1, bestModel = -1;
    const auto em = assistantContextField(f, "chart", "em"), other = assistantContextField(f, "chart", "em"); auto bestDistance = viewArithmetic(f, em, other, 1);
    auto xs = controlEmptyArray(f), ys = controlEmptyArray(f);
    for (double m = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(m), panelUsageRead(f, assistantContextField(f, "chart", "models"), "length"), 0); ++m) {
        const auto model = textIndex(f, assistantContextField(f, "chart", "models"), QJSValue(m));
        if (!panelUsageTruth(panelUsageRead(f, model, "calculatedShown")) || panelUsageTruth(panelUsageMemberCall(f, assistantContextField(f, "chart", "hiddenModels"), "includes", {model}))) continue;
        const auto mx = panelUsageRead(f, model, panelUsageTruth(assistantContextField(f, "chart", "squared")) ? "calculated" : "calculatedF");
        const auto my = panelUsageRead(f, model, panelUsageTruth(assistantContextField(f, "chart", "squared")) ? "measured" : "measuredF");
        for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, mx, "length"), 0); ++i) {
            const auto x = textIndex(f, mx, QJSValue(i)), xLow = assistantContextField(f, "axisX", "min");
            const auto xShare = viewArithmetic(f, viewArithmetic(f, x, xLow, 0), span, 2);
            const auto dx = viewArithmetic(f, viewArithmetic(f, xShare, assistantContextField(f, "plot", "width"), 1), px, 0);
            const auto y = textIndex(f, my, QJSValue(i)), yLow = assistantContextField(f, "axisY", "min"); const auto yOffset = viewArithmetic(f, y, yLow, 0);
            const auto yShare = viewArithmetic(f, yOffset, chartSpan(f, "axisY"), 2); const auto inverted = viewArithmetic(f, QJSValue(1), yShare, 0);
            const auto dy = viewArithmetic(f, viewArithmetic(f, inverted, assistantContextField(f, "plot", "height"), 1), py, 0);
            const auto horizontal = viewArithmetic(f, dx, dx, 1), vertical = viewArithmetic(f, dy, dy, 1); const auto distance = panelUsageAdd(f, horizontal, vertical);
            if (numberFinite(f, distance) && assistantRelation(f, distance, bestDistance, 0)) { best = i; bestDistance = distance; bestModel = m; xs = mx; ys = my; }
        }
    }
    if (best < 0) return consentNull();
    auto hit = panelUsageLiteral(f); panelUsageWrite(f, hit.value, "model", QJSValue(bestModel)); panelUsageWrite(f, hit.value, "row", QJSValue(best));
    panelUsageWrite(f, hit.value, "x", textIndex(f, xs, QJSValue(best))); panelUsageWrite(f, hit.value, "y", textIndex(f, ys, QJSValue(best))); return panelUsageComplete(f, hit);
}
void ApplicationInfo::singleHoverRead(const QJSValue& px, const QJSValue& py) const {
    const auto f = panelUsageEngine(this); const auto hit = panelUsageGlobalCall(f, "nearest", {px, py}); if (hit.isNull()) { panelUsageGlobalCall(f, "hide"); return; }
    const auto span = chartSpan(f, "axisX"); const auto models = assistantContextField(f, "chart", "models"); const auto model = textIndex(f, models, panelUsageRead(f, hit, "model"));
    const QJSValueList args{panelUsageRead(f, hit, "row"), assistantContextField(f, "chart", "squared")}; const auto text = panelUsageMemberCall(f, model, "hoverText", args);
    const auto label = panelUsageContextRead(f, "hoverText"); QJSValue readout = text;
    if (panelUsageTruth(assistantContextField(f, "chart", "stacked"))) {
        const auto experiments = assistantContextField(f, "chart", "stackedExperiments"), index = panelUsageRead(f, hit, "model");
        const auto name = panelUsageRead(f, textIndex(f, experiments, index), "name"); const auto first = panelUsageAdd(f, QJSValue(QStringLiteral("<b>")), name);
        const auto prefix = panelUsageAdd(f, first, QJSValue(QStringLiteral("</b><br>"))); readout = panelUsageAdd(f, prefix, text);
    }
    assistantMemberWrite(f, label, "text", readout);
    const auto plotX = assistantContextField(f, "plot", "x"), x = panelUsageRead(f, hit, "x"), xLow = assistantContextField(f, "axisX", "min");
    const auto xShare = viewArithmetic(f, viewArithmetic(f, x, xLow, 0), span, 2); const auto atX = panelUsageAdd(f, plotX, viewArithmetic(f, xShare, assistantContextField(f, "plot", "width"), 1));
    const auto plotY = assistantContextField(f, "plot", "y"), y = panelUsageRead(f, hit, "y"), yLow = assistantContextField(f, "axisY", "min");
    const auto yShare = viewArithmetic(f, viewArithmetic(f, y, yLow, 0), chartSpan(f, "axisY"), 2); const auto inverted = viewArithmetic(f, QJSValue(1), yShare, 0);
    const auto atY = panelUsageAdd(f, plotY, viewArithmetic(f, inverted, assistantContextField(f, "plot", "height"), 1)); chartHoverPosition(f, atX, atY);
}
void ApplicationInfo::singlePointer(const QJSValue& mouse, int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        const auto x = panelUsageRead(f, mouse, "x"); panelUsageContextWrite(f, "lastX", x); panelUsageContextWrite(f, "pressX", x);
        const auto y = panelUsageRead(f, mouse, "y"); panelUsageContextWrite(f, "lastY", y); panelUsageContextWrite(f, "pressY", y); projectInvoke(f, "hoverLabel", "hide"); return;
    }
    if (event == 1) {
        bool panning = panelUsageTruth(panelUsageContextRead(f, "pressed"));
        if (panning) { const auto buttons = panelUsageContextRead(f, "pressedButtons"), left = assistantContextField(f, "Qt", "LeftButton"); panning = panelUsageTruth(chartBinary(f, buttons, left, false)); }
        if (panning && assistantContextField(f, "Preferences", "patternPointerMode").strictlyEquals(QJSValue(QStringLiteral("pan")))) {
            const auto x = panelUsageRead(f, mouse, "x"), beforeX = panelUsageContextRead(f, "lastX"); const auto xDistance = viewArithmetic(f, x, beforeX, 0);
            const auto xShare = viewArithmetic(f, xDistance, panelUsageContextRead(f, "width"), 2), dx = viewArithmetic(f, xShare, chartSpan(f, "axisX"), 1);
            const auto y = panelUsageRead(f, mouse, "y"), beforeY = panelUsageContextRead(f, "lastY"); const auto yDistance = viewArithmetic(f, y, beforeY, 0);
            const auto yShare = viewArithmetic(f, yDistance, panelUsageContextRead(f, "height"), 2), dy = viewArithmetic(f, yShare, chartSpan(f, "axisY"), 1);
            const auto chart = panelUsageContextRead(f, "chart");
            const QJSValueList ends{viewArithmetic(f, assistantContextField(f, "axisX", "min"), dx, 0), viewArithmetic(f, assistantContextField(f, "axisX", "max"), dx, 0), panelUsageAdd(f, assistantContextField(f, "axisY", "min"), dy), panelUsageAdd(f, assistantContextField(f, "axisY", "max"), dy)};
            assistantMemberWrite(f, chart, "zoom", assistantGeometryArray(f, ends)); panelUsageContextWrite(f, "lastX", panelUsageRead(f, mouse, "x")); panelUsageContextWrite(f, "lastY", panelUsageRead(f, mouse, "y"));
        }
        if (panelUsageTruth(assistantContextField(f, "Preferences", "patternHoverShown")) && !panelUsageTruth(panelUsageContextRead(f, "pressed"))) {
            const auto label = panelUsageContextRead(f, "hoverLabel"); const QJSValueList args{panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")}; panelUsageMemberCall(f, label, "read", args);
        } else projectInvoke(f, "hoverLabel", "hide"); return;
    }
    if (event == 2) {
        const auto button = panelUsageRead(f, mouse, "button"), right = assistantContextField(f, "Qt", "RightButton");
        if (button.strictlyEquals(right)) { projectWrite(f, "chart", "zoom", controlEmptyArray(f)); return; }
        const bool still = singleStillIn(f, mouse, "x", "pressX") && singleStillIn(f, mouse, "y", "pressY");
        if (still) {
            const auto legend = panelUsageContextRead(f, "chartLegend"); const QJSValueList args{panelUsageContextRead(f, "pointer"), panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")};
            if (panelUsageTruth(panelUsageMemberCall(f, legend, "toggleAt", args))) return;
        }
        if (panelUsageTruth(assistantContextField(f, "chart", "stacked")) && panelUsageTruth(assistantContextField(f, "chart", "project")) && still) {
            const auto label = panelUsageContextRead(f, "hoverLabel"); const QJSValueList args{panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")}; const auto hit = panelUsageMemberCall(f, label, "nearest", args);
            if (!hit.isNull()) { const auto project = assistantContextField(f, "chart", "project"); assistantMemberWrite(f, project, "currentExperimentIndex", panelUsageRead(f, hit, "model")); } return;
        }
        if (!assistantContextField(f, "Preferences", "patternPointerMode").strictlyEquals(QJSValue(QStringLiteral("zoom"))) || singleStillIn(f, mouse, "x", "pressX") || singleStillIn(f, mouse, "y", "pressY")) return;
        QJSValueList ends;
        for (const auto& operation : {std::array<const char*, 3>{"xAt", "min", "pressX"}, {"xAt", "max", "pressX"}, {"yAt", "max", "pressY"}, {"yAt", "min", "pressY"}}) {
            const auto value = numberMath(f, operation[1], [&] { return QJSValueList{panelUsageContextRead(f, operation[2]), panelUsageRead(f, mouse, std::string_view(operation[0]) == "xAt" ? "x" : "y")}; });
            ends.append(panelUsageGlobalCall(f, operation[0], {value}));
        }
        const auto box = assistantGeometryArray(f, ends); if (singleBoxIncreasing(f, box, true)) projectWrite(f, "chart", "zoom", box); return;
    }
    if (panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y").strictlyEquals(QJSValue(0))) return;
    const auto factor = numberMath(f, "pow", [&] { return QJSValueList{QJSValue(0.8), viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y"), QJSValue(120), 2)}; });
    const auto ax = panelUsageGlobalCall(f, "xAt", {panelUsageRead(f, mouse, "x")}), ay = panelUsageGlobalCall(f, "yAt", {panelUsageRead(f, mouse, "y")});
    const QJSValueList ends{singleWheelEnd(f, ax, factor, "axisX", false), singleWheelEnd(f, ax, factor, "axisX", true), singleWheelEnd(f, ay, factor, "axisY", false), singleWheelEnd(f, ay, factor, "axisY", true)};
    const auto box = assistantGeometryArray(f, ends);
    if (panelUsageTruth(panelUsageMemberCall(f, box, "every", {panelUsageContextRead(f, "isFinite")})) && singleBoxIncreasing(f, box, false)) projectWrite(f, "chart", "zoom", box);
}

namespace {
QJSValue scanProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>& arg) {
    const auto value = arg(0);
    if (operation == 305) return projectInvoke(f, "chart", "capitalised", {value});
    if (operation == 300 && panelUsageTruth(panelUsageMemberCall(f, value, "startsWith", {QJSValue(QStringLiteral("x: "))}))) return value;
    const char* source = operation == 300 ? QT_TRANSLATE_NOOP("ScanViewChart", "x: %1") : operation == 301 ? QT_TRANSLATE_NOOP("ScanViewChart", "y: %1")
        : operation == 302 ? QT_TRANSLATE_NOOP("ScanViewChart", "%1: %2") : operation == 303 ? QT_TRANSLATE_NOOP("ScanViewChart", "spacing: %1") : QT_TRANSLATE_NOOP("ScanViewChart", "direction: %1");
    auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(source))});
    if (operation == 302) format = panelUsageMemberCall(f, format, "arg", {panelUsageContextRead(f, "axis")});
    return panelUsageMemberCall(f, format, "arg", {value});
}
QJSValue scanAtShare(const PanelUsageFrame& f, const QJSValue& share, bool vertical) {
    const char* axis = vertical ? "axisY" : "axisX"; const auto start = assistantContextField(f, axis, vertical ? "max" : "min");
    const auto scaled = viewArithmetic(f, share, chartSpan(f, axis), 1);
    return vertical ? viewArithmetic(f, start, scaled, 0) : panelUsageAdd(f, start, scaled);
}
void scanWant(const PanelUsageFrame& f) {
    if (panelUsageTruth(panelUsageContextRead(f, "shown")) && !panelUsageContextRead(f, "scan").isNull()) {
        const auto scan = panelUsageContextRead(f, "scan"); assistantMemberWrite(f, scan, "wanted", QJSValue(true));
    }
}
} // namespace

QJSValue ApplicationInfo::scanStackedPalette() const {
    const auto f = panelUsageEngine(this); const auto stored = !assistantContextField(f, "Preferences", "scanStackedPalette").strictlyEquals(QJSValue(QStringLiteral("")))
        ? assistantContextField(f, "Preferences", "scanStackedPalette") : assistantContextField(f, "Preferences", "colourScheme");
    if (assistantRelation(f, panelUsageMemberCall(f, panelUsageContextRead(f, "stackedChoices"), "indexOf", {stored}), QJSValue(0), 2)) return stored;
    const auto actor = panelUsageContextRead(f, "ApplicationInfo"); return panelUsageMemberCall(f, actor, "colourSchemeOrDefault", {assistantContextField(f, "Preferences", "colourScheme")});
}
QJSValue ApplicationInfo::chartCapitalised(const QJSValue& text) const { const auto f = panelUsageEngine(this); return chartCapitalisedValue(f, text); }
void ApplicationInfo::scanSetZoom(const QJSValue& x, const QJSValue& y) const {
    const auto f = panelUsageEngine(this); panelUsageContextWrite(f, "settingZoom", QJSValue(true)); panelUsageContextWrite(f, "zoomX", x); panelUsageContextWrite(f, "zoomY", y);
    panelUsageContextWrite(f, "settingZoom", QJSValue(false)); panelUsageGlobalCall(f, "publishZoom");
}
void ApplicationInfo::scanResetZoom() const {
    const auto f = panelUsageEngine(this); const QJSValueList args{controlEmptyArray(f), controlEmptyArray(f)}; panelUsageGlobalCall(f, "setZoom", args);
}
void ApplicationInfo::scanPublishZoom() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageContextRead(f, "shown")) || panelUsageTruth(panelUsageContextRead(f, "settingZoom"))) return;
    const auto object = panelUsageContextRead(f, "Object"), empty = panelUsageComplete(f, panelUsageLiteral(f)); const auto source = assistantContextField(f, "AppState", "scanZoom");
    const auto next = panelUsageMemberCall(f, object, "assign", {empty, source}), mode = panelUsageContextRead(f, "mode");
    auto range = panelUsageLiteral(f); panelUsageWrite(f, range.value, "x", panelUsageContextRead(f, "zoomX")); panelUsageWrite(f, range.value, "y", panelUsageContextRead(f, "zoomY"));
    textIndexWrite(f, next, mode, panelUsageComplete(f, range)); projectWrite(f, "AppState", "scanZoom", next);
}
void ApplicationInfo::scanViewLifecycle(int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        if (panelUsageTruth(panelUsageContextRead(f, "shown"))) {
            const auto zoom = panelUsageContextRead(f, "sharedZoom"); const QJSValueList args{panelUsageRead(f, zoom, "x"), panelUsageRead(f, zoom, "y")}; panelUsageGlobalCall(f, "setZoom", args);
        }
        scanWant(f);
    } else if (event == 1) { scanWant(f); panelUsageGlobalCall(f, "reportShown"); }
    else if (event == 2) { panelUsageGlobalCall(f, "resetZoom"); scanWant(f); }
    else {
        const auto previous = panelUsageContextRead(f, "presentedTo");
        if (!previous.isNull() && !previous.isUndefined()) panelUsageMemberCall(f, previous, "setScanViewShown", {panelUsageContextRead(f, "chart"), QJSValue(false)});
        panelUsageContextWrite(f, "presentedTo", consentNull());
    }
}
void ApplicationInfo::scanReportShown() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageContextRead(f, "presentedTo").isNull()) {
        bool retire = !panelUsageTruth(panelUsageContextRead(f, "presenting"));
        if (!retire) { const auto previous = panelUsageContextRead(f, "presentedTo"), project = panelUsageContextRead(f, "project"); retire = !previous.strictlyEquals(project); }
        if (retire) {
            const auto previous = panelUsageContextRead(f, "presentedTo"); panelUsageMemberCall(f, previous, "setScanViewShown", {panelUsageContextRead(f, "chart"), QJSValue(false)});
            panelUsageContextWrite(f, "presentedTo", consentNull());
        }
    }
    if (panelUsageTruth(panelUsageContextRead(f, "presenting")) && panelUsageContextRead(f, "presentedTo").isNull()) {
        const auto project = panelUsageContextRead(f, "project"); panelUsageMemberCall(f, project, "setScanViewShown", {panelUsageContextRead(f, "chart"), QJSValue(true)});
        panelUsageContextWrite(f, "presentedTo", panelUsageContextRead(f, "project"));
    }
}
void ApplicationInfo::scanPointer(const QJSValue& mouse, int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        const auto top = numberMath(f, "max", [&] { return QJSValueList{QJSValue(1), assistantContextField(f, "layer", "stackTop")}; });
        const auto high = assistantContextField(f, "chart", "yMax"), low = assistantContextField(f, "chart", "yMin"); const auto span = viewArithmetic(f, high, low, 0);
        if (!assistantContextField(f, "chart", "mode").strictlyEquals(QJSValue(QStringLiteral("stacked"))) || panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y").strictlyEquals(QJSValue(0))
            || !assistantRelation(f, span, QJSValue(0), 1) || assistantRelation(f, span, top, 2)) { assistantMemberWrite(f, mouse, "accepted", QJSValue(false)); return; }
        const auto from = numberMath(f, "max", [&] {
            return QJSValueList{QJSValue(0), numberMath(f, "min", [&] {
                const auto first = viewArithmetic(f, top, span, 0), start = assistantContextField(f, "chart", "yMin");
                const auto delta = viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, mouse, "angleDelta"), "y"), QJSValue(120), 2);
                const auto movement = viewArithmetic(f, viewArithmetic(f, delta, span, 1), QJSValue(0.2), 1);
                return QJSValueList{first, panelUsageAdd(f, start, movement)};
            })};
        });
        const auto chart = panelUsageContextRead(f, "chart"), x = assistantContextField(f, "chart", "zoomX");
        const auto y = assistantGeometryArray(f, {from, panelUsageAdd(f, from, span)}); panelUsageMemberCall(f, chart, "setZoom", {x, y}); return;
    }
    if (event == 1) {
        const auto button = panelUsageRead(f, mouse, "button"), right = assistantContextField(f, "Qt", "RightButton"); if (button.strictlyEquals(right)) return;
        const auto qt = panelUsageContextRead(f, "Qt"); const QJSValueList args{panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")};
        panelUsageContextWrite(f, "start", panelUsageMemberCall(f, qt, "point", args)); projectWrite(f, "zoomBox", "width", QJSValue(0)); projectWrite(f, "zoomBox", "height", QJSValue(0)); return;
    }
    if (event == 2) {
        const auto buttons = panelUsageRead(f, mouse, "buttons"), left = assistantContextField(f, "Qt", "LeftButton");
        if (!panelUsageTruth(chartBinary(f, buttons, left, false))) {
            QJSValue hovered(-1);
            if (!assistantContextField(f, "chart", "scan").isNull()) {
                const auto layer = panelUsageContextRead(f, "layer"); const auto x = chartCoordinateValue(f, [&] { return panelUsageRead(f, mouse, "x"); }, false);
                const auto y = chartCoordinateValue(f, [&] { return panelUsageRead(f, mouse, "y"); }, true); hovered = panelUsageMemberCall(f, layer, "datasetNear", {x, y});
            }
            panelUsageContextWrite(f, "hovered", hovered); return;
        }
        const auto x = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), numberMath(f, "min", [&] { return QJSValueList{panelUsageContextRead(f, "width"), panelUsageRead(f, mouse, "x")}; })}; });
        const auto y = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), numberMath(f, "min", [&] { return QJSValueList{panelUsageContextRead(f, "height"), panelUsageRead(f, mouse, "y")}; })}; });
        const auto horizontal = panelUsageContextRead(f, "zoomBox");
        assistantMemberWrite(f, horizontal, "x", numberMath(f, "min", [&] { return QJSValueList{panelUsageRead(f, panelUsageContextRead(f, "start"), "x"), x}; }));
        const auto vertical = panelUsageContextRead(f, "zoomBox");
        assistantMemberWrite(f, vertical, "y", numberMath(f, "min", [&] { return QJSValueList{panelUsageRead(f, panelUsageContextRead(f, "start"), "y"), y}; }));
        const auto width = panelUsageContextRead(f, "zoomBox");
        assistantMemberWrite(f, width, "width", numberMath(f, "abs", [&] { return QJSValueList{viewArithmetic(f, x, panelUsageRead(f, panelUsageContextRead(f, "start"), "x"), 0)}; }));
        const auto height = panelUsageContextRead(f, "zoomBox");
        assistantMemberWrite(f, height, "height", numberMath(f, "abs", [&] { return QJSValueList{viewArithmetic(f, y, panelUsageRead(f, panelUsageContextRead(f, "start"), "y"), 0)}; }));
        const auto box = panelUsageContextRead(f, "zoomBox"); const bool visible = assistantRelation(f, assistantContextField(f, "zoomBox", "width"), QJSValue(4), 1) || assistantRelation(f, assistantContextField(f, "zoomBox", "height"), QJSValue(4), 1);
        assistantMemberWrite(f, box, "visible", QJSValue(visible)); return;
    }
    const auto button = panelUsageRead(f, mouse, "button"), right = assistantContextField(f, "Qt", "RightButton"); if (button.strictlyEquals(right)) { projectInvoke(f, "chart", "resetZoom"); return; }
    if (!panelUsageTruth(assistantContextField(f, "zoomBox", "visible"))) {
        const auto legend = panelUsageContextRead(f, "stackedLegend"); const QJSValueList args{panelUsageContextRead(f, "pointer"), panelUsageRead(f, mouse, "x"), panelUsageRead(f, mouse, "y")};
        if (panelUsageTruth(panelUsageMemberCall(f, legend, "toggleAt", args))) return;
    }
    if (panelUsageTruth(assistantContextField(f, "zoomBox", "visible"))) {
        projectWrite(f, "zoomBox", "visible", QJSValue(false));
        if (assistantRelation(f, assistantContextField(f, "zoomBox", "width"), QJSValue(4), 1) && assistantRelation(f, assistantContextField(f, "zoomBox", "height"), QJSValue(4), 1)) {
            const auto chart = panelUsageContextRead(f, "chart");
            const auto firstX = viewArithmetic(f, assistantContextField(f, "zoomBox", "x"), panelUsageContextRead(f, "width"), 2); const auto lowX = scanAtShare(f, firstX, false);
            const auto x = assistantContextField(f, "zoomBox", "x"), w = assistantContextField(f, "zoomBox", "width"); const auto lastX = viewArithmetic(f, panelUsageAdd(f, x, w), panelUsageContextRead(f, "width"), 2);
            const auto xRange = assistantGeometryArray(f, {lowX, scanAtShare(f, lastX, false)});
            const auto y = assistantContextField(f, "zoomBox", "y"), h = assistantContextField(f, "zoomBox", "height"); const auto firstY = viewArithmetic(f, panelUsageAdd(f, y, h), panelUsageContextRead(f, "height"), 2); const auto lowY = scanAtShare(f, firstY, true);
            const auto lastY = viewArithmetic(f, assistantContextField(f, "zoomBox", "y"), panelUsageContextRead(f, "height"), 2); const auto yRange = assistantGeometryArray(f, {lowY, scanAtShare(f, lastY, true)});
            panelUsageMemberCall(f, chart, "setZoom", {xRange, yRange});
        }
        return;
    }
    if (assistantContextField(f, "chart", "scan").isNull() || assistantContextField(f, "chart", "project").isNull()) return;
    const auto layer = panelUsageContextRead(f, "layer"), mouseX = panelUsageRead(f, mouse, "x"); const auto xShare = viewArithmetic(f, mouseX, panelUsageContextRead(f, "width"), 2); const auto x = scanAtShare(f, xShare, false);
    const auto mouseY = panelUsageRead(f, mouse, "y"); const auto yShare = viewArithmetic(f, mouseY, panelUsageContextRead(f, "height"), 2), y = scanAtShare(f, yShare, true);
    const auto dataset = panelUsageMemberCall(f, layer, "datasetNear", {x, y});
    if (assistantRelation(f, dataset, QJSValue(0), 2)) assistantMemberWrite(f, assistantContextField(f, "chart", "project"), "currentExperimentIndex", dataset);
}
QJSValue ApplicationInfo::scanIntensityCounts(const QJSValue& value) const {
    const auto f = panelUsageEngine(this); const auto scale = assistantContextField(f, "Preferences", "patternYScale");
    if (scale.strictlyEquals(QJSValue(QStringLiteral("log")))) return numberPower(f, [&] { return value; });
    if (scale.strictlyEquals(QJSValue(QStringLiteral("sqrt")))) {
        const auto sign = numberMath(f, "sign", [&] { return QJSValueList{value}; }); const auto first = viewArithmetic(f, sign, value, 1); return viewArithmetic(f, first, value, 1);
    }
    return value;
}
QJSValue ApplicationInfo::scanIntensityText(const QJSValue& value) const {
    const auto f = panelUsageEngine(this); const auto counts = panelUsageGlobalCall(f, "intensityCounts", {value});
    if (!numberFinite(f, counts)) return QJSValue(QStringLiteral("")); if (counts.strictlyEquals(QJSValue(0))) return QJSValue(QStringLiteral("0"));
    return numberReplaceExponent(f, projectInvoke(f, "NumberText", "exponent", {counts, QJSValue(2)}));
}
void ApplicationInfo::scanLegendToggle(const QJSValue& key) const {
    const auto f = panelUsageEngine(this); if (!key.strictlyEquals(QJSValue(QStringLiteral("")))) {
        const auto layer = panelUsageContextRead(f, "layer"); panelUsageMemberCall(f, layer, "toggleHidden", {panelUsageGlobalCall(f, "Number", {key})});
    }
}
QJSValue ApplicationInfo::scanRowEntries() const {
    const auto f = panelUsageEngine(this); QJSValue input;
    if (panelUsageTruth(panelUsageContextRead(f, "hasValue"))) {
        const auto title = panelUsageRead(f, assistantContextField(f, "chart", "scan"), "valueTitle"), order = panelUsageContextRead(f, "order"); input = assistantGeometryArray(f, {title, order});
    } else input = assistantGeometryArray(f, {panelUsageContextRead(f, "order")});
    return panelUsageMemberCall(f, input, "map", {projectGuardedClosure(f, 305, 1)});
}
QJSValue ApplicationInfo::scanClosedTexts(int kind) const {
    const auto f = panelUsageEngine(this); const auto source = kind == 3 ? assistantContextField(f, "ApplicationInfo", "stackedSpacingTitles") : kind == 4 ? assistantContextField(f, "ApplicationInfo", "scanMapDirectionTitles") : panelUsageContextRead(f, "entries");
    return panelUsageMemberCall(f, source, "map", {projectGuardedClosure(f, uint(300 + kind), 1)});
}
void ApplicationInfo::scanChoice(const QJSValue& index, int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) {
        if (panelUsageTruth(assistantContextField(f, "chart", "project")) && panelUsageTruth(panelUsageContextRead(f, "nativeOffered"))) assistantMemberWrite(f, assistantContextField(f, "chart", "project"), "patternDSpacing", QJSValue(index.strictlyEquals(QJSValue(1))));
    } else if (kind == 1) {
        if (panelUsageTruth(assistantContextField(f, "chart", "project")) && panelUsageTruth(panelUsageRead(f, assistantContextField(f, "chart", "project"), "evolution"))) {
            const auto evolution = panelUsageRead(f, assistantContextField(f, "chart", "project"), "evolution"); assistantMemberWrite(f, evolution, "xMode", panelUsageTruth(panelUsageContextRead(f, "hasValue")) ? index : QJSValue(1));
        }
    } else if (kind == 2 || kind == 4) {
        const auto preferences = panelUsageContextRead(f, "Preferences"); const auto choices = kind == 2 ? panelUsageContextRead(f, "tokens") : assistantContextField(f, "chart", "mapChoices");
        assistantMemberWrite(f, preferences, kind == 2 ? "patternYScale" : "scanMapColours", textIndex(f, choices, index));
    } else if (panelUsageTruth(assistantContextField(f, "chart", "project"))) {
        const auto project = assistantContextField(f, "chart", "project"), choices = panelUsageContextRead(f, kind == 3 ? "steps" : "directions");
        assistantMemberWrite(f, project, kind == 3 ? "stackedSpacing" : "mapDirection", textIndex(f, choices, index));
    }
}
void ApplicationInfo::scanToggle(int kind) const {
    const auto f = panelUsageEngine(this); const char* names[] = {"scanStackedLegendShown", "patternHoverShown", "scanStackedReversed", "scanMapSmooth", "chartIncludedOnly", "chartSubtractBackground", "chartHighlightSelected"};
    if (kind < 0 || kind >= int(std::size(names))) return;
    const auto preferences = panelUsageContextRead(f, "Preferences"); assistantMemberWrite(f, preferences, names[kind], QJSValue(!panelUsageTruth(assistantContextField(f, "Preferences", names[kind]))));
}

namespace {
QJSValue workingRandom(const PanelUsageFrame& f, int choices) {
    return numberMath(f, "floor", [&] { return QJSValueList{viewArithmetic(f, numberMath(f, "random", [] { return QJSValueList{}; }), QJSValue(choices), 1)}; });
}
QJSValue workingPhase(const PanelUsageFrame& f, const QJSValue& now) {
    const auto elapsed = viewArithmetic(f, now, assistantContextField(f, "workStatus", "rotationStartedAt"), 0);
    const auto phase = chartBinary(f, elapsed, QJSValue(2000), true), positive = panelUsageAdd(f, phase, QJSValue(2000));
    return chartBinary(f, positive, QJSValue(2000), true);
}
void workingSeekPeak(const PanelUsageFrame& f, const QJSValue& now, const QJSValue& phase) {
    const auto timer = panelUsageContextRead(f, "peakSwitch");
    const auto interval = numberMath(f, "max", [&] { return QJSValueList{QJSValue(1), numberMath(f, "ceil", [&] {
        return QJSValueList{numberMath(f, "min", [&] {
            const auto remaining = viewArithmetic(f, QJSValue(2000), phase, 0), deadline = assistantContextField(f, "workStatus", "variantSwitchDeadline");
            return QJSValueList{remaining, viewArithmetic(f, deadline, now, 0)};
        })};
    })}; });
    assistantMemberWrite(f, timer, "interval", interval); projectInvoke(f, "peakSwitch", "start");
}
} // namespace

void ApplicationInfo::queueToolbarBinding(const QJSValue& install) const { const auto f = panelUsageEngine(this); panelUsageCallLater(f, install); }
QJSValue ApplicationInfo::toolbarWidestEntry() const {
    const auto f = panelUsageEngine(this);
    if (!panelUsageTruth(panelUsageRead(f, assistantContextField(f, "metrics", "font"), "family"))) return QJSValue(0);
    QJSValue widest(0); const auto model = assistantContextField(f, "box", "model"); const auto base = panelUsageTruth(model) ? model : controlEmptyArray(f);
    const auto entries = panelUsageDeferredMemberCall(f, base, "concat", [&] { return QJSValueList({assistantContextField(f, "box", "closedTexts")}); });
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, entries, "length"), 0); ++i)
        widest = numberMath(f, "max", [&] {
            const auto metrics = panelUsageContextRead(f, "metrics");
            return QJSValueList{widest, panelUsageDeferredMemberCall(f, metrics, "advanceWidth", [&] { return QJSValueList({numberString(f, textIndex(f, entries, QJSValue(i)))}); })};
        });
    return numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
}
QJSValue ApplicationInfo::tabTitleSegments() const {
    const auto f = panelUsageEngine(this); auto record = panelUsageLiteral(f);
    panelUsageWrite(f, record.value, "text", assistantContextField(f, "tab", "text")); panelUsageWrite(f, record.value, "bold", assistantContextField(f, "tab", "checked")); const auto name = panelUsageComplete(f, record);
    if (assistantContextField(f, "tab", "fontIcon").strictlyEquals(QJSValue(QStringLiteral("")))) return assistantGeometryArray(f, {name});
    auto icon = panelUsageLiteral(f); panelUsageWrite(f, icon.value, "icon", assistantContextField(f, "tab", "fontIcon"));
    const auto color = !assistantContextField(f, "tab", "iconColor").strictlyEquals(QJSValue(QStringLiteral(""))) ? assistantContextField(f, "tab", "iconColor") : projectInvoke(f, "tab", "foregroundColor");
    panelUsageWrite(f, icon.value, "color", color); return assistantGeometryArray(f, {panelUsageComplete(f, icon), name});
}
QJSValue ApplicationInfo::digitCellWidth() const {
    const auto f = panelUsageEngine(this); const auto font = assistantContextField(f, "metrics", "font"); Q_UNUSED(font)
    QJSValue widest(0);
    for (int digit = 0; digit <= 9 && panelUsageReady(f); ++digit)
        widest = numberMath(f, "max", [&] {
            const auto metrics = panelUsageContextRead(f, "metrics");
            return QJSValueList{widest, panelUsageDeferredMemberCall(f, metrics, "advanceWidth", [&] { return QJSValueList({numberString(f, QJSValue(digit))}); })};
        });
    return numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
}
QJSValue ApplicationInfo::digitTextRuns() const {
    const auto f = panelUsageEngine(this); const auto text = panelUsageContextRead(f, "text");
    const auto expression = panelRegex(f, QString::fromUtf8("[0-9]|→|[^0-9→]+"), QV4::CompiledData::RegExp::RegExp_Global);
    const auto runs = panelUsageDeferredMemberCall(f, text, "match", [&] { return QJSValueList({expression}); }); return runs.isNull() || runs.isUndefined() ? controlEmptyArray(f) : runs;
}
QJSValue ApplicationInfo::digitRunIsDigit(const QJSValue& text) const {
    const auto f = panelUsageEngine(this); return panelUsageDeferredMemberCall(f, panelRegex(f, QStringLiteral("^[0-9]$")), "test", [&] { return QJSValueList({text}); });
}
QJSValue ApplicationInfo::palettePositions() const {
    const auto f = panelUsageEngine(this); const auto kinds = controlEmptyArray(f), project = assistantContextField(f, "Session", "project");
    if (panelUsageTruth(project)) {
        panelUsageEach(f, panelUsageRead(f, project, "experimentColourPositions"), [&](const QJSValue& position) { textIndexWrite(f, kinds, position, QJSValue(QStringLiteral("experiment"))); return panelUsageReady(f); });
        panelUsageEach(f, panelUsageRead(f, project, "structureColourPositions"), [&](const QJSValue& position) { textIndexWrite(f, kinds, position, QJSValue(QStringLiteral("structure"))); return panelUsageReady(f); });
    }
    return kinds;
}
QJSValue ApplicationInfo::nameBlockIcon(const QJSValue& kind) const {
    return QJSValue(kind.strictlyEquals(QJSValue(QStringLiteral("structure"))) ? QStringLiteral("layer-group") : kind.strictlyEquals(QJSValue(QStringLiteral("experiment"))) ? QStringLiteral("microscope") : kind.strictlyEquals(QJSValue(QStringLiteral("parameter"))) ? QStringLiteral("chart-line") : QString());
}
QJSValue ApplicationInfo::nameParameterIcon(const QJSValue& name) const {
    const auto f = panelUsageEngine(this);
    static constexpr std::pair<const char*, const char*> icons[] = {{"length_", "ruler"}, {"angle_", "ruler"}, {"fract_", "map-marker-alt"}, {"occupancy", "fill"}, {"adp_", "arrows-alt"}, {"scale", "weight"}, {"setup_wavelength", "radiation"}, {"setup_twotheta_bank", "hashtag"}, {"calib_d_to_tof_offset", "arrows-alt-h"}, {"calib_d_to_tof_", "radiation"}, {"calib_", "arrows-alt-h"}, {"broad_", "shapes"}, {"rise_", "shapes"}, {"decay_", "shapes"}, {"asym_", "balance-scale-left"}, {"intensity", "mountain"}};
    for (const auto& icon : icons) if (panelUsageTruth(panelUsageDeferredMemberCall(f, name, "startsWith", [&] { return QJSValueList({QJSValue(QString::fromLatin1(icon.first))}); }))) return QJSValue(QString::fromLatin1(icon.second));
    return QJSValue(QStringLiteral(""));
}
QJSValue ApplicationInfo::nameSegments(const QJSValue& item) const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(item)) return controlEmptyArray(f);
    const auto minor = chartStyle(f, "themeForegroundMinor"); QJSValue categoryColor = minor;
    if (!panelUsageRead(f, item, "elementSymbol").strictlyEquals(QJSValue(QStringLiteral("")))) {
        const auto colors = panelUsageContextRead(f, "AppColors"); categoryColor = panelUsageDeferredMemberCall(f, colors, "element", [&] { return QJSValueList({panelUsageRead(f, item, "elementSymbol")}); });
    } else if (assistantRelation(f, panelUsageRead(f, item, "phaseIndex"), QJSValue(0), 2)) {
        const auto colors = panelUsageContextRead(f, "AppColors"); categoryColor = panelUsageDeferredMemberCall(f, colors, "structure", [&] { return QJSValueList({panelUsageRead(f, item, "phaseIndex")}); });
    }
    auto block = panelUsageLiteral(f); const auto names = panelUsageContextRead(f, "names"); panelUsageWrite(f, block.value, "icon", panelUsageDeferredMemberCall(f, names, "blockIcon", [&] { return QJSValueList({panelUsageRead(f, item, "blockKind")}); }));
    const auto colors = panelUsageContextRead(f, "AppColors"); panelUsageWrite(f, block.value, "color", panelUsageDeferredMemberCall(f, colors, "block", [&] { return QJSValueList({panelUsageRead(f, item, "blockKind"), panelUsageRead(f, item, "blockIndex")}); }));
    const auto pieces = assistantGeometryArray(f, {panelUsageComplete(f, block)});
    if (!panelUsageRead(f, item, "categoryIcon").strictlyEquals(QJSValue(QStringLiteral("")))) {
        panelUsageDeferredMemberCall(f, pieces, "push", [&] { return QJSValueList({chartRecord(f, {{"icon", panelUsageRead(f, item, "categoryIcon")}, {"color", categoryColor}})}); });
    }
    if (!panelUsageRead(f, item, "rowLabel").strictlyEquals(QJSValue(QStringLiteral("")))) {
        panelUsageDeferredMemberCall(f, pieces, "push", [&] { return QJSValueList({chartRecord(f, {{"text", panelUsageRead(f, item, "rowLabel")}, {"color", categoryColor}})}); });
    }
    const auto receiver = panelUsageContextRead(f, "names"), parameter = panelUsageDeferredMemberCall(f, receiver, "parameterIcon", [&] { return QJSValueList({panelUsageRead(f, item, "name")}); });
    if (!parameter.strictlyEquals(QJSValue(QStringLiteral("")))) panelUsageDeferredMemberCall(f, pieces, "push", [&] { return QJSValueList({chartRecord(f, {{"icon", parameter}, {"color", minor}})}); });
    panelUsageDeferredMemberCall(f, pieces, "push", [&] { return QJSValueList({chartRecord(f, {{"text", panelUsageRead(f, item, "shortName")}})}); }); return pieces;
}
QJSValue ApplicationInfo::blockNamesShown() const {
    const auto f = panelUsageEngine(this); const auto rows = controlEmptyArray(f);
    if (assistantRelation(f, panelUsageContextRead(f, "count"), QJSValue(11), 3)) {
        for (double row = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(row), panelUsageContextRead(f, "count"), 0); ++row) panelUsageDeferredMemberCall(f, rows, "push", [&] { return QJSValueList({QJSValue(row)}); });
        return rows;
    }
    for (int row = 0; row < 5 && panelUsageReady(f); ++row) panelUsageDeferredMemberCall(f, rows, "push", [&] { return QJSValueList({QJSValue(row)}); });
    panelUsageDeferredMemberCall(f, rows, "push", [&] { return QJSValueList({QJSValue(-1)}); }); const auto start = panelUsageNumber(f, viewArithmetic(f, panelUsageContextRead(f, "count"), QJSValue(5), 0)); if (!start) return {};
    for (double row = *start; panelUsageReady(f) && assistantRelation(f, QJSValue(row), panelUsageContextRead(f, "count"), 0); ++row) panelUsageDeferredMemberCall(f, rows, "push", [&] { return QJSValueList({QJSValue(row)}); });
    return rows;
}
QJSValue ApplicationInfo::blockNamesLine(const QJSValue& row) const {
    const auto f = panelUsageEngine(this);
    if (assistantRelation(f, assistantContextField(f, "names", "revision"), QJSValue(0), 0) || !panelUsageTruth(assistantContextField(f, "names", "blocks")) || assistantRelation(f, row, QJSValue(0), 0)) return QJSValue(QStringLiteral(""));
    if (assistantContextField(f, "names", "blockKind").strictlyEquals(QJSValue(QStringLiteral("experiment")))) {
        const auto first = panelUsageDeferredMemberCall(f, assistantContextField(f, "names", "blocks"), "text", [&] { return QJSValueList({row, QJSValue(QStringLiteral("name"))}); });
        const auto prefix = panelUsageAdd(f, first, QJSValue(QStringLiteral(" · ")));
        return panelUsageAdd(f, prefix, panelUsageDeferredMemberCall(f, assistantContextField(f, "names", "blocks"), "text", [&] { return QJSValueList({row, QJSValue(QStringLiteral("file"))}); }));
    }
    return panelUsageDeferredMemberCall(f, assistantContextField(f, "names", "blocks"), "text", [&] { return QJSValueList({row, QJSValue(QStringLiteral("label"))}); });
}
void ApplicationInfo::blockNamesChanged() const {
    const auto f = panelUsageEngine(this); const auto names = panelUsageContextRead(f, "names"); const auto previous = panelUsageNumber(f, assistantContextField(f, "names", "revision"));
    if (previous) assistantMemberWrite(f, names, "revision", QJSValue(*previous + 1));
}
QJSValue ApplicationInfo::workingInitialVariant() const { const auto f = panelUsageEngine(this); return workingRandom(f, 3); }
QJSValue ApplicationInfo::workingText() const {
    const auto f = panelUsageEngine(this);
    if (assistantRelation(f, panelUsageContextRead(f, "elapsedSeconds"), QJSValue(60), 0)) {
        const auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("AssistantWorking", "%1s · Agent working...")))});
        return panelUsageDeferredMemberCall(f, format, "arg", [&] { return QJSValueList({panelUsageContextRead(f, "elapsedSeconds")}); });
    }
    const auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("AssistantWorking", "%1m %2s · Agent working...")))});
    const auto first = panelUsageDeferredMemberCall(f, format, "arg", [&] { return QJSValueList({numberMath(f, "floor", [&] { return QJSValueList{viewArithmetic(f, panelUsageContextRead(f, "elapsedSeconds"), QJSValue(60), 2)}; })}); }); return panelUsageDeferredMemberCall(f, first, "arg", [&] { return QJSValueList({chartBinary(f, panelUsageContextRead(f, "elapsedSeconds"), QJSValue(60), true)}); });
}
void ApplicationInfo::workingStateChanged(int event) const {
    const auto f = panelUsageEngine(this);
    if (event == 0) {
        panelUsageContextWrite(f, "workingSince", panelUsageTruth(panelUsageContextRead(f, "working")) ? panelUsageNow(f) : QJSValue(0)); panelUsageContextWrite(f, "elapsedSeconds", QJSValue(0));
    } else if (event == 1) {
        if (!panelUsageTruth(panelUsageContextRead(f, "animating")) && panelUsageTruth(assistantContextField(f, "peakSwitch", "running"))) { projectInvoke(f, "peakSwitch", "stop"); panelUsageGlobalCall(f, "changeVariant"); }
    } else {
        if (panelUsageTruth(panelUsageContextRead(f, "working"))) panelUsageContextWrite(f, "workingSince", panelUsageNow(f)); panelUsageGlobalCall(f, "scheduleVariantChange");
    }
}
void ApplicationInfo::workingScheduleVariant() const {
    const auto f = panelUsageEngine(this); panelUsageContextWrite(f, "variantSwitchDeadline", panelUsageAdd(f, panelUsageNow(f), QJSValue(60000)));
    const auto cadence = panelUsageContextRead(f, "variantCadence"); assistantMemberWrite(f, cadence, "interval", panelUsageAdd(f, QJSValue(30000), workingRandom(f, 28001))); projectInvoke(f, "variantCadence", "start");
}
void ApplicationInfo::workingChangeVariant() const {
    const auto f = panelUsageEngine(this); const bool wasLinear = panelUsageContextRead(f, "variant").strictlyEquals(QJSValue(0));
    const auto first = panelUsageAdd(f, panelUsageContextRead(f, "variant"), QJSValue(1)); const auto next = panelUsageAdd(f, first, workingRandom(f, 2)); panelUsageContextWrite(f, "variant", chartBinary(f, next, QJSValue(3), true));
    if (panelUsageTruth(panelUsageContextRead(f, "animating")) && wasLinear != panelUsageContextRead(f, "variant").strictlyEquals(QJSValue(0))) projectInvoke(f, "rotationAnimator", "restart");
    panelUsageGlobalCall(f, "scheduleVariantChange");
}
void ApplicationInfo::workingElapsed() const {
    const auto f = panelUsageEngine(this); const auto status = panelUsageContextRead(f, "workStatus");
    const auto elapsed = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), numberMath(f, "floor", [&] {
        const auto now = panelUsageNow(f), start = assistantContextField(f, "workStatus", "workingSince"); return QJSValueList{viewArithmetic(f, viewArithmetic(f, now, start, 0), QJSValue(1000), 2)};
    })}; }); assistantMemberWrite(f, status, "elapsedSeconds", elapsed);
}
void ApplicationInfo::workingCadence(bool peak) const {
    const auto f = panelUsageEngine(this); const auto now = panelUsageNow(f);
    if (panelUsageTruth(assistantContextField(f, "workStatus", "animating")) && !assistantContextField(f, "workStatus", "variant").strictlyEquals(QJSValue(0)) && assistantRelation(f, now, assistantContextField(f, "workStatus", "variantSwitchDeadline"), 0)) {
        const auto phase = workingPhase(f, now); if (!peak || assistantRelation(f, phase, QJSValue(32), 1)) { workingSeekPeak(f, now, phase); return; }
    }
    projectInvoke(f, "workStatus", "changeVariant");
}
void ApplicationInfo::workingAnimation(bool started) const {
    const auto f = panelUsageEngine(this);
    if (started) { const auto status = panelUsageContextRead(f, "workStatus"); assistantMemberWrite(f, status, "rotationStartedAt", panelUsageNow(f)); }
    else if (!panelUsageTruth(assistantContextField(f, "workStatus", "animating"))) projectWrite(f, "workGlyph", "rotation", QJSValue(0));
}

namespace {
QJSValue recentLabel(const PanelUsageFrame& f, const char* source, const QJSValue& name) {
    const auto format = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(source))});
    return panelUsageDeferredMemberCall(f, format, "arg", [&] { return QJSValueList({name}); });
}
QJSValue rowInstanceOf(const PanelUsageFrame& f, const QJSValue& input, const char* name) {
    const auto type = panelUsageContextRead(f, name); if (!panelUsageReady(f)) return {};
    QV4::Scope scope(f.vm()); QV4::ScopedValue value(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), input)), target(scope, QJSValuePrivate::convertToReturnedValue(f.vm(), type));
    QV4::ScopedValue result(scope, QV4::Runtime::Instanceof::call(f.vm(), *value, *target)); f.checked(); return QJSValuePrivate::fromReturnedValue(result->asReturnedValue());
}
void rowFocusOnClick(const PanelUsageFrame& f, const QJSValue& item) {
    const auto policy = panelUsageRead(f, item, "focusPolicy"), tab = assistantContextField(f, "Qt", "TabFocus");
    if (policy.strictlyEquals(tab)) assistantMemberWrite(f, item, "focusPolicy", assistantContextField(f, "Qt", "StrongFocus"));
    const auto original = panelUsageRead(f, item, "children"); const auto children = original.isNull() || original.isUndefined() ? controlEmptyArray(f) : original;
    panelUsageEach(f, children, [&](const QJSValue& child) { rowFocusOnClick(f, child); return panelUsageReady(f); });
}
QJSValue recentRowCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& arg) {
    if (operation == 320) return QJSValue(assistantRelation(f, panelUsageRead(f, arg(0), "length"), QJSValue(0), 1));
    if (operation == 321) {
        const auto path = arg(0); auto row = panelUsageLiteral(f); panelUsageWrite(f, row.value, "path", path); panelUsageWrite(f, row.value, "label", path); panelUsageWrite(f, row.value, "inBrowser", QJSValue(false));
        panelUsageWrite(f, row.value, "available", panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "Session"), "projectDirectoryExists", [&] { return QJSValueList({path}); })); return panelUsageComplete(f, row);
    }
    if (operation == 322) return QJSValue(!arg(0).strictlyEquals(saved(0)));
    if (operation == 323) panelUsageDeferredMemberCall(f, saved(0), "applyWidths", [&] { return QJSValueList({saved(1)}); });
    const auto qt = panelUsageContextRead(f, "Qt"); panelUsageDeferredMemberCall(f, qt, "callLater", [&] { return QJSValueList({panelUsageRead(f, saved(0), "fitColumns")}); }); return {};
}
} // namespace

QJSValue ApplicationInfo::recentWebRows() const {
    const auto f = panelUsageEngine(this); const auto kept = controlEmptyArray(f), saved = controlEmptyArray(f), places = assistantContextField(f, "WebStorage", "places");
    for (double row = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(row), panelUsageRead(f, places, "count"), 0); ++row) {
        const auto key = panelUsageDeferredMemberCall(f, places, "key", [&] { return QJSValueList({QJSValue(row)}); }), name = panelUsageDeferredMemberCall(f, places, "name", [&] { return QJSValueList({QJSValue(row)}); });
        const bool inBrowser = panelUsageDeferredMemberCall(f, places, "kind", [&] { return QJSValueList({QJSValue(row)}); }).strictlyEquals(QJSValue(QStringLiteral("browser")));
        if (panelUsageTruth(panelUsageDeferredMemberCall(f, places, "recovery", [&] { return QJSValueList({QJSValue(row)}); }))) {
            panelUsageDeferredMemberCall(f, kept, "push", [&] {
            auto item = panelUsageLiteral(f); panelUsageWrite(f, item.value, "path", panelUsageAdd(f, QJSValue(QStringLiteral("kept:")), key));
            panelUsageWrite(f, item.value, "label", recentLabel(f, QT_TRANSLATE_NOOP("RecentProjects", "Continue where you left off: %1"), name));
            panelUsageWrite(f, item.value, "inBrowser", QJSValue(false)); panelUsageWrite(f, item.value, "available", QJSValue(true)); return QJSValueList{panelUsageComplete(f, item)}; });
        }
        if (panelUsageTruth(panelUsageDeferredMemberCall(f, places, "saved", [&] { return QJSValueList({QJSValue(row)}); }))) {
            panelUsageDeferredMemberCall(f, saved, "push", [&] {
            auto item = panelUsageLiteral(f); panelUsageWrite(f, item.value, "path", panelUsageAdd(f, QJSValue(QStringLiteral("place:")), key));
            const char* source = inBrowser ? QT_TRANSLATE_NOOP("RecentProjects", "%1 · in this browser") : QT_TRANSLATE_NOOP("RecentProjects", "%1 · on this computer");
            panelUsageWrite(f, item.value, "label", recentLabel(f, source, name)); panelUsageWrite(f, item.value, "inBrowser", QJSValue(inBrowser)); panelUsageWrite(f, item.value, "available", QJSValue(true));
            return QJSValueList{panelUsageComplete(f, item)}; });
        }
    }
    return panelUsageDeferredMemberCall(f, kept, "concat", [&] { return QJSValueList({saved}); });
}
QJSValue ApplicationInfo::recentWebKey(const QJSValue& path) const {
    const auto f = panelUsageEngine(this); const auto at = panelUsageDeferredMemberCall(f, path, "indexOf", [&] { return QJSValueList({QJSValue(QStringLiteral(":"))}); });
    return panelUsageDeferredMemberCall(f, path, "substring", [&] { return QJSValueList({panelUsageAdd(f, at, QJSValue(1))}); });
}
void ApplicationInfo::recentOpen(const QJSValue& path) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) {
        const auto session = panelUsageContextRead(f, "Session");
        panelUsageDeferredMemberCall(f, session, "openStoredProject", [&] {
            const auto key = panelUsageGlobalCall(f, "webKey", {path}), kept = panelUsageDeferredMemberCall(f, path, "startsWith", [&] { return QJSValueList({QJSValue(QStringLiteral("kept:"))}); }); return QJSValueList{key, kept};
        });
    } else {
        const auto session = panelUsageContextRead(f, "Session"); panelUsageDeferredMemberCall(f, session, "openProject", [&] { return QJSValueList{panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "Session"), "projectDirectoryUrl", [&] { return QJSValueList({path}); })}; });
    }
}
QJSValue ApplicationInfo::recentPaths() const {
    const auto f = panelUsageEngine(this); return panelUsageDeferredMemberCall(f, assistantContextField(f, "recentSettings", "recent"), "filter", [&] { return QJSValueList({projectGuardedClosure(f, 320, 1)}); });
}
void ApplicationInfo::recentRefresh() const {
    const auto f = panelUsageEngine(this); QJSValue saved;
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) saved = panelUsageGlobalCall(f, "webRows");
    else saved = panelUsageDeferredMemberCall(f, panelUsageGlobalCall(f, "paths"), "map", [&] { return QJSValueList({projectGuardedClosure(f, 321, 1)}); });
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, saved, "length"), 0); ++index) {
        const auto row = textIndex(f, saved, QJSValue(index));
        if (assistantRelation(f, QJSValue(index), assistantContextField(f, "rows", "count"), 0)) panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "rows"), "set", [&] { return QJSValueList({QJSValue(index), row}); }); else panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "rows"), "append", [&] { return QJSValueList({row}); });
    }
    const auto count = assistantContextField(f, "rows", "count"), length = panelUsageRead(f, saved, "length");
    if (assistantRelation(f, count, length, 1)) {
        const auto rows = panelUsageContextRead(f, "rows"); panelUsageDeferredMemberCall(f, rows, "remove", [&] {
            const auto at = panelUsageRead(f, saved, "length"), present = assistantContextField(f, "rows", "count"), wanted = panelUsageRead(f, saved, "length"); return QJSValueList{at, viewArithmetic(f, present, wanted, 0)};
        });
    }
}
void ApplicationInfo::recentRemember(const QJSValue& path) const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(path) || panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) return;
    const auto paths = panelUsageGlobalCall(f, "paths"), saved = panelUsageDeferredMemberCall(f, paths, "filter", [&] { return QJSValueList({panelUsageClosure(f, 322, {path}, 1)}); });
    panelUsageDeferredMemberCall(f, saved, "unshift", [&] { return QJSValueList({path}); }); projectWrite(f, "recentSettings", "recent", saved); projectWrite(f, "recentSettings", "last", path); panelUsageGlobalCall(f, "refresh");
}
void ApplicationInfo::recentForget(const QJSValue& index) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) {
        QJSValue path(QStringLiteral(""));
        if (assistantRelation(f, index, QJSValue(0), 2) && assistantRelation(f, index, assistantContextField(f, "rows", "count"), 0)) path = panelUsageRead(f, panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "rows"), "get", [&] { return QJSValueList({index}); }), "path");
        if (panelUsageTruth(panelUsageDeferredMemberCall(f, path, "startsWith", [&] { return QJSValueList({QJSValue(QStringLiteral("kept:"))}); }))) {
            const auto storage = panelUsageContextRead(f, "WebStorage"); panelUsageDeferredMemberCall(f, storage, "dropRecovery", [&] { return QJSValueList({panelUsageGlobalCall(f, "webKey", {path})}); });
        } else if (panelUsageTruth(panelUsageDeferredMemberCall(f, path, "startsWith", [&] { return QJSValueList({QJSValue(QStringLiteral("place:"))}); }))) {
            const auto storage = panelUsageContextRead(f, "WebStorage"); panelUsageDeferredMemberCall(f, storage, "forget", [&] { return QJSValueList({panelUsageGlobalCall(f, "webKey", {path})}); });
        }
        return;
    }
    const auto saved = panelUsageGlobalCall(f, "paths"); if (assistantRelation(f, index, QJSValue(0), 0) || assistantRelation(f, index, panelUsageRead(f, saved, "length"), 2)) return;
    panelUsageDeferredMemberCall(f, saved, "splice", [&] { return QJSValueList({index, QJSValue(1)}); }); projectWrite(f, "recentSettings", "recent", saved); panelUsageGlobalCall(f, "refresh");
}
void ApplicationInfo::recentCompleted() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "Session", "project")) && !panelUsageTruth(assistantContextField(f, "Session", "needsSaveAs")) && !panelUsageTruth(assistantContextField(f, "WebFiles", "available")))
        panelUsageGlobalCall(f, "remember", {assistantContextField(f, "Session", "projectLocation")});
    else panelUsageGlobalCall(f, "refresh");
}
void ApplicationInfo::tableRowEditing() const { const auto f = panelUsageEngine(this); if (panelUsageTruth(assistantContextField(f, "row", "editing"))) projectInvoke(f, "row", "activated"); }
void ApplicationInfo::tableRowActivated() const {
    const auto f = panelUsageEngine(this); const auto table = chartAs(f, assistantContextField(f, "row", "listView"), "DataTable");
    if (table.isNull() || assistantRelation(f, assistantContextField(f, "row", "index"), QJSValue(0), 0)) return;
    if (panelUsageTruth(panelUsageRead(f, table, "selectable")) && !panelUsageTruth(assistantContextField(f, "row", "inSelection"))) {
        panelUsageDeferredMemberCall(f, table, "selectWithModifiers", [&] { return QJSValueList({assistantContextField(f, "row", "index"), assistantContextField(f, "Qt", "NoModifier")}); });
    }
    panelUsageDeferredMemberCall(f, table, "rowActivated", [&] { return QJSValueList({assistantContextField(f, "row", "index")}); });
}
void ApplicationInfo::tableRowCompleted(const QJSValue& installOpacity) const {
    const auto f = panelUsageEngine(this);
    panelUsageEach(f, assistantContextField(f, "row", "contentRowData"), [&](const QJSValue& cell) { rowFocusOnClick(f, cell); return panelUsageReady(f); });
    const auto table = chartAs(f, assistantContextField(f, "row", "listView"), "DataTable");
    if (!table.isNull()) {
        const auto array = panelUsageContextRead(f, "Array"); const auto children = panelUsageDeferredMemberCall(f, array, "from", [&] { return QJSValueList({assistantContextField(f, "row", "contentRowData")}); });
        const auto first = panelUsageDeferredMemberCall(f, children, "find", [&] { return QJSValueList({panelUsageClosure(f, 131, {}, 1)}); });
        const auto cells = panelUsageTruth(first) ? panelUsageRead(f, first, "parent") : consentNull();
        if (!cells.isNull()) panelUsageDeferredMemberCall(f, panelUsageRead(f, cells, "childrenChanged"), "connect", [&] { return QJSValueList({panelUsageClosure(f, 323, {table, cells}, 0)}); });
        panelUsageEach(f, assistantContextField(f, "row", "contentRowData"), [&](const QJSValue& cell) {
            if (!panelUsageTruth(rowInstanceOf(f, cell, "Item"))) return panelUsageReady(f);
            panelUsageDeferredMemberCall(f, panelUsageRead(f, cell, "implicitWidthChanged"), "connect", [&] { return QJSValueList({panelUsageClosure(f, 324, {table}, 0)}); });
            if (tableHas(f, cell, "numberChanged")) panelUsageDeferredMemberCall(f, panelUsageRead(f, cell, "numberChanged"), "connect", [&] { return QJSValueList({panelUsageClosure(f, 324, {table}, 0)}); });
            return panelUsageReady(f);
        });
    }
    QJSValue hover = consentNull();
    panelUsageEach(f, assistantContextField(f, "row", "data"), [&](const QJSValue& child) { if (panelUsageTruth(rowInstanceOf(f, child, "HoverHandler"))) hover = child; return panelUsageReady(f); });
    panelUsageEach(f, assistantContextField(f, "row", "data"), [&](const QJSValue& child) {
        if (!panelUsageTruth(rowInstanceOf(f, child, "Rectangle"))) return panelUsageReady(f);
        const auto fill = panelUsageRead(f, panelUsageRead(f, child, "anchors"), "fill"), row = panelUsageContextRead(f, "row");
        if (!fill.strictlyEquals(row) || !assistantRelation(f, panelUsageRead(f, panelUsageRead(f, child, "children"), "length"), QJSValue(0), 1)) return panelUsageReady(f);
        projectCall(f, installOpacity, {child, hover});
        panelUsageEach(f, panelUsageRead(f, child, "children"), [&](const QJSValue& area) {
            if (panelUsageTruth(rowInstanceOf(f, area, "MouseArea"))) {
                const auto clicked = panelUsageRead(f, area, "clicked"); panelUsageDeferredMemberCall(f, clicked, "connect", [&] { return QJSValueList({assistantContextField(f, "row", "activated")}); });
            }
            return panelUsageReady(f);
        }); return panelUsageReady(f);
    });
    if (!panelUsageTruth(assistantContextField(f, "row", "highlightsHover")) && !hover.isNull()) assistantMemberWrite(f, hover, "enabled", QJSValue(false));
}

namespace {
bool searchCurrent(const PanelUsageFrame& f, const QJSValue& component, const QJSValue& pending,
    const QJSValue& popup, const QJSValue& opening, const QJSValue& window, bool withWindow) {
    if (!consentQtObject(f, component) || !consentQtObject(f, pending) || !consentQtObject(f, popup) || (withWindow && !consentQtObject(f, window))) return false;
    if (!panelUsageTruth(opening) || !consentFieldEquals(f, pending, "opening", opening) || !consentFieldEquals(f, opening, "popup", popup)
        || !consentFieldEquals(f, component, "popup", popup) || !panelUsageTruth(panelUsageRead(f, popup, "visible"))) return false;
    if (withWindow) return panelUsageRead(f, panelUsageRead(f, component, "Window"), "window").strictlyEquals(window);
    return true;
}
bool searchOpeningCurrent(const PanelUsageFrame& f, const QJSValue& component, const QJSValue& pending,
    const QJSValue& popup, const QJSValue& opening) {
    return consentQtObject(f, component) && consentQtObject(f, pending) && consentQtObject(f, popup)
        && consentFieldEquals(f, pending, "opening", opening) && consentFieldEquals(f, component, "popup", popup) && panelUsageTruth(panelUsageRead(f, popup, "visible"));
}
bool searchRequestCurrent(const PanelUsageFrame& f, const QJSValue& component, const QJSValue& pending,
    const QJSValue& popup, const QJSValue& original, bool first) {
    return consentQtObject(f, pending) && panelUsageRead(f, pending, "request").isNull() && consentFieldEquals(f, pending, "opening", original)
        && (!first || panelUsageTruth(original)) && consentQtObject(f, component) && consentQtObject(f, popup)
        && consentFieldEquals(f, component, "popup", popup) && panelUsageTruth(panelUsageRead(f, popup, "visible"));
}
QJSValue searchHeaderItem(const PanelUsageFrame& f, const QJSValue& popup) {
    const auto list = chartAs(f, panelUsageRead(f, popup, "contentItem"), "ListView");
    return list.isNull() || list.isUndefined() ? QJSValue() : panelUsageRead(f, list, "headerItem");
}
} // namespace

void ApplicationInfo::searchPositionPopup(const QJSValue& opening) const {
    const auto f = panelUsageEngine(this); const auto component = panelUsageContextRead(f, "control"), pending = panelUsageContextRead(f, "popupLayout"), popup = panelUsageRead(f, component, "popup");
    const auto current = [&] { return searchCurrent(f, component, pending, popup, opening, QJSValue(), false); };
    if (!current()) return; const auto list = chartAs(f, panelUsageRead(f, popup, "contentItem"), "ListView"); if (!panelUsageTruth(list)) return;
    panelUsageMemberCall(f, list, "forceLayout");
    if (!current() || !consentQtObject(f, list) || !consentFieldEquals(f, popup, "contentItem", list)) return;
    const auto content = panelUsageRead(f, list, "contentHeight"), height = panelUsageRead(f, list, "height");
    if (assistantRelation(f, content, height, 3)) panelUsageMemberCall(f, list, "positionViewAtBeginning");
    else panelUsageDeferredMemberCall(f, list, "positionViewAtIndex", [&] {
        return QJSValueList{numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), panelUsageRead(f, component, "currentIndex")}; }), assistantContextField(f, "ListView", "Contain")};
    });
}
QJSValue ApplicationInfo::searchMeasuredWidth(bool optionsOnly) const {
    const auto f = panelUsageEngine(this); QJSValue widest(0);
    if (!optionsOnly) widest = panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "optionMetrics"), "advanceWidth", [&] { return QJSValueList{panelUsageContextRead(f, "displayText")}; });
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageContextRead(f, "count"), 0); ++index)
        widest = numberMath(f, "max", [&] {
            return QJSValueList{widest, panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "optionMetrics"), "advanceWidth", [&] { return QJSValueList{panelUsageGlobalCall(f, "textAt", {QJSValue(index)})}; })};
        });
    if (optionsOnly) {
        const auto measured = numberMath(f, "ceil", [&] { return QJSValueList{widest}; }); const auto pixels = panelUsageRead(f, panelUsageContextRead(f, "font"), "pixelSize");
        return panelUsageAdd(f, measured, viewArithmetic(f, pixels, QJSValue(3), 1));
    }
    QJSValue label(0);
    if (panelUsageTruth(panelUsageContextRead(f, "contentItemLabel"))) {
        const auto left = assistantContextField(f, "contentItemLabel", "leftPadding"), right = assistantContextField(f, "contentItemLabel", "rightPadding"); label = panelUsageAdd(f, left, right);
    }
    QJSValue besides = label;
    if (panelUsageTruth(panelUsageContextRead(f, "contentItem"))) {
        const auto implicit = assistantContextField(f, "contentItem", "implicitWidth");
        const auto measured = panelUsageDeferredMemberCall(f, panelUsageContextRead(f, "optionMetrics"), "advanceWidth", [&] { return QJSValueList{panelUsageContextRead(f, "displayText")}; }); besides = viewArithmetic(f, implicit, measured, 0);
    }
    const auto fit = numberMath(f, "ceil", [&] {
        const auto spacing = numberMath(f, "max", [&] { return QJSValueList{label, besides}; }); const auto first = panelUsageAdd(f, widest, spacing);
        const auto pixels = panelUsageRead(f, panelUsageContextRead(f, "font"), "pixelSize"); return QJSValueList{panelUsageAdd(f, first, viewArithmetic(f, pixels, QJSValue(0.5), 1))};
    }); const auto left = panelUsageAdd(f, fit, panelUsageContextRead(f, "leftPadding")); return panelUsageAdd(f, left, panelUsageContextRead(f, "rightPadding"));
}
QJSValue ApplicationInfo::searchAnyMatch() const {
    const auto f = panelUsageEngine(this); if (panelUsageContextRead(f, "filter").strictlyEquals(QJSValue(QStringLiteral("")))) return QJSValue(true);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageContextRead(f, "count"), 0); ++i)
        if (panelUsageTruth(panelUsageGlobalCall(f, "matches", {panelUsageGlobalCall(f, "textAt", {QJSValue(i)})}))) return QJSValue(true);
    return QJSValue(false);
}
QJSValue ApplicationInfo::searchFolded(const QJSValue& text) const {
    const auto f = panelUsageEngine(this); const auto string = numberString(f, text), lowered = panelUsageMemberCall(f, string, "toLowerCase");
    return panelUsageDeferredMemberCall(f, lowered, "replace", [&] { return QJSValueList{panelRegex(f, QStringLiteral("\\s+"), QV4::CompiledData::RegExp::RegExp_Global), QJSValue(QStringLiteral(""))}; });
}
void ApplicationInfo::searchPlacePopup(const QJSValue& opening) const {
    const auto f = panelUsageEngine(this); const auto component = panelUsageContextRead(f, "control"), pending = panelUsageContextRead(f, "popupLayout"), popup = panelUsageRead(f, component, "popup");
    const auto window = panelUsageRead(f, panelUsageRead(f, component, "Window"), "window"); const auto current = [&] { return searchCurrent(f, component, pending, popup, opening, window, true); };
    if (!current()) return;
    const auto left = panelUsageRead(f, panelUsageMemberCall(f, component, "mapToItem", {consentNull(), QJSValue(0), QJSValue(0)}), "x");
    const auto horizontal = numberMath(f, "min", [&] {
        const auto width = panelUsageRead(f, window, "width"), margin = numberMath(f, "max", [&] { return QJSValueList{QJSValue(0), panelUsageRead(f, popup, "rightMargin")}; });
        const auto first = viewArithmetic(f, width, margin, 0), second = viewArithmetic(f, first, panelUsageRead(f, popup, "width"), 0); return QJSValueList{QJSValue(0), viewArithmetic(f, second, left, 0)};
    }); assistantMemberWrite(f, popup, "x", horizontal); if (!current()) return;
    const auto top = panelUsageRead(f, panelUsageMemberCall(f, component, "mapToItem", {consentNull(), QJSValue(0), QJSValue(0)}), "y");
    const auto windowHeight = panelUsageRead(f, window, "height"), belowTop = viewArithmetic(f, windowHeight, top, 0);
    const auto belowComponent = viewArithmetic(f, belowTop, panelUsageRead(f, component, "height"), 0), below = viewArithmetic(f, belowComponent, panelUsageRead(f, popup, "bottomMargin"), 0);
    const auto above = viewArithmetic(f, top, panelUsageRead(f, popup, "topMargin"), 0); double entries = 0;
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, component, "count"), 0); ++index)
        if (panelUsageTruth(panelUsageDeferredMemberCall(f, component, "matches", [&] { return QJSValueList{panelUsageMemberCall(f, component, "textAt", {QJSValue(index)})}; }))) ++entries;
    const auto header = searchHeaderItem(f, popup); const auto style = panelUsageContextRead(f, "EaStyle"), pixels = panelUsageRead(f, panelUsageRead(f, style, "Sizes"), "comboBoxHeight");
    const auto rows = viewArithmetic(f, QJSValue(entries), pixels, 1), headerHeight = panelUsageTruth(header) ? panelUsageRead(f, header, "height") : QJSValue(0);
    const auto first = panelUsageAdd(f, rows, headerHeight), padded = panelUsageAdd(f, first, panelUsageRead(f, popup, "topPadding")); const auto wanted = panelUsageAdd(f, padded, panelUsageRead(f, popup, "bottomPadding"));
    if (assistantRelation(f, below, wanted, 2) || assistantRelation(f, below, above, 2)) {
        assistantMemberWrite(f, popup, "height", numberMath(f, "min", [&] { return QJSValueList{wanted, below}; })); if (!current()) return; assistantMemberWrite(f, popup, "y", panelUsageRead(f, component, "height"));
    } else {
        assistantMemberWrite(f, popup, "height", numberMath(f, "min", [&] { return QJSValueList{wanted, above}; })); if (!current()) return; assistantMemberWrite(f, popup, "y", numberNegate(f, panelUsageRead(f, popup, "height")));
    }
}
QJSValue ApplicationInfo::searchMatches(const QJSValue& text) const {
    const auto f = panelUsageEngine(this); if (panelUsageContextRead(f, "filter").strictlyEquals(QJSValue(QStringLiteral("")))) return QJSValue(true);
    const auto folded = panelUsageMemberCall(f, panelUsageContextRead(f, "control"), "folded", {text});
    return panelUsageDeferredMemberCall(f, folded, "includes", [&] { return QJSValueList{panelUsageContextRead(f, "filter")}; });
}
QJSValue ApplicationInfo::searchPickedIndex() const {
    const auto f = panelUsageEngine(this); double first = -1;
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageContextRead(f, "count"), 0); ++i) {
        const auto text = panelUsageGlobalCall(f, "textAt", {QJSValue(i)}), folded = panelUsageMemberCall(f, panelUsageContextRead(f, "control"), "folded", {text});
        if (folded.strictlyEquals(panelUsageContextRead(f, "filter"))) return QJSValue(i);
        if (first < 0 && panelUsageTruth(panelUsageGlobalCall(f, "matches", {text}))) first = i;
    }
    return QJSValue(first);
}
void ApplicationInfo::searchAccepted() const {
    const auto f = panelUsageEngine(this); const auto index = projectInvoke(f, "control", "pickedIndex"); if (assistantRelation(f, index, QJSValue(0), 0)) return;
    projectWrite(f, "control", "currentIndex", index); projectInvoke(f, "control", "activated", {index}); panelUsageMemberCall(f, assistantContextField(f, "control", "popup"), "close");
}
void ApplicationInfo::searchCompleted(const QJSValue& alignBinding, const QJSValue& modelBinding, const QJSValue& focusBinding) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "control", "contentItemLabel"))) {
        projectCall(f, alignBinding); if (panelUsageTruth(assistantContextField(f, "control", "inTable"))) assistantMemberWrite(f, assistantContextField(f, "control", "contentItemLabel"), "leftPadding", QJSValue(0));
    }
    const auto content = panelUsageRead(f, assistantContextField(f, "control", "popup"), "contentItem"); assistantMemberWrite(f, content, "header", panelUsageContextRead(f, "searchHeader")); projectCall(f, modelBinding);
    const auto list = panelUsageRead(f, assistantContextField(f, "control", "popup"), "contentItem"); assistantMemberWrite(f, list, "headerPositioning", assistantContextField(f, "ListView", "OverlayHeader")); projectCall(f, focusBinding);
}
void ApplicationInfo::searchSchedule(const QJSValue& original) const {
    const auto f = panelUsageEngine(this); const auto pending = panelUsageContextRead(f, "popupLayout"); if (!consentFieldEquals(f, pending, "opening", original)) return;
    assistantMemberWrite(f, pending, "request", original);
    if (consentQtObject(f, pending) && consentFieldEquals(f, pending, "opening", original) && consentFieldEquals(f, pending, "request", original)) panelUsageMemberCall(f, pending, "restart");
}
void ApplicationInfo::searchTriggered() const {
    const auto f = panelUsageEngine(this); const auto pending = panelUsageContextRead(f, "popupLayout"), component = panelUsageContextRead(f, "control"), original = panelUsageContextRead(f, "request");
    const auto popup = panelUsageTruth(original) ? panelUsageRead(f, original, "popup") : consentNull(); assistantMemberWrite(f, pending, "request", consentNull());
    if (!searchRequestCurrent(f, component, pending, popup, original, true)) return; panelUsageMemberCall(f, component, "placePopup", {original});
    if (!searchRequestCurrent(f, component, pending, popup, original, false)) return; panelUsageMemberCall(f, component, "positionPopup", {original});
}
void ApplicationInfo::searchAboutToShow() const {
    const auto f = panelUsageEngine(this); const auto component = panelUsageContextRead(f, "control"), pending = panelUsageContextRead(f, "popupLayout"), popup = panelUsageRead(f, component, "popup");
    const auto opening = chartRecord(f, {{"popup", popup}}); assistantMemberWrite(f, pending, "opening", opening);
    if (!searchOpeningCurrent(f, component, pending, popup, opening)) return; const auto field = searchHeaderItem(f, popup); if (panelUsageTruth(field)) panelUsageMemberCall(f, field, "clear");
    if (!searchOpeningCurrent(f, component, pending, popup, opening)) return; assistantMemberWrite(f, component, "searchText", QJSValue(QStringLiteral("")));
    if (!searchOpeningCurrent(f, component, pending, popup, opening)) return; panelUsageMemberCall(f, component, "placePopup", {opening});
    if (searchOpeningCurrent(f, component, pending, popup, opening)) panelUsageMemberCall(f, pending, "schedule", {opening});
}
void ApplicationInfo::searchAboutToHide() const {
    const auto f = panelUsageEngine(this); const auto pending = panelUsageContextRead(f, "popupLayout"); assistantMemberWrite(f, pending, "opening", consentNull());
    if (!consentQtObject(f, pending) || !panelUsageRead(f, pending, "opening").isNull()) return; assistantMemberWrite(f, pending, "request", consentNull());
    if (consentQtObject(f, pending) && panelUsageRead(f, pending, "opening").isNull() && panelUsageRead(f, pending, "request").isNull()) panelUsageMemberCall(f, pending, "stop");
}
void ApplicationInfo::searchOpened() const {
    const auto f = panelUsageEngine(this); const auto component = panelUsageContextRead(f, "control"), pending = panelUsageContextRead(f, "popupLayout"), popup = panelUsageRead(f, component, "popup"); const auto opening = panelUsageRead(f, pending, "opening");
    if (!panelUsageTruth(opening) || !consentQtObject(f, popup) || !consentFieldEquals(f, opening, "popup", popup) || !panelUsageTruth(panelUsageRead(f, popup, "visible"))) return;
    panelUsageMemberCall(f, component, "positionPopup", {opening}); if (!searchOpeningCurrent(f, component, pending, popup, opening)) return;
    const auto field = searchHeaderItem(f, popup); if (panelUsageTruth(field) && panelUsageTruth(panelUsageRead(f, component, "searchable"))) panelUsageMemberCall(f, field, "focusField");
}

namespace {
QJSValue formsProcedureCallback(const PanelUsageFrame& f, uint operation,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>&) {
    if (operation == 340) return panelUsageMemberCall(f, saved(0), "setType", {saved(1), saved(2)});
    const auto owner = panelUsageContextRead(f, operation == 341 ? "Session" : "RecentProjects");
    return panelUsageMemberCall(f, owner, operation == 341 ? "openExample" : "open", {assistantContextField(f, "row", operation == 341 ? "exampleId" : "path")});
}
QJSValue formsStyleSize(const PanelUsageFrame& f, const char* name) {
    return panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "EaStyle"), "Sizes"), name);
}
} // namespace

void ApplicationInfo::descriptionPressed(const QJSValue& mouse) const {
    const auto f = panelUsageEngine(this); projectInvoke(f, "tab", "forceActiveFocus"); assistantMemberWrite(f, mouse, "accepted", QJSValue(false));
}
void ApplicationInfo::descriptionCommit(int field, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this);
    if (field == 0) {
        if (!panelUsageTruth(assistantContextField(f, "tab", "project"))) return;
        const auto text = panelUsageContextRead(f, "text"), name = panelUsageRead(f, assistantContextField(f, "tab", "project"), "name"); if (text.strictlyEquals(name)) return;
        if (panelUsageContextRead(f, "text").strictlyEquals(QJSValue(QStringLiteral(""))))
            panelUsageContextWrite(f, "refusal", panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("DescriptionTab", "A project needs a name")))}));
        else {
            const auto project = assistantContextField(f, "tab", "project"); assistantMemberWrite(f, project, "name", panelUsageContextRead(f, "text"));
            panelUsageContextWrite(f, "refusal", panelUsageRead(f, assistantContextField(f, "tab", "project"), "lastError"));
        }
        projectCall(f, restoreBinding); return;
    }
    const char* name = field == 1 ? "title" : field == 2 ? "authors" : "description";
    if (panelUsageTruth(assistantContextField(f, "tab", "project"))) {
        const auto text = panelUsageContextRead(f, "text"), current = panelUsageRead(f, assistantContextField(f, "tab", "project"), name);
        if (!text.strictlyEquals(current)) { const auto project = assistantContextField(f, "tab", "project"); assistantMemberWrite(f, project, name, panelUsageContextRead(f, "text")); }
    }
}
void ApplicationInfo::parameterPickerChanged(int kind, bool chosen, const QJSValue& index) const {
    const auto f = panelUsageEngine(this); const char* picker = kind == 0 ? "datablockPicker" : kind == 1 ? "categoryPicker" : "variabilityPicker";
    if (chosen) {
        const auto filter = panelUsageContextRead(f, "parameterFilter");
        const auto value = kind == 2 ? index : textIndex(f, assistantContextField(f, "parameterFilter", kind == 0 ? "datablocks" : "categories"), index);
        assistantMemberWrite(f, filter, kind == 0 ? "datablockFilter" : kind == 1 ? "categoryFilter" : "variability", value);
        projectInvoke(f, picker, "follow");
    } else {
        projectInvoke(f, picker, "follow"); const auto qt = panelUsageContextRead(f, "Qt"); panelUsageMemberCall(f, qt, "callLater", {assistantContextField(f, picker, "follow")});
    }
}
void ApplicationInfo::parameterShownGroupsFollow() const {
    const auto f = panelUsageEngine(this);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, panelUsageContextRead(f, "wanted"), "length"), 0); ++i)
        panelUsageGlobalCall(f, "setShownGroup", {QJSValue(i + 1), textIndex(f, panelUsageContextRead(f, "wanted"), QJSValue(i))});
}
QJSValue ApplicationInfo::atomWyckoffWidth() const {
    const auto f = panelUsageEngine(this); QJSValue widest(0);
    const auto names = panelUsageTruth(panelUsageContextRead(f, "sites")) ? assistantContextField(f, "sites", "wyckoffNames") : controlEmptyArray(f);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, names, "length"), 0); ++i)
        widest = numberMath(f, "max", [&] { const auto metrics = panelUsageContextRead(f, "wyckoffMetrics"); return QJSValueList{widest, panelUsageMemberCall(f, metrics, "advanceWidth", {textIndex(f, names, QJSValue(i))})}; });
    const auto measured = numberMath(f, "ceil", [&] { return QJSValueList{numberMath(f, "max", [&] { return QJSValueList{widest, projectInvoke(f, "wyckoffMetrics", "advanceWidth", {QJSValue(QStringLiteral("WP"))})}; })}; });
    return panelUsageAdd(f, measured, viewArithmetic(f, formsStyleSize(f, "fontPixelSize"), QJSValue(2.5), 1));
}
QJSValue ApplicationInfo::atomAdpIsoWidth() const {
    const auto f = panelUsageEngine(this); const auto own = panelUsageContextRead(f, "modelRevision"), other = assistantContextField(f, "group", "adpRevision"), revision = panelUsageAdd(f, own, other); Q_UNUSED(revision)
    bool beta = false;
    for (double row = 0; panelUsageReady(f) && panelUsageTruth(assistantContextField(f, "group", "adps")) && assistantRelation(f, QJSValue(row), panelUsageContextRead(f, "count"), 0) && !beta; ++row)
        beta = panelUsageMemberCall(f, assistantContextField(f, "group", "adps"), "text", {QJSValue(row), QJSValue(QStringLiteral("adpType"))}).strictlyEquals(QJSValue(QStringLiteral("beta")));
    if (!beta) return QJSValue(-1);
    auto widest = panelUsageGlobalCall(f, "advance", {projectInvoke(f, "Session", "label", {QJSValue(QStringLiteral("atom_site.adp_iso"))})});
    for (double row = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(row), panelUsageContextRead(f, "count"), 0); ++row) {
        const auto item = chartAs(f, panelUsageMemberCall(f, assistantContextField(f, "group", "adps"), "item", {QJSValue(row), QJSValue(QStringLiteral("adpIso"))}), "ParameterItem");
        if (panelUsageTruth(item)) widest = numberMath(f, "max", [&] {
            QJSValue text;
            if (!panelUsageRead(f, item, "fileValue").strictlyEquals(QJSValue(QStringLiteral("")))) text = panelUsageRead(f, item, "fileValue");
            else {
                const auto numbers = panelUsageContextRead(f, "NumberText"), value = panelUsageRead(f, item, "value");
                const auto error = panelUsageTruth(panelUsageRead(f, item, "hasUncertainty")) ? panelUsageRead(f, item, "uncertainty") : QJSValue(0); text = panelUsageMemberCall(f, numbers, "parameter", {value, error, QJSValue(5)});
            }
            return QJSValueList{widest, panelUsageGlobalCall(f, "advance", {text})};
        });
    }
    const auto measured = numberMath(f, "ceil", [&] { return QJSValueList{widest}; }); return panelUsageAdd(f, measured, viewArithmetic(f, assistantContextField(f, "AppSizes", "fieldSpacing"), QJSValue(2), 1));
}
void ApplicationInfo::scientificSelectorChanged(const QJSValue& index, int kind, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this);
    if (kind == 5) {
        const auto site = assistantContextField(f, "row", "index"), type = panelUsageGlobalCall(f, "textAt", {index}), adps = assistantContextField(f, "group", "adps");
        projectCall(f, restoreBinding); const auto qt = panelUsageContextRead(f, "Qt"); const auto change = panelUsageClosure(f, 340, {adps, site, type}, 0); panelUsageMemberCall(f, qt, "callLater", {change}); return;
    }
    if (kind == 0 || kind == 1) {
        const auto sites = assistantContextField(f, "group", "sites"), row = assistantContextField(f, "row", "index"); QJSValue value;
        if (kind == 0) value = panelUsageGlobalCall(f, "textAt", {index}); else value = textIndex(f, panelUsageRead(f, assistantContextField(f, "group", "sites"), "wyckoffLetters"), index);
        panelUsageMemberCall(f, sites, "setText", {row, QJSValue(kind == 0 ? QStringLiteral("typeSymbol") : QStringLiteral("wyckoffLetter")), value});
    } else if (kind == 2 || kind == 3) {
        const auto spaceGroup = assistantContextField(f, "row", "spaceGroup"); assistantMemberWrite(f, spaceGroup, kind == 2 ? "nameHM" : "coordSystemCode", panelUsageGlobalCall(f, "textAt", {index}));
    } else {
        const auto rows = assistantContextField(f, "group", "rows"), row = assistantContextField(f, "row", "index");
        const auto value = textIndex(f, panelUsageRead(f, assistantContextField(f, "group", "rows"), "structureNames"), index); panelUsageMemberCall(f, rows, "setStructureId", {row, value});
    }
    projectCall(f, restoreBinding);
}
void ApplicationInfo::appearanceCommit(bool probability, const QJSValue& restoreBinding) const {
    const auto f = panelUsageEngine(this); if (assistantContextField(f, "group", "options").isNull()) return;
    const auto text = panelUsageContextRead(f, "text"), value = assistantContextField(f, probability ? "probability" : "scale", "value");
    if (text.strictlyEquals(value)) return;
    const auto options = assistantContextField(f, "group", "options"); assistantMemberWrite(f, options, probability ? "adpProbability" : "atomScale", panelUsageGlobalCall(f, "Number", {panelUsageContextRead(f, "text")})); projectCall(f, restoreBinding);
}
QJSValue ApplicationInfo::spaceGroupNumberAdmitted(const QJSValue& text) const {
    const auto f = panelUsageEngine(this); const auto pattern = panelRegex(f, QStringLiteral("^\\s*\\d+\\s*$")); if (!panelUsageTruth(panelUsageMemberCall(f, pattern, "test", {text}))) return QJSValue(false);
    if (!assistantRelation(f, panelUsageGlobalCall(f, "Number", {text}), QJSValue(1), 2)) return QJSValue(false);
    return QJSValue(assistantRelation(f, panelUsageGlobalCall(f, "Number", {text}), QJSValue(230), 3));
}
void ApplicationInfo::spaceGroupNumberCommit(const QJSValue& text) const {
    const auto f = panelUsageEngine(this); const auto group = assistantContextField(f, "row", "spaceGroup");
    assistantMemberWrite(f, group, "itNumber", text.strictlyEquals(QJSValue(QStringLiteral(""))) ? QJSValue(0) : panelUsageGlobalCall(f, "Number", {text}));
}
QJSValue ApplicationInfo::reflectionShown(const QJSValue& uid, const QJSValue& value, bool residual) const {
    const auto f = panelUsageEngine(this); if (value.isUndefined() || panelUsageTruth(panelUsageGlobalCall(f, "isNaN", {value}))) return QJSValue(QStringLiteral(""));
    return residual ? panelUsageMemberCall(f, value, "toFixed", {QJSValue(2)}) : projectInvoke(f, "Session", "display", {uid, value});
}
void ApplicationInfo::placeReflectionTable() const {
    const auto f = panelUsageEngine(this); const auto column = assistantContextField(f, "page", "extrasColumn"); if (!panelUsageTruth(column) || !panelUsageTruth(panelUsageRead(f, column, "contentItem"))) return;
    const auto top = panelUsageRead(f, panelUsageGlobalCall(f, "mapToItem", {panelUsageRead(f, column, "contentItem"), QJSValue(0), QJSValue(0)}), "y");
    const auto height = numberMath(f, "floor", [&] { const auto first = viewArithmetic(f, panelUsageRead(f, column, "height"), top, 0); return QJSValueList{viewArithmetic(f, first, formsStyleSize(f, "fontPixelSize"), 0)}; }); panelUsageContextWrite(f, "spareHeight", height);
}
QJSValue ApplicationInfo::exampleChoiceIndex(const QJSValue& model, const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, model, "count"), 0); ++i)
        if (panelUsageMemberCall(f, model, "text", {QJSValue(i), QJSValue(QStringLiteral("value"))}).strictlyEquals(value)) return QJSValue(i);
    return QJSValue(0);
}
void ApplicationInfo::openProjectRow(bool recent, bool activate) const {
    const auto f = panelUsageEngine(this); if (activate) projectInvoke(f, "row", "activated"); if (recent && !panelUsageTruth(assistantContextField(f, "row", "available"))) return;
    const auto state = panelUsageContextRead(f, "AppState"), action = projectGuardedClosure(f, recent ? 342 : 341, 0); panelUsageMemberCall(f, state, "afterChanges", {action});
}
QJSValue ApplicationInfo::projectDescriptionAdmitted(const QJSValue& value, bool title) const {
    const auto f = panelUsageEngine(this); if (!tableTypeof(f, value).strictlyEquals(QJSValue(QStringLiteral("string")))) return QJSValue(false);
    if (!title) {
        const auto validator = assistantContextField(f, "projectNameField", "validator"), expression = panelUsageRead(f, validator, "regularExpression"); return panelUsageMemberCall(f, expression, "test", {value});
    }
    const auto length = panelUsageRead(f, value, "length"), maximum = assistantContextField(f, "projectTitleField", "maximumLength"); if (!assistantRelation(f, length, maximum, 3)) return QJSValue(false);
    return QJSValue(!panelUsageTruth(panelUsageMemberCall(f, panelRegex(f, QString::fromLatin1(R"([\x00\r\n\t])")), "test", {value})));
}
QJSValue ApplicationInfo::projectJoinedPath(const QJSValue& folder, const QJSValue& name) const {
    const auto f = panelUsageEngine(this); auto path = folder; const QJSValue slash(QStringLiteral("/")), backslash(QStringLiteral("\\"));
    while (panelUsageReady(f) && assistantRelation(f, panelUsageRead(f, path, "length"), QJSValue(1), 1)
        && (panelUsageTruth(panelUsageMemberCall(f, path, "endsWith", {slash})) || panelUsageTruth(panelUsageMemberCall(f, path, "endsWith", {backslash})))) path = panelUsageMemberCall(f, path, "slice", {QJSValue(0), QJSValue(-1)});
    if (path.strictlyEquals(QJSValue(QStringLiteral("")))) return name;
    if (panelUsageTruth(panelUsageMemberCall(f, path, "endsWith", {slash})) || panelUsageTruth(panelUsageMemberCall(f, path, "endsWith", {backslash}))) return panelUsageAdd(f, path, name);
    const auto utils = panelUsageRead(f, panelUsageContextRead(f, "EaLogic"), "Utils"), separator = panelUsageMemberCall(f, utils, "osPathSep"); const auto first = panelUsageAdd(f, path, separator); return panelUsageAdd(f, first, name);
}
void ApplicationInfo::projectDescriptionOpened() const {
    const auto f = panelUsageEngine(this); const auto create = panelUsageGlobalCall(f, "standardButton", {assistantContextField(f, "Dialog", "Ok")}); if (panelUsageTruth(create)) assistantMemberWrite(f, create, "objectName", QJSValue(QStringLiteral("createProject.accept")));
}
void ApplicationInfo::toolTipAboutToShow() const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(panelUsageContextRead(f, "parent"))) return;
    const auto parent = panelUsageContextRead(f, "parent"), height = assistantContextField(f, "parent", "height");
    const auto bottom = panelUsageRead(f, panelUsageMemberCall(f, parent, "mapToItem", {consentNull(), QJSValue(0), height}), "y");
    const auto first = panelUsageAdd(f, bottom, panelUsageContextRead(f, "gap")), lower = panelUsageAdd(f, first, panelUsageContextRead(f, "implicitHeight"));
    const auto windowHeight = panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "parent"), "Window"), "height"), room = viewArithmetic(f, windowHeight, panelUsageContextRead(f, "margins"), 0); QJSValue y;
    if (assistantRelation(f, lower, room, 3)) { const auto height = assistantContextField(f, "parent", "height"); y = panelUsageAdd(f, height, panelUsageContextRead(f, "gap")); }
    else { const auto height = numberNegate(f, panelUsageContextRead(f, "implicitHeight")); y = viewArithmetic(f, height, panelUsageContextRead(f, "gap"), 0); } panelUsageContextWrite(f, "y", y);
}
QJSValue ApplicationInfo::styleScalePx(const QJSValue& size) const {
    const auto f = panelUsageEngine(this); return numberMath(f, "round", [&] { return QJSValueList{viewArithmetic(f, size, viewArithmetic(f, panelUsageContextRead(f, "defaultScale"), QJSValue(100), 2), 1)}; });
}

namespace {
QJSValue presentationCallback(const PanelUsageFrame& f, uint op,
    const std::function<QJSValue(uint)>&, const std::function<QJSValue(uint)>& a) {
    if (op == 360) {
        const auto structure = panelUsageRead(f, a(1), "structure"), length = panelUsageRead(f, structure, "length"), longest = panelUsageRead(f, a(0), "length");
        return assistantRelation(f, length, longest, 1) ? panelUsageRead(f, a(1), "structure") : a(0);
    }
    if (op == 361) return QJSValue(!panelUsageRead(f, a(0), "structure").strictlyEquals(QJSValue(QStringLiteral(""))));
    if (op == 362) return panelUsageMemberCall(f, assistantContextField(f, "dialog", "results"), "text", {a(0), QJSValue(QStringLiteral("metric"))});
    if (op == 363) {
        const auto outcome = panelUsageMemberCall(f, assistantContextField(f, "dialog", "results"), "text", {a(0), QJSValue(QStringLiteral("outcome"))});
        return !outcome.strictlyEquals(QJSValue(QStringLiteral(""))) ? projectInvoke(f, "FitOutcomes", "word", {outcome}) : panelUsageMemberCall(f, assistantContextField(f, "dialog", "results"), "text", {a(0), QJSValue(QStringLiteral("value"))});
    }
    if (op == 364) return assistantContextField(f, "dialog", "factorWidth");
    if (op == 365) return panelUsageAdd(f, a(0), a(1));
    if (op == 366) {
        const auto prefix = panelUsageAdd(f, panelUsageRead(f, a(0), "id"), QJSValue(QStringLiteral(": ")));
        return panelUsageAdd(f, prefix, panelUsageMemberCall(f, panelUsageRead(f, a(0), "paths"), "join", {QJSValue(QStringLiteral(", "))}));
    }
    if (op == 367) return QJSValue(-1);
    if (op == 368) {
        const auto values = panelUsageRead(f, assistantContextField(f, "row", "model"), "componentIntensities");
        const auto item = textIndex(f, (values.isNull() || values.isUndefined()) ? controlEmptyArray(f) : values, a(1));
        return (item.isNull() || item.isUndefined()) ? panelUsageContextRead(f, "NaN") : item;
    }
    if (op == 369) return projectInvoke(f, "Session", "optionLabel", {QJSValue(QStringLiteral("su_format.rule")), a(0)});
    return QJSValue(!a(0).strictlyEquals(QJSValue(QStringLiteral(""))));
}
QJSValue presentationStyle(const PanelUsageFrame& f, const char* name) {
    return panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "EaStyle"), "Colors"), name);
}
QJSValue presentationPositioned(const PanelUsageFrame& f, const QJSValue& positions, const QJSValue& index, const QJSValue& dark) {
    const auto project = assistantContextField(f, "Session", "project");
    if (!panelUsageTruth(project) || assistantRelation(f, index, QJSValue(0), 0) || assistantRelation(f, index, panelUsageRead(f, positions, "length"), 2)) return presentationStyle(f, "themeForegroundMinor");
    const auto info = panelUsageContextRead(f, "ApplicationInfo");
    return panelUsageDeferredMemberCall(f, info, "figureColour", [&] { return QJSValueList{assistantContextField(f, "Preferences", "colourScheme"), textIndex(f, positions, index), panelUsageRead(f, project, "colourPositionCount"), dark.isUndefined() ? presentationStyle(f, "isDarkPalette") : dark}; });
}
QJSValue presentationColumns(const PanelUsageFrame& f, const QJSValue& initial, const QJSValue& names) {
    const auto first = panelUsageDeferredMemberCall(f, initial, "concat", [&] { return QJSValueList{panelUsageMemberCall(f, names, "map", {panelUsageClosure(f, 367, {}, 0)})}; });
    return panelUsageMemberCall(f, first, "concat", {assistantGeometryArray(f, {QJSValue(0.001)})});
}
} // namespace

QJSValue ApplicationInfo::appColour(int kind, const QJSValue& first, const QJSValue& second, const QJSValue& third) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) return presentationPositioned(f, first, second, third);
    if (kind == 1 || kind == 2) {
        const auto colors = panelUsageContextRead(f, "colors");
        return panelUsageDeferredMemberCall(f, colors, "positioned", [&] {
            const auto positions = panelUsageTruth(assistantContextField(f, "Session", "project")) ? panelUsageRead(f, assistantContextField(f, "Session", "project"), kind == 1 ? "structureColourPositions" : "experimentColourPositions") : controlEmptyArray(f);
            return QJSValueList{positions, first, second};
        });
    }
    if (kind == 3) {
        if (first.strictlyEquals(QJSValue(QStringLiteral("structure")))) return projectInvoke(f, "colors", "structure", {second});
        if (first.strictlyEquals(QJSValue(QStringLiteral("experiment")))) return projectInvoke(f, "colors", "experiment", {second});
        return presentationStyle(f, "themeForegroundMinor");
    }
    const auto info = panelUsageContextRead(f, "ApplicationInfo");
    const auto colour = panelUsageDeferredMemberCall(f, info, "elementColor", [&] { return QJSValueList{panelUsageGlobalCall(f, "String", {first}), presentationStyle(f, "themeForegroundMinor"), assistantContextField(f, "colors", "elementScheme")}; });
    const auto colors = panelUsageContextRead(f, "colors");
    return panelUsageDeferredMemberCall(f, colors, "readable", [&] { return QJSValueList{colour, second.isUndefined() ? assistantContextField(f, "colors", "tableUnderlays") : second}; });
}
QJSValue ApplicationInfo::fitResultProjection(int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) return panelUsageMemberCall(f, assistantContextField(f, "dialog", "factorColumns"), "reduce", {panelUsageClosure(f, 360, {}, 2), QJSValue(QStringLiteral(""))});
    if (kind == 1) return panelUsageMemberCall(f, assistantContextField(f, "dialog", "factorColumns"), "some", {panelUsageClosure(f, 361, {}, 1)});
    return panelUsageDeferredMemberCall(f, assistantGeometryArray(f, {assistantContextField(f, "AppSizes", "iconOnlyColumnWidth"), QJSValue(-1)}), "concat", [&] { return QJSValueList{panelUsageMemberCall(f, assistantContextField(f, "dialog", "factorColumns"), "map", {panelUsageClosure(f, 364, {}, 0)})}; });
}
void ApplicationInfo::fitResultsPassive(const QJSValue& row) const {
    const auto f = panelUsageEngine(this); panelUsageEach(f, panelUsageRead(f, row, "resources"), [&](const QJSValue& handler) {
        if (panelUsageTruth(rowInstanceOf(f, handler, "HoverHandler"))) assistantMemberWrite(f, handler, "enabled", QJSValue(false)); return panelUsageReady(f);
    });
}
QJSValue ApplicationInfo::fitResultsSummaryWidth(const QJSValue& title, const QJSValue& cell) const {
    const auto f = panelUsageEngine(this); const auto revision = assistantContextField(f, "dialog", "resultsRevision"); Q_UNUSED(revision)
    auto widest = projectInvoke(f, "table", "advance", {title});
    for (double row = 0; panelUsageReady(f) && panelUsageTruth(assistantContextField(f, "dialog", "results")) && assistantRelation(f, QJSValue(row), panelUsageRead(f, assistantContextField(f, "dialog", "results"), "count"), 0); ++row)
        widest = numberMath(f, "max", [&] { const auto table = panelUsageContextRead(f, "table"); return QJSValueList{widest, panelUsageDeferredMemberCall(f, table, "advance", [&] { return QJSValueList{projectCall(f, cell, {QJSValue(row)})}; })}; });
    const auto rounded = numberMath(f, "ceil", [&] { return QJSValueList{widest}; });
    return panelUsageAdd(f, rounded, viewArithmetic(f, assistantContextField(f, "AppSizes", "fieldSpacing"), QJSValue(2), 1));
}
QJSValue ApplicationInfo::fitResultsColumnWidth(bool value) const {
    const auto f = panelUsageEngine(this); const auto title = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(value ? QT_TRANSLATE_NOOP("FitResultsDialog", "Value") : QT_TRANSLATE_NOOP("FitResultsDialog", "Metric")))});
    const auto width = panelUsageGlobalCall(f, "widestSummaryText", {title, panelUsageClosure(f, value ? 363 : 362, {}, 1)});
    return value ? panelUsageAdd(f, width, formsStyleSize(f, "fontPixelSize")) : width;
}
void ApplicationInfo::fitResultsRevisionChanged() const {
    const auto f = panelUsageEngine(this); const auto dialog = panelUsageContextRead(f, "dialog"); const auto number = panelUsageNumber(f, panelUsageRead(f, dialog, "resultsRevision"));
    if (number) assistantMemberWrite(f, dialog, "resultsRevision", QJSValue(*number + 1));
}
void ApplicationInfo::fitResultsShowEvolution() const {
    const auto f = panelUsageEngine(this); projectInvoke(f, "dialog", "close"); const auto state = panelUsageContextRead(f, "AppState");
    panelUsageDeferredMemberCall(f, state, "open", [&] { return QJSValueList{panelUsageRead(f, assistantContextField(f, "AppState", "Page"), "Analysis")}; }); projectInvoke(f, "AppState", "evolutionRequested");
}
void ApplicationInfo::aboutOpenLicence() const {
    const auto f = panelUsageEngine(this); const auto popup = panelUsageContextRead(f, "licencePopup"); assistantMemberWrite(f, popup, "title", assistantContextField(f, "licenceEntry", "modelData"));
    const auto next = panelUsageContextRead(f, "licencePopup"), info = panelUsageContextRead(f, "ApplicationInfo");
    const auto licence = panelUsageDeferredMemberCall(f, info, "licenceText", [&] { return QJSValueList{textIndex(f, assistantContextField(f, "ApplicationInfo", "appLicenceUrls"), assistantContextField(f, "licenceEntry", "index"))}; });
    assistantMemberWrite(f, next, "licence", licence); projectInvoke(f, "licencePopup", "open");
}
void ApplicationInfo::aboutPopulateComponents() const {
    const auto f = panelUsageEngine(this);
    for (double index = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(index), panelUsageRead(f, assistantContextField(f, "ApplicationInfo", "componentNames"), "length"), 0); ++index) {
        const auto component = textIndex(f, assistantContextField(f, "ApplicationInfo", "componentNames"), QJSValue(index));
        const auto version = textIndex(f, assistantContextField(f, "ApplicationInfo", "componentVersions"), QJSValue(index));
        const auto licence = textIndex(f, assistantContextField(f, "ApplicationInfo", "componentLicences"), QJSValue(index));
        const auto row = chartRecord(f, {{"component", component}, {"version", version}, {"licence", licence}}); panelUsageGlobalCall(f, "append", {row});
    }
}
QJSValue ApplicationInfo::aboutComponentsWidth() const {
    const auto f = panelUsageEngine(this); auto width = panelUsageMemberCall(f, panelUsageContextRead(f, "naturalWidths"), "reduce", {panelUsageClosure(f, 365, {}, 2), QJSValue(0)});
    const auto gap = formsStyleSize(f, "tableColumnSpacing"), count = viewArithmetic(f, panelUsageRead(f, panelUsageContextRead(f, "naturalWidths"), "length"), QJSValue(1), 0);
    width = panelUsageAdd(f, width, viewArithmetic(f, gap, count, 1)); width = panelUsageAdd(f, width, viewArithmetic(f, formsStyleSize(f, "borderThickness"), QJSValue(2), 1));
    return panelUsageAdd(f, width, viewArithmetic(f, panelUsageContextRead(f, "rowPadding"), QJSValue(2), 1));
}
QJSValue ApplicationInfo::parameterFieldValue(bool error) const {
    const auto f = panelUsageEngine(this); const char* field = error ? "error" : "value";
    if (panelUsageRead(f, panelUsageContextRead(f, "parameter"), field).isUndefined()) return QJSValue(QStringLiteral(""));
    if (numberType(f, panelUsageRead(f, panelUsageContextRead(f, "parameter"), "value"))) {
        const auto utils = panelUsageRead(f, panelUsageContextRead(f, "EaLogic"), "Utils");
        return panelUsageDeferredMemberCall(f, utils, error ? "toSinglePrecision" : "toErrSinglePrecision", [&] {
            const auto value = panelUsageRead(f, panelUsageContextRead(f, "parameter"), field);
            if (error) return QJSValueList{value}; return QJSValueList{value, panelUsageRead(f, panelUsageContextRead(f, "parameter"), "error")};
        });
    }
    return panelUsageRead(f, panelUsageContextRead(f, "parameter"), field);
}
void ApplicationInfo::parameterFieldMenu(const QJSValue& parent) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageContextRead(f, "contextMenu").isNull()) {
        const auto component = panelUsageContextRead(f, "contextMenuComponent"); panelUsageContextWrite(f, "contextMenu", panelUsageMemberCall(f, component, "createObject", {parent}));
    }
    projectInvoke(f, "contextMenu", "popup");
}
void ApplicationInfo::parameterFieldMouse(const QJSValue& mouse, bool hold) const {
    const auto f = panelUsageEngine(this); const auto actual = panelUsageRead(f, mouse, hold ? "source" : "button"), wanted = assistantContextField(f, "Qt", hold ? "MouseEventNotSynthesized" : "RightButton");
    if (actual.strictlyEquals(wanted)) { const auto control = panelUsageContextRead(f, "control"); panelUsageDeferredMemberCall(f, control, "openContextMenu", [&] { return QJSValueList{panelUsageContextRead(f, "menuArea")}; }); }
}
QJSValue ApplicationInfo::assistantPlanDescription() const {
    const auto f = panelUsageEngine(this); const auto plan = assistantContextField(f, "card", "assistant"); const auto actual = panelUsageRead(f, plan, "pendingPlan");
    if (!panelUsageTruth(panelUsageRead(f, actual, "budget"))) return QJSValue(QStringLiteral(""));
    const auto original = panelUsageRead(f, actual, "groups"), groups = panelUsageMemberCall(f, panelUsageMemberCall(f, panelUsageTruth(original) ? original : controlEmptyArray(f), "map", {panelUsageClosure(f, 366, {}, 1)}), "join", {QJSValue(QStringLiteral("\n"))});
    auto text = panelUsageAdd(f, groups, QJSValue(QStringLiteral("\n")));
    auto budget = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("AssistantPlan", "Budget: %1 trials, %2 iterations, %3 seconds")))});
    budget = panelUsageDeferredMemberCall(f, budget, "arg", [&] { return QJSValueList{panelUsageRead(f, panelUsageRead(f, actual, "budget"), "max_trials")}; });
    budget = panelUsageDeferredMemberCall(f, budget, "arg", [&] { return QJSValueList{panelUsageRead(f, panelUsageRead(f, actual, "budget"), "max_iterations")}; });
    budget = panelUsageDeferredMemberCall(f, budget, "arg", [&] { return QJSValueList{viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, actual, "budget"), "max_elapsed_ms"), QJSValue(1000), 2)}; });
    text = panelUsageAdd(f, panelUsageAdd(f, text, budget), QJSValue(QStringLiteral("\n")));
    auto objective = panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(QT_TRANSLATE_NOOP("AssistantPlan", "Improvement tolerance: absolute %1, relative %2")))});
    objective = panelUsageDeferredMemberCall(f, objective, "arg", [&] { return QJSValueList{panelUsageRead(f, panelUsageRead(f, actual, "objective"), "absolute_tolerance")}; });
    objective = panelUsageDeferredMemberCall(f, objective, "arg", [&] { return QJSValueList{panelUsageRead(f, panelUsageRead(f, actual, "objective"), "relative_tolerance")}; }); return panelUsageAdd(f, text, objective);
}
QJSValue ApplicationInfo::assistantSkillsIndex() const {
    const auto f = panelUsageEngine(this);
    for (double i = 0; panelUsageReady(f) && assistantRelation(f, QJSValue(i), panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "assistant"), "skills"), "count"), 0); ++i) {
        const auto skills = panelUsageRead(f, panelUsageContextRead(f, "assistant"), "skills"); const auto id = panelUsageMemberCall(f, skills, "text", {QJSValue(i), QJSValue(QStringLiteral("id"))});
        if (id.strictlyEquals(panelUsageRead(f, panelUsageContextRead(f, "assistant"), "selectedSkill"))) return QJSValue(i);
    }
    if (panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "assistant"), "selectedSkill"), "length").strictlyEquals(QJSValue(0)) && assistantRelation(f, panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "assistant"), "skills"), "count"), QJSValue(0), 1))
        return numberMath(f, "min", [&] { return QJSValueList{panelUsageContextRead(f, "inspectedIndex"), viewArithmetic(f, panelUsageRead(f, panelUsageRead(f, panelUsageContextRead(f, "assistant"), "skills"), "count"), QJSValue(1), 0)}; });
    return QJSValue(-1);
}
void ApplicationInfo::assistantSkillClicked() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageRead(f, panelUsageRead(f, assistantContextField(f, "dialog", "assistant"), "selectedSkill"), "length").strictlyEquals(QJSValue(0))) projectWrite(f, "dialog", "inspectedIndex", panelUsageContextRead(f, "index"));
    else { const auto assistant = assistantContextField(f, "dialog", "assistant"); panelUsageDeferredMemberCall(f, assistant, "selectSkill", [&] { return QJSValueList{assistantContextField(f, "model", "id")}; }); }
}
QJSValue ApplicationInfo::nativeListProjection(int kind) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) { const auto initial = assistantGeometryArray(f, {panelUsageContextRead(f, "numberColumnWidth")}); const auto names = assistantContextField(f, "categoryData", "names"); return presentationColumns(f, initial, names); }
    if (kind == 1) { const auto initial = assistantGeometryArray(f, {panelUsageContextRead(f, "numberColumnWidth"), QJSValue(-1), QJSValue(-1), QJSValue(-1), QJSValue(-1), QJSValue(-1), QJSValue(-1), QJSValue(-1), QJSValue(-1)}); const auto names = panelUsageContextRead(f, "componentNames"); return presentationColumns(f, initial, names); }
    if (kind == 2) return panelUsageMemberCall(f, assistantContextField(f, "table", "componentNames"), "map", {panelUsageClosure(f, 368, {}, 2)});
    if (kind == 3) return panelUsageMemberCall(f, assistantContextField(f, "group", "rules"), "map", {panelUsageClosure(f, 369, {}, 1)});
    const auto identity = panelUsageTruth(assistantContextField(f, "identityLabel", "truncated")) ? assistantContextField(f, "identityLabel", "text") : QJSValue(QStringLiteral(""));
    const auto tags = assistantRelation(f, assistantContextField(f, "tagRow", "width"), assistantContextField(f, "descriptionCell", "width"), 1) ? panelUsageMemberCall(f, assistantContextField(f, "row", "tagLabels"), "join", {QJSValue(QStringLiteral(" · "))}) : QJSValue(QStringLiteral(""));
    const auto detail = panelUsageTruth(assistantContextField(f, "detailLabel", "truncated")) ? assistantContextField(f, "row", "detail") : QJSValue(QStringLiteral(""));
    return panelUsageMemberCall(f, panelUsageMemberCall(f, assistantGeometryArray(f, {identity, tags, detail}), "filter", {panelUsageClosure(f, 370, {}, 1)}), "join", {QJSValue(QStringLiteral("\n"))});
}

namespace {
QJSValue createGroupField(const PanelUsageFrame& f, const char* name) { return assistantContextField(f, "group", name); }
void createGroupWrite(const PanelUsageFrame& f, const char* name, const QJSValue& value) { projectWrite(f, "group", name, value); }
bool createSameProject(const PanelUsageFrame& f, const QJSValue& original) { return assistantContextField(f, "Session", "project").strictlyEquals(panelUsageRead(f, original, "project")); }
bool createAlive(const PanelUsageFrame& f, const QJSValue& life) { return panelUsageTruth(panelUsageRead(f, life, "alive")); }
QJSValue lifecycleCallback(const PanelUsageFrame& f, uint op,
    const std::function<QJSValue(uint)>& saved, const std::function<QJSValue(uint)>& a) {
    if (op == 380) { projectInvoke(f, "Preferences", "apply"); return projectInvoke(f, "RecentProjects", "refresh"); }
    if (op == 381) return panelUsageRead(f, a(0), "wanted");
    if (op == 382) {
        const auto wanted = panelUsageRead(f, a(0), "wanted"); if (!panelUsageTruth(wanted)) return wanted;
        return QJSValue(panelUsageRead(f, a(0), "status").strictlyEquals(assistantContextField(f, "Loader", "Ready")));
    }
    if (op == 383) {
        if (!panelUsageTruth(panelUsageRead(f, a(0), "wanted"))) return QJSValue(true);
        return QJSValue(panelUsageRead(f, a(0), "status").strictlyEquals(assistantContextField(f, "Loader", "Ready")));
    }
    if (op == 384) {
        if (!saved(0).isNull() && (!createGroupField(f, "assistantCreate").strictlyEquals(saved(0)) || !assistantContextField(f, "Session", "project").strictlyEquals(panelUsageRead(f, saved(0), "project")))) return {};
        return projectInvoke(f, "group", "chooseCreate");
    }
    if (op == 385) {
        if (!saved(0).isNull()) { const auto assistant = assistantContextField(f, "Session", "assistant"); return panelUsageDeferredMemberCall(f, assistant, "nativeProjectCreateReady", [&] { return QJSValueList{panelUsageRead(f, saved(0), "id"), QJSValue(false)}; }); } return {};
    }
    if (op == 386) {
        const auto life = saved(0), original = saved(1);
        if (!createAlive(f, life) || !createGroupField(f, "createIntent").strictlyEquals(original) || panelUsageTruth(assistantContextField(f, "createDialog", "visible"))) return {};
        if (!original.isNull() && !panelUsageRead(f, original, "assistant").isNull() && createGroupField(f, "assistantCreate").strictlyEquals(panelUsageRead(f, original, "assistant"))) createGroupWrite(f, "assistantCreate", consentNull());
        if (!createAlive(f, life) || !createGroupField(f, "createIntent").strictlyEquals(original) || panelUsageTruth(assistantContextField(f, "createDialog", "visible"))) return {};
        createGroupWrite(f, "createIntent", consentNull());
        if (!createAlive(f, life) || !createGroupField(f, "createIntent").isNull() || panelUsageTruth(assistantContextField(f, "createDialog", "visible"))) return {};
        assistantMemberWrite(f, panelUsageRead(f, panelUsageContextRead(f, "EaGlobals"), "Vars"), "showProjectDescriptionDialog", QJSValue(false)); return {};
    }
    if (op == 387) {
        const auto life = saved(0), original = saved(1);
        if (!createAlive(f, life) || !createGroupField(f, "createOperation").strictlyEquals(original) || !createSameProject(f, original) || (!panelUsageRead(f, original, "assistant").isNull() && panelUsageTruth(panelUsageRead(f, panelUsageRead(f, original, "assistant"), "cancelled")))) return {};
        const auto session = panelUsageContextRead(f, "Session");
        const auto outcome = panelUsageDeferredMemberCall(f, session, "createProjectWithOutcome", [&] {
            return QJSValueList{saved(2), saved(3), saved(4), assistantContextField(f, "Preferences", "newProjectSuRule"), saved(5), saved(6), QJSValue(assistantContextField(f, "Preferences", "newReportLibraries").strictlyEquals(QJSValue(QStringLiteral("embedded")))), !panelUsageRead(f, original, "assistant").isNull() ? panelUsageRead(f, panelUsageRead(f, original, "assistant"), "id") : QJSValue(QStringLiteral(""))};
        });
        if (!panelUsageTruth(panelUsageRead(f, outcome, "success")) && panelUsageTruth(panelUsageRead(f, outcome, "current")) && panelUsageTruth(projectInvoke(f, "Session", "creationOutcomeCurrent", {outcome})) && assistantRelation(f, panelUsageRead(f, panelUsageRead(f, outcome, "error"), "length"), QJSValue(0), 1) && panelUsageRead(f, original, "assistant").isNull()) return projectInvoke(f, "AppState", "createFailed");
    }
    if (op == 388) return projectInvoke(f, "openChoice", "open");
    return {};
}
QJSValue mainText(const PanelUsageFrame& f, const char* text) { return panelUsageGlobalCall(f, "qsTr", {QJSValue(QString::fromUtf8(text))}); }
} // namespace

QJSValue ApplicationInfo::workflowPagesCount(bool built) const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(assistantContextField(f, "Session", "hasProject"))) return QJSValue(0);
    return panelUsageRead(f, panelUsageMemberCall(f, panelUsageContextRead(f, "pageLoaders"), "filter", {panelUsageClosure(f, built ? 382 : 381, {}, 1)}), "length");
}
QJSValue ApplicationInfo::workflowPageTurn(const QJSValue& loader) const {
    const auto f = panelUsageEngine(this); const auto started = panelUsageContextRead(f, "pagesStarted"); if (!panelUsageTruth(started)) return started;
    const auto loaders = panelUsageContextRead(f, "pageLoaders");
    const auto earlier = panelUsageDeferredMemberCall(f, loaders, "slice", [&] { return QJSValueList{QJSValue(0), panelUsageMemberCall(f, panelUsageContextRead(f, "pageLoaders"), "indexOf", {loader})}; });
    return panelUsageMemberCall(f, earlier, "every", {panelUsageClosure(f, 383, {}, 1)});
}
void ApplicationInfo::workflowProjectChanging() const {
    const auto f = panelUsageEngine(this); projectWrite(f, "window", "pagesStarted", QJSValue(false));
    if (assistantRelation(f, panelUsageRead(f, assistantContextField(f, "window", "appBarCentralTabs"), "currentIndex"), QJSValue(1), 1)) panelUsageMemberCall(f, assistantContextField(f, "window", "appBarCentralTabs"), "setCurrentIndex", {QJSValue(1)});
}
QJSValue ApplicationInfo::workflowPreparingTab() const {
    const auto f = panelUsageEngine(this); if (!panelUsageTruth(assistantContextField(f, "tabBarHover", "hovered"))) return consentNull();
    const auto tabs = assistantGeometryArray(f, {panelUsageContextRead(f, "projectTab"), panelUsageContextRead(f, "structureTab"), panelUsageContextRead(f, "experimentTab"), panelUsageContextRead(f, "analysisTab"), panelUsageContextRead(f, "reportTab")});
    QJSValue found = consentNull(); panelUsageEach(f, tabs, [&](const QJSValue& tab) {
        const auto point = panelUsageDeferredMemberCall(f, tab, "mapFromItem", [&] { return QJSValueList{panelUsageContextRead(f, "tabBarOverlay"), panelUsageRead(f, panelUsageRead(f, assistantContextField(f, "tabBarHover", "point"), "position"), "x"), panelUsageRead(f, panelUsageRead(f, assistantContextField(f, "tabBarHover", "point"), "position"), "y")}; });
        if (panelUsageTruth(panelUsageRead(f, tab, "preparing")) && panelUsageTruth(panelUsageMemberCall(f, tab, "contains", {point}))) { found = tab; return false; } return panelUsageReady(f);
    }); return found;
}
void ApplicationInfo::windowAssistantAction(int kind, const QJSValue& page, const QJSValue& extra) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) {
        const auto project = assistantContextField(f, "Session", "project"); if (!panelUsageTruth(project)) return; QJSValue target = consentNull(), destination(-1);
        const char* loader = nullptr; const char* name = nullptr;
        if (page.strictlyEquals(QJSValue(QStringLiteral("analysis"))) && panelUsageTruth(assistantContextField(f, "AppState", "analysisPageEnabled"))) { loader = "analysisLoader"; name = "Analysis"; }
        else if (page.strictlyEquals(QJSValue(QStringLiteral("experiment"))) && panelUsageTruth(assistantContextField(f, "AppState", "experimentPageEnabled"))) { loader = "experimentLoader"; name = "Experiment"; }
        else if (page.strictlyEquals(QJSValue(QStringLiteral("structure"))) && panelUsageTruth(assistantContextField(f, "AppState", "structurePageEnabled"))) { loader = "structureLoader"; name = "Structure"; }
        if (loader) { target = assistantContextField(f, loader, "item"); destination = panelUsageRead(f, assistantContextField(f, "AppState", "Page"), name); }
        if (!panelUsageTruth(target) || assistantRelation(f, destination, QJSValue(0), 0)) return;
        projectInvoke(f, "AppState", "open", {destination});
        if (assistantContextField(f, "Session", "project").strictlyEquals(project) && target.strictlyEquals(assistantContextField(f, "window", "assistantWorkflowPage"))) panelUsageMemberCall(f, target, "showSidebarTab", {extra}); return;
    }
    if (kind == 1) { if (!panelUsageTruth(panelUsageRead(f, assistantContextField(f, "Session", "assistant"), "showingActions"))) projectWrite(f, "window", "assistantManualPane", QJSValue(false)); return; }
    if (kind == 2) { if (!panelUsageRead(f, assistantContextField(f, "Session", "assistant"), "state").strictlyEquals(QJSValue(QStringLiteral("agent_active")))) projectInvoke(f, "assistantPointer", "hide"); return; }
    projectWrite(f, "window", "assistantManualTakeoverProject", assistantContextField(f, "Session", "project")); projectWrite(f, "window", "assistantEmptyManualTakeover", QJSValue(assistantContextField(f, "Session", "project").isNull()));
}
void ApplicationInfo::windowWebSaved(const QJSValue& kind) const {
    const auto f = panelUsageEngine(this); if (!kind.strictlyEquals(QJSValue(QStringLiteral("browser")))) return;
    if (!assistantContextField(f, "browserSaved", "warnedFor").strictlyEquals(assistantContextField(f, "Session", "project"))) {
        projectWrite(f, "browserSaved", "warnedFor", assistantContextField(f, "Session", "project")); projectWrite(f, "browserSaved", "kept", QJSValue(true)); projectInvoke(f, "browserSaved", "open");
    } else { const auto notice = panelUsageContextRead(f, "webNotice"); panelUsageDeferredMemberCall(f, notice, "show", [&] { return QJSValueList{mainText(f, QT_TRANSLATE_NOOP("Main", "Saved in this browser only."))}; }); }
}
void ApplicationInfo::windowStorageUnavailable() const { const auto f = panelUsageEngine(this); projectWrite(f, "browserSaved", "kept", QJSValue(false)); projectInvoke(f, "browserSaved", "open"); }
void ApplicationInfo::windowWebDownloaded(const QJSValue& name, const QJSValue& fromFile) const {
    const auto f = panelUsageEngine(this); auto text = panelUsageMemberCall(f, mainText(f, QT_TRANSLATE_NOOP("Main", "%1 was handed to the browser to download.")), "arg", {name});
    if (panelUsageTruth(fromFile)) text = panelUsageAdd(f, text, panelUsageAdd(f, QJSValue(QStringLiteral(" ")), mainText(f, QT_TRANSLATE_NOOP("Main", "To replace the original file, have the browser ask where to save downloads and choose that file."))));
    projectInvoke(f, "webNotice", "show", {text});
}
void ApplicationInfo::windowFailure(int kind, const QJSValue& message) const {
    const auto f = panelUsageEngine(this); const char* popup = kind == 0 ? "webFilesError" : kind == 3 ? "fitError" : "refusal";
    if (kind == 1 || kind == 2) { const auto target = panelUsageContextRead(f, popup); assistantMemberWrite(f, target, "title", mainText(f, kind == 1 ? QT_TRANSLATE_NOOP("Main", "The project was not opened") : QT_TRANSLATE_NOOP("Main", "The change was not made"))); }
    projectWrite(f, popup, "message", message); projectInvoke(f, popup, "open");
}
void ApplicationInfo::windowBrowserWarningReady() const {
    const auto f = panelUsageEngine(this); const auto button = panelUsageGlobalCall(f, "standardButton", {assistantContextField(f, "Dialog", "Apply")});
    assistantMemberWrite(f, button, "text", mainText(f, QT_TRANSLATE_NOOP("Main", "Save project as…")));
    assistantMemberWrite(f, panelUsageGlobalCall(f, "standardButton", {assistantContextField(f, "Dialog", "Apply")}), "objectName", QJSValue(QStringLiteral("webStorageWarning.saveAs")));
    assistantMemberWrite(f, panelUsageGlobalCall(f, "standardButton", {assistantContextField(f, "Dialog", "Ok")}), "objectName", QJSValue(QStringLiteral("webStorageWarning.ok")));
}
void ApplicationInfo::windowBrowserWarningApplied() const { const auto f = panelUsageEngine(this); panelUsageGlobalCall(f, "close", {}); projectInvoke(f, "window", "saveProjectAs"); }
void ApplicationInfo::windowNotice(const QJSValue& message) const { const auto f = panelUsageEngine(this); panelUsageContextWrite(f, "text", message); panelUsageGlobalCall(f, "open", {}); projectInvoke(f, "webNoticeTimer", "restart"); }
void ApplicationInfo::windowAutomaticResults() const { const auto f = panelUsageEngine(this); if (panelUsageTruth(assistantContextField(f, "Preferences", "showFitResults"))) projectInvoke(f, "fitResults", "open"); }
void ApplicationInfo::windowCompleted() const {
    const auto f = panelUsageEngine(this); const auto renderer = panelUsageContextRead(f, "RenderingInfo"); panelUsageDeferredMemberCall(f, renderer, "observe", [&] { return QJSValueList{panelUsageContextRead(f, "window")}; });
    panelUsageGlobalCall(f, "restoreGeometry", {}); const auto qt = panelUsageContextRead(f, "Qt"); panelUsageMemberCall(f, qt, "callLater", {projectGuardedClosure(f, 380)});
}
void ApplicationInfo::resetPatternProjectView() const {
    const auto f = panelUsageEngine(this); const auto state = panelUsageContextRead(f, "AppState");
    const auto ranges = assistantGeometryArray(f, {panelUsageContextRead(f, "NaN"), panelUsageContextRead(f, "NaN"), panelUsageContextRead(f, "NaN"), panelUsageContextRead(f, "NaN")}); assistantMemberWrite(f, state, "patternViewRanges", ranges);
    projectWrite(f, "AppState", "patternViewAxis", QJSValue(QStringLiteral(""))); projectWrite(f, "AppState", "scanZoom", panelUsageComplete(f, panelUsageLiteral(f)));
}

QJSValue ApplicationInfo::prepareAssistantCreate(const QJSValue& id) const {
    const auto f = panelUsageEngine(this);
    if (panelUsageRead(f, id, "length").strictlyEquals(QJSValue(0)) || !panelUsageContextRead(f, "createIntent").isNull() || !panelUsageContextRead(f, "assistantCreate").isNull() || panelUsageTruth(assistantContextField(f, "createDialog", "visible")) || !panelUsageTruth(panelUsageMemberCall(f, assistantContextField(f, "Session", "assistant"), "nativeProjectCreateCurrent", {id}))) return QJSValue(false);
    const auto before = assistantContextField(f, "Session", "project"); const auto next = chartRecord(f, {{"id", id}, {"project", before}, {"cancelled", QJSValue(false)}}); panelUsageContextWrite(f, "assistantCreate", next);
    if (panelUsageContextRead(f, "assistantCreate").isNull()) return QJSValue(false);
    if (!panelUsageRead(f, panelUsageContextRead(f, "assistantCreate"), "id").strictlyEquals(id)) return QJSValue(false);
    return QJSValue(assistantContextField(f, "Session", "project").strictlyEquals(before));
}
QJSValue ApplicationInfo::assistantCreateDialog(const QJSValue& id) const {
    const auto f = panelUsageEngine(this); return !panelUsageContextRead(f, "assistantCreate").isNull() && panelUsageRead(f, panelUsageContextRead(f, "assistantCreate"), "id").strictlyEquals(id) ? panelUsageContextRead(f, "createDialog") : consentNull();
}
void ApplicationInfo::retireAssistantCreate(const QJSValue& id, bool manual) const {
    const auto f = panelUsageEngine(this); const auto original = panelUsageContextRead(f, "assistantCreate"); if (original.isNull() || !panelUsageRead(f, original, "id").strictlyEquals(id)) return;
    assistantMemberWrite(f, original, "cancelled", QJSValue(true)); const auto pending = panelUsageContextRead(f, "createIntent");
    if (manual && !pending.isNull() && panelUsageRead(f, pending, "assistant").strictlyEquals(original)) assistantMemberWrite(f, pending, "assistant", consentNull());
    if (panelUsageContextRead(f, "assistantCreate").strictlyEquals(original)) panelUsageContextWrite(f, "assistantCreate", consentNull());
    if (!manual && panelUsageContextRead(f, "createIntent").strictlyEquals(pending) && !pending.isNull() && panelUsageRead(f, pending, "assistant").strictlyEquals(original)) projectInvoke(f, "createDialog", "close");
}
QJSValue ApplicationInfo::createProjectNameError(const QJSValue& name) const {
    const auto f = panelUsageEngine(this); if (panelUsageTruth(projectInvoke(f, "createDialog", "acceptsProjectName", {name}))) return QJSValue(QStringLiteral(""));
    return mainText(f, QT_TRANSLATE_NOOP("GetStartedGroup", "Project Name must contain 2–31 characters: start with an ASCII letter, then use letters, digits, underscore, hyphen or period. Put human-readable text in Title. The supplied Name was not changed."));
}
QJSValue ApplicationInfo::createProjectDefaults(const QJSValue& name, const QJSValue& description, const QJSValue& title) const {
    const auto f = panelUsageEngine(this); if (!panelUsageContextRead(f, "createIntent").isNull() || panelUsageTruth(assistantContextField(f, "createDialog", "visible"))) return panelUsageComplete(f, panelUsageLiteral(f));
    const auto actual = assistantRelation(f, panelUsageRead(f, name, "length"), QJSValue(0), 1) ? name : QJSValue(QStringLiteral("project")); const auto error = panelUsageGlobalCall(f, "nativeProjectNameError", {actual});
    if (assistantRelation(f, panelUsageRead(f, error, "length"), QJSValue(0), 1)) return chartRecord(f, {{"error", error}, {"target", QJSValue(QStringLiteral("createProject.name"))}});
    const auto actualTitle = title.isUndefined() || title.isNull() ? assistantContextField(f, "createDialog", "projectTitle") : title;
    if (!panelUsageTruth(projectInvoke(f, "createDialog", "acceptsProjectTitle", {actualTitle}))) {
        const auto text = mainText(f, QT_TRANSLATE_NOOP("GetStartedGroup", "Project Title must fit the original single-line field (%1 UTF-16 units), without NUL, newline, carriage-return or tab. The supplied Title was not changed."));
        const auto message = panelUsageDeferredMemberCall(f, text, "arg", [&] { return QJSValueList{assistantContextField(f, "createDialog", "projectTitleMaximumLength")}; }); return chartRecord(f, {{"error", message}, {"target", QJSValue(QStringLiteral("createProject.title"))}});
    }
    QJSValue parent;
    if (panelUsageTruth(assistantContextField(f, "createDialog", "projectParentDirectory"))) {
        const auto utils = panelUsageRead(f, panelUsageContextRead(f, "EaLogic"), "Utils"); parent = panelUsageDeferredMemberCall(f, utils, "urlToLocalFile", [&] { return QJSValueList{assistantContextField(f, "createDialog", "projectParentDirectory")}; });
    } else parent = assistantContextField(f, "createDialog", "defaultProjectParentDirectory");
    const auto authors = assistantContextField(f, "createDialog", "projectAuthors");
    const auto location = panelUsageTruth(assistantContextField(f, "WebFiles", "available")) ? QJSValue(QStringLiteral("")) : projectInvoke(f, "createDialog", "joinedPath", {parent, actual});
    const auto rule = assistantContextField(f, "Preferences", "newProjectSuRule"), libraries = assistantContextField(f, "Preferences", "newReportLibraries");
    return chartRecord(f, {{"name", actual}, {"description", description}, {"title", actualTitle}, {"authors", authors}, {"location", location}, {"suRule", rule}, {"reportLibraries", QJSValue(libraries.strictlyEquals(QJSValue(QStringLiteral("embedded"))))}});
}
void ApplicationInfo::chooseCreateProject() const {
    const auto f = panelUsageEngine(this); if (!panelUsageContextRead(f, "createIntent").isNull() || panelUsageTruth(assistantContextField(f, "createDialog", "visible"))) return;
    const auto life = panelUsageContextRead(f, "createLife"), project = assistantContextField(f, "Session", "project"), assistant = panelUsageContextRead(f, "assistantCreate"); const auto original = chartRecord(f, {{"project", project}, {"assistant", assistant}});
    panelUsageContextWrite(f, "createOperation", original); if (!createAlive(f, life) || !panelUsageContextRead(f, "createOperation").strictlyEquals(original)) return;
    panelUsageContextWrite(f, "createIntent", original); if (!createAlive(f, life) || !panelUsageContextRead(f, "createIntent").strictlyEquals(original) || !createSameProject(f, original)) return;
    assistantMemberWrite(f, panelUsageRead(f, panelUsageContextRead(f, "EaGlobals"), "Vars"), "showProjectDescriptionDialog", QJSValue(true));
}
void ApplicationInfo::createProjectClicked() const {
    const auto f = panelUsageEngine(this); const auto original = createGroupField(f, "assistantCreate"), state = panelUsageContextRead(f, "AppState");
    panelUsageMemberCall(f, state, "afterChanges", {panelUsageClosure(f, 384, {original}), panelUsageClosure(f, 385, {original})});
}
void ApplicationInfo::createProjectDialogEvent(int kind) const {
    const auto f = panelUsageEngine(this); QJSValue life; if (kind >= 2) life = createGroupField(f, "createLife"); const auto original = createGroupField(f, "createIntent");
    if (kind == 0 || kind == 1) {
        if (!original.isNull() && !panelUsageRead(f, original, "assistant").isNull()) {
            const auto assistant = assistantContextField(f, "Session", "assistant"); panelUsageDeferredMemberCall(f, assistant, "observeCreateDialog", [&] { return QJSValueList{panelUsageContextRead(f, "createDialog"), panelUsageRead(f, panelUsageRead(f, original, "assistant"), "id"), QJSValue(kind == 0 ? QStringLiteral("opened") : QStringLiteral("rejected"))}; });
        } return;
    }
    if (kind == 2) {
        const auto qt = panelUsageContextRead(f, "Qt"); panelUsageMemberCall(f, qt, "callLater", {panelUsageClosure(f, 386, {life, original})}); return;
    }
    if (original.isNull() || !createSameProject(f, original) || (!panelUsageRead(f, original, "assistant").isNull() && panelUsageTruth(panelUsageRead(f, panelUsageRead(f, original, "assistant"), "cancelled")))) return;
    if (!panelUsageRead(f, original, "assistant").isNull()) {
        const auto assistant = assistantContextField(f, "Session", "assistant"); const auto accepted = panelUsageDeferredMemberCall(f, assistant, "observeCreateDialog", [&] { return QJSValueList{panelUsageContextRead(f, "createDialog"), panelUsageRead(f, panelUsageRead(f, original, "assistant"), "id"), QJSValue(QStringLiteral("accepted"))}; }); if (!panelUsageTruth(accepted)) return;
    }
    createGroupWrite(f, "createIntent", consentNull()); if (!createAlive(f, life) || !createGroupField(f, "createOperation").strictlyEquals(original) || !createSameProject(f, original)) return;
    if (!panelUsageRead(f, original, "assistant").isNull() && createGroupField(f, "assistantCreate").strictlyEquals(panelUsageRead(f, original, "assistant"))) createGroupWrite(f, "assistantCreate", consentNull());
    const auto name = assistantContextField(f, "createDialog", "projectName"), description = assistantContextField(f, "createDialog", "projectDescription");
    const auto location = panelUsageTruth(assistantContextField(f, "WebFiles", "available")) ? QJSValue(QStringLiteral("")) : assistantContextField(f, "createDialog", "projectLocation");
    const auto title = assistantContextField(f, "createDialog", "projectTitle"), authors = assistantContextField(f, "createDialog", "projectAuthors");
    assistantMemberWrite(f, panelUsageRead(f, panelUsageContextRead(f, "EaGlobals"), "Vars"), "showProjectDescriptionDialog", QJSValue(false));
    const auto qt = panelUsageContextRead(f, "Qt"); panelUsageMemberCall(f, qt, "callLater", {panelUsageClosure(f, 387, {life, original, name, description, location, title, authors})});
}
void ApplicationInfo::openProjectChoice() const {
    const auto f = panelUsageEngine(this);
    if (panelUsageTruth(assistantContextField(f, "WebFiles", "available"))) projectInvoke(f, "Session", "openWebProject", {panelUsageTruth(panelUsageContextRead(f, "zip")) ? QJSValue(QStringLiteral("file")) : QJSValue(QStringLiteral("folder"))});
    else if (panelUsageTruth(panelUsageContextRead(f, "zip"))) projectInvoke(f, "openZipDialog", "open"); else projectInvoke(f, "openFolderDialog", "open");
}
void ApplicationInfo::askOpenProjectChoice() const { const auto f = panelUsageEngine(this); const auto state = panelUsageContextRead(f, "AppState"); panelUsageMemberCall(f, state, "afterChanges", {projectGuardedClosure(f, 388)}); }
void ApplicationInfo::windowSaveChoiceOpened() const {
    const auto f = panelUsageEngine(this); if (panelUsageTruth(panelUsageContextRead(f, "nativeAcceptButton"))) assistantMemberWrite(f, panelUsageContextRead(f, "nativeAcceptButton"), "objectName", QJSValue(QStringLiteral("saveAs.accept")));
}
QJSValue ApplicationInfo::windowUnsavedText() const {
    const auto f = panelUsageEngine(this); const auto text = mainText(f, QT_TRANSLATE_NOOP("Main", "The current project <b>%1</b> has unsaved changes."));
    return panelUsageDeferredMemberCall(f, text, "arg", [&] {
        QJSValue name(QStringLiteral("")); if (!assistantContextField(f, "Session", "project").isNull()) {
            const auto first = panelUsageMemberCall(f, panelUsageRead(f, assistantContextField(f, "Session", "project"), "name"), "replace", {panelRegex(f, QStringLiteral("&"), QV4::CompiledData::RegExp::RegExp_Global), QJSValue(QStringLiteral("&amp;"))});
            name = panelUsageMemberCall(f, first, "replace", {panelRegex(f, QStringLiteral("<"), QV4::CompiledData::RegExp::RegExp_Global), QJSValue(QStringLiteral("&lt;"))});
        } return QJSValueList{name};
    });
}

void ApplicationInfo::finishUiEvent(int kind, const QJSValue& value) const {
    const auto f = panelUsageEngine(this);
    if (kind == 0) { projectWrite(f, "control", "enterFlash", QJSValue(true)); projectInvoke(f, "enterFlashTimer", "start"); return; }
    if (kind == 1) { panelUsageContextWrite(f, "flashing", QJSValue(true)); projectInvoke(f, "flashEnd", "restart"); return; }
    if (kind == 2) {
        if (!panelUsageTruth(panelUsageContextRead(f, "patternEnabled")) && panelUsageTruth(panelUsageContextRead(f, "patternShown"))) panelUsageGlobalCall(f, "showMainTab", {QJSValue(0)}); return;
    }
    if (kind == 3) { if (!panelUsageTruth(panelUsageContextRead(f, "scanMode"))) projectInvoke(f, "page", "showMainTab", {QJSValue(0)}); return; }
    if (kind == 4) { if (panelUsageTruth(panelUsageContextRead(f, "parent"))) assistantMemberWrite(f, panelUsageContextRead(f, "parent"), "z", QJSValue(1)); return; }
    if (kind == 5) {
        if (panelUsageTruth(assistantContextField(f, "table", "sourceModel"))) { const auto model = assistantContextField(f, "table", "sourceModel"); panelUsageDeferredMemberCall(f, model, "sortBy", [&] { return QJSValueList{assistantContextField(f, "title", "role")}; }); } return;
    }
    if (kind == 6) { if (!panelUsageTruth(assistantContextField(f, "slider", "pressed"))) projectInvoke(f, "sliderRow", "updateLimits"); return; }
    if (kind >= 7 && kind <= 9) {
        if (panelUsageTruth(assistantContextField(f, "dialog", "messages"))) {
            const auto messages = assistantContextField(f, "dialog", "messages");
            if (kind == 9) panelUsageDeferredMemberCall(f, messages, "dismiss", [&] { return QJSValueList{assistantContextField(f, "row", "index")}; });
            else panelUsageMemberCall(f, messages, kind == 7 ? "markViewed" : "dismissAll", {});
        } return;
    }
    if (kind >= 10 && kind <= 12) {
        if (panelUsageTruth(panelUsageContextRead(f, "activeFocus"))) {
            if (kind == 11) { const auto group = panelUsageContextRead(f, "group"); assistantMemberWrite(f, group, "selected", assistantContextField(f, "row", "parameter")); }
            else { const auto project = assistantContextField(f, "group", "project"); assistantMemberWrite(f, project, kind == 10 ? "currentStructureIndex" : "currentExperimentIndex", assistantContextField(f, "row", "index")); }
        } return;
    }
    if (kind == 13 || kind == 14) {
        const bool active = panelUsageTruth(panelUsageContextRead(f, kind == 13 ? "visible" : "collapsed"));
        if (kind == 13 ? active : !active) projectInvoke(f, "RecentProjects", "refresh"); return;
    }
    if (kind == 15) {
        const bool pattern = panelUsageTruth(assistantContextField(f, "page", "patternShown")); const auto project = assistantContextField(f, "page", "project"); assistantMemberWrite(f, project, pattern ? "currentExperimentIndex" : "currentStructureIndex", value);
    }
}

void ApplicationInfo::workflowTextItemChanged() const {
    const auto f = panelUsageEngine(this); const auto page = panelUsageContextRead(f, "page");
    const bool dirty = !panelUsageContextRead(f, "item").isNull() && panelUsageRead(f, panelUsageContextRead(f, "item"), "dirty").strictlyEquals(QJSValue(true));
    assistantMemberWrite(f, page, "textDirty", QJSValue(dirty));
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
