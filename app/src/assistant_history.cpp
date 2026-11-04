// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_history.hpp"
#include "background.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QMetaObject>
#include <QPointer>
#include <QSaveFile>
#include <QStandardPaths>
#include <algorithm>
#include <QUuid>
#include <atomic>
#include <limits>
#include <map>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <utility>

namespace edi_app {
QJsonArray merge_assistant_history(const QJsonArray& initial,const QJsonArray& current) {
    QJsonArray result;QHash<QString,qsizetype> positions;
    const auto append=[&](const QJsonArray& rows) {
        for(const auto& value:rows) {const auto id=value.toObject().value("id").toString();
            const auto found=positions.constFind(id);
            if(!id.isEmpty() && found!=positions.cend())result[found.value()]=value;
            else {if(!id.isEmpty())positions.insert(id,result.size());result.append(value);}
        }
    };
    append(initial);append(current);return result;
}
struct AssistantHistoryArchive::Control {
    struct Snapshot { QJsonArray rows; std::uint64_t revision = 0; bool includes_initial = false; };
    static std::mutex owners_mutex;
    static std::map<QString,std::shared_ptr<Control>> owners;
    mutable std::mutex mutex;
    QString requested, path;
    QJsonArray initial;
    Snapshot latest;
    std::optional<Snapshot> pending;
    std::uint64_t owner = 0, durable = 0, clear = 0, failure_revision = 0;
    bool loaded = false, running = false, recovered = false;
    const char* failure_stage = nullptr;
    Notice notice;
    QPointer<QObject> receiver,clear_receiver;
    Notice clear_notice;
    std::uint64_t clear_notice_revision=0;
    View view() const {
        return {path,clear?QJsonArray{}:initial,latest.rows,latest.revision,durable,clear,failure_revision,
            loaded,latest.includes_initial,latest.revision>durable,recovered,failure_stage,running};
    }
};
std::mutex AssistantHistoryArchive::Control::owners_mutex;
std::map<QString,std::shared_ptr<AssistantHistoryArchive::Control>> AssistantHistoryArchive::Control::owners;
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
AssistantHistoryArchive::AssistantHistoryArchive(QObject* receiver,QString requested,Notice notice,bool provisional)
    : pending_receiver_(receiver),pending_notice_(std::move(notice)) {
    // A replacement VM reuses the same file owner, including its accepted final
    // snapshot. An older worker can never land after a newer archive revision.
    {
        std::lock_guard lock(Control::owners_mutex);
        auto& cell=Control::owners[requested];
        if(!cell) {cell=std::make_shared<Control>();cell->requested=requested;cell->path=requested;}
        control_=cell;
    }
    bool start=false;
    {
        std::lock_guard lock(control_->mutex);
        if(!control_->running && (!control_->loaded || control_->pending || control_->latest.revision>control_->durable)) {
            if(!control_->pending && control_->latest.revision>control_->durable)control_->pending=control_->latest;
            control_->running=true;start=true;
        }
    }
    if(start)launch(control_);
    if(!provisional)activate();
}
AssistantHistoryArchive::ClearBarrier::~ClearBarrier() {
    try {if(state_) {std::lock_guard lock(state_->mutex);
        if(state_->clear_notice_revision==revision_) {state_->clear_notice={};state_->clear_receiver.clear();}
    }}catch(...) {}
}
AssistantHistoryArchive::ClearBarrier& AssistantHistoryArchive::ClearBarrier::operator=(ClearBarrier&& other) noexcept {
    if(this==&other)return *this;
    try {if(state_) {std::lock_guard lock(state_->mutex);
        if(state_->clear_notice_revision==revision_) {state_->clear_notice={};state_->clear_receiver.clear();}
    }}catch(...) {}
    state_=std::move(other.state_);revision_=std::exchange(other.revision_,0);return *this;
}
AssistantHistoryArchive::View AssistantHistoryArchive::ClearBarrier::view() const {
    if(!state_)return {};
    std::lock_guard lock(state_->mutex);return state_->view();
}
bool AssistantHistoryArchive::ClearBarrier::retry() noexcept {
    try {
        if(!state_ || !revision_)return false;
        bool start=false;
        {std::lock_guard lock(state_->mutex);
            if(state_->durable>=revision_)return true;
            if(!state_->running) {state_->pending=state_->latest;state_->running=true;start=true;}
        }
        if(start)AssistantHistoryArchive::launch(state_);
        return true;
    }catch(...) {return false;}
}
std::vector<AssistantHistoryArchive::ClearBarrier> AssistantHistoryArchive::clearCaches(QObject* receiver,Notice notice) {
    const auto root=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant";
    QStringList paths{root+"/history.json"};
    const auto recovery=[](const QString& name) {return name.startsWith("history-recovered-") && !QUuid(name.mid(18)).isNull();};
    for(const auto& folder:{root,root+"/history"})for(const auto& file:QDir(folder).entryInfoList({QStringLiteral("*.json")},QDir::Files|QDir::NoSymLinks)) {
        const auto base=file.completeBaseName();bool generated=base.size()==64;
        if(generated)for(const auto ch:base)if(!((ch>='0' && ch<='9') || (ch>='a' && ch<='f'))){generated=false;break;}
        if(generated || recovery(base) || (base.startsWith("draft-") && !QUuid(base.mid(6)).isNull()))paths.append(file.absoluteFilePath());
    }
    std::vector<std::shared_ptr<Control>> states;
    {std::lock_guard lock(Control::owners_mutex);
        for(const auto& [path,state]:Control::owners)states.push_back(state);
    }
    // Reuse an actual requested/current-path owner, including its accepted-but-unwritten snapshot.
    for(const auto& path:paths) {
        bool known=false;
        for(const auto& state:states) {std::lock_guard lock(state->mutex);if(state->requested==path || state->path==path){known=true;break;}}
        if(known)continue;
        AssistantHistoryArchive provisional(receiver,path,{},true);
        if(std::none_of(states.begin(),states.end(),[&](const auto& state){return state==provisional.control_;}))states.push_back(provisional.control_);
    }
    std::vector<ClearBarrier> barriers;barriers.reserve(states.size());
    for(const auto& state:states) {
        std::lock_guard lock(state->mutex);
        if(state->latest.revision==std::numeric_limits<std::uint64_t>::max())throw std::overflow_error("History revision exhausted");
        barriers.push_back(ClearBarrier(state,state->latest.revision+1));
    }
    for(auto& barrier:barriers) {
        const auto& state=barrier.state_;bool start=false;
        {std::lock_guard lock(state->mutex);
            Control::Snapshot empty{{},barrier.revision_,true};state->pending=empty;state->latest=std::move(empty);state->clear=barrier.revision_;
            state->clear_receiver=receiver;state->clear_notice=notice;state->clear_notice_revision=barrier.revision_;
            if(!state->running){state->running=true;start=true;}
        }
        if(start)launch(state);
    }
    return barriers;
}
void AssistantHistoryArchive::activate() {
    if(owner_)return; // A committed predecessor cannot reclaim a newer owner's token.
    const auto state=control_;
    if(!state)throw std::logic_error("The history candidate has closed");
    Notice retired_notice;
    {
        std::lock_guard lock(state->mutex);
        if(state->owner==std::numeric_limits<std::uint64_t>::max())throw std::overflow_error("History owner identity exhausted");
        // All fallible preparation precedes this callback-free token transfer.
        retired_notice=std::move(state->notice);
        state->receiver=pending_receiver_;state->notice=std::move(pending_notice_);
        owner_=++state->owner;
    }
    notify(state);
}
AssistantHistoryArchive::~AssistantHistoryArchive(){closeOwner();}
void AssistantHistoryArchive::closeOwner() noexcept {
    try {if(control_) {std::lock_guard lock(control_->mutex);
        if(owner_ && control_->owner==owner_) {control_->receiver.clear();control_->notice={};}}}catch(...){}
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
            if(!owner_ || state->owner!=owner_ || state->latest.revision==std::numeric_limits<std::uint64_t>::max())return false;
            Control::Snapshot next{std::move(rows),state->latest.revision+1,includesInitial || logicalClear || state->clear!=0};
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
        QPointer<QObject> receiver,clear_receiver;Notice notice,clear_notice;std::uint64_t owner=0,clearRevision=0;View view;
        {std::lock_guard lock(state->mutex);receiver=state->receiver;notice=state->notice;owner=state->owner;
            clear_receiver=state->clear_receiver;clear_notice=state->clear_notice;clearRevision=state->clear_notice_revision;view=state->view();}
        auto* app=QCoreApplication::instance();if(!app)return;
        if(notice)QMetaObject::invokeMethod(app,[state,receiver,notice=std::move(notice),owner,view] {
            if(!receiver)return;
            {std::lock_guard lock(state->mutex);if(state->owner!=owner || !state->notice || state->receiver!=receiver)return;}
            try {notice(view);}catch(...) {}
        },Qt::QueuedConnection);
        if(clear_notice)QMetaObject::invokeMethod(app,[state,clear_receiver,notice=std::move(clear_notice),clearRevision,view] {
            if(!clear_receiver)return;
            {std::lock_guard lock(state->mutex);if(state->clear_notice_revision!=clearRevision || state->clear_receiver!=clear_receiver)return;}
            try {notice(view);}catch(...) {}
        },Qt::QueuedConnection);
    }catch(...) {} // Actual file outcome remains available to each original revision owner.
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
                    if(valid)initial=merge_assistant_history({},document.array());
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
            if(!snapshot.includes_initial)rows=merge_assistant_history(initial,rows);
            else rows=merge_assistant_history({},rows);
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
