// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_view_model.hpp"

#include <QFile>
#include <QSettings>
#include <QThread>
#include <array>
#include <limits>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaObject>
#include <QSaveFile>
#include <QStandardPaths>
#include <QDir>
#include <QUuid>
#include <optional>
#include <stdexcept>
#include <algorithm>
#include <map>

#if defined(Q_OS_WIN)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

#include "engine_setup.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#ifndef __EMSCRIPTEN__
#include "chatgpt_connection.hpp"
#include "connection_services.hpp"
#endif

namespace edi_app {
namespace {
using Object = QJsonObject;
std::string json(const Object& object) { return QJsonDocument(object).toJson(QJsonDocument::Compact).toStdString(); }
Object object(const std::string& text) { return QJsonDocument::fromJson(QByteArray::fromStdString(text)).object(); }

void open_selected_regular(QFile& file, const QString& path) {
#if defined(Q_OS_WIN)
    const auto native = QDir::toNativeSeparators(path).toStdWString();
    HANDLE handle = CreateFileW(native.c_str(), GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Selected file could not be opened");
    BY_HANDLE_FILE_INFORMATION information{};
    if (GetFileType(handle) != FILE_TYPE_DISK || !GetFileInformationByHandle(handle, &information) ||
        (information.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) {
        CloseHandle(handle); throw std::runtime_error("Select regular files directly, not folders, devices or links");
    }
    const int descriptor = _open_osfhandle(reinterpret_cast<intptr_t>(handle), _O_RDONLY | _O_BINARY);
    if (descriptor < 0) { CloseHandle(handle); throw std::runtime_error("Selected file could not be opened"); }
    if (!file.open(descriptor, QIODevice::ReadOnly | QIODevice::Unbuffered, QFileDevice::AutoCloseHandle)) {
        _close(descriptor); throw std::runtime_error("Selected file could not be read");
    }
#else
    const auto native = QFile::encodeName(path);
    int flags = O_RDONLY | O_NONBLOCK;
#ifdef O_CLOEXEC
    flags |= O_CLOEXEC;
#endif
#ifdef O_NOFOLLOW
    flags |= O_NOFOLLOW;
#endif
    const int descriptor = ::open(native.constData(), flags);
    if (descriptor < 0) throw std::runtime_error("Selected file could not be opened");
    struct stat information{};
    if (::fstat(descriptor, &information) != 0 || !S_ISREG(information.st_mode)) {
        ::close(descriptor); throw std::runtime_error("Select regular files directly, not folders, devices or links");
    }
    if (!file.open(descriptor, QIODevice::ReadOnly | QIODevice::Unbuffered, QFileDevice::AutoCloseHandle)) {
        ::close(descriptor); throw std::runtime_error("Selected file could not be read");
    }
#endif
}

class Rows : public RowTableModel {
   public:
    Rows(const QStringList& names, QObject* parent, const QJsonArray* canonical = nullptr)
        : RowTableModel(names, parent), names_(names), canonical_(canonical) {}
    void assign(const QJsonArray& data) {
        // Keys only: payloads belong to the canonical JSON array, not a second
        // recursively converted QVariant snapshot in the model.
        if (!canonical_) own_ = data;
        const auto& source = canonical_ ? *canonical_ : own_;
        QList<Row> rows; rows.reserve(source.size());
        for (qsizetype i = 0; i < source.size(); ++i)
            rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)), {}});
        setTableRows(rows);
        announceRows(0, static_cast<int>(source.size()) - 1);
    }
   protected:
    QList<QVariant> rowValues(int row) const override {
        const auto& source = canonical_ ? *canonical_ : own_;
        if (row < 0 || row >= source.size()) return {};
        const auto entry = source.at(row).toObject();
        QList<QVariant> values; values.reserve(names_.size());
        for (const auto& name : names_) values.append(entry.value(name).toVariant());
        return values;
    }
   private:
    QStringList names_;
    const QJsonArray* canonical_;
    QJsonArray own_;
};}

struct AssistantViewModel::State {
    AssistantViewModel& owner;
    ProjectViewModel* project = nullptr;
    std::unique_ptr<edi::work::Worker> idle_worker;
    std::unique_ptr<edi::assistant::Controller> controller;
#ifndef __EMSCRIPTEN__
    std::unique_ptr<edi::assistant::native::ChatGptConnection> connection;
#endif
    QJsonArray history;
    Rows messages{{"id", "kind", "text", "status", "payload"}, &owner, &history};
    Rows models{{"id", "displayName", "efforts", "available"}, &owner};
    Rows skills{{"id", "version", "title", "summary", "path", "sha256", "requires", "capabilities", "references", "content", "available", "blocked_reason"}, &owner};
    QString selected_skill, workflow_error;
    QByteArray skill_catalog_binding;
    QJsonArray selected_rows;
    Rows selected_files{{"id", "name", "bytes", "textReadable", "format"}, &owner, &selected_rows};
    std::string selected_reply; // bounded descriptors only; canonical bytes belong solely to Controller
    bool selected_rows_dirty = false, file_staging = false, file_authority_exhausted = false;
    std::uint64_t file_epoch = 0, file_connection_epoch = 0;
    struct FileSelection {
        QString id, collection_id, next_collection_id, connection_id, native_status;
        std::uint64_t owner_generation = 0, epoch = 0, connection_epoch = 0, selection_generation = 0;
        edi::assistant::Controller* controller = nullptr;
        ProjectViewModel* project = nullptr;
        edi::assistant::Revision revision;
    };
    std::optional<FileSelection> file_selection;
    Object core, native, plan, question;
    QString model, effort, error, preference_error, preference_save_error;
    // Edi preferences, scoped to this provider, never a connection ID or provider profile.
    QString choice_store, remembered_model, remembered_effort;
    bool restore_choice_pending = true, choice_warning_shown = false, choice_read_complete = false;

    bool own_edit = false, auth_pending = false;
    QString observed_native_error;
    std::uint64_t generation = 0;
    QTimer timer{&owner};
    QString history_path;
    QByteArray consented_context;
    bool archive_refused = false;
    using Limits = edi::assistant::Limits;
    QVariantMap observed;
    // Only the controller owns a lease. This index borrows it for quota checks and
    // event deduplication; explicit State teardown destroys the controller first.
    struct Lease;
    std::map<QString, Lease*> retentions;
    struct FailureSlot {
        Object row;
        QString request_id;
        bool pending = false;
    };
    std::optional<FailureSlot> failure_slot;
    QString queued_request, connection_scope;
    bool publishing = true, render_queued = false, render_dirty = false;
    const QString capacity_error = QObject::tr("Assistant history capacity is unavailable. Existing history and project state are preserved.");
    const QString storage_error = QObject::tr("Assistant history could not be saved. The pending outcome and project state are preserved; retry after storage is available.");
    const QString quarantine_error = QObject::tr("The complete assistant outcome is pending retention. Stop preserves it; retry retention or explicitly clear the conversation.");


    void retire_file_selection() noexcept {
        if (file_epoch == UINT64_MAX) file_authority_exhausted = true;
        else ++file_epoch;
        QString id;
        if (file_selection) { id = std::move(file_selection->id); file_selection.reset(); }
        // Authority is already gone before receiver cleanup can allocate or reenter.
        if (!id.isEmpty()) try { emit owner.fileSelectionRetired(id); } catch (...) {}
    }
    Object file_context() const {
        if (!controller) throw std::runtime_error("The assistant owner is unavailable");
        const auto text = controller->context();
        if (text.size() > edi::assistant::Limits::context_bytes) throw std::length_error("Selected-file context exceeds limit");
        QJsonParseError parsing;
        const auto document = QJsonDocument::fromJson(QByteArray::fromStdString(text), &parsing);
        if (parsing.error != QJsonParseError::NoError || !document.isObject()) throw std::runtime_error("Selected-file context is unavailable");
        const auto context = document.object();
        if (context.contains("error") || !context.value("selected_files").isObject())
            throw std::length_error("Selected-file context is unavailable within its limit");
        return context.value("selected_files").toObject();
    }
    static std::uint64_t file_generation(const Object& descriptor) {
        bool valid = false;
        const auto value = descriptor.value("generation").toString().toULongLong(&valid);
        if (!valid) throw std::runtime_error("Selected-file generation is unavailable");
        return value;
    }
    Object file_native_state() const {
#ifndef __EMSCRIPTEN__
        return connection ? object(connection->state()) : Object{};
#else
        return {{"status", "disconnected"}};
#endif
    }
    bool file_current(const FileSelection& scope) const {
        if (!publishing || file_authority_exhausted || scope.epoch != file_epoch ||
            scope.owner_generation != generation || scope.controller != controller.get() || scope.project != project ||
            scope.connection_epoch != file_connection_epoch || !controller) return false;
        const auto revision = controller->revision();
        if (revision.project_id != scope.revision.project_id || revision.revision != scope.revision.revision) return false;
        const auto current_native = file_native_state();
        if (current_native.value("connection_id").toString() != scope.connection_id ||
            current_native.value("status").toString() != scope.native_status) return false;
        const auto descriptor = file_context();
        return descriptor.value("collection_id").toString() == scope.collection_id &&
            file_generation(descriptor) == scope.selection_generation;
    }
    bool flush_selected_rows() {
        if (!selected_rows_dirty) return true;
        try {
            if (selected_reply.size() > edi::assistant::Limits::context_bytes) throw std::length_error("Selected-file descriptor exceeds limit");
            QJsonParseError parsing;
            const auto document = QJsonDocument::fromJson(QByteArray::fromStdString(selected_reply), &parsing);
            if (parsing.error != QJsonParseError::NoError || !document.isObject() || !document.object().value("files").isArray())
                throw std::runtime_error("Selected-file descriptor is unavailable");
            const auto descriptor = document.object();
            QJsonArray rows;
            for (const auto& value : descriptor.value("files").toArray()) {
                const auto file = value.toObject();
                rows.append(Object{{"id", file.value("id")}, {"name", file.value("name")}, {"bytes", file.value("bytes")},
                                   {"textReadable", file.value("text_readable")}, {"format", file.value("format")}});
            }
            selected_rows.swap(rows);
            selected_files.assign(selected_rows);
            selected_rows_dirty = false;
            if (error == QObject::tr("Selected files were retained, but their list could not be displayed. Sending is blocked until the list recovers or the conversation is cleared.")) error.clear();
            return true;
        } catch (...) {
            error = QObject::tr("Selected files were retained, but their list could not be displayed. Sending is blocked until the list recovers or the conversation is cleared.");
            return false;
        }
    }
    void observe_file_connection(const Object& incoming) {
        if (incoming.value("type") != "connection") return;
        const auto next = incoming.value("connection_id").toString();
        if (next != connection_scope || incoming.value("status") != "ready") {
            if (file_connection_epoch == UINT64_MAX) file_authority_exhausted = true;
            else ++file_connection_epoch;
            retire_file_selection(); consented_context.clear();
        }
    }
    std::vector<edi::assistant::SelectedFile> read_selected_urls(const QList<QUrl>& urls, const Object& current) {
        using Bounds = edi::assistant::SelectedFileLimits;
        const auto old = current.value("files").toArray();
        if (urls.size() > static_cast<qsizetype>(Bounds::files) ||
            urls.size() > static_cast<qsizetype>(Bounds::files) - old.size())
            throw std::length_error("Selected-file count exceeds limit");
        std::uint64_t total = 0;
        for (const auto& value : old) {
            const auto n = value.toObject().value("bytes").toDouble(-1);
            if (n < 0 || n > static_cast<double>(Bounds::collection_bytes) ||
                static_cast<std::uint64_t>(n) > Bounds::collection_bytes - total)
                throw std::length_error("Selected-file collection exceeds limit");
            total += static_cast<std::uint64_t>(n);
        }
        std::vector<edi::assistant::SelectedFile> files;
        files.reserve(static_cast<std::size_t>(urls.size()));
        for (const auto& url : urls) {
            if (!url.isLocalFile() || url.hasQuery() || url.hasFragment() || !QDir::isAbsolutePath(url.toLocalFile()))
                throw std::runtime_error("Select local regular files using the file chooser or a file drop");
            QFile file;
            open_selected_regular(file, url.toLocalFile());
            const auto size = file.size();
            if (size < 0 || static_cast<std::uint64_t>(size) > Bounds::file_bytes ||
                static_cast<std::uint64_t>(size) > Bounds::collection_bytes - total)
                throw std::length_error("Selected-file byte limit exceeded");
            edi::assistant::SelectedFile next;
            next.id = QUuid::createUuid().toString(QUuid::WithoutBraces).toStdString();
            next.relative_name = QFileInfo(url.toLocalFile()).fileName().toUtf8().toStdString();
            if (next.relative_name.size() > Bounds::name_bytes)
                throw std::length_error("Selected-file name exceeds limit");
            next.bytes.resize(static_cast<std::size_t>(size)); // declared size admitted before growth
            std::size_t offset = 0;
            while (offset < next.bytes.size()) {
                const auto count = std::min<std::size_t>(Bounds::read_bytes, next.bytes.size() - offset);
                const auto read = file.read(reinterpret_cast<char*>(next.bytes.data() + offset), static_cast<qint64>(count));
                if (read <= 0) throw std::runtime_error("Selected file changed or could not be read");
                offset += static_cast<std::size_t>(read);
            }
            char extra = 0;
            const auto extra_count = file.read(&extra, 1); // fixed stack byte; no unadmitted vector growth
            if (extra_count != 0 || file.error() != QFileDevice::NoError)
                throw std::runtime_error("Selected file changed or could not be read");
            total += next.bytes.size();
            files.push_back(std::move(next));
        }
        return files;
    }

    static Object public_row(const QString& kind, const QString& text, const Object& payload, const QString& status) {
        return {{"id", QUuid::createUuid().toString(QUuid::WithoutBraces)}, {"kind", kind},
                {"text", text}, {"status", status}, {"payload", payload}};
    }
    static QString bounded_error(const QString& source) {
        QByteArray bytes;
        for (qsizetype i = 0; i < source.size();) {
            const auto c = source.at(i);
            const qsizetype width = c.isHighSurrogate() && i + 1 < source.size() && source.at(i + 1).isLowSurrogate() ? 2 : 1;
            if (c.unicode() >= 32 && c.unicode() != 127) {
                const auto part = source.mid(i, width).toUtf8();
                if (static_cast<std::uint64_t>(bytes.size() + part.size()) > Limits::error_bytes) break;
                bytes += part;
            }
            i += width;
        }
        return QString::fromUtf8(bytes);
    }
    bool queue_render() {
        if (!publishing) return false;
        render_dirty = true;
        if (render_queued) return true;
        render_queued = QMetaObject::invokeMethod(&owner, [this] {
            render_queued = false;
            if (!publishing) return;
            try {
                messages.assign(history); render_dirty = false;
                sync();
            } catch (...) { error = storage_error; render_dirty = true; }
        }, Qt::QueuedConnection);
        return render_queued;
    }
    struct Lease final : edi::assistant::TerminalRetention {
        State& host;
        const std::uint64_t generation;
        QString call_id, job_id;
        Object binding, terminal_row;
        QJsonArray known;
        QStringList row_ids;
        bool visible = false, complete = false;
        Lease(State& state, const Object& prospective) : host(state), generation(state.generation) {
            const auto call = prospective.value("call").toObject();
            const auto pending = prospective.value("pending_result").toObject();
            const auto activity = prospective.value("activity").toObject();
            call_id = call.value("call_id").toString(); binding = pending;
            if (call_id.isEmpty() || pending.value("call_id") != call.value("call_id") ||
                prospective.value("schema") != "edi.assistant.terminal-retention/1" || !pending.value("pending").toBool())
                throw std::invalid_argument("Invalid terminal-retention input");
            known.append(public_row("tool", QObject::tr("Project tool running"),
                                    {{"call", call}, {"pending_result", pending}}, "running"));
            if (activity.value("type") == "question") {
                const auto question = activity.value("question").toObject();
                known.append(public_row("question", question.value("text").toString(), question, "awaiting_answer"));
            } else if (activity.value("type") == "fit") {
                job_id = activity.value("job_id").toString();
                known.append(public_row("tool", QObject::tr("Refinement trial running"), activity, "running"));
            } else throw std::invalid_argument("Invalid terminal-retention activity");
            for (const auto& value : known) row_ids.append(value.toObject().value("id").toString());
            terminal_row = public_row("tool", QObject::tr("Project tool outcome"), {}, "interrupted");
        }
        ~Lease() noexcept override {
            const auto found = host.retentions.find(call_id);
            if (found != host.retentions.end() && found->second == this) host.retentions.erase(found);
        }
        bool current() const noexcept { return host.publishing && host.generation == generation; }
        QJsonArray quarantine_rows(QJsonArray rows) const {
            for (qsizetype i = 0; i < rows.size(); ++i) {
                auto row = rows.at(i).toObject();
                if (row_ids.contains(row.value("id").toString())) {
                    row["status"] = "quarantined";
                    row["text"] = host.quarantine_error;
                    rows.replace(i, row);
                }
            }
            return rows;
        }
        std::pair<std::uint64_t, std::uint64_t> held(const QJsonArray& current, bool started) const {
            auto next = current;
            if (!started) for (const auto& row : known) next.append(row);
            auto alternative = quarantine_rows(next);
            next.append(terminal_row); alternative.append(terminal_row);
            const auto used = host.archive_size(current);
            const auto future = std::max(host.archive_size(next), host.archive_size(alternative));
            const auto growth = future >= used + 2 ? future - used - 2 : 0;
            if (growth > Limits::ui_history_bytes || Limits::message_bytes > Limits::ui_history_bytes - growth)
                return {Limits::ui_history_bytes + 1, Limits::ui_messages + 1};
            return {growth + Limits::message_bytes, static_cast<std::uint64_t>(next.size() - current.size())};
        }
        bool started() noexcept override {
            if (!current() || visible || complete) return false;
            try {
                auto next = host.history;
                Object shown_question;
                for (const auto& row : known) {
                    next.append(row);
                    if (row.toObject().value("kind") == "question") shown_question = row.toObject().value("payload").toObject();
                }
                if (!host.publish(std::move(next), this, true)) return false;
                visible = true; known = {};
                if (!shown_question.isEmpty()) host.question.swap(shown_question);
                return true;
            } catch (...) { host.error = host.storage_error; return false; }
        }
        bool settle(const edi::assistant::JsonText& terminal) noexcept override {
            if (!current() || complete) return false;
            try {
                if (terminal.size() > Limits::message_bytes) return false;
                QJsonParseError parsing;
                const auto document = QJsonDocument::fromJson(QByteArray::fromStdString(terminal), &parsing);
                if (parsing.error != QJsonParseError::NoError || !document.isObject()) return false;
                const auto result = document.object();
                if (result.size() != 12 || result.value("schema") != "edi.assistant/1" ||
                    result.value("type") != "tool_result" || !result.value("pending").isBool() ||
                    result.value("pending").toBool() || !result.value("ok").isBool() || !result.value("code").isString() ||
                    !result.contains("result")) return false;
                for (const auto* field : {"connection_id", "turn_id", "request_id", "project_id", "revision", "call_id"})
                    if (result.value(field) != binding.value(field)) return false;
                auto row = terminal_row;
                row["payload"] = result;
                const auto actual_status = result.value("result").toObject().value("status").toString();
                row["status"] = result.value("ok").toBool() ? "completed" :
                    actual_status == "cancelled" ? "cancelled" : actual_status == "error" ? "failed" : "refused";
                auto next = host.history;
                if (!visible) for (const auto& value : known) next.append(value);
                next.append(row);
                if (!host.publish(std::move(next), this, false)) return false;
                complete = true; visible = true; known = {}; binding = {};
                if (host.error == host.storage_error || host.error == host.quarantine_error || host.error == host.capacity_error)
                    host.error.clear();
                return true;
            } catch (...) { host.error = host.storage_error; return false; }
        }
        void quarantine() noexcept override {
            if (!current() || complete) return;
            try {
                auto next = host.history;
                if (!visible) for (const auto& value : known) next.append(value);
                next = quarantine_rows(std::move(next));
                if (host.publish(std::move(next), this, true)) { visible = true; known = {}; }
                host.error = host.quarantine_error;
                (void)host.queue_render();
            } catch (...) { host.error = host.quarantine_error; }
        }
    };
    std::unique_ptr<edi::assistant::TerminalRetention> reserve(const std::string& input) {
        if (input.size() > Limits::message_bytes || archive_refused || !publishing ||
            retentions.size() >= Limits::completed_calls) return {};
        QJsonParseError parsing;
        const auto doc = QJsonDocument::fromJson(QByteArray::fromStdString(input), &parsing);
        if (parsing.error != QJsonParseError::NoError || !doc.isObject() || doc.object().size() != 4) return {};
        auto lease = std::make_unique<Lease>(*this, doc.object());
        if (retentions.count(lease->call_id) || !admit(history, nullptr, lease.get(), false)) return {};
        retentions.emplace(lease->call_id, lease.get());
        return lease;
    }
    bool managed(const Object& event) const {
        const auto call_id = event.value("call_id").toString();
        const auto matches = [&](const Object& bound) {
            if (bound.value("call_id").toString() != call_id || call_id.isEmpty()) return false;
            for (const auto* field : {"connection_id", "turn_id", "request_id"})
                if (bound.value(field) != event.value(field)) return false;
            return true;
        };
        if (const auto found = retentions.find(call_id); found != retentions.end() && matches(found->second->binding)) return true;
        for (const auto& value : history) {
            const auto payload = value.toObject().value("payload").toObject();
            if (matches(payload) || matches(payload.value("pending_result").toObject())) return true;
        }
        return false;
    }

    void notify() {
        auto property = [this](const QString& name, const auto& value, auto signal) {
            const QVariant next = QVariant::fromValue(value);
            if (!observed.contains(name) || observed.value(name) != next) { observed[name] = next; (owner.*signal)(); }
        };
        property("state", owner.state(), &AssistantViewModel::stateChanged);
        property("connected", owner.connected(), &AssistantViewModel::connectedChanged);
        property("connectionLabel", owner.connectionLabel(), &AssistantViewModel::connectionLabelChanged);
        property("selectedModel", owner.selectedModel(), &AssistantViewModel::selectedModelChanged);
        property("selectedSkill", owner.selectedSkill(), &AssistantViewModel::selectedSkillChanged);
        property("selectedEffort", owner.selectedEffort(), &AssistantViewModel::selectedEffortChanged);
        property("availableEfforts", owner.availableEfforts(), &AssistantViewModel::availableEffortsChanged);
        property("pendingPlan", owner.pendingPlan(), &AssistantViewModel::pendingPlanChanged);
        property("pendingQuestion", owner.pendingQuestion(), &AssistantViewModel::pendingQuestionChanged);
        property("activeJobId", owner.activeJobId(), &AssistantViewModel::activeJobIdChanged);
        property("canCancel", owner.canCancel(), &AssistantViewModel::canCancelChanged);
        property("lastError", owner.lastError(), &AssistantViewModel::lastErrorChanged);
        property("contextPreview", owner.contextPreview(), &AssistantViewModel::contextPreviewChanged);
        property("contextConsentRequired", owner.contextConsentRequired(), &AssistantViewModel::contextPreviewChanged);
    }
    ~State() {
        publishing = false; retire_file_selection(); timer.stop(); ++generation;
#ifndef __EMSCRIPTEN__
        try { if (connection) connection->cancel(core.value("active_turn_id").toString().toStdString()); } catch (...) {}
#endif
        controller.reset(); // lease destructors still have a live State/index/archive
        retentions.clear(); failure_slot.reset();
    }
    explicit State(AssistantViewModel& vm) : owner(vm) { initialize(); }
#ifndef __EMSCRIPTEN__
    State(AssistantViewModel& vm, edi::assistant::native::NativeDependencies dependencies) : owner(vm) {
        edi::assistant::native::validate_dependencies(dependencies);
        initialize(std::move(dependencies));
    }
    void initialize(std::optional<edi::assistant::native::NativeDependencies> dependencies = {}) {
#else
    void initialize() {
#endif
        idle_worker = std::make_unique<edi::work::Worker>([this](edi::work::Delivery delivery) {
            QMetaObject::invokeMethod(&owner, std::move(delivery), Qt::QueuedConnection);
        });
        history_path = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/history.json";
        QFile saved(history_path);
        if (QFileInfo::exists(history_path)) {
            QJsonParseError parsing;
            if (!saved.open(QIODevice::ReadOnly) || saved.size() > static_cast<qint64>(Limits::ui_history_bytes)) archive_refused = true;
            else {
                const auto bytes = saved.read(static_cast<qint64>(Limits::ui_history_bytes) + 1);
                const auto document = QJsonDocument::fromJson(bytes, &parsing);
                archive_refused = bytes.size() > static_cast<qint64>(Limits::ui_history_bytes) || parsing.error != QJsonParseError::NoError || !document.isArray() || document.array().size() > static_cast<qsizetype>(Limits::ui_messages);
                if (!archive_refused) {
                    for (const auto& row : document.array()) if (!row.isObject() || !row.toObject().value("text").isString() || !row.toObject().value("kind").isString()) archive_refused = true;
                    if (!archive_refused) history = document.array();
                }
            }
            if (archive_refused) error = QObject::tr("Saved assistant history could not be loaded within its limits. The file is preserved; clear history explicitly to start again.");
        }
        messages.assign(history);
#ifndef __EMSCRIPTEN__
        const auto sink = [this](const std::string& text) {
            const auto incoming_generation = generation;
            Object incoming;
            try { incoming = object(text); observe_file_connection(incoming); }
            catch (...) { retire_file_selection(); throw; }
            // Snapshot native diagnostics at the exact terminal emission, not
            // after queued callbacks can change the connection's last error.
            QString emitted_code;
            if (incoming.value("type") == "turn_finished" && connection) {
                const auto emitted_state = object(connection->state());
                const auto code = emitted_state.value("last_error_code").toString();
                if (incoming.value("connection_id") == emitted_state.value("connection_id") &&
                    code.startsWith("edi.assistant.") && static_cast<std::uint64_t>(code.toUtf8().size()) <= Limits::id_bytes)
                    emitted_code = code;
            }
            QMetaObject::invokeMethod(&owner, [this, text, incoming, emitted_code, incoming_generation] {
                if (!publishing || !controller || incoming_generation != generation) return;
                try {
                    native = object(connection->state());
                    const auto current_turn = object(controller->state()).value("active_turn_id").toString();
                    const bool terminal = incoming.value("type") == "turn_finished" &&
                        incoming.value("connection_id") == native.value("connection_id") &&
                        incoming.value("turn_id").toString() == current_turn &&
                        failure_slot && failure_slot->request_id == incoming.value("request_id").toString();
                    const auto reply = controller->provider_event(text);
                    if (!reply.ok) error = bounded_error(object(reply.value).value("message").toString());
                    if (terminal) {
                        if (incoming.value("status") == "completed" && reply.ok) failure_slot.reset();
                        else retain_failure(incoming, emitted_code.isEmpty() ? QString::fromStdString(reply.code) : emitted_code,
                            incoming.value("message").toString().isEmpty() ? error : incoming.value("message").toString());
                    }
                    if (incoming.value("type") == "connection" && reply.ok) {
                        const auto next_connection = incoming.value("connection_id").toString();
                        if (next_connection != connection_scope || incoming.value("status") != "ready") {
                            queued_request.clear(); failure_slot.reset();
                        }
                        connection_scope = next_connection;
                    }
                    sync();
                } catch (...) {
                    error = storage_error;
                    controller->cancel();
                    (void)queue_render();
                }
            }, Qt::QueuedConnection);
        };
        if (dependencies) connection = std::make_unique<edi::assistant::native::ChatGptConnection>(sink, std::move(*dependencies));
        else connection = std::make_unique<edi::assistant::native::ChatGptConnection>(sink);
#endif
        timer.setInterval(200);
        QObject::connect(&timer, &QTimer::timeout, &owner, [this] {
            try {
                if (controller) controller->poll();
                if (render_dirty) { messages.assign(history); render_dirty = false; }
                if (selected_rows_dirty) (void)flush_selected_rows();
                sync();
            } catch (...) { error = storage_error; render_dirty = true; }
        });
        timer.start();
    }
    std::uint64_t archive_size(const QJsonArray& rows) const {
        return static_cast<std::uint64_t>(QJsonDocument(rows).toJson(QJsonDocument::Compact).size());
    }
    bool admit(const QJsonArray& next, const Lease* except = nullptr,
               const Lease* extra = nullptr, bool extra_started = false, bool release_failure = false) {
        if (archive_refused || next.size() > static_cast<qsizetype>(Limits::ui_messages)) {
            error = capacity_error; return false;
        }
        auto bytes = archive_size(next);
        auto message_count = static_cast<std::uint64_t>(next.size());
        const auto add = [&](std::uint64_t growth, std::uint64_t count) {
            if (bytes > Limits::ui_history_bytes || growth > Limits::ui_history_bytes - bytes ||
                message_count > Limits::ui_messages || count > Limits::ui_messages - message_count) return false;
            bytes += growth; message_count += count; return true;
        };
        if (!add(0, 0)) { error = capacity_error; return false; }
        for (const auto& [id, lease] : retentions) {
            (void)id;
            if (lease == except || lease->complete) continue;
            const auto hold = lease->held(next, lease->visible);
            if (!add(hold.first, hold.second)) { error = capacity_error; return false; }
        }
        if (extra) {
            const auto hold = extra->held(next, extra_started);
            if (!add(hold.first, hold.second)) { error = capacity_error; return false; }
        }
        if (failure_slot && !release_failure) {
            auto with_failure = next; with_failure.append(failure_slot->row);
            if (!add(archive_size(with_failure) - archive_size(next), 1)) { error = capacity_error; return false; }
        }
        return true;
    }
    bool write_archive(const QByteArray& bytes) {
        if (archive_refused || !QDir().mkpath(QFileInfo(history_path).absolutePath())) return false;
        QSaveFile file(history_path);
        return file.open(QIODevice::WriteOnly) && file.setPermissions(QFile::ReadOwner | QFile::WriteOwner) &&
               file.write(bytes) == bytes.size() && file.commit();
    }
    bool publish(QJsonArray next, const Lease* except = nullptr, bool remaining_terminal = false,
                 bool release_failure = false) {
        if (!admit(next, except, remaining_terminal ? except : nullptr, true, release_failure)) return false;
        const auto bytes = QJsonDocument(next).toJson(QJsonDocument::Compact);
        // Queue allocations precede the disk/memory commit. The callback reads
        // canonical history later; a failed write cannot expose a completed T.
        if (!queue_render() || !write_archive(bytes)) { error = storage_error; return false; }
        history.swap(next);
        return true;
    }
    bool append(const QString& kind, const QString& text, const Object& payload = {}, const QString& row_status = "completed") {
        auto next = history; next.append(public_row(kind, text, payload, row_status));
        return publish(std::move(next));
    }
    static Object failure_payload(const Object& scope, const QString& code, const QString& message, const QString& status) {
        return {{"schema", "edi.assistant/1"}, {"type", "provider_failure"},
                {"connection_id", scope.value("connection_id")}, {"turn_id", scope.value("turn_id")},
                {"request_id", scope.value("request_id")}, {"status", status},
                {"code", code}, {"message", bounded_error(message)}};
    }
    bool reserve_failure() {
        if (failure_slot) return !failure_slot->pending;
        // A finite generated-error role, not another full scientific terminal.
        // Each worst-case scalar uses the declared bound and maximal JSON escaping.
        const QString id(static_cast<qsizetype>(Limits::id_bytes), QChar(1));
        const QString explanation(static_cast<qsizetype>(Limits::error_bytes), QChar(1));
        const Object maximum{{"schema", "edi.assistant/1"}, {"type", "provider_failure"},
                             {"connection_id", id}, {"turn_id", id}, {"request_id", id},
                             {"status", "interrupted"}, {"code", id}, {"message", explanation}};
        FailureSlot prepared{public_row("error", explanation, maximum, "interrupted"), {}, false};
        failure_slot.emplace(std::move(prepared));
        if (!admit(history)) { failure_slot.reset(); return false; }
        return true;
    }
    bool flush_failure() {
        if (!failure_slot || !failure_slot->pending) return true;
        auto next = history; next.append(failure_slot->row);
        if (!publish(std::move(next), nullptr, false, true)) return false;
        error = failure_slot->row.value("payload").toObject().value("message").toString();
        failure_slot.reset(); return true;
    }
    void retain_failure(const Object& scope, const QString& code, const QString& message) {
        if (!failure_slot && !reserve_failure()) throw std::runtime_error("Assistant failure capacity is unavailable");
        const auto status = scope.value("status").toString() == "interrupted" ? QString("interrupted") : QString("failed");
        auto row = failure_slot->row;
        row["status"] = status;
        const auto shown = bounded_error(message.isEmpty() ? QObject::tr("Provider turn did not complete") : message);
        row["text"] = shown;
        row["payload"] = failure_payload(scope, code, shown, status);
        // Bound every scalar used by the finite generated-error reservation.
        const auto payload = row.value("payload").toObject();
        for (const auto* field : {"connection_id", "turn_id", "request_id", "code"})
            if (static_cast<std::uint64_t>(payload.value(field).toString().toUtf8().size()) > Limits::id_bytes)
                throw std::length_error("Assistant failure identity exceeds its bound");
        failure_slot->row.swap(row); failure_slot->pending = true;
        if (!flush_failure()) { error = storage_error; (void)queue_render(); }
    }
    void event(const std::string& input) {
        const Object value = object(input); const auto type = value.value("type").toString();
        // Rendering is queued: no controller/provider calls from an event hook or lease.
        if (type == "state_changed") {
            core = value.value("state").toObject();
            queued_request = value.value("request_id").toString();
            if (failure_slot && !failure_slot->pending && !queued_request.isEmpty())
                failure_slot->request_id = queued_request;
        } else if (type == "message_delta") {
            if (!history.isEmpty() && history.last().toObject().value("kind") == "assistant" &&
                history.last().toObject().value("payload").toObject().value("turn_id") == value.value("turn_id") &&
                history.last().toObject().value("payload").toObject().value("request_id") == value.value("request_id")) {
                auto last = history.last().toObject();
                last["text"] = last.value("text").toString() + value.value("text").toString();
                auto next = history; next.replace(next.size() - 1, last);
                if (!publish(std::move(next))) throw std::length_error("Assistant message could not be retained");
            } else if (!append("assistant", value.value("text").toString(), value))
                throw std::length_error("Assistant message could not be retained");
        } else if (type == "plan_proposed") {
            auto next_plan = value.value("plan").toObject();
            if (!append("plan", next_plan.value("summary").toString(), next_plan))
                throw std::length_error("Assistant plan could not be retained");
            plan.swap(next_plan);
        } else if (type == "plan_approved") plan = {};
        else if (type == "question") {
            const auto shown = value.value("question").toObject();
            const auto found = retentions.find(shown.value("call_id").toString());
            if (found == retentions.end()) throw std::logic_error("Question has no terminal retention owner");
            // Its known row/card publishes only through started(), after core admission.
        } else if (type == "question_answered" || type == "question_invalidated") question = {};
        else if (type == "tool_result") {
            if (!managed(value)) {
                const bool pending = value.value("pending").toBool();
                if (pending) throw std::logic_error("Pending tool has no terminal retention owner");
                if (!append("tool", value.value("ok").toBool() ? QObject::tr("Project tool completed") : QObject::tr("Project tool refused"),
                            value, value.value("ok").toBool() ? "completed" : "refused"))
                    throw std::length_error("Assistant tool outcome could not be retained");
            }
        } else if (type == "job_started") {
            const auto job = value.value("job_id").toString();
            const bool owned = std::any_of(retentions.begin(), retentions.end(), [&](const auto& item) { return item.second->job_id == job; });
            if (!owned) throw std::logic_error("Fit has no terminal retention owner");
        } else if (type == "trial_finished") {
            if (!append("trial", value.value("result").toObject().value("reason").toString(), value))
                throw std::length_error("Assistant trial decision could not be retained");
        } else if (type == "error") error = bounded_error(value.value("message").toString());
        if (!queue_render()) throw std::runtime_error("Assistant presentation queue is unavailable");
    }
    void load_choice_preference() noexcept {
        try {
            const auto path = settings_file_path();
            if (path != choice_store) {
                // Retire the old association before any fallible new-store preparation.
                remembered_model.clear(); remembered_effort.clear();
                preference_error.clear(); preference_save_error.clear();
                choice_read_complete = false;
                restore_choice_pending = true; choice_warning_shown = false;
                choice_store = path;
            }
            if (path.isEmpty()) return; // Retired store ownership; never use a personal/default store.
            if (choice_read_complete) return;
            QSettings settings(path, QSettings::IniFormat);
            settings.sync(); // Import actual same-path recovery before interpreting absence.
            const auto key = QStringLiteral("Assistant/Providers/chatgpt/selection");
            const bool present = settings.contains(key);
            if (settings.status() != QSettings::NoError) {
                preference_error = QObject::tr("Assistant preferences could not be read. Restoration will retry when the store is available.");
                return; // Failure is NOT a completed read, including failed contains().
            }
            if (!present) {
                remembered_model.clear(); remembered_effort.clear();
                choice_read_complete = true; // Confirmed successful absence, not an I/O failure.
                preference_error.clear();
                return;
            }
            const auto value = settings.value(key);
            const auto pair = value.toStringList();
            if (settings.status() != QSettings::NoError) {
                preference_error = QObject::tr("Assistant preferences could not be read. Restoration will retry when the store is available.");
                return;
            }
            if (value.metaType().id() != QMetaType::QStringList || pair.size() != 2 ||
                pair[0].isEmpty() || static_cast<std::uint64_t>(pair[0].toUtf8().size()) > Limits::id_bytes ||
                static_cast<std::uint64_t>(pair[1].toUtf8().size()) > Limits::id_bytes) {
                remembered_model.clear(); remembered_effort.clear();
                choice_read_complete = true; // Deliberate rejection of successfully read malformed data.
                preference_error = QObject::tr("The saved assistant selection is unavailable. Choose a model and reasoning effort again.");
                return;
            }
            // All preparation/validation precedes completion. A failed attempt remains retryable.
            auto next_model = pair[0]; auto next_effort = pair[1];
            remembered_model.swap(next_model); remembered_effort.swap(next_effort);
            choice_read_complete = true;
            preference_error.clear();
        } catch (...) {
            choice_read_complete = false;
            try { preference_error = QObject::tr("Assistant preferences could not be read. Restoration will retry when the store is available."); } catch (...) {}
        }
    }
    void remember_choice() noexcept {
        try {
            if (owner.canCancel() || native.value("status") != "ready") return;
            bool offered = false;
            for (const auto& value : native.value("models").toArray()) {
                const auto row = value.toObject();
                if (row.value("id") == model && row.value("available").toBool())
                    offered = effort.isEmpty() || row.value("efforts").toArray().contains(effort);
            }
            if (!offered) return;
            preference_error.clear(); // A valid explicit choice resolves only selection-owned diagnostics.
            load_choice_preference();
            remembered_model = model; remembered_effort = effort;
            restore_choice_pending = false; choice_warning_shown = false;
            const auto path = settings_file_path();
            if (path.isEmpty()) { preference_error.clear(); preference_save_error.clear(); return; } // No personal/default-store fallback.
            QSettings settings(path, QSettings::IniFormat);
            // A single value binds the effort to its actual model; fallback never writes this value.
            settings.setValue(QStringLiteral("Assistant/Providers/chatgpt/selection"), QStringList{model, effort});
            settings.sync();
            if (settings.status() != QSettings::NoError) {
                preference_save_error = QObject::tr("The assistant selection changed, but its preference could not be saved.");
                return;
            }
            choice_read_complete = true;
            store_settings_now(); // The existing browser flush; desktop settings already synced.
            preference_save_error.clear();
            preference_error.clear();
        } catch (...) {
            try { preference_save_error = QObject::tr("The assistant selection changed, but its preference could not be saved."); } catch (...) {}
        }
    }
    void select_from_catalog(const QJsonArray& choices) {
        if (native.value("status") != "ready" || choices.isEmpty()) {
            restore_choice_pending = true;
            return; // Sign-out/empty catalogs must neither erase nor persist an automatic fallback.
        }
        if (owner.canCancel()) return;
        load_choice_preference();
        const auto available = [&](const QString& id) {
            for (const auto& value : choices) {
                const auto row = value.toObject();
                if (row.value("id") == id && row.value("available").toBool()) return row;
            }
            return Object{};
        };
        if (restore_choice_pending && !remembered_model.isEmpty()) {
            const auto saved = available(remembered_model);
            if (!saved.isEmpty()) {
                model = remembered_model;
                const bool supported = remembered_effort.isEmpty() || saved.value("efforts").toArray().contains(remembered_effort);
                effort = supported ? remembered_effort : QString();
                restore_choice_pending = !supported;
                if (supported && choice_read_complete) preference_error.clear();
                if (!supported && !choice_warning_shown) {
                    preference_error = QObject::tr("The saved reasoning effort is unavailable. Provider default is selected; your preference is preserved.");
                    choice_warning_shown = true;
                }
            } else if (!choice_warning_shown) {
                preference_error = QObject::tr("The saved model is unavailable. Inspect the available model and effort before sending; your preference is preserved.");
                choice_warning_shown = true;
            }
        }
        if (available(model).isEmpty()) {
            const bool replacing_explicit = !model.isEmpty();
            model.clear(); effort.clear();
            for (const auto& value : choices) if (value.toObject().value("available").toBool()) {
                model = value.toObject().value("id").toString(); break;
            }
            if (replacing_explicit && !choice_warning_shown)
                preference_error = QObject::tr("The previous model is unavailable. Inspect the new model and Provider default effort before sending.");
        }
        if (!effort.isEmpty() && !available(model).value("efforts").toArray().contains(effort)) {
            effort.clear();
            preference_error = QObject::tr("The previous reasoning effort is unavailable. Selection reset to Provider default.");
        }
    }
    void sync_skills() {
        try {
            if (!controller) { skills.assign({}); selected_skill.clear(); skill_catalog_binding.clear(); workflow_error.clear(); return; }
            // This bounded host door is independent of project-context size or
            // scientific validity; it must remain usable for smaller-skill recovery.
            const auto reply = controller->user_command(json(Object{{"schema", "edi.assistant/1"}, {"type", "skill_catalog"}}));
            if (!reply.ok) {
                workflow_error = bounded_error(object(reply.value).value("message").toString()); return;
            }
            if (reply.value.size() > Limits::context_bytes) throw std::length_error("Workflow catalog exceeds context capacity");
            const auto catalog = object(reply.value);
            if (!catalog.value("selected_id").isString() || !catalog.value("skills").isArray())
                throw std::runtime_error("Workflow catalog is unavailable");
            const auto id = catalog.value("selected_id").toString();
            const auto rows = catalog.value("skills").toArray();
            if (id.isEmpty() || rows.size() > static_cast<qsizetype>(Limits::models))
                throw std::runtime_error("Workflow catalog exceeds its bounded model");
            auto binding = id.toUtf8();
            for (const auto& row : rows) binding.append(row.toObject().value("available").toBool() ? '1' : '0');
            if (binding != skill_catalog_binding) { skills.assign(rows); selected_skill = id; skill_catalog_binding = binding; }
            workflow_error.clear();
        } catch (...) {
            // A normal assistant-capacity/catalog refusal cannot unwind manual
            // Session project replacement or prevent other state synchronization.
            workflow_error = QObject::tr("Workflow guidance is unavailable within the assistant limits.");
        }
    }
    void sync() {
        const Object next_core = controller ? object(controller->state()) : Object{};
#ifndef __EMSCRIPTEN__
        const Object next_native = object(connection->state());
#else
        const Object next_native{{"status", "disconnected"}};
#endif
        core = next_core; native = next_native;
        QJsonArray choices;
        for (const auto& value : native.value("models").toArray()) {
            const auto item = value.toObject(); choices.append(Object{{"id", item.value("id")},
                {"displayName", item.value("display_name")}, {"efforts", item.value("efforts")}, {"available", item.value("available").toBool()}});
        }
        sync_skills();
        models.assign(choices);
        select_from_catalog(choices);
        if (core.value("pending_plan_id").toString().isEmpty()) plan = {};
        if (core.value("pending_question_id").toString().isEmpty()) question = {};
        const auto native_error = native.value("last_error").toString();
        if (auth_pending && (native.value("status") == "ready" || !native_error.isEmpty())) auth_pending = false;
        if (native_error != observed_native_error) {
            observed_native_error = native_error;
            if (!native_error.isEmpty()) error = bounded_error(native_error);
        }
        notify();
    }
    edi::assistant::Reply command(Object command) {
        if (!controller) return {false, "edi.assistant.interrupted", "{}"};
        command["schema"] = "edi.assistant/1";
        auto reply = controller->user_command(json(command));
        if (!reply.ok) error = object(reply.value).value("message").toString();
        else error.clear();
        sync(); notify();
        return reply;
    }
    void bind(ProjectViewModel* next) {
        emit owner.conversationRetired(); // Before any fallible replacement preparation.
        retire_file_selection();
#ifndef __EMSCRIPTEN__
        if (controller && connection) connection->cancel(core.value("active_turn_id").toString().toStdString());
#endif
        ++generation;
        consented_context.clear();
        if (project) {
            QObject::disconnect(project, nullptr, &owner, nullptr);
            QObject::disconnect(project->fit(), nullptr, &owner, nullptr);
        }
        controller.reset(); retentions.clear(); failure_slot.reset(); queued_request.clear();
        skill_catalog_binding.clear(); selected_skill.clear(); skills.assign({});
        selected_reply.clear(); selected_rows = {}; selected_files.assign(selected_rows); selected_rows_dirty = false;
        project = next; plan = {}; question = {};
        edi::assistant::Hooks hooks;
        hooks.reserve_terminal = [this](const std::string& input) { return reserve(input); };
        hooks.event = [this](const std::string& text) { event(text); };
        hooks.apply = [this](const edi::Edit& edit, bool structural) {
            if (!project) return std::string("The project was closed");
            own_edit = true;
            try {
                const auto error_text = project->apply(edit, structural); own_edit = false;
                return error_text.toStdString();
            } catch (...) { own_edit = false; throw; }
        };
        hooks.provider_request = [this](const std::string& text) {
            const auto scope = generation;
            const auto captured = object(text);
            if (!QMetaObject::invokeMethod(&owner, [this, text, scope, captured] {
                if (!publishing || !controller || scope != generation) return;
                const auto current_turn = object(controller->state()).value("active_turn_id").toString();
                if (captured.value("turn_id").toString() != current_turn || current_turn.isEmpty() ||
                    captured.value("request_id").toString() != queued_request) return;
                try {
                    if (!flush_failure() || !reserve_failure()) throw std::length_error("Assistant failure capacity is unavailable");
                    failure_slot->request_id = captured.value("request_id").toString();
#ifndef __EMSCRIPTEN__
                    const auto current_native = object(connection->state());
                    if (captured.value("connection_id") != current_native.value("connection_id")) return;
                    const auto requested_context = QJsonDocument(captured.value("context").toObject()).toJson(QJsonDocument::Compact);
                    if (requested_context != consented_context) {
                        error = QObject::tr("Project context changed. Inspect and approve the current outgoing context before continuing.");
                        retain_failure(captured, "edi.assistant.interrupted", error);
                        controller->cancel(); sync(); return;
                    }
                    const auto reply = connection->send(text);
                    if (!reply.ok) {
                        error = bounded_error(object(reply.value).value("message").toString());
                        retain_failure(captured, QString::fromStdString(reply.code), error);
                        controller->cancel(); sync();
                    }
#else
                    error = QObject::tr("Browser AI connection is unavailable in this build.");
                    retain_failure(captured, "edi.assistant.connection_required", error);
                    controller->cancel(); sync();
#endif
                } catch (...) { error = storage_error; controller->cancel(); (void)queue_render(); }
            }, Qt::QueuedConnection)) throw std::runtime_error("Assistant dispatch queue is unavailable");
        };
        controller = std::make_unique<edi::assistant::Controller>(project ? project->assistantWorker() : *idle_worker, std::move(hooks));
        if (project) {
            controller->attach(project->assistantProject(), QUuid::createUuid().toString(QUuid::WithoutBraces).toStdString());
            QObject::connect(project, &ProjectViewModel::projectEdited, &owner, [this] {
                if (controller && !own_edit) { retire_file_selection(); controller->notify_changed(); plan = {}; question = {}; sync(); }
            });
            QObject::connect(project->fit(), &FitViewModel::finished, &owner, [this] { retire_file_selection(); if (controller) controller->notify_changed(); });
        }
#ifndef __EMSCRIPTEN__
        const auto state = object(connection->state());
        connection_scope = state.value("connection_id").toString();
        QJsonArray capabilities;
        for (const auto& row : state.value("models").toArray()) {
            auto item = row.toObject(); if (item.take("available").toBool()) capabilities.append(item);
        }
        if (state.value("status") == "ready") controller->provider_event(json(Object{{"schema", "edi.assistant/1"},
            {"type", "connection"}, {"connection_id", state.value("connection_id")}, {"status", "ready"}, {"capabilities", capabilities}}));
#endif
        sync(); notify();
    }
};

AssistantViewModel::AssistantViewModel(QObject* parent) : QObject(parent), state_(std::make_unique<State>(*this)) { state_->bind(nullptr); }
#ifndef __EMSCRIPTEN__
AssistantViewModel::AssistantViewModel(edi::assistant::native::NativeDependencies dependencies, QObject* parent)
    : QObject(parent), state_(std::make_unique<State>(*this, std::move(dependencies))) { state_->bind(nullptr); }
#endif
AssistantViewModel::~AssistantViewModel() = default;
QString AssistantViewModel::state() const { return state_->auth_pending ? QString("connecting") : state_->core.value("state").toString(); }
bool AssistantViewModel::connected() const { return state_->native.value("status") == "ready"; }
QString AssistantViewModel::connectionLabel() const { return state_->auth_pending ? tr("Connecting to ChatGPT…") : connected() ? state_->native.value("label").toString() : tr("Connect ChatGPT"); }
RowTableModel* AssistantViewModel::models() const { return &state_->models; }
QString AssistantViewModel::selectedModel() const { return state_->model; }
QString AssistantViewModel::selectedEffort() const { return state_->effort; }
QStringList AssistantViewModel::availableEfforts() const {
    for (const auto& item : state_->native.value("models").toArray()) {
        const auto model = item.toObject();
        if (model.value("id").toString() == state_->model) return model.value("efforts").toVariant().toStringList();
    }
    return {};
}
RowTableModel* AssistantViewModel::messages() const { return &state_->messages; }
RowTableModel* AssistantViewModel::selectedFiles() const { return &state_->selected_files; }
RowTableModel* AssistantViewModel::skills() const { return &state_->skills; }
QString AssistantViewModel::selectedSkill() const { return state_->selected_skill; }
QVariantMap AssistantViewModel::pendingPlan() const { return state_->plan.toVariantMap(); }
QVariantMap AssistantViewModel::pendingQuestion() const { return state_->question.toVariantMap(); }
QString AssistantViewModel::activeJobId() const { return state_->core.value("active_job_id").toString(); }
bool AssistantViewModel::canCancel() const { return state_->auth_pending || state_->file_selection.has_value() || state_->file_staging || state_->core.value("can_cancel").toBool(); }
QString AssistantViewModel::lastError() const { return !state_->error.isEmpty() ? state_->error : !state_->workflow_error.isEmpty() ? state_->workflow_error : !state_->preference_save_error.isEmpty() ? state_->preference_save_error : state_->preference_error; }
QString AssistantViewModel::contextPreview() const { return state_->controller ? QString::fromStdString(state_->controller->context()) : QString(); }
bool AssistantViewModel::contextConsentRequired() const {
    return !state_->controller || QJsonDocument(object(state_->controller->context())).toJson(QJsonDocument::Compact) != state_->consented_context;
}
void AssistantViewModel::setSelectedModel(const QString& model) {
    if (canCancel() && model != state_->model) { state_->preference_error = tr("Stop the active operation before changing its model."); state_->notify(); return; }
    for (const auto& row : state_->native.value("models").toArray()) if (row.toObject().value("id") == model && row.toObject().value("available").toBool()) {
        if (state_->model != model) {
            const auto offered = row.toObject().value("efforts").toVariant().toStringList();
            if (!state_->effort.isEmpty() && !offered.contains(state_->effort)) {
                state_->effort.clear();
                state_->preference_error = tr("The previous reasoning effort is unavailable for this model. Selection reset to Provider default.");
            }
            state_->model = model; state_->remember_choice(); state_->sync();
        } else { state_->remember_choice(); state_->notify(); }
        return;
    }
    state_->preference_error = tr("This model is unavailable."); state_->notify();
}
void AssistantViewModel::setSelectedEffort(const QString& effort) {
    if (canCancel() && effort != state_->effort) { state_->preference_error = tr("Stop the active operation before changing its reasoning effort."); state_->notify(); return; }
    if (!effort.isEmpty() && !availableEfforts().contains(effort)) { state_->preference_error = tr("This reasoning effort is unavailable."); state_->notify(); return; }
    if (state_->effort != effort) { state_->effort = effort; state_->remember_choice(); state_->notify(); }
    else { state_->remember_choice(); state_->notify(); }
}
void AssistantViewModel::selectSkill(const QString& id) {
    try {
        const auto reply = state_->command({{"type", "select_skill"}, {"id", id}});
        if (reply.ok) { state_->consented_context.clear(); state_->sync(); }
    } catch (...) { state_->error = state_->storage_error; state_->notify(); }
}
void AssistantViewModel::setProject(ProjectViewModel* project) { state_->bind(project); }
void AssistantViewModel::send(const QString& text) {
    if (text.trimmed().isEmpty()) return;
    try {
        if (static_cast<std::uint64_t>(text.size()) > State::Limits::message_bytes ||
            static_cast<std::uint64_t>(text.toUtf8().size()) > State::Limits::message_bytes) {
            state_->error = state_->capacity_error; state_->notify(); return;
        }
        if (state_->selected_rows_dirty && !state_->flush_selected_rows()) { state_->notify(); return; }
        if (canCancel()) { state_->error = tr("Stop the active operation before sending another message."); state_->notify(); return; }
        if (contextConsentRequired()) { state_->error = tr("Inspect and approve the outgoing project context before sending."); state_->notify(); return; }
        if (!state_->flush_failure() || !state_->reserve_failure()) { state_->notify(); return; }
        auto prospective = state_->history;
        prospective.append(State::public_row("user", text, {}, "completed"));
        if (!state_->admit(prospective)) { state_->failure_slot.reset(); state_->notify(); return; }
        // Prepare filesystem/encoding work before core user admission. The
        // temporary file is not committed if the controller rejects the input.
        const auto bytes = QJsonDocument(prospective).toJson(QJsonDocument::Compact);
        if (!QDir().mkpath(QFileInfo(state_->history_path).absolutePath())) throw std::runtime_error("Assistant history directory is unavailable");
        QSaveFile staged(state_->history_path);
        if (!staged.open(QIODevice::WriteOnly) || !staged.setPermissions(QFile::ReadOwner | QFile::WriteOwner) ||
            staged.write(bytes) != bytes.size() || !state_->queue_render()) throw std::runtime_error("Assistant history could not be prepared");
        Object command{{"type", "message"}, {"text", text}, {"connection_id", state_->native.value("connection_id")}, {"model", state_->model}};
        if (!state_->effort.isEmpty()) command["effort"] = state_->effort;
        command["schema"] = "edi.assistant/1";
        const auto wire = json(command);
        const auto reply = state_->controller->user_command(wire);
        if (!reply.ok) {
            staged.cancelWriting(); state_->failure_slot.reset();
            state_->error = State::bounded_error(object(reply.value).value("message").toString());
            (void)state_->queue_render(); return;
        }
        if (!staged.commit()) {
            state_->controller->cancel(); state_->queued_request.clear();
            state_->error = state_->storage_error; state_->failure_slot.reset(); state_->sync(); return;
        }
        state_->history.swap(prospective);
        state_->error.clear(); // explicit acknowledgement, independent of prior native last_error
        // The already-prepared queued render now observes the admitted prompt.

    } catch (...) {
        if (state_->controller) state_->controller->cancel();
        state_->queued_request.clear();
        if (state_->failure_slot && !state_->failure_slot->pending) state_->failure_slot.reset();
        state_->error = state_->storage_error; (void)state_->queue_render();
    }
}
void AssistantViewModel::approvePlan(const QString& id) {
    const auto revision = state_->controller->revision();
    state_->command({{"type", "approve_plan"}, {"plan_id", id}, {"project_id", QString::fromStdString(revision.project_id)},
                     {"revision", QString::number(revision.revision)}});
}
void AssistantViewModel::answerQuestion(const QString& id, const QString& answer) { state_->command({{"type", "answer"}, {"question_id", id}, {"answer", answer}}); }
void AssistantViewModel::cancel() {
    state_->retire_file_selection();
    state_->queued_request.clear(); // retire not-yet-dispatched work before any callback
#ifndef __EMSCRIPTEN__
    if (state_->auth_pending) {
        state_->auth_pending = false;
        state_->connection->sign_out(); // existing native teardown fences browser/loopback generations
    } else state_->connection->cancel(state_->core.value("active_turn_id").toString().toStdString());
#endif
    state_->controller->cancel(); state_->sync(); state_->notify();
}
void AssistantViewModel::signIn() {
    if (!state_->controller) return;
    if (canCancel()) { state_->error = tr("Stop the active operation before connecting."); state_->notify(); return; }
    const auto context = object(state_->controller->context());
    if (context.contains("error")) { state_->error = tr("Project context exceeds the assistant limit; nothing was sent."); state_->notify(); return; }
    state_->consented_context = QJsonDocument(context).toJson(QJsonDocument::Compact);
    if (connected()) { state_->error.clear(); state_->notify(); return; }
#ifndef __EMSCRIPTEN__
    const auto reply = state_->connection->sign_in();
    state_->auth_pending = reply.ok;
    state_->error = reply.ok ? QString() : State::bounded_error(object(reply.value).value("message").toString());
#else
    state_->error = tr("Browser AI connection is unavailable in this build.");
#endif
    state_->sync(); state_->notify();
}
void AssistantViewModel::signOut() {
    state_->retire_file_selection(); state_->consented_context.clear();
    state_->queued_request.clear(); state_->auth_pending = false;
#ifndef __EMSCRIPTEN__
    state_->connection->sign_out();
#endif
    state_->controller->cancel(); state_->sync(); state_->notify();
}
void AssistantViewModel::clearHistory() {
    try {
#ifndef __EMSCRIPTEN__
        if (state_->auth_pending) state_->connection->sign_out();
#endif
        state_->auth_pending = false;
        state_->bind(state_->project);
        const bool was_refused = state_->archive_refused;
        state_->archive_refused = false;
        if (!state_->publish({})) {
            state_->archive_refused = was_refused; state_->error = state_->storage_error;
        } else state_->error.clear();
        state_->sync();
    } catch (...) { state_->error = state_->storage_error; (void)state_->queue_render(); }
}

QString AssistantViewModel::beginFileSelection() {
    if (QThread::currentThread() != thread()) return {};
#ifdef __EMSCRIPTEN__
    state_->error = tr("File selection is unavailable until the browser transfer is implemented."); state_->notify(); return {};
#else
    try {
        if (!state_->publishing || !state_->controller || state_->file_staging || state_->file_authority_exhausted || state_->file_epoch == UINT64_MAX)
            throw std::runtime_error("The selected-file owner is unavailable");
        if (state_->auth_pending || (state_->project && state_->project->fit()->running()))
            throw std::runtime_error("Finish the active operation before selecting files");
        if (!state_->flush_selected_rows()) { state_->notify(); return {}; }
        const auto descriptor = state_->file_context();
        const auto native = state_->file_native_state();
        State::FileSelection scope;
        scope.id = QUuid::createUuid().toString(QUuid::WithoutBraces);
        scope.collection_id = descriptor.value("collection_id").toString();
        scope.next_collection_id = scope.collection_id.isEmpty() ? QUuid::createUuid().toString(QUuid::WithoutBraces) : scope.collection_id;
        scope.selection_generation = State::file_generation(descriptor);
        scope.owner_generation = state_->generation; scope.controller = state_->controller.get(); scope.project = state_->project;
        scope.revision = state_->controller->revision(); scope.epoch = state_->file_epoch + 1;
        scope.connection_epoch = state_->file_connection_epoch;
        scope.connection_id = native.value("connection_id").toString(); scope.native_status = native.value("status").toString();
        // The existing core door supplies the one policy decision, with an empty no-op that cannot alter bytes.
        const auto check = state_->controller->update_selected_files(scope.next_collection_id.toStdString(), scope.selection_generation, {}, {});
        if (!check.ok) { state_->error = State::bounded_error(object(check.value).value("message").toString()); state_->notify(); return {}; }
        const auto id = scope.id;
        state_->retire_file_selection();
        // A reentrant retirement receiver cannot be overwritten by the outer prepared begin.
        if (scope.epoch != state_->file_epoch || state_->file_selection || scope.owner_generation != state_->generation) return {};
        state_->file_selection.emplace(std::move(scope));
        state_->error.clear();
        try { state_->notify(); } catch (...) {} // a committed capability still returns its actual ID
        return id;
    } catch (...) { state_->error = tr("File selection could not be prepared. Existing files are preserved."); try { state_->notify(); } catch (...) {} return {}; }
#endif
}
bool AssistantViewModel::addSelectedFiles(const QString& requestId, const QList<QUrl>& urls) {
    if (QThread::currentThread() != thread() || !state_->file_selection || state_->file_selection->id != requestId) return false;
    bool admitted = false;
    const auto owner_at_entry = state_->generation, epoch_at_entry = state_->file_epoch;
    try {
        if (!state_->file_current(*state_->file_selection)) { state_->retire_file_selection(); return false; }
        auto scope = std::move(*state_->file_selection); state_->file_selection.reset();
        state_->file_staging = true; // consumed once, but Stop/rebind can still retire its epoch
        try {
            if (urls.isEmpty()) throw std::runtime_error("No files were selected");
            if (state_->project && state_->project->fit()->running()) throw std::runtime_error("Finish the active operation before selecting files");
            auto files = state_->read_selected_urls(urls, state_->file_context());
            if (!state_->file_current(scope)) throw std::runtime_error("The selected-file owner changed");
            auto result = state_->controller->update_selected_files(scope.next_collection_id.toStdString(), scope.selection_generation, std::move(files), {});
            admitted = result.ok;
            if (admitted) {
                state_->selected_reply = std::move(result.value); // noexcept transfer of the core-prepared descriptor
                state_->selected_rows_dirty = true;
                state_->consented_context.clear(); state_->error.clear();
                (void)state_->flush_selected_rows();
            } else state_->error = State::bounded_error(object(result.value).value("message").toString());
        } catch (const std::exception& error) { state_->error = State::bounded_error(QString::fromUtf8(error.what())); }
        catch (...) { state_->error = tr("Selected files could not be retained. Existing files are preserved."); }
        state_->file_staging = false;
        // All staging has ended before temporary chooser/transport ownership may be released.
        try { emit fileSelectionRetired(requestId); } catch (...) {}
        try { state_->notify(); } catch (...) {}
        return admitted; // actual admission, including a recoverable post-admission presentation failure
    } catch (...) {
        if (state_->generation != owner_at_entry || state_->file_epoch != epoch_at_entry ||
            (state_->file_selection && state_->file_selection->id != requestId)) return admitted;
        state_->file_staging = false;
        if (state_->file_selection && state_->file_selection->id == requestId) state_->retire_file_selection();
        state_->error = tr("Selected files could not be retained. Inspect the file list before retrying.");
        try { state_->notify(); } catch (...) {}
        return admitted;
    }
}
void AssistantViewModel::cancelFileSelection(const QString& requestId) {
    if (QThread::currentThread() != thread() || !state_->file_selection || state_->file_selection->id != requestId) return;
    state_->retire_file_selection(); state_->notify();
}
bool AssistantViewModel::removeSelectedFile(const QString& id) {
    if (QThread::currentThread() != thread() || !state_->publishing) return false;
    bool admitted = false;
    try {
        if (state_->file_selection || state_->file_staging || state_->auth_pending ||
            (state_->project && state_->project->fit()->running())) throw std::runtime_error("Finish the active operation before changing files");
        if (!state_->flush_selected_rows()) { state_->notify(); return false; }
        const auto current = state_->file_context();
        auto result = state_->controller->update_selected_files(current.value("collection_id").toString().toStdString(), State::file_generation(current), {}, {id.toStdString()});
        admitted = result.ok;
        if (admitted) {
            state_->selected_reply = std::move(result.value); state_->selected_rows_dirty = true;
            state_->consented_context.clear(); state_->error.clear(); (void)state_->flush_selected_rows();
        } else state_->error = State::bounded_error(object(result.value).value("message").toString());
        state_->notify();
    } catch (...) { state_->error = tr("Selected file could not be removed. Inspect the retained file list before retrying."); try { state_->notify(); } catch (...) {} }
    return admitted;
}

}  // namespace edi_app
