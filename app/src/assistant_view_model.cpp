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
#include <QDirIterator>
#include <QTemporaryDir>
#include <QDesktopServices>
#include <QMap>
#include <QSet>
#include "edi/io.hpp"
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
#include "codex_agent.hpp"
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


#ifndef __EMSCRIPTEN__
    // The default native facade uses one official runtime. The existing injected
    // NativeDependencies constructor is solely the old adapter's compatibility door.
    bool generic_mode = false, generic_connecting = false, generic_busy = false, generic_blocked = false;
    bool generic_authenticated = false, generic_retiring = false, generic_writing_input = false;
    std::unique_ptr<CodexAgent> agent;
    QString generic_workspace, generic_thread, generic_turn, generic_login, generic_terminal_turn;
    Object generic_native{{"status", "disconnected"}};
    QMap<QString, QString> generic_input_paths;
    std::unique_ptr<QTemporaryDir> generic_input_cache;
    QStringList generic_skill_paths;
    QMap<QString, Object> generic_items;
    QMap<QString, QString> generic_item_rows, generic_rpc_rows, generic_rpc_turns;
    QSet<QString> generic_final_items;
    quint64 generic_catalog_bytes = 2; // Complete raw result objects, including array framing.
    std::optional<Object> generic_held_row;
    QJsonValue generic_question_rpc;
    QString generic_question_item, generic_question_id, generic_question_public_id, generic_question_thread, generic_question_turn;
    quint64 generic_item_bytes = 0;

    static QString generic_id(const QJsonValue& value) {
        if (!value.isString()) throw std::runtime_error("Agent protocol identifier is unavailable");
        const auto id = value.toString();
        if (id.isEmpty() || id.size() > static_cast<qsizetype>(Limits::id_bytes) ||
            static_cast<quint64>(id.toUtf8().size()) > Limits::id_bytes)
            throw std::runtime_error("Agent protocol identifier exceeds its limit");
        return id;
    }
    static quint64 generic_size(const QJsonValue& value, quint64 cap) {
        quint64 bytes = 0;
        if (!codex_encoded_size(value, cap, bytes)) throw std::length_error("Agent payload exceeds its limit");
        return bytes;
    }
    bool generic_present(Object row) {
        const auto id = row.value("id").toString();
        quint64 bytes = 2;
        bool existing = false;
        for (const auto& value : history) {
            if (value.toObject().value("id") == id) { existing = true; continue; }
            const auto size = generic_size(value, Limits::ui_history_bytes);
            if (size + 1 > Limits::ui_history_bytes - bytes) return false;
            bytes += size + 1;
        }
        const auto size = generic_size(row, Limits::message_bytes);
        if (size > Limits::ui_history_bytes - bytes || (!existing && history.size() >= static_cast<qsizetype>(Limits::ui_messages))) return false;
        auto next = history;
        bool replaced = false;
        for (qsizetype i = 0; i < next.size(); ++i)
            if (next[i].toObject().value("id").toString() == id) { next[i] = row; replaced = true; break; }
        if (!replaced) next.append(row);
        // The public archive is the sole persisted/displayed row owner. Complete
        // output is retained separately only while its publication is unsettled.
        if (!publish(std::move(next))) { generic_held_row = std::move(row); return false; }
        return true;
    }
    void generic_retire_question() noexcept {
        question = {}; generic_question_rpc = {}; generic_question_id.clear();
        generic_question_public_id.clear(); generic_question_item.clear();
        generic_question_thread.clear(); generic_question_turn.clear();
    }
    void generic_interrupt_rows() noexcept {
        try {
            auto next = history;
            for (qsizetype i = 0; i < next.size(); ++i) {
                auto row = next[i].toObject();
                if (row.value("status") == "pending" || row.value("status") == "in_progress") {
                    row["status"] = "interrupted"; next[i] = row;
                }
            }
            (void)publish(std::move(next));
        } catch (...) {} // Execution authority is fenced independently of diagnostics/storage.
    }
    void generic_fail(const QString& explanation) noexcept {
        generic_authenticated = false; generic_retiring = false;
        generic_busy = false; generic_connecting = false; generic_blocked = true;
        retire_file_selection(); consented_context.clear(); generic_retire_question();
        if (agent) try { agent->retire(); } catch (...) {}
        generic_interrupt_rows();
        generic_rpc_rows.clear(); generic_rpc_turns.clear();
        generic_turn.clear(); generic_thread.clear();
        try {
            generic_native["status"] = "disconnected"; native = generic_native;
            error = bounded_error(explanation); notify();
        } catch (...) {}
    }
    QString generic_request(const QString& method, const Object& params = {}) {
        const auto id = agent->request(method, params);
        if (id.isEmpty()) throw std::runtime_error("Agent request could not be delivered");
        return id;
    }
    struct GenericFileStage {
        QMap<QString, QString> paths;
        QStringList fresh;
        ~GenericFileStage() { for (const auto& path : fresh) QFile::remove(path); }
    };
    std::unique_ptr<GenericFileStage> generic_stage_files(const std::vector<edi::assistant::SelectedFile>& files) {
        if (!generic_input_cache) {
            generic_input_cache = std::make_unique<QTemporaryDir>();
            if (!generic_input_cache->isValid()) throw std::runtime_error("Selected snapshot cache is unavailable");
        }
        auto stage = std::make_unique<GenericFileStage>(); stage->paths = generic_input_paths;
        for (const auto& file : files) {
            const auto name = QString::fromUtf8(file.relative_name.data(), static_cast<qsizetype>(file.relative_name.size()));
            if (name.isEmpty() || name == "." || name == ".." || name.contains('/') || name.contains('\\') || name.contains(QChar(0)))
                throw std::runtime_error("Selected file has an unsupported relative name");
            const auto id = QString::fromStdString(file.id);
            const auto path = generic_input_cache->path() + "/" + id + "~" + name;
            stage->fresh.append(path);
            QSaveFile snapshot(path);
            if (!snapshot.open(QIODevice::WriteOnly) || !snapshot.setPermissions(QFile::ReadOwner | QFile::WriteOwner) ||
                snapshot.write(reinterpret_cast<const char*>(file.bytes.data()), static_cast<qint64>(file.bytes.size())) != static_cast<qint64>(file.bytes.size()) || !snapshot.commit())
                throw std::runtime_error("Selected file snapshot could not be retained");
            stage->paths.insert(id, path);
        }
        return stage;
    }
    void generic_prepare_workspace() {
        if (!generic_workspace.isEmpty()) return;
        const auto root = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) +
            "/assistant/agent/" + QUuid::createUuid().toString(QUuid::WithoutBraces);
        if (!QDir().mkpath(root + "/workspace/inputs") || !QFile::setPermissions(root, QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner))
            throw std::runtime_error("Agent working copy could not be prepared");
        const auto workspace = root + "/workspace";
        for (auto it = generic_input_paths.constBegin(); it != generic_input_paths.constEnd(); ++it) {
            QFile original(it.value());
            if (!original.open(QIODevice::ReadOnly)) throw std::runtime_error("Selected snapshot is unavailable");
            const auto name = QFileInfo(it.value()).fileName().section('~', 1);
            if (name.isEmpty() || name == "." || name == ".." || name.contains('/') || name.contains('\\'))
                throw std::runtime_error("Selected snapshot name is unavailable");
            if (!QFile::copy(it.value(), workspace + "/inputs/" + name))
                throw std::runtime_error("Selected snapshot could not be staged");
        }
        if (project) {
            try { edi::save_project(*project->assistantProject(), (workspace + "/project").toStdString()); }
            catch (...) { throw std::runtime_error("The current project could not be staged"); }
        }
        // All packaged skills, including future added valid files, are exposed to
        // the runtime's own discovery. No relay developer instructions are copied.
        QStringList skills;
        quint64 packaged_bytes = 0;
        QDirIterator files(":/edi/assistant/skills", QDir::Files, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const auto resource = files.next();
            const auto relative = resource.mid(QString(":/edi/assistant/skills/").size());
            if (relative.contains("..") || relative.size() > static_cast<qsizetype>(Limits::id_bytes) || (relative.endsWith("/SKILL.md") && skills.size() >= static_cast<qsizetype>(Limits::models)))
                throw std::length_error("Bundled skill catalog exceeds its limit");
            QFile source(resource);
            if (!source.open(QIODevice::ReadOnly) || source.size() < 0 || static_cast<quint64>(source.size()) > Limits::context_bytes)
                throw std::runtime_error("Bundled skill content is unavailable");
            if (static_cast<quint64>(source.size()) > Limits::context_bytes - packaged_bytes)
                throw std::length_error("Bundled skill resources exceed their aggregate limit");
            packaged_bytes += static_cast<quint64>(source.size());
            const auto destination = workspace + "/.agents/skills/" + relative;
            if (!QDir().mkpath(QFileInfo(destination).absolutePath()) || !QFile::copy(resource, destination))
                throw std::runtime_error("Bundled skill content could not be staged");
            if (relative.endsWith("/SKILL.md")) skills.append(QFileInfo(destination).absoluteFilePath());
        }
        if (skills.isEmpty()) throw std::runtime_error("No bundled skills are available");
        generic_skill_paths = std::move(skills); generic_workspace = workspace;
    }
    void generic_revoke_workspace() noexcept {
        generic_authenticated = false; generic_retiring = false;
        if (agent) try { agent->retire(); } catch (...) {}
        generic_busy = false; generic_connecting = false;
        generic_interrupt_rows();
        generic_thread.clear(); generic_turn.clear(); generic_login.clear(); generic_terminal_turn.clear();
        generic_items.clear(); generic_item_rows.clear(); generic_final_items.clear(); generic_rpc_rows.clear(); generic_rpc_turns.clear();
        generic_retire_question();
        generic_item_bytes = 0; generic_workspace.clear(); generic_skill_paths.clear();
        // Keep retired workspace artifacts for explicit recovery; no live writer
        // is adopted, and no files are published back to the current project.
        try { generic_native["status"] = "disconnected"; } catch (...) {}
    }
    void generic_initialize() {
        agent = std::make_unique<CodexAgent>(&owner);
        QObject::connect(agent.get(), &CodexAgent::started, &owner, [this] {
            try {
                generic_request("initialize", {{"clientInfo", Object{{"name", "edi"}, {"title", "Edi"}, {"version", "1"}}}});
            } catch (...) { generic_fail(QObject::tr("The official agent could not be initialized.")); }
        });
        QObject::connect(agent.get(), &CodexAgent::failed, &owner, [this](const QString& message) { generic_fail(message); });
        QObject::connect(agent.get(), &CodexAgent::response, &owner,
            [this](const QString& id, const QString& method, const Object& reply) {
                try { generic_response(id, method, reply); }
                catch (...) { generic_fail(QObject::tr("The official agent reply is invalid or exceeds its limits.")); }
            });
        QObject::connect(agent.get(), &CodexAgent::event, &owner, [this](const QString& method, const Object& params) {
            try { generic_event(method, params); }
            catch (...) { generic_fail(QObject::tr("The official agent event is invalid or exceeds its limits.")); }
        });
        QObject::connect(agent.get(), &CodexAgent::serverRequest, &owner,
            [this](const QJsonValue& id, const QString& method, const Object& params) {
                try { generic_server_request(id, method, params); }
                catch (...) { generic_fail(QObject::tr("The official agent request could not be retained.")); }
            });
    }
    void generic_sign_in() {
        if (project && project->fit()->running()) throw std::runtime_error("Finish the active manual fit first");
        if (generic_busy || generic_connecting || generic_held_row) throw std::runtime_error("Finish or clear the active agent operation first");
        generic_blocked = false; error.clear();
        generic_revoke_workspace(); // Never relabel a modified recovery directory as a fresh snapshot.
        generic_prepare_workspace();
        generic_catalog_bytes = 2;
        const auto executable = CodexAgent::executable();
        if (executable.isEmpty()) {
            generic_fail(QObject::tr("The bundled official agent is unavailable. Rebuild or reinstall this Edi candidate.")); return;
        }
        generic_connecting = true;
        if (!agent->start(executable, generic_workspace)) throw std::runtime_error("The official agent could not be started");
        notify();
    }
    void generic_start_thread() {
        Object params{{"cwd", generic_workspace}, {"sandbox", "workspace-write"},
            {"approvalPolicy", "on-request"}, {"approvalsReviewer", "user"}, {"modelProvider", "openai"},
            {"developerInstructions", "You are Edi's scientific assistant using the official runtime. Work only in this staged working copy; inputs and the open application project are not yours to overwrite. Use the bundled relevant Edi skills and the actual installed Python/CLI. Ask about missing scientific metadata. Obtain an explicit scientific plan approval before fitting. Preserve original inputs and accepted-best evidence. Never claim a conversion or engine outcome you did not perform. No automatic adoption into the open app is available."}};
        params["developerInstructions"] = params.value("developerInstructions").toString() +
            " Edi Python executable: " + qEnvironmentVariable("EDI_AGENT_PYTHON", "python") +
            "; EDI_EXTENSION_DIR: " + qEnvironmentVariable("EDI_EXTENSION_DIR") +
            ". If importing edi fails, report the missing bootstrap prerequisite rather than inventing a result.";
        if (!model.isEmpty()) params["model"] = model;
        generic_request("thread/start", params);
    }
    void generic_response(const QString& id, const QString& method, const Object& reply) {
        if (!publishing || !generic_mode || (generic_retiring && method != "account/logout")) return;
        if (reply.contains("error")) {
            if (generic_rpc_rows.contains(id)) {
                const auto rowId = generic_rpc_rows.take(id);
                for (const auto& value : history) if (value.toObject().value("id") == rowId) {
                    auto row = value.toObject(); row["status"] = "interrupted"; (void)generic_present(row); break;
                }
            }
            // A rejected or uncertain steer is never guessed into a new turn.
            generic_fail(QObject::tr("The official agent refused the request. Inspect the retained message before retrying.")); return;
        }
        if (!reply.value("result").isObject()) throw std::runtime_error("Agent reply result is invalid");
        const auto result = reply.value("result").toObject();
        if (method == "initialize") {
            if (!agent->notification("initialized")) throw std::runtime_error("Agent handshake failed");
            agent->settleOperation(); agent->beginOperation(Limits::sign_in_ms, 0);
            generic_request("account/read", {{"refreshToken", false}});
        } else if (method == "account/read") {
            const auto account = result.value("account").toObject();
            if (account.value("type") == "chatgpt") {
                generic_native["label"] = account.value("email").isString() ? account.value("email") : QJsonValue("ChatGPT");
                generic_native["models"] = QJsonArray{};
                generic_request("model/list", {{"includeHidden", true}});
            } else if (result.value("account").isNull()) generic_request("account/login/start", {{"type", "chatgpt"}});
            else throw std::runtime_error("Managed ChatGPT login is required");
        } else if (method == "account/login/start") {
            if (result.value("type") != "chatgpt") throw std::runtime_error("Managed ChatGPT login is required");
            generic_login = generic_id(result.value("loginId"));
            const QUrl url(result.value("authUrl").toString());
            if (!url.isValid() || url.scheme() != "https" || !url.userInfo().isEmpty() || (url.host() != "auth.openai.com" && url.host() != "chatgpt.com")) throw std::runtime_error("Agent login URL is unavailable");
            if (!QDesktopServices::openUrl(url)) throw std::runtime_error("The sign-in browser could not be opened");
        } else if (method == "model/list") {
            if (!result.value("data").isArray()) throw std::runtime_error("Agent model catalog is unavailable");
            const auto rawBytes = generic_size(result, Limits::http_json_bytes);
            const quint64 separator = generic_catalog_bytes == 2 ? 0 : 1;
            if (separator > Limits::http_json_bytes - generic_catalog_bytes || rawBytes > Limits::http_json_bytes - generic_catalog_bytes - separator)
                throw std::length_error("The complete raw model catalog exceeds its aggregate limit");
            generic_catalog_bytes += rawBytes + separator;
            auto choices = generic_native.value("models").toArray();
            const auto incoming = result.value("data").toArray();
            if (incoming.size() > static_cast<qsizetype>(Limits::models) - choices.size()) throw std::length_error("Agent model catalog exceeds limit");
            for (const auto& entry : incoming) {
                const auto item = entry.toObject();
                const auto slug = generic_id(item.value("model"));
                const auto options = item.value("supportedReasoningEfforts").toArray();
                if (options.size() > static_cast<qsizetype>(Limits::model_options)) throw std::length_error("Agent reasoning options exceed limit");
                QJsonArray efforts;
                for (const auto& option : options) efforts.append(generic_id(option.toObject().value("reasoningEffort")));
                if (!item.value("displayName").isString() || !item.value("hidden").isBool()) throw std::runtime_error("Agent model has invalid metadata");
                const auto defaultEffort = generic_id(item.value("defaultReasoningEffort"));
                if (!efforts.contains(defaultEffort)) throw std::runtime_error("Agent default effort is not supported by its catalog");
                choices.append(Object{{"default_effort", defaultEffort}, {"id", slug}, {"display_name", item.value("displayName")}, {"efforts", efforts},
                    {"available", !item.value("hidden").toBool()}, {"attachment_types", QJsonArray{}}});
            }
            generic_size(choices, Limits::http_json_bytes); generic_native["models"] = choices;
            if (result.value("nextCursor").isString() && !result.value("nextCursor").toString().isEmpty())
                generic_request("model/list", {{"includeHidden", true}, {"cursor", result.value("nextCursor")}});
            else {
                native = generic_native; sync();
                generic_request("skills/list", {{"cwds", QJsonArray{generic_workspace}}, {"forceReload", true}});
            }
        } else if (method == "skills/list") {
            if (!result.value("data").isArray()) throw std::runtime_error("Agent skill catalog is unavailable");
            QStringList found; QJsonArray catalog;
            for (const auto& entry : result.value("data").toArray()) {
                const auto group = entry.toObject();
                if (group.value("cwd") != generic_workspace) continue;
                if (!group.value("errors").isArray() || !group.value("errors").toArray().isEmpty()) throw std::runtime_error("Agent skill discovery reported an error");
                for (const auto& value : group.value("skills").toArray()) {
                    const auto skill = value.toObject(); const auto path = skill.value("path").toString();
                    if (!generic_skill_paths.contains(path)) continue;
                    if (!skill.value("enabled").isBool() || !skill.value("enabled").toBool()) throw std::runtime_error("A bundled skill is disabled");
                    const auto name = generic_id(skill.value("name"));
                    if (found.contains(path)) throw std::runtime_error("A bundled skill registration is ambiguous");
                    found.append(path);
                    QFile file(path); if (!file.open(QIODevice::ReadOnly) || file.size() > static_cast<qint64>(Limits::context_bytes)) throw std::runtime_error("Bundled skill is unavailable");
                    catalog.append(Object{{"id", name}, {"title", name}, {"version", "See content"}, {"summary", skill.value("description")},
                        {"path", path}, {"content", QString::fromUtf8(file.read(Limits::context_bytes + 1))}, {"available", true}, {"blocked_reason", ""}, {"references", QJsonArray{}}});
                }
            }
            if (found.size() != generic_skill_paths.size()) throw std::runtime_error("Not all bundled skills are registered");
            generic_size(catalog, Limits::context_bytes); skills.assign(catalog); selected_skill.clear();
            generic_start_thread();
        } else if (method == "thread/start") {
            const auto sandbox = result.value("sandbox").toObject();
            const auto roots = sandbox.value("writableRoots").toArray();
            if (!sandbox.value("writableRoots").isArray() || !sandbox.value("networkAccess").isBool() ||
                !sandbox.value("excludeSlashTmp").isBool() || !sandbox.value("excludeTmpdirEnvVar").isBool())
                throw std::runtime_error("Agent effective sandbox metadata is unavailable");
            if (result.value("cwd") != generic_workspace || result.value("modelProvider") != "openai" ||
                result.value("approvalPolicy") != "on-request" || result.value("approvalsReviewer") != "user" ||
                sandbox.value("type") != "workspaceWrite" || sandbox.value("networkAccess").toBool(true) ||
                !sandbox.value("excludeSlashTmp").toBool() || !sandbox.value("excludeTmpdirEnvVar").toBool())
                throw std::runtime_error("Agent effective policy differs from the admitted workspace boundary");
            for (const auto& root : roots) if (!root.isString() || QDir::cleanPath(root.toString()) != QDir::cleanPath(generic_workspace))
                throw std::runtime_error("Agent effective writable roots exceed the admitted workspace");
            generic_thread = generic_id(result.value("thread").toObject().value("id"));
            generic_native["connection_id"] = generic_thread; generic_native["status"] = "ready";
            generic_connecting = false; generic_authenticated = true; generic_retiring = false; agent->settleOperation(); error.clear();
        } else if (method == "turn/start") {
            const auto turn = result.value("turn").toObject();
            const auto turnId = generic_id(turn.value("id"));
            if (!generic_turn.isEmpty() && generic_turn != turnId) throw std::runtime_error("Agent turn identity changed");
            if (turnId != generic_terminal_turn) { generic_turn = turnId; generic_busy = true; }
            generic_acknowledge(id);
        } else if (method == "turn/steer") {
            const auto expected = generic_rpc_turns.take(id);
            if (expected.isEmpty() || generic_id(result.value("turnId")) != expected)
                throw std::runtime_error("Agent steering reply has the wrong turn binding");
            generic_acknowledge(id);
        }
        else if (method == "account/logout") {
            generic_revoke_workspace(); generic_blocked = false; error.clear();
        }
        sync(); notify();
    }
    void generic_acknowledge(const QString& id) {
        if (!generic_rpc_rows.contains(id)) return;
        const auto rowId = generic_rpc_rows.take(id);
        for (const auto& value : history) if (value.toObject().value("id") == rowId) {
            auto row = value.toObject(); row["status"] = "completed";
            if (!generic_present(row)) generic_fail(storage_error);
            return;
        }
    }
    bool generic_bound(const Object& params) const {
        return generic_authenticated && !generic_retiring && !generic_thread.isEmpty() && !generic_turn.isEmpty() &&
            params.value("threadId").isString() && params.value("threadId") == generic_thread &&
            params.value("turnId").isString() && params.value("turnId") == generic_turn;
    }
    bool generic_item(const Object& item, bool completed) {
        const auto id = generic_id(item.value("id")), type = generic_id(item.value("type"));
        if (!generic_items.contains(id) && generic_items.size() >= static_cast<qsizetype>(Limits::stream_items)) throw std::length_error("Agent item limit exceeded");
        const auto old = generic_items.value(id);
        if (!old.isEmpty() && old.value("type") != type) throw std::runtime_error("Agent item type changed");
        if (generic_final_items.contains(id)) {
            if (completed && old == item) return false;
            throw std::runtime_error("An agent item changed after finalization");
        }
        if (!completed && !old.isEmpty()) {
            if (old == item) return false;
            throw std::runtime_error("A repeated agent item declaration changed");
        }
        if (type == "agentMessage" && !item.value("text").isString()) throw std::runtime_error("Agent text item is invalid");
        if (type == "commandExecution") {
            if (!item.value("command").isString() || !item.value("cwd").isString() || !item.value("commandActions").isArray() ||
                !item.value("status").isString()) throw std::runtime_error("Agent command item is invalid");
            if (!old.isEmpty() && (old.value("command") != item.value("command") || old.value("cwd") != item.value("cwd"))) throw std::runtime_error("Agent command identity changed");
        }
        if (type == "fileChange" && (!item.value("changes").isArray() || !item.value("status").isString())) throw std::runtime_error("Agent file item is invalid");
        if (completed && (type == "commandExecution" || type == "fileChange") &&
            item.value("status") != "completed" && item.value("status") != "failed" && item.value("status") != "declined")
            throw std::runtime_error("Agent tool final item is not settled");
        const auto oldBytes = old.isEmpty() ? 0 : generic_size(old, Limits::stream_retained_bytes);
        const auto bytes = generic_size(item, Limits::stream_retained_bytes);
        if (bytes > Limits::stream_retained_bytes - (generic_item_bytes - oldBytes) || !agent->retainOutput(generic_item_bytes - oldBytes + bytes)) throw std::length_error("Agent output exceeds retained limit");
        generic_items[id] = item; generic_item_bytes = generic_item_bytes - oldBytes + bytes;
        if (completed) { generic_final_items.insert(id); if (generic_question_item == id) generic_retire_question(); }
        if (type == "userMessage" || type == "reasoning") return true;
        if (!generic_item_rows.contains(id)) generic_item_rows[id] = QUuid::createUuid().toString(QUuid::WithoutBraces);
        const auto text = type == "agentMessage" ? item.value("text").toString() : type == "commandExecution" ? item.value("command").toString() : type == "fileChange" ? QObject::tr("Working-copy file changes") : type;
        Object row{{"id", generic_item_rows.value(id)}, {"kind", type == "agentMessage" ? "assistant" : "activity"}, {"text", text},
            {"status", completed ? (type == "agentMessage" ? "in_progress" : item.value("status").toString("completed")) : "in_progress"}, {"payload", type == "agentMessage" ? Object{} : item}};
        if (!generic_present(row)) { generic_fail(storage_error); return false; }
        return true;
    }
    void generic_event(const QString& method, const Object& params) {
        if (!publishing) return;
        if (method == "account/login/completed") {
            if (params.value("loginId") != generic_login) return;
            if (!params.value("success").toBool()) throw std::runtime_error("Agent sign-in was not completed");
            generic_login.clear(); generic_request("account/read", {{"refreshToken", false}}); return;
        }
        if (method == "account/updated") {
            if (params.value("authMode") != "chatgpt" || generic_authenticated || !generic_thread.isEmpty())
                generic_fail(QObject::tr("The agent account changed. Reconnect to approve the current account and a fresh working copy."));
            return;
        }
        if (method == "serverRequest/resolved") {
            if (!generic_authenticated || params.value("threadId") != generic_thread) return;
            agent->resolved(params.value("requestId"));
            if (params.value("requestId") == generic_question_rpc) generic_retire_question();
            notify(); return;
        }
        if (method == "turn/started") {
            if (!generic_authenticated || generic_retiring || params.value("threadId") != generic_thread || !generic_busy) return;
            const auto id = generic_id(params.value("turn").toObject().value("id"));
            if (!generic_turn.isEmpty() && generic_turn != id) throw std::runtime_error("Agent turn changed");
            if (id == generic_terminal_turn || id == generic_turn) return;
            generic_turn = id; agent->activity(); notify(); return;
        }
        if (method == "turn/completed") {
            if (!generic_authenticated || generic_retiring || params.value("threadId") != generic_thread || generic_turn.isEmpty()) return;
        } else if (!generic_bound(params)) return;
        if (method == "item/started" || method == "item/completed") {
            if (generic_item(params.value("item").toObject(), method == "item/completed")) agent->activity();
        } else if (method == "item/agentMessage/delta") {
            const auto id = generic_id(params.value("itemId"));
            if (!params.value("delta").isString()) throw std::runtime_error("Agent delta is invalid");
            if (!generic_item_rows.contains(id) || generic_items.value(id).value("type") != "agentMessage" || generic_final_items.contains(id)) throw std::runtime_error("Agent text has no current unfinished original item");
            for (const auto& value : history) if (value.toObject().value("id") == generic_item_rows.value(id)) {
                auto row = value.toObject(); const auto delta = params.value("delta").toString();
                const auto old = row.value("text").toString();
                if (old.size() > static_cast<qsizetype>(Limits::message_bytes) || delta.size() > static_cast<qsizetype>(Limits::message_bytes) - old.size()) throw std::length_error("Agent text exceeds message limit");
                quint64 prospective = 0;
                if (!codex_encoded_size(old, Limits::message_bytes, prospective) || prospective < 2)
                    throw std::length_error("Agent text exceeds message limit");
                prospective -= 2;
                if (!codex_encoded_size(delta, Limits::message_bytes, prospective))
                    throw std::length_error("Agent text exceeds message limit");
                row["text"] = old + delta;
                generic_size(row, Limits::message_bytes);
                if (!generic_present(row)) generic_fail(storage_error);
                else if (!delta.isEmpty()) agent->activity();
                break;
            }
        } else if (method == "turn/completed") {
            const auto turn = params.value("turn").toObject();
            if (generic_id(turn.value("id")) != generic_turn) return;
            const auto status = turn.value("status").toString();
            if (status != "completed" && status != "interrupted" && status != "failed") throw std::runtime_error("Agent terminal status is invalid");
            if (turn.contains("items")) {
                if (!turn.value("items").isArray()) throw std::runtime_error("Agent terminal snapshot is invalid");
                for (const auto& value : turn.value("items").toArray()) { generic_item(value.toObject(), true); if (!generic_authenticated) return; }
            }
            if (status == "completed") for (auto it = generic_items.constBegin(); it != generic_items.constEnd(); ++it)
                if (it.value().value("type") != "agentMessage" && it.value().value("type") != "userMessage" && it.value().value("type") != "reasoning" && !generic_final_items.contains(it.key()))
                    throw std::runtime_error("Agent terminal omitted an unfinished activity outcome");
            auto next = history;
            for (qsizetype i = 0; i < next.size(); ++i) {
                auto row = next[i].toObject();
                if (row.value("status") == "in_progress") { row["status"] = status; next[i] = row; }
            }
            if (!publish(std::move(next))) { generic_fail(storage_error); return; }
            generic_terminal_turn = generic_turn;
            generic_busy = false; generic_turn.clear(); generic_items.clear(); generic_item_rows.clear(); generic_final_items.clear(); generic_item_bytes = 0;
            generic_retire_question(); agent->retainOutput(0); agent->settleOperation();
            if (status != "completed") error = QObject::tr("The official agent turn was interrupted or failed. Retained work is preserved.");
        }
        notify();
    }
    void generic_server_request(const QJsonValue& id, const QString& method, const Object& params) {
        if (!generic_bound(params)) { agent->reject(id); return; }
        if (method == "item/commandExecution/requestApproval" || method == "item/fileChange/requestApproval") {
            // on-request approval can mean a sandbox escape. First prototype
            // never grants broader writes/network merely because it is once.
            const auto item = generic_id(params.value("itemId"));
            if (!generic_items.contains(item)) { agent->reject(id); return; }
            const auto row = public_row("activity", QObject::tr("The agent requested authority beyond the admitted working copy. Edi declined it."),
                {{"item_id", item}, {"decision", "decline"}}, "refused");
            if (!generic_present(row)) { generic_fail(storage_error); return; }
            if (!agent->answer(id, {{"decision", "decline"}})) generic_fail(QObject::tr("The agent refusal could not be delivered."));
        } else if (method == "item/tool/requestUserInput") {
            if (!question.isEmpty() || !params.value("questions").isArray() || params.value("questions").toArray().size() != 1) { agent->reject(id); return; }
            const auto itemId = generic_id(params.value("itemId"));
            if (!generic_items.contains(itemId) || generic_final_items.contains(itemId)) { agent->reject(id); return; }
            const auto q = params.value("questions").toArray().first().toObject();
            const auto qid = generic_id(q.value("id"));
            if (!q.value("question").isString() || q.value("question").toString().toUtf8().size() > static_cast<qsizetype>(Limits::question_text_bytes)) { agent->reject(id); return; }
            QJsonArray options;
            for (const auto& option : q.value("options").toArray()) {
                if (options.size() >= static_cast<qsizetype>(Limits::question_options)) throw std::length_error("Agent question exceeds option limit");
                const auto value = option.toObject(); const auto label = value.value("label").toString();
                if (label.isEmpty() || label.toUtf8().size() > static_cast<qsizetype>(Limits::question_option_label_bytes)) throw std::runtime_error("Agent option is invalid");
                if (!value.value("description").isString() || value.value("description").toString().toUtf8().size() > static_cast<qsizetype>(Limits::question_option_description_bytes)) throw std::length_error("Agent option description exceeds limit");
                options.append(Object{{"id", label}, {"label", label}, {"description", value.value("description")}});
            }
            generic_question_public_id = QUuid::createUuid().toString(QUuid::WithoutBraces);
            question = {{"question_id", generic_question_public_id}, {"text", q.value("question")}, {"options", options}, {"allow_free_text", true}};
            generic_question_rpc = id; generic_question_id = qid; generic_question_item = itemId; generic_question_thread = generic_thread; generic_question_turn = generic_turn; notify();
        } else agent->reject(id); // No fabricated result for unsupported callbacks.
    }
    void generic_send(const QString& text) {
        if (!generic_authenticated || generic_retiring || generic_blocked || generic_connecting || generic_native.value("status") != "ready" || generic_held_row)
            throw std::runtime_error("Connect the official agent or clear its interrupted conversation first");
        const auto context = owner.contextPreview();
        if (context.toUtf8().size() > static_cast<qsizetype>(Limits::context_bytes)) throw std::length_error("Agent context exceeds limit");
        const bool steering = generic_busy;
        if (steering && generic_turn.isEmpty()) {
            // No steer has been admitted or written. Keep the draft and the
            // original running request alive; a preflight refusal is not a
            // transport/retention failure and must not retire its process.
            error = QObject::tr("The agent is starting this turn. Submit the retained draft when its turn is ready.");
            notify(); return;
        }
        Object params{{"threadId", generic_thread}, {"input", QJsonArray{Object{{"type", "text"}, {"text", text}}}}};
        const auto row = public_row("user", text, {}, "pending");
        params["clientUserMessageId"] = row.value("id");
        if (steering) params["expectedTurnId"] = generic_turn;
        else {
            params["model"] = model;
            QString effectiveEffort = effort;
            if (effectiveEffort.isEmpty()) {
                for (const auto& value : generic_native.value("models").toArray()) {
                    const auto entry = value.toObject();
                    if (entry.value("id") == model) effectiveEffort = entry.value("default_effort").toString();
                }
                if (effectiveEffort.isEmpty()) throw std::runtime_error("The selected model has no supported default effort");
            }
            params["effort"] = effectiveEffort; // Explicit actual catalog default resets the sticky prior override.
            params["sandboxPolicy"] = Object{{"type", "workspaceWrite"}, {"writableRoots", QJsonArray{generic_workspace}},
                {"networkAccess", false}, {"excludeSlashTmp", true}, {"excludeTmpdirEnvVar", true}};
            params["approvalPolicy"] = "on-request"; params["approvalsReviewer"] = "user";
            params["additionalContext"] = Object{{"edi", Object{{"kind", "application"}, {"value", context}}}};
            agent->beginOperation(Limits::inference_total_ms, Limits::inference_idle_ms);
        }
        const auto rpc = agent->request(steering ? "turn/steer" : "turn/start", params, [this, row, steering](const QString& id) {
            try {
                if (steering) generic_rpc_turns.insert(id, generic_turn);
                generic_rpc_rows.insert(id, row.value("id").toString());
                if (!generic_present(row)) { generic_rpc_rows.remove(id); generic_rpc_turns.remove(id); return false; }
                generic_writing_input = true; generic_busy = true; return true;
            } catch (...) { generic_rpc_rows.remove(id); generic_rpc_turns.remove(id); return false; }
        });
        if (rpc.isEmpty()) { if (!steering && !generic_writing_input) agent->settleOperation(); throw std::runtime_error("Agent input could not be admitted"); }
        error.clear(); notify();
    }
#endif

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
        return generic_mode ? generic_native : connection ? object(connection->state()) : Object{};
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
        if (agent) agent->retire();
#endif
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
        else { generic_mode = true; generic_initialize(); }
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
        const Object next_native = generic_mode ? generic_native : object(connection->state());
#else
        const Object next_native{{"status", "disconnected"}};
#endif
        core = next_core; native = next_native;
        QJsonArray choices;
        for (const auto& value : native.value("models").toArray()) {
            const auto item = value.toObject(); choices.append(Object{{"id", item.value("id")},
                {"displayName", item.value("display_name")}, {"efforts", item.value("efforts")}, {"available", item.value("available").toBool()}});
        }
#ifndef __EMSCRIPTEN__
        if (!generic_mode) sync_skills();
#else
        sync_skills();
#endif
        models.assign(choices);
        select_from_catalog(choices);
        if (core.value("pending_plan_id").toString().isEmpty()) plan = {};
        #ifndef __EMSCRIPTEN__
        if (!generic_mode)
#endif
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
#ifndef __EMSCRIPTEN__
        if (generic_mode) {
            generic_revoke_workspace(); generic_input_paths.clear(); generic_input_cache.reset();
            generic_held_row.reset(); generic_blocked = false;
        }
#endif
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
                if (controller && !own_edit) {
#ifndef __EMSCRIPTEN__
                    if (generic_mode) { generic_revoke_workspace(); consented_context.clear(); }
#endif
                    retire_file_selection(); controller->notify_changed(); plan = {}; question = {}; sync();
                }
            });
            QObject::connect(project->fit(), &FitViewModel::finished, &owner, [this] {
#ifndef __EMSCRIPTEN__
                if (generic_mode) { generic_revoke_workspace(); consented_context.clear(); }
#endif
                retire_file_selection(); if (controller) controller->notify_changed(); sync();
            });
        }
#ifndef __EMSCRIPTEN__
        const auto state = generic_mode ? generic_native : object(connection->state());
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
QString AssistantViewModel::state() const {
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) return state_->generic_connecting ? "connecting" : state_->generic_busy ? "agent_active" : state_->generic_blocked ? "interrupted" : connected() ? "idle" : "disconnected";
#endif
    return state_->auth_pending ? QString("connecting") : state_->core.value("state").toString();
}
bool AssistantViewModel::connected() const {
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) return state_->generic_authenticated && !state_->generic_retiring && state_->native.value("status") == "ready";
#endif
    return state_->native.value("status") == "ready";
}
QString AssistantViewModel::connectionLabel() const { return state() == "connecting" ? tr("Connecting to ChatGPT…") : connected() ? state_->native.value("label").toString() : tr("Connect ChatGPT"); }
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
bool AssistantViewModel::canCancel() const {
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) return state_->generic_retiring || state_->generic_connecting || state_->generic_busy || state_->file_selection.has_value() || state_->file_staging;
#endif
    return state_->auth_pending || state_->file_selection.has_value() || state_->file_staging || state_->core.value("can_cancel").toBool(); }
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
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) return; // Automatic runtime discovery, optional catalog inspection only.
#endif
    try {
        const auto reply = state_->command({{"type", "select_skill"}, {"id", id}});
        if (reply.ok) { state_->consented_context.clear(); state_->sync(); }
    } catch (...) { state_->error = state_->storage_error; state_->notify(); }
}
void AssistantViewModel::setProject(ProjectViewModel* project) { state_->bind(project); }
void AssistantViewModel::send(const QString& text) {
    if (text.trimmed().isEmpty()) return;
    try {
#ifndef __EMSCRIPTEN__
        if (state_->generic_mode) {
            state_->generic_writing_input = false;
            if (static_cast<quint64>(text.size()) > State::Limits::message_bytes || static_cast<quint64>(text.toUtf8().size()) > State::Limits::message_bytes)
                throw std::length_error("Agent message exceeds limit");
            if (contextConsentRequired()) { state_->error = tr("Approve the current outgoing context before sending."); state_->notify(); return; }
            if (state_->file_selection || state_->file_staging) { state_->error = tr("Finish file selection first."); state_->notify(); return; }
            state_->generic_send(text); state_->generic_writing_input = false; return;
        }
#endif
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
#ifndef __EMSCRIPTEN__
        if (state_->generic_mode) {
            if (state_->generic_writing_input || state_->generic_blocked) state_->generic_fail(tr("Agent input delivery is uncertain. Inspect the retained message before retrying."));
            else { state_->error = tr("The new input was not admitted. The existing operation and draft are preserved."); try { state_->notify(); } catch (...) {} }
            state_->generic_writing_input = false; return;
        }
#endif
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
void AssistantViewModel::answerQuestion(const QString& id, const QString& answer) {
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) {
        try {
            if (id != state_->generic_question_public_id || state_->generic_question_rpc.isUndefined() || !state_->generic_authenticated || state_->generic_retiring || !state_->generic_busy || state_->generic_turn.isEmpty() ||
                state_->generic_question_thread != state_->generic_thread || state_->generic_question_turn != state_->generic_turn || !state_->generic_items.contains(state_->generic_question_item) || state_->generic_final_items.contains(state_->generic_question_item) ||
                answer.toUtf8().size() > static_cast<qsizetype>(State::Limits::question_answer_bytes)) return;
            const auto rpc = state_->generic_question_rpc;
            const auto key = state_->generic_question_id;
            state_->generic_retire_question();
            if (!state_->agent->answer(rpc, {{"answers", Object{{key, Object{{"answers", QJsonArray{answer}}}}}}}))
                state_->generic_fail(tr("The question answer could not be delivered."));
            state_->notify();
        } catch (...) { state_->generic_fail(tr("The question answer could not be retained.")); }
        return;
    }
#endif
    state_->command({{"type", "answer"}, {"question_id", id}, {"answer", answer}});
}
void AssistantViewModel::cancel() {
    state_->retire_file_selection();
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) {
        try {
            if (state_->generic_retiring) { state_->generic_fail(tr("Agent sign-out was interrupted; account state must be checked before reconnecting.")); }
            else if (state_->generic_busy && !state_->generic_turn.isEmpty()) {
                state_->agent->beginOperation(State::Limits::revoke_ms, 0);
                state_->generic_request("turn/interrupt", {{"threadId", state_->generic_thread}, {"turnId", state_->generic_turn}});
            } else if (state_->generic_connecting || state_->generic_busy) state_->generic_fail(tr("Agent sign-in or input was interrupted."));
            state_->notify();
        } catch (...) { state_->generic_fail(tr("The agent interruption could not be delivered.")); }
        return;
    }
#endif
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
    if (state_->generic_mode) {
        try { state_->generic_sign_in(); }
        catch (const std::exception&) { state_->generic_fail(tr("The official agent could not be prepared. Check its executable, bundled skills and project context.")); }
        catch (...) { state_->generic_fail(tr("The official agent could not be prepared.")); }
        return;
    }
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
#ifndef __EMSCRIPTEN__
    if (state_->generic_mode) {
        state_->generic_authenticated = false; state_->generic_retiring = true;
        state_->generic_busy = false; state_->generic_connecting = false;
        state_->generic_retire_question(); state_->generic_interrupt_rows();
        state_->generic_rpc_rows.clear(); state_->generic_rpc_turns.clear(); state_->generic_turn.clear();
        try { state_->agent->beginOperation(State::Limits::revoke_ms, 0); state_->generic_request("account/logout"); }
        catch (...) { state_->generic_revoke_workspace(); }
        state_->sync(); state_->notify(); return;
    }
#endif
    state_->queued_request.clear(); state_->auth_pending = false;
#ifndef __EMSCRIPTEN__
    state_->connection->sign_out();
#endif
    state_->controller->cancel(); state_->sync(); state_->notify();
}
void AssistantViewModel::clearHistory() {
    try {
#ifndef __EMSCRIPTEN__
        if (state_->auth_pending && state_->connection) state_->connection->sign_out();
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
        if (state_->auth_pending || (state_->generic_mode && (state_->generic_busy || state_->generic_connecting)) || (state_->project && state_->project->fit()->running()))
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
#ifndef __EMSCRIPTEN__
            auto generic_stage = state_->generic_mode ? state_->generic_stage_files(files) : nullptr;
#endif
            if (!state_->file_current(scope)) throw std::runtime_error("The selected-file owner changed");
            auto result = state_->controller->update_selected_files(scope.next_collection_id.toStdString(), scope.selection_generation, std::move(files), {});
            admitted = result.ok;
            if (admitted) {
#ifndef __EMSCRIPTEN__
                if (generic_stage) {
                    state_->generic_revoke_workspace();
                    state_->generic_input_paths.swap(generic_stage->paths);
                    generic_stage->fresh.clear();
                    state_->native = state_->generic_native;
                }
#endif
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
#ifndef __EMSCRIPTEN__
            (state_->generic_mode && (state_->generic_busy || state_->generic_connecting)) ||
#endif
            (state_->project && state_->project->fit()->running())) throw std::runtime_error("Finish the active operation before changing files");
        if (!state_->flush_selected_rows()) { state_->notify(); return false; }
        const auto current = state_->file_context();
#ifndef __EMSCRIPTEN__
        auto generic_paths = state_->generic_input_paths;
        const auto generic_removed = generic_paths.take(id);
#endif
        auto result = state_->controller->update_selected_files(current.value("collection_id").toString().toStdString(), State::file_generation(current), {}, {id.toStdString()});
        admitted = result.ok;
        if (admitted) {
#ifndef __EMSCRIPTEN__
            if (state_->generic_mode) {
                state_->generic_revoke_workspace(); state_->generic_input_paths.swap(generic_paths);
                if (!generic_removed.isEmpty()) QFile::remove(generic_removed);
                state_->native = state_->generic_native;
            }
#endif
            state_->selected_reply = std::move(result.value); state_->selected_rows_dirty = true;
            state_->consented_context.clear(); state_->error.clear(); (void)state_->flush_selected_rows();
        } else state_->error = State::bounded_error(object(result.value).value("message").toString());
        state_->notify();
    } catch (...) { state_->error = tr("Selected file could not be removed. Inspect the retained file list before retrying."); try { state_->notify(); } catch (...) {} }
    return admitted;
}

}  // namespace edi_app
