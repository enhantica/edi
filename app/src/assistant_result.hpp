// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QByteArray>
#include <QString>
#include <QStringList>
#include <QTemporaryDir>
#include <functional>
#include <memory>
#include <limits>
#include <string>
#include <utility>
#include <vector>
#include "edi/model.hpp"

namespace edi_app {
// Same bounded single-leaf domain as ordinary result Save As; no path grant.
void validate_assistant_result_leaf(const QString& name);
// App-private: no provider-visible operation or writable application path.
struct AssistantResultDirectory;
struct ImmutableAssistantResult {
    std::shared_ptr<QTemporaryDir> lease;
    std::shared_ptr<AssistantResultDirectory> handle;
    QString directory; // Physical host-owned sealed copy; identity checked against the retained descriptor.
    QString recovery_directory;
    QByteArray receipt;
    QString intent;
    QJsonArray files;
    // Only host-owned current-project capture enables arbitrary carried leaves;
    // provider result receipts retain the original fixed native layout.
    bool carried_tree = false;
    QStringList directories;
};
std::shared_ptr<ImmutableAssistantResult> capture_assistant_result(const QString& workspace, const QString& intent);
// The same checked real-loader door is used again by Session adoption.
edi::Project load_captured_assistant_result(const ImmutableAssistantResult& result);
// App-private downstream boundary for ALREADY bounded real-writer documents.
// This checks before host copies/files grow; it does not bound the writer that
// produced the input and cannot itself authorize/register a save operation.
std::shared_ptr<ImmutableAssistantResult> capture_prepared_native_documents(
    const std::vector<std::pair<std::string, std::string>>& documents);
// Rechecks the real loader's declared mode before any ProjectViewModel/cache construction.
void check_assistant_result_mode(const edi::Project& project);

/// App-private immutable capture of the current Session-owned native source.
/// The caller must prove its actual Session/PVM path authority; a path or this
/// helper alone grants no write permission. All capture and currentness calls
/// run on the owning thread. The retained protected copy/record may be read by
/// its exclusive save worker until completion. No source bytes are changed.
/// Refuses changed/no-follow identity, unsupported file closure or bounds before
/// exposing an input; allocation, filesystem and parsing failures propagate.
class AssistantSaveSource {
 public:
    AssistantSaveSource(const QString& ownedDirectory, quint64 retainedLimit, const std::function<bool()>& current);
    ~AssistantSaveSource();
    AssistantSaveSource(const AssistantSaveSource&) = delete;
    AssistantSaveSource& operator=(const AssistantSaveSource&) = delete;
    const QString& path() const noexcept;
    const std::string& record() const noexcept;
    const ImmutableAssistantResult& snapshot() const noexcept;
    quint64 retainedBytes() const noexcept;
    bool current() const noexcept;
 private:
    friend class AssistantResultExport;
    struct State;
    std::unique_ptr<State> state_;
};

/// Carry bounded original files through the ordinary writer's regenerated-file
/// policy. The source is an already admitted immutable owned-project capture;
/// arbitrary provider paths or documents never enable carried-tree parsing.
std::shared_ptr<ImmutableAssistantResult> capture_prepared_native_documents(
    const std::vector<std::pair<std::string, std::string>>& documents, const AssistantSaveSource& source);

// A native picker, never a provider path argument, constructs this grant.
// It pins the physical root; mutable descendants remain untrusted and must use
// the existing bounded no-follow readers/writers. No directory enumeration here.
class AssistantWorkingFolder {
 public:
    explicit AssistantWorkingFolder(const QString& selected);
    ~AssistantWorkingFolder();
    AssistantWorkingFolder(const AssistantWorkingFolder&) = delete;
    AssistantWorkingFolder& operator=(const AssistantWorkingFolder&) = delete;
    const QString& path() const noexcept;
    bool current() const noexcept;
 private:
    friend class AssistantResultExport;
    struct State;
    std::unique_ptr<State> state_;
};

// User-click read-only report snapshots reuse the same no-follow bounded file
// reader. A retained lease outlives the asynchronous platform viewer.
struct ImmutableAssistantReport {
    std::shared_ptr<QTemporaryDir> lease;
    QString file;
    quint64 bytes = 0;
};
std::shared_ptr<ImmutableAssistantReport> capture_assistant_report(const QString& workspace, const QString& relative, quint64 remaining);

class AssistantResultExport {
 public:
    // Allocation-free receipt shape/role count. The native caller preowns this
    // parser workspace before export construction; no path/write authority.
    static quint64 receiptPreparationBytes(const QByteArray& receipt);
    AssistantResultExport(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf);
    // Native automation must use the actual pinned picker capability, never a
    // provider-supplied parent string. The existing raw-parent form is Save As.
    AssistantResultExport(const ImmutableAssistantResult& source, std::shared_ptr<const AssistantWorkingFolder> folder, const QString& leaf,
                          quint64 preparationLimit = std::numeric_limits<quint64>::max());
    /// Replace only the exact original Session-owned directory represented by
    /// the admitted capture. The old tree is retained at recoveryDirectory();
    /// namespace uncertainty after exchange is committed, never "not written".
    AssistantResultExport(const ImmutableAssistantResult& source, std::shared_ptr<const AssistantSaveSource> owned,
                          std::shared_ptr<const AssistantWorkingFolder> folder = {},
                          quint64 preparationLimit = std::numeric_limits<quint64>::max());
    ~AssistantResultExport();
    AssistantResultExport(const AssistantResultExport&) = delete;
    AssistantResultExport& operator=(const AssistantResultExport&) = delete;
    // All strings/receipt buffers and independent load are prepared before this call.
    // No overwrite/copy/remove fallback. On success committed() latches before returning.
    void publish(const std::function<bool()>& current);
    // Counted peak stays owned through verification/publication and unwind.
    quint64 preparationBytes() const noexcept;
    bool committed() const noexcept;
    const QString& destination() const noexcept;
    const QJsonArray& files() const noexcept;
    const QString& recoveryDirectory() const noexcept;
    edi::Project reopen() const;
 private:
    void prepare(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf,
                 std::shared_ptr<const AssistantWorkingFolder> folder, std::shared_ptr<const AssistantSaveSource> owned = {},
                 quint64 preparationLimit = std::numeric_limits<quint64>::max(), quint64 entranceBytes = 0);
    struct State;
    std::unique_ptr<State> state_;
};
} // namespace edi_app
