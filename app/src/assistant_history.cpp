// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_history.hpp"
#include "background.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QMetaObject>
#include <QPointer>
#include <QSaveFile>
#include <QUuid>
#include <atomic>
#include <limits>
#include <map>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <utility>

namespace edi_app {
struct AssistantHistoryArchive::Control {
    struct Snapshot { QJsonArray rows; std::uint64_t revision = 0; bool includes_initial = false; };
    mutable std::mutex mutex;
    QString requested, path;
    QJsonArray initial;
    Snapshot latest;
    std::optional<Snapshot> pending;
    std::uint64_t owner = 0, durable = 0, clear = 0, failure_revision = 0;
    bool loaded = false, running = false, recovered = false;
    const char* failure_stage = nullptr;
    Notice notice;
    QPointer<QObject> receiver;
    View view() const {
        return {path,initial,latest.rows,latest.revision,durable,clear,failure_revision,
            loaded,latest.includes_initial,latest.revision>durable,recovered,failure_stage};
    }
};
namespace {
const char* write_history_file(const QString& path,const QJsonArray& rows) {
    if(!QDir().mkpath(QFileInfo(path).absolutePath()))return "directory";
    QSaveFile file(path);
    file.setDirectWriteFallback(false); // Preserve the original atomic replacement.
    if(!file.open(QIODevice::WriteOnly))return "open";
    if(!file.setPermissions(QFile::ReadOwner|QFile::WriteOwner))return "permissions";
    if(file.write("[")!=1)return "write";
    bool comma=false;
    for(const auto& value:rows) {
        if(comma && file.write(",")!=1)return "write";
        const auto row=QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact);
        if(file.write(row)!=row.size())return "write";
        comma=true;
    }
    if(file.write("]")!=1)return "write";
    return file.commit()?nullptr:"commit";
}
}
AssistantHistoryArchive::AssistantHistoryArchive(QObject* receiver,QString requested,Notice notice) {
    // A replacement VM reuses the same file owner, including its accepted final
    // snapshot. An older worker can never land after a newer archive revision.
    static std::mutex ownersMutex;
    static std::map<QString,std::shared_ptr<Control>> owners;
    {
        std::lock_guard lock(ownersMutex);
        auto& cell=owners[requested];
        if(!cell) {cell=std::make_shared<Control>();cell->requested=requested;cell->path=requested;}
        control_=cell;
    }
    bool start=false;
    {
        std::lock_guard lock(control_->mutex);
        if(control_->owner==std::numeric_limits<std::uint64_t>::max())throw std::overflow_error("History owner identity exhausted");
        owner_=++control_->owner;
        control_->receiver=receiver;control_->notice=std::move(notice);
        if(!control_->running && (!control_->loaded || control_->pending || control_->latest.revision>control_->durable)) {
            if(!control_->pending && control_->latest.revision>control_->durable)control_->pending=control_->latest;
            control_->running=true;start=true;
        }
    }
    if(start)launch(control_);
    else notify(control_);
}
AssistantHistoryArchive::~AssistantHistoryArchive(){closeOwner();}
void AssistantHistoryArchive::closeOwner() noexcept {
    try {if(control_) {std::lock_guard lock(control_->mutex);
        if(control_->owner==owner_) {control_->receiver.clear();control_->notice={};}}}catch(...){}
    // Accepted immutable snapshots remain owned/drained independently of Qt.
    control_.reset();
}
AssistantHistoryArchive::View AssistantHistoryArchive::view() const {
    if(!control_)return {};
    std::lock_guard lock(control_->mutex);return control_->view();
}
bool AssistantHistoryArchive::retain(QJsonArray rows,bool includesInitial,bool logicalClear) noexcept {
    try {
        const auto state=control_;if(!state)return false;
        bool start=false;
        {
            std::lock_guard lock(state->mutex);
            if(state->owner!=owner_ || state->latest.revision==std::numeric_limits<std::uint64_t>::max())return false;
            Control::Snapshot next{std::move(rows),state->latest.revision+1,includesInitial || logicalClear};
            state->pending=next;state->latest=std::move(next);
            if(logicalClear)state->clear=state->latest.revision;
            if(!state->running) {state->running=true;start=true;}
        }
        if(start)launch(state);
        return true;
    }catch(...) {return false;} // No provider/native cancellation or lost GUI rows.
}
void AssistantHistoryArchive::launch(const std::shared_ptr<Control>& state) noexcept {
    struct Lease {
        std::shared_ptr<Control> state;
        std::atomic<bool> started{false};
        ~Lease() {
            if(started.load(std::memory_order_acquire))return;
            try {{std::lock_guard lock(state->mutex);
                state->running=false;state->failure_stage="launch";state->failure_revision=state->latest.revision;
            } AssistantHistoryArchive::notify(state);}catch(...){}
        }
    };
    std::shared_ptr<Lease> lease;
    try {
        lease=std::make_shared<Lease>();lease->state=state;
        run_in_background([state,lease] {
            lease->started.store(true,std::memory_order_release);drain(state);
        });
    }catch(...) {
        // A surviving worker capture, not a discarded future, proves admission.
        // Last unstarted lease destruction retains the pending snapshot/failure.
        if(!lease)try {std::lock_guard lock(state->mutex);state->running=false;
            state->failure_stage="launch";state->failure_revision=state->latest.revision;
        }catch(...){}
    }
}
void AssistantHistoryArchive::notify(const std::shared_ptr<Control>& state) noexcept {
    try {
        QPointer<QObject> receiver;Notice notice;std::uint64_t owner=0;View view;
        {std::lock_guard lock(state->mutex);receiver=state->receiver;notice=state->notice;owner=state->owner;view=state->view();}
        if(!notice)return;
        if(auto* app=QCoreApplication::instance())QMetaObject::invokeMethod(app,[state,receiver,notice=std::move(notice),owner,view=std::move(view)] {
            if(!receiver)return;
            {std::lock_guard lock(state->mutex);if(state->owner!=owner || !state->notice || state->receiver!=receiver)return;}
            try {notice(view);}catch(...) {} // Metadata only; never republishes history.
        },Qt::QueuedConnection);
    }catch(...) {} // Actual file outcome remains available to the archive owner.
}
void AssistantHistoryArchive::drain(const std::shared_ptr<Control>& state) noexcept {
    try {
        bool load=false;QString path;
        {std::lock_guard lock(state->mutex);load=!state->loaded;path=state->path;}
        if(load) {
            QJsonArray initial;bool recovered=false;
            if(QFileInfo::exists(path)) {
                QFile saved(path);QJsonParseError parsing;
                bool valid=saved.open(QIODevice::ReadOnly);
                if(valid) {
                    const auto document=QJsonDocument::fromJson(saved.readAll(),&parsing);
                    valid=saved.error()==QFileDevice::NoError && parsing.error==QJsonParseError::NoError && document.isArray();
                    if(valid)for(const auto& row:document.array())
                        if(!row.isObject() || !row.toObject().value("text").isString() || !row.toObject().value("kind").isString()){valid=false;break;}
                    if(valid)initial=document.array();
                }
                if(!valid) {
                    path=QFileInfo(path).absolutePath()+"/history-recovered-"+QUuid::createUuid().toString(QUuid::WithoutBraces)+".json";
                    recovered=true; // The original unreadable file is untouched.
                }
            }
            {std::lock_guard lock(state->mutex);
                state->path=path;state->initial=std::move(initial);state->loaded=true;state->recovered=recovered;
                if(!state->latest.revision) {state->latest.rows=state->initial;state->latest.includes_initial=true;}}
            notify(state);
        }
        for(;;) {
            Control::Snapshot snapshot;QJsonArray initial;
            {std::lock_guard lock(state->mutex);
                if(!state->pending) {state->running=false;break;}
                snapshot=std::move(*state->pending);state->pending.reset();path=state->path;initial=state->initial;}
            QJsonArray rows=std::move(snapshot.rows);
            if(!snapshot.includes_initial) {auto merged=std::move(initial);for(const auto& row:rows)merged.append(row);rows=std::move(merged);}
            const char* failure=nullptr;
            try {failure=write_history_file(path,rows);}catch(...) {failure="encode_or_write";}
            {std::lock_guard lock(state->mutex);
                if(failure) {state->failure_stage=failure;state->failure_revision=snapshot.revision;}
                else {
                    state->durable=snapshot.revision;
                    if(state->failure_revision<=state->durable){state->failure_stage=nullptr;state->failure_revision=0;}
                }}
            notify(state);
            // Drain the newest accepted full snapshot even after receiver death.
        }
        notify(state);
    }catch(...) {
        try {std::lock_guard lock(state->mutex);state->running=false;state->failure_stage="load_or_worker";state->failure_revision=state->latest.revision;}catch(...){}
        notify(state);
    }
}
} // namespace edi_app
