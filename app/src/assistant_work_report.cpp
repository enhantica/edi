// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_work_report.hpp"
#include "assistant_view_model.hpp"
#include "assistant_file_primitives.hpp"
#include "assistant_result.hpp"
#include "background.hpp"
#include "codex_agent.hpp"
#include "edi/assistant_limits.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QPointer>
#include <QThread>
#include <QtCore/qarraydata.h>
#include <cstddef>
#include <initializer_list>
#include <string>
#include <string_view>
#include <QScopeGuard>
#include <QStandardPaths>
#include <QUuid>
#include <algorithm>
#include <array>
#include <optional>
#include <atomic>
#include <limits>
#include <mutex>
#include <utility>
#include <stdexcept>
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
#endif

namespace edi_app {
namespace {
using L=edi::assistant::Limits;
using Object=QJsonObject;
QString decimal(quint64 n) { return QString::number(n); }
Object observed(const QJsonValue& v) { return work_report_observed(v); }
Object missing(const char* reason="not_observed") { return work_report_missing(reason); }
Object receiptBase(const QString& id,const QString& scope,quint64 revision,const char* disposition) {
    return {{"id",id.isEmpty()?QJsonValue(QJsonValue::Null):QJsonValue(id)},
        {"phase","terminal"},{"disposition",QLatin1StringView(disposition)},
        {"scope_id",scope.isEmpty()?missing("not_present"):observed(scope)},
        {"snapshot_revision",observed(decimal(revision))},{"scope_retired",false},
        {"complete_evidence",false},{"coverage",work_report_receipt_coverage()},
        {"artifact",missing("not_present")},{"error_code",missing("not_present")},{"recovery_required",false}};
}
struct FileResult { Object artifact; const char* disposition="failed_precommit"; bool recovery=false; };
// One existing writer's completion metadata, not another request or task queue.
struct WriterCompletion {
    using Fallback=std::pair<Object,QVariantMap>;
    static constexpr std::size_t publicationCases=5,cases=2*publicationCases;
    enum Delivery { Pending,Queued,Delivering,Settled,Unavailable };
    const QString scope;
    const std::array<Fallback,cases> fallback;
    std::atomic<unsigned> outcome{0};
    std::atomic<Delivery> delivery{Pending};
    std::atomic<bool> consumed{false};
    WriterCompletion(QString originalScope,std::array<Fallback,cases> receipts)
        :scope(std::move(originalScope)),fallback(std::move(receipts)) {}

    void publication(const FileResult& result) noexcept {
        const unsigned selected=std::string_view(result.disposition)=="saved" || std::string_view(result.disposition)=="committed_unverified"?3:
            std::string_view(result.disposition)=="publication_indeterminate"?4:
            std::string_view(result.disposition)=="writer_busy_or_recovery_required"?2:result.recovery?1:0;
        outcome.store(selected,std::memory_order_release);
    }
    void unavailable() noexcept {
        auto expected=Pending;
        (void)delivery.compare_exchange_strong(expected,Unavailable,std::memory_order_acq_rel);
        // Successful original Queued/Delivering/Settled work is never consumed
        // as an unavailable path, even during old/new owner reentry.
    }
    bool beginDelivery() noexcept {
        auto observed=delivery.load(std::memory_order_acquire);
        while(observed==Pending || observed==Queued)
            if(delivery.compare_exchange_weak(observed,Delivering,std::memory_order_acq_rel))return true;
        return false;
    }
};
struct WriterWorkerLease {
    std::shared_ptr<WriterCompletion> completion;
    explicit WriterWorkerLease(std::shared_ptr<WriterCompletion> cell):completion(std::move(cell)) {}
    ~WriterWorkerLease() {
        // Last actual original worker capture is gone. If launch never queued
        // a completion, no future write remains hidden behind a failed launch.
        auto expected=WriterCompletion::Pending;
        (void)completion->delivery.compare_exchange_strong(expected,WriterCompletion::Unavailable,std::memory_order_acq_rel);
    }
};
std::array<WriterCompletion::Fallback,WriterCompletion::cases> completionFallbacks(const Object& receipt) {
    std::array<WriterCompletion::Fallback,WriterCompletion::cases> result;
    constexpr const char* dispositions[]={"failed_precommit","failed_precommit","writer_busy_or_recovery_required","committed_unverified","publication_indeterminate"};
    for(std::size_t i=0;i<result.size();++i) {
        auto terminal=receipt;terminal["phase"]="terminal";terminal["disposition"]=QLatin1StringView(dispositions[i%WriterCompletion::publicationCases]);
        terminal["scope_retired"]=i>=WriterCompletion::publicationCases;
        terminal["recovery_required"]=i%WriterCompletion::publicationCases!=0;terminal["artifact"]=missing("not_observed");
        terminal["error_code"]=observed("completion_dispatch_unavailable");
        auto covered=terminal.value("coverage").toObject();covered["reason"]="storage";terminal["coverage"]=covered;
        auto variant=terminal.toVariantMap();result[i]={std::move(terminal),std::move(variant)};
    }return result;
}

#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
using namespace assistant_files;
void checkDirectory(int fd,mode_t forbidden=0077) {
    struct stat s{};
    if(::fstat(fd,&s) || !S_ISDIR(s.st_mode) || s.st_uid!=::getuid() || (s.st_mode&forbidden))
        throw std::runtime_error("Work report directory ownership");
}
Fd childDirectory(int parent,const char* name,mode_t forbidden=0077) {
    if(::mkdirat(parent,name,0700) && errno!=EEXIST)throw std::runtime_error("Work report directory");
    Fd fd(::openat(parent,name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));checkDirectory(fd.n,forbidden);return fd;
}
void privateFile(int fd) {
    struct stat s{};
    if(::fstat(fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=::getuid() || s.st_nlink!=1 || (s.st_mode&0077) || s.st_size<0 || static_cast<quint64>(s.st_size)>L::record_bytes)
        throw std::runtime_error("Work report file ownership");
}
QByteArray fileHash(int fd,quint64 expected) {
    privateFile(fd);const Identity identity(fd);
    if(::lseek(fd,0,SEEK_SET)<0)throw std::runtime_error("Work report readback");
    QCryptographicHash hash(QCryptographicHash::Sha256);
    std::array<char,edi::assistant::SelectedFileLimits::read_bytes> block{};quint64 count=0;
    for(;;) {
        auto n=::read(fd,block.data(),block.size());
        if(n<0){if(errno==EINTR)continue;throw std::runtime_error("Work report readback");}
        if(!n)break;
        if(static_cast<quint64>(n)>expected-count)throw std::runtime_error("Work report size changed");
        count+=static_cast<quint64>(n);hash.addData(QByteArrayView(block.data(),n));
    }
    if(count!=expected || !identity.unchanged(fd))throw std::runtime_error("Work report changed");
    return hash.result().toHex();
}
QString identityToken(const Identity& id) {
    return QString::number(static_cast<qulonglong>(id.value.st_dev))+u':'+QString::number(static_cast<qulonglong>(id.value.st_ino));
}
FileResult publishFile(const QString& projectRoot,const QByteArray& bytes,const QByteArray& digest) {
    FileResult result;
    bool locked=false,created=false,changed=false,indeterminate=false,verified=false,oldPresent=false;
    Fd root,folder,lock,candidate,oldFile;
    std::optional<Identity> rootId,folderId,lockId,candidateId,oldId;
    try {
        root=directory(projectRoot);checkDirectory(root.n,0);rootId.emplace(root.n);
        folder=childDirectory(root.n,"reports",0);folderId.emplace(folder.n);
        if(::mkdirat(folder.n,".writer",0700)) {
            result.disposition="writer_busy_or_recovery_required";result.recovery=true;return result;
        }
        locked=true;lock=Fd(::openat(folder.n,".writer",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));checkDirectory(lock.n);lockId.emplace(lock.n);
        candidate=Fd(::openat(lock.n,"candidate.json",O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));created=true;candidateId.emplace(candidate.n);
        struct stat existing{};
        if(!::fstatat(folder.n,"work-report.json",&existing,AT_SYMLINK_NOFOLLOW)) {
            oldFile=Fd(::openat(folder.n,"work-report.json",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC));privateFile(oldFile.n);oldId.emplace(oldFile.n);oldPresent=true;
        } else if(errno!=ENOENT)throw std::runtime_error("Work report destination unavailable");
        if(work_report_test_fault(WorkReportFaultPoint::StageWrite))throw std::runtime_error("Work report test write fault");
        std::size_t off=0;
        while(off<static_cast<std::size_t>(bytes.size())) {
            auto n=::write(candidate.n,bytes.constData()+off,static_cast<std::size_t>(bytes.size())-off);
            if(n<0){if(errno==EINTR)continue;throw std::runtime_error("Work report write");}
            if(!n)throw std::runtime_error("Work report short write");off+=static_cast<std::size_t>(n);
        }
        if(::fsync(candidate.n) || fileHash(candidate.n,bytes.size())!=digest)throw std::runtime_error("Work report candidate verification");
        auto current=below(folder.n,".writer",true);
        if(!folderId->object(folder.n) || !lockId->object(current.n))throw std::runtime_error("Work report lock changed");
        auto named=below(lock.n,"candidate.json");
        if(!candidateId->object(named.n))throw std::runtime_error("Work report candidate changed");
        if(oldPresent){auto prior=below(folder.n,"work-report.json");if(!oldId->unchanged(prior.n))throw std::runtime_error("Work report prior changed");}
        const auto currentNamespace=[&] {
            auto currentRoot=directory(projectRoot);auto currentFolder=below(currentRoot.n,"reports",true);
            if(!rootId->object(currentRoot.n) || !folderId->object(currentFolder.n))
                throw std::runtime_error("Work report namespace changed");
        };
        currentNamespace();
        if(work_report_test_fault(WorkReportFaultPoint::BeforeAtomicPublish))throw std::runtime_error("Work report test publish fault");
        if(atomic_publish(lock.n,"candidate.json",folder.n,"work-report.json",oldPresent)) {
            // Preserve uncertainty if the platform cannot prove the namespace
            // is still exactly the precommit state after a failed syscall.
            bool original=false;
            try {auto staged=below(lock.n,"candidate.json");original=candidateId->object(staged.n);
                if(oldPresent){auto previous=below(folder.n,"work-report.json");original=original && oldId->unchanged(previous.n);}
                else {struct stat absent{};original=original && ::fstatat(folder.n,"work-report.json",&absent,AT_SYMLINK_NOFOLLOW)<0 && errno==ENOENT;}
            }catch(...){original=false;}
            indeterminate=!original;throw std::runtime_error("Work report atomic publication refused");
        }
        changed=true; // Namespace changed before any readback/callback can fail.
        if(work_report_test_fault(WorkReportFaultPoint::AfterAtomicPublishReadback))throw std::runtime_error("Work report test readback fault");
        auto installed=below(folder.n,"work-report.json");
        if(!candidateId->object(installed.n) || fileHash(installed.n,bytes.size())!=digest)throw std::runtime_error("Work report installed changed");
        if(oldPresent){auto prior=below(lock.n,"candidate.json");if(!oldId->object(prior.n))throw std::runtime_error("Work report old exchange unverified");}
        if(work_report_test_fault(WorkReportFaultPoint::OldCandidateCleanup))throw std::runtime_error("Work report test cleanup fault");
        if(oldPresent && ::unlinkat(lock.n,"candidate.json",0))throw std::runtime_error("Work report old cleanup refused");
        auto sameLock=below(folder.n,".writer",true);
        if(!lockId->object(sameLock.n) || ::unlinkat(folder.n,".writer",AT_REMOVEDIR))throw std::runtime_error("Work report lock cleanup refused");
        currentNamespace();
        verified=true;result.disposition="saved";
        result.artifact={{"path",projectRoot+QStringLiteral("/reports/work-report.json")},
            {"sha256",QString::fromLatin1(digest)},{"bytes",decimal(bytes.size())},{"physical_identity",identityToken(*candidateId)}};
    } catch(...) {
        if(indeterminate){result.disposition="publication_indeterminate";result.recovery=true;}
        else if(changed){result.disposition="committed_unverified";result.recovery=true;}
        else if(locked) {
            try {
                if(created){auto named=below(lock.n,"candidate.json");if(!candidateId || !candidateId->object(named.n) || ::unlinkat(lock.n,"candidate.json",0))throw std::runtime_error("Unverified candidate");}
                auto same=below(folder.n,".writer",true);
                if(!lockId || !lockId->object(same.n) || ::unlinkat(folder.n,".writer",AT_REMOVEDIR))throw std::runtime_error("Unverified lock");
            }catch(...){result.recovery=true;}
        }
    }
    Q_UNUSED(verified);return result;
}
#endif
} // namespace

bool work_report_next_serial(std::uint64_t current,std::uint64_t& next) noexcept {
    if(current==std::numeric_limits<std::uint64_t>::max())return false;next=current+1;return true;
}
Object work_report_missing(const char* reason) {return {{"state","missing"},{"reason",QLatin1StringView(reason)}};}
Object work_report_observed(const QJsonValue& value,const char* source,const QString& row) {
    return {{"state","observed"},{"value",value},{"source",QLatin1StringView(source)},
        {"row_id",row.isEmpty()?QJsonValue(QJsonValue::Null):QJsonValue(row)}};
}
Object work_report_receipt_coverage(const QString& reason) {
    return {{"retained_rows",missing()},{"included_rows",missing()},{"excluded_rows",missing()},
        {"omitted_rows",missing()},{"omitted_automatic_captures",missing()},{"extent_unknown",true},{"reason",reason}};
}
namespace {
struct RefusalBank {Object serial,capacity;QVariantMap serialVariant,capacityVariant;};
const RefusalBank& refusal_bank() {
    static const RefusalBank bank=[] {
        RefusalBank value;
        value.serial=receiptBase({}, {},0,"report_capacity");value.serial["snapshot_revision"]=missing("capacity");
        value.serial["error_code"]=observed("serial_exhausted");value.serial["coverage"]=work_report_receipt_coverage("capacity");
        value.capacity=value.serial;value.capacity["scope_id"]=missing("capacity");
        auto coverage=work_report_receipt_coverage("capacity");
        for(const char* key:{"retained_rows","included_rows","excluded_rows","omitted_rows","omitted_automatic_captures"})coverage[key]=missing("capacity");
        value.capacity["coverage"]=coverage;value.capacity["error_code"]=observed("report_unavailable");
        value.serialVariant=value.serial.toVariantMap();value.capacityVariant=value.capacity.toVariantMap();return value;
    }();return bank;
}
}
const Object& work_report_serial_refusal(){return refusal_bank().serial;}
const QVariantMap& work_report_serial_variant(){return refusal_bank().serialVariant;}
const QVariantMap& work_report_capacity_variant(){return refusal_bank().capacityVariant;}
Object work_report_empty_document() {
    static const Object frame=[]() -> Object {
    const auto m=missing();
    Object build;for(const char* k:{"edi_commit","edi_version","edi_dirty","sdk_version","sdk_source_commit","gui_declared_commit","gui_archive_sha256","gui_source_sha256","qt_loaded_version","platform","architecture"})build[k]=m;
    build["sdk_source_kind"]="unknown";
    Object runtime;for(const char* k:{"executable","version","sha256","selected_model","effective_model","selected_effort","effective_effort"})runtime[k]=m;
    runtime["adapter"]="official";
    Object scope{{"scope_id",""},{"instance_id",""},{"owner_generation","0"},{"snapshot_revision","0"},
        {"trigger","manual"},{"lifecycle","in_progress"},{"turns",QJsonArray{}}};
    for(const char* k:{"project_generation","account_epoch","input_generation","transport_generation"})scope[k]=m;
    Object coverage{{"complete_evidence",false},{"retained_rows","0"},{"included_rows","0"},
        {"first_retained_row",m},{"last_retained_row",m},{"excluded_unbound_rows","0"},{"known_omitted_rows","0"},
        {"missing_extent_unknown",true},{"gaps",QJsonArray{}}};
    return {{"schema","edi.assistant.work-report/1"},{"scope_coverage",scope},
        {"identity_inputs",Object{{"build",build},{"runtime",runtime},{"skills",QJsonArray{}},
            {"tool_schema",Object{{"sha256",m},{"count",m},{"body",m}}},{"objectives",QJsonArray{}},{"inputs",QJsonArray{}}}},
        {"history_evidence",QJsonArray{}},{"observations",Object{{"ui",QJsonArray{}},{"science",QJsonArray{}}}},
        {"agent_assessment",QJsonArray{}},{"coverage",coverage},{"artifact",Object{{"receipt_id",""},{"state","prepublication_snapshot"}}}};
    }();return frame;
}

struct AssistantWorkReports::Control {
    std::shared_ptr<WriterCompletion> completion;
    AssistantWorkReportOptions options;
    QString instance=QUuid::createUuid().toString(QUuid::WithoutBraces),scope,attempt;
    std::uint64_t serial=0,revision=0,missed=0,missing=0;
    bool enabled=false,exhausted=false,serialExhausted=false,unknown=false,busy=false,closing=false;
    Object last,activeReceipt;
    QVariantMap lastVariant;
    bool capturing=false;
    QString activeScope,activeRoot;quint64 activeRevision=0;
};
AssistantWorkReports::AssistantWorkReports(AssistantWorkReportOptions options,AssistantViewModel* owner) noexcept
    :options_(options),owner_(owner),collection_requested_(options.automatic) {}
AssistantWorkReports::~AssistantWorkReports(){closeOwner();}
void AssistantWorkReports::closeOwner() noexcept {if(control_)control_->closing=true;}
bool AssistantWorkReports::tryInitialize() noexcept {
    if(control_)return true;
    try {
        (void)refusal_bank();
        auto state=std::make_shared<Control>();state->options=options_;
        state->enabled=collection_requested_;state->unknown=unavailable_evidence_;control_=std::move(state);
        retireScope();if(unavailable_evidence_)control_->unknown=true;return true;
    }catch(...){unavailable_evidence_=true;return false;}
}
bool AssistantWorkReports::available() const noexcept{return bool(control_);}
std::shared_ptr<const void> AssistantWorkReports::releaseOwner() const noexcept{return control_;}
bool AssistantWorkReports::automatic() const noexcept{return options_.automatic;}
bool AssistantWorkReports::collecting() const noexcept{return control_ && control_->enabled;}
void AssistantWorkReports::enableManualCollection() noexcept{collection_requested_=true;if(control_)control_->enabled=true;}
const QString& AssistantWorkReports::scope() const noexcept{static const QString empty;return control_?control_->scope:empty;}
quint64 AssistantWorkReports::revision() const noexcept{return control_?control_->revision:0;}
bool AssistantWorkReports::exhausted() const noexcept{return !control_ || control_->exhausted;}
void AssistantWorkReports::changed() noexcept {
    if(!control_){unavailable_evidence_=true;return;}
    std::uint64_t next=0;if(!work_report_next_serial(control_->revision,next)){control_->exhausted=true;control_->unknown=true;return;}control_->revision=next;
}
QString AssistantWorkReports::newEvent() {
    if(!control_){unavailable_evidence_=true;return {};}
    std::uint64_t next=0;if(control_->serialExhausted || !work_report_next_serial(control_->serial,next)){control_->serialExhausted=true;control_->exhausted=true;control_->unknown=true;return {};}
    control_->serial=next;return "we/"+control_->instance+u'/'+decimal(next);
}
void AssistantWorkReports::retireScope() noexcept {
    if(!control_){unavailable_evidence_=true;return;}
    control_->scope.clear();control_->last={};control_->lastVariant={};
    try {const auto event=newEvent();if(event.isEmpty())return;control_->exhausted=false;control_->scope="wc/"+control_->instance+u'/'+decimal(control_->serial);
        control_->last={};
        control_->attempt.clear();control_->revision=0;control_->missed=0;control_->missing=0;control_->unknown=false;changed();}catch(...){control_->exhausted=true;control_->unknown=true;}
}
QString AssistantWorkReports::beginAttempt(){if(!control_){unavailable_evidence_=true;return {};}const auto event=newEvent();if(event.isEmpty())return {};control_->attempt="wa/"+control_->instance+u'/'+decimal(control_->serial);changed();static const QString empty;return control_?control_->attempt:empty;}
const QString& AssistantWorkReports::attempt() const noexcept{static const QString empty;return control_?control_->attempt:empty;}
void AssistantWorkReports::missEvidence() noexcept {if(!control_){unavailable_evidence_=true;return;}std::uint64_t n=0;if(work_report_next_serial(control_->missing,n))control_->missing=n;else control_->unknown=true;changed();}
void AssistantWorkReports::missedAutomaticCapture() noexcept {if(!control_){std::uint64_t next=0;if(work_report_next_serial(unavailable_captures_,next))unavailable_captures_=next;unavailable_evidence_=true;return;}std::uint64_t n=0;if(work_report_next_serial(control_->missed,n))control_->missed=n;else control_->unknown=true;changed();}
quint64 AssistantWorkReports::missedAutomaticCaptures() const noexcept{return control_?control_->missed:unavailable_captures_;}
bool AssistantWorkReports::coverageUnknown() const noexcept{return !control_ || control_->unknown || control_->missing;}
bool AssistantWorkReports::ownsScope(QAnyStringView scope) const noexcept {
    // JSON may expose Latin-1/UTF-8/UTF-16. Compare borrowed views only;
    // current instance spellings are ASCII and require no QString allocation.
    return control_ && scope.size()>3+control_->instance.size() &&
        QAnyStringView::compare(scope.first(3),QLatin1StringView("wc/"))==0 &&
        QAnyStringView::compare(scope.sliced(3,control_->instance.size()),control_->instance)==0 &&
        QAnyStringView::compare(scope.sliced(3+control_->instance.size(),1),QLatin1StringView("/"))==0;
}
Object AssistantWorkReports::stamp(const QString& attempt) const {if(!control_)return {};return {{"scope_id",control_->scope},{"attempt_id",attempt.isEmpty()?control_->attempt:attempt}};}
void AssistantWorkReports::settleCompletion(const std::shared_ptr<Control>& state) noexcept {
    if(!state)return;
    const auto cell=state->completion;
    if(!cell || cell->delivery.load(std::memory_order_acquire)!=WriterCompletion::Unavailable ||
       cell->consumed.exchange(true,std::memory_order_acq_rel))return;
    // Owner-thread checkpoint; clearing the cell cannot replay an accepted writer.
    if(state->completion!=cell)return;
    state->busy=false;state->activeReceipt={};state->activeRoot.clear();state->completion.reset();
    if(state->scope==cell->scope && !state->closing) {

        const auto& fallback=cell->fallback[cell->outcome.load(std::memory_order_acquire)];
        state->last=fallback.first;state->lastVariant=fallback.second;
        // No fabricated finished signal or worker retry on this unavailable path.
    }
}
QVariantMap AssistantWorkReports::receipt() const {
    const auto state=control_;
    if(QThread::currentThread()==owner_->thread())settleCompletion(state);
    return state?state->lastVariant:work_report_capacity_variant();
}
void AssistantWorkReports::present(const Object& receipt,const QVariantMap& variant){
    const auto state=control_;

    state->last=receipt;state->lastVariant=variant;
    try {emit owner_->workReportReceiptChanged();}catch(...){}
}
QVariantMap AssistantWorkReports::immediate(const Object& receipt) {
    const auto reply=receipt.toVariantMap();present(receipt,reply);return reply;
}

bool AssistantWorkReports::artifactCurrent(const Object& artifact,QStringView storageRoot) const noexcept {
#if defined(Q_OS_UNIX) && !defined(__EMSCRIPTEN__)
    try {const auto path=artifact.value("path").toString();
        constexpr QStringView suffix=u"/reports/work-report.json";
        if(!QStringView(path).endsWith(suffix) || QStringView(path).size()!=storageRoot.size()+suffix.size() ||
           QStringView(path).first(storageRoot.size())!=storageRoot)return false;
        auto root=assistant_files::directory(storageRoot.toString());checkDirectory(root.n,0);
        auto dir=assistant_files::below(root.n,"reports",true);checkDirectory(dir.n,0);
        auto file=assistant_files::below(dir.n,"work-report.json");privateFile(file.n);const Identity id(file.n);
        bool ok=false;const auto bytes=artifact.value("bytes").toString().toULongLong(&ok);
        return ok && bytes<=L::record_bytes && identityToken(id)==artifact.value("physical_identity").toString() &&
            fileHash(file.n,bytes)==artifact.value("sha256").toString().toLatin1();
    }catch(...){return false;}
#else
    Q_UNUSED(artifact);Q_UNUSED(storageRoot);return false;
#endif
}

QVariantMap AssistantWorkReports::capture(bool automaticTrigger,AssistantWorkReportCoverage counts,QStringView storageRoot,
        const std::function<AssistantWorkReportSnapshot(quint64)>& build,const QString& expectedScope,quint64 expectedRevision,bool projectionBlocked) {
    // The original worker and owner-thread completion retain their own snapshots.
    struct WorkCapture {
        std::shared_ptr<WriterWorkerLease> lease;
        std::shared_ptr<Control> state;
        std::shared_ptr<WriterCompletion> completion;
        Object document,receipt;
        QString projectRoot,scope;
        QPointer<AssistantViewModel> receiver;
    };
    struct FinishCapture {
        std::shared_ptr<Control> state;
        std::shared_ptr<WriterCompletion> completion;
        Object terminal;
        QString scope;
        QPointer<AssistantViewModel> receiver;
        bool fallbackOnly;
    };
    const QPointer<AssistantViewModel> receiver(owner_);
    if(QThread::currentThread()!=receiver->thread())throw std::logic_error("Work report capture requires its native owner thread");
    enableManualCollection();
    const auto state=control_;
    settleCompletion(state);
    if(!state){if(automaticTrigger)missedAutomaticCapture();return work_report_capacity_variant();}
    if(state->scope!=expectedScope) {
        if(newEvent().isEmpty())return work_report_serial_variant();
        auto retired=receiptBase("wr/"+state->instance+u'/'+decimal(state->serial),expectedScope,expectedRevision,"superseded");
        retired["scope_retired"]=true;retired["coverage"]=work_report_receipt_coverage("superseded");
        return retired.toVariantMap(); // Do not present an old request on a replacement binding.
    }
    if(projectionBlocked) {
        // A zero byte budget is not a fence: no active/saved reuse is lawful
        // until the native terminal facts are ready, even at one revision.
        if(automaticTrigger)missedAutomaticCapture();
        if(newEvent().isEmpty())return work_report_serial_variant();
        auto limited=receiptBase("wr/"+state->instance+u'/'+decimal(state->serial),state->scope,state->revision,"report_capacity");
        if(state->exhausted)limited["snapshot_revision"]=missing("capacity");
        limited["error_code"]=observed("settlement_pending");
        limited["coverage"]=work_report_receipt_coverage("settlement_unknown");
        if(state->capturing)return limited.toVariantMap(); // No recursive presentation.
        state->capturing=true;const auto leave=qScopeGuard([state]{state->capturing=false;});
        return immediate(limited);
    }
    if(state->capturing) {
        if(!state->serialExhausted && !state->exhausted && state->busy &&
           state->activeScope==state->scope && state->activeRevision==state->revision && QStringView(state->activeRoot)==storageRoot) {
            auto shared=state->activeReceipt;shared["disposition"]="coalesced";
            return shared.toVariantMap(); // No recursive signal; exact active identity only.
        }
        // Never reuse a prior scope/revision or the no-Control exception. The
        // preowned reentry frame has a real ID and emits no recursive signal.
        if(automaticTrigger)missedAutomaticCapture();
        if(newEvent().isEmpty())return work_report_serial_variant();
        auto limited=receiptBase("wr/"+state->instance+u'/'+decimal(state->serial),state->scope,state->revision,"report_capacity");
        if(state->exhausted)limited["snapshot_revision"]=missing("capacity");
        limited["error_code"]=observed("report_capacity");limited["coverage"]=work_report_receipt_coverage("capacity");
        return limited.toVariantMap();
    }
    state->capturing=true;const auto leave=qScopeGuard([state]{state->capturing=false;});
    if(state->serialExhausted){return work_report_serial_variant();}
    if(state->exhausted) {
        const auto event=newEvent();if(event.isEmpty()){return work_report_serial_variant();}
        auto receipt=receiptBase("wr/"+state->instance+u'/'+decimal(state->serial),state->scope,state->revision,"report_capacity");
        receipt["snapshot_revision"]=missing("capacity");receipt["error_code"]=observed("snapshot_revision_exhausted");
        receipt["coverage"]=work_report_receipt_coverage("capacity");return immediate(receipt);
    }
    if(state->busy && state->activeScope==state->scope && state->activeRevision==state->revision && QStringView(state->activeRoot)==storageRoot) {
        auto r=state->activeReceipt;r["disposition"]="coalesced";return immediate(r);
    }
    if(!state->busy && state->last.value("scope_id").toObject().value("value")==state->scope &&
       state->last.value("snapshot_revision").toObject().value("value")==decimal(state->revision) &&
       (state->last.value("disposition")=="saved" || state->last.value("disposition")=="saved_incomplete")) {
        const auto artifact=state->last.value("artifact").toObject().value("value").toObject();
        if(artifactCurrent(artifact,storageRoot))return state->lastVariant;
    }
    if(automaticTrigger && state->busy)missedAutomaticCapture();
    const auto event=newEvent();
    if(event.isEmpty()){return work_report_serial_variant();}
    const auto id="wr/"+state->instance+u'/'+decimal(state->serial);
    auto receipt=receiptBase(id,state->scope,state->revision,"report_capacity");

    auto coverage=work_report_receipt_coverage(state->busy?"busy":"capacity");
    coverage["omitted_automatic_captures"]=state->unknown?missing("capacity"):observed(decimal(state->missed));
    if(counts.known){coverage["retained_rows"]=observed(decimal(counts.retained));coverage["excluded_rows"]=observed(decimal(counts.excluded));}
    if(state->busy) {
        if(counts.known)coverage["omitted_rows"]=observed(decimal(counts.retained));
        coverage["included_rows"]=observed("0");receipt["disposition"]="busy";receipt["coverage"]=coverage;
        return immediate(receipt);
    }
#if !defined(Q_OS_UNIX) || defined(__EMSCRIPTEN__)
    receipt["disposition"]="unsupported";return immediate(receipt);
#else
    std::shared_ptr<WriterCompletion> completion;
    QVariantMap acceptedReply;bool accepted=false;
    const char* preparationCode="snapshot_unavailable";
    try {
        const auto scope=state->scope;const auto revision=state->revision;
        if(storageRoot.isEmpty() || storageRoot.contains(QChar(0)) || storageRoot.size()>static_cast<qsizetype>(L::message_bytes)) {
            preparationCode="storage_root_unavailable";throw std::runtime_error("Report storage unavailable");
        }
        const auto projectRoot=storageRoot.toString();
        const auto snapshot=build(L::record_bytes);
        if(snapshot.scope!=scope || snapshot.revision!=revision || state->scope!=scope || state->revision!=revision) {
            receipt["disposition"]="superseded";receipt["coverage"]=work_report_receipt_coverage("superseded");
            return immediate(receipt);
        }
        if(snapshot.document.isEmpty()) {
            receipt["disposition"]="no_work";auto zero=work_report_receipt_coverage("no_work");
            if(!counts.known)throw std::length_error("Unknown ownership is not no work");
            zero["retained_rows"]=observed("0");zero["included_rows"]=observed("0");zero["omitted_rows"]=observed("0");
            zero["excluded_rows"]=observed(decimal(counts.excluded));zero["omitted_automatic_captures"]=observed(decimal(state->missed));
            zero["extent_unknown"]=state->unknown;receipt["coverage"]=zero;return immediate(receipt);
        }
        preparationCode="artifact_capacity";
        auto document=snapshot.document;
        document["artifact"]=Object{{"receipt_id",id},{"state","prepublication_snapshot"}};
        auto scopeData=document.value("scope_coverage").toObject();scopeData["trigger"]=automaticTrigger?"automatic":"manual";document["scope_coverage"]=scopeData;
        quint64 artifactBytes=0;
        if(!codex_encoded_size(document,L::record_bytes,artifactBytes))throw std::length_error("Report exceeds artifact capacity");
        const auto full=document.value("coverage").toObject();
        QString coverageReason="none";
        const auto gaps=full.value("gaps").toArray();
        if(!gaps.isEmpty()) {
            const auto reason=gaps.first().toObject().value("reason").toString();
            coverageReason=(reason=="capacity" || reason=="unbound_owner" || reason=="busy" || reason=="settlement_unknown")?reason:QStringLiteral("not_observed");
        }
        coverage=work_report_receipt_coverage(coverageReason);
        coverage["retained_rows"]=observed(full.value("retained_rows"));coverage["included_rows"]=observed(full.value("included_rows"));
        coverage["excluded_rows"]=observed(full.value("excluded_unbound_rows"));coverage["omitted_rows"]=observed(full.value("known_omitted_rows"));
        coverage["omitted_automatic_captures"]=state->unknown?missing("capacity"):observed(decimal(state->missed));
        coverage["extent_unknown"]=full.value("missing_extent_unknown").toBool() || state->unknown;
        receipt["coverage"]=coverage;receipt["complete_evidence"]=full.value("complete_evidence").toBool();
        receipt["phase"]="accepted";receipt["disposition"]="accepted";
        completion=std::make_shared<WriterCompletion>(scope,completionFallbacks(receipt));
        const auto workerLease=std::make_shared<WriterWorkerLease>(completion);
        state->busy=true;state->activeScope=scope;state->activeRoot=projectRoot;state->activeRevision=revision;state->activeReceipt=receipt;state->completion=completion;
        const auto acceptedVariant=receipt.toVariantMap();acceptedReply=acceptedVariant;accepted=true;
        present(receipt,acceptedVariant);
        const auto input=std::make_shared<WorkCapture>(WorkCapture{workerLease,state,completion,std::move(document),receipt,projectRoot,scope,receiver});
        auto work=[input]() mutable {
            const auto& state=input->state;const auto& completion=input->completion;
            auto& document=input->document;const auto& receipt=input->receipt;const auto& projectRoot=input->projectRoot;
            const auto& scope=input->scope;const auto& receiver=input->receiver;
            // Worker mutates only its local Qt owners and this original cell's
            // fixed atomics. Never State/Project/QObject/owner-thread Qt data.
            try {
                auto terminal=receipt;bool fallbackOnly=false;
                try {
                    terminal["phase"]="terminal";
                    const auto bytes=QJsonDocument(document).toJson(QJsonDocument::Compact);
                    if(bytes.size()<0 || static_cast<quint64>(bytes.size())>L::record_bytes)
                        throw std::length_error("Report exceeds artifact capacity");
                    const auto hash=QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex();
                    auto result=publishFile(projectRoot,bytes,hash);
                    completion->publication(result); // POD latch BEFORE fallible receipt assembly.
                    terminal["disposition"]=QLatin1StringView(result.disposition);terminal["recovery_required"]=result.recovery;
                    if(!result.artifact.isEmpty()) {
                        terminal["artifact"]=observed(result.artifact);
                        if(!terminal.value("complete_evidence").toBool())terminal["disposition"]="saved_incomplete";
                    }else {
                        terminal["artifact"]=missing(completion->outcome.load(std::memory_order_acquire)>=3?"not_observed":"not_present");
                        terminal["error_code"]=observed(QLatin1StringView(result.disposition));
                        auto covered=terminal.value("coverage").toObject();covered["reason"]="storage";terminal["coverage"]=covered;
                    }
                }catch(...) {fallbackOnly=true;terminal={};} // Immutable fallback already owns every field/Variant.
                document={};
                const auto output=std::make_shared<FinishCapture>(FinishCapture{state,completion,std::move(terminal),scope,receiver,fallbackOnly});
                auto deliver=[output]() mutable {
                    const auto& state=output->state;const auto& completion=output->completion;
                    auto& terminal=output->terminal;const auto& scope=output->scope;const auto& receiver=output->receiver;
                    bool fallbackOnly=output->fallbackOnly;
                    if(!completion->beginDelivery())return; // A late old callback cannot settle another writer.
                    completion->consumed.store(true,std::memory_order_release);
                    const auto finished=qScopeGuard([completion]{completion->delivery.store(WriterCompletion::Settled,std::memory_order_release);});
                    // Settled means original callback execution, never receiver
                    // delivery/consumption acknowledgement after death/throw.
                    const auto fallbackIndex=completion->outcome.load(std::memory_order_acquire)+
                        (state->scope!=scope || state->closing?WriterCompletion::publicationCases:0);
                    const auto& fallback=completion->fallback[fallbackIndex];
                    QVariantMap terminalVariant;
                    if(!fallbackOnly)try {terminal["scope_retired"]=state->scope!=scope || state->closing;terminalVariant=terminal.toVariantMap();}
                        catch(...) {fallbackOnly=true;}
                    if(fallbackOnly){terminal=fallback.first;terminalVariant=fallback.second;}
                    // An unavailable old scope is never presented on a successor.
                    // A normal original delivery still settles its actual waiter.
                    if(state->completion==completion) {
                        state->busy=false;state->activeRoot.clear();state->activeReceipt={};state->completion.reset();
                    }
                    if(receiver) {
                        if(state->scope==scope && !state->closing) {

                            state->last=terminal;state->lastVariant=terminalVariant;
                            try {emit receiver->workReportReceiptChanged();}catch(...){}
                        }
                        if(receiver && !state->closing)try {emit receiver->workReportFinished(terminalVariant);}catch(...){}
                    }
                    terminal={};
                };
                auto* app=QCoreApplication::instance();
                if(!app || !QMetaObject::invokeMethod(app,std::move(deliver),Qt::QueuedConnection))completion->unavailable();
                else {auto expected=WriterCompletion::Pending;(void)completion->delivery.compare_exchange_strong(expected,WriterCompletion::Queued,std::memory_order_acq_rel);}
            }catch(...) {completion->unavailable();} // No second enqueue/capture; original file outcome survives.
        };
        run_in_background(std::move(work));return acceptedVariant;
    } catch(...) {
        if(accepted && completion) {
            // A discarded QtConcurrent future is not proof a task never began.
            // The actual last worker lease proves failed launch, or the one
            // original worker/queued callback still owns this accepted attempt.
            settleCompletion(state);
            if(completion->delivery.load(std::memory_order_acquire)==WriterCompletion::Unavailable) {
                const auto index=completion->outcome.load(std::memory_order_acquire)+
                    (state->scope!=completion->scope || state->closing?WriterCompletion::publicationCases:0);
                return completion->fallback[index].second;
            }
            return acceptedReply;
        }
        // Preparation did not start a worker. Retire only this original cell.
        if(completion && state->completion==completion) {
            state->busy=false;state->activeRoot.clear();state->activeReceipt={};state->completion.reset();
        }
        receipt["phase"]="terminal";receipt["disposition"]="report_capacity";
        receipt["coverage"]=coverage;receipt["error_code"]=observed(QLatin1StringView(preparationCode));
        const auto reply=receipt.toVariantMap();
        if(receiver && !state->closing)present(receipt,reply);
        return reply;
    }
#endif
}
} // namespace edi_app
