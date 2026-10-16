// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QByteArray>
#include <QString>
#include <QTemporaryDir>
#include <functional>
#include <memory>
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
    AssistantResultExport(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf);
    // Native automation must use the actual pinned picker capability, never a
    // provider-supplied parent string. The existing raw-parent form is Save As.
    AssistantResultExport(const ImmutableAssistantResult& source, std::shared_ptr<const AssistantWorkingFolder> folder, const QString& leaf);
    ~AssistantResultExport();
    AssistantResultExport(const AssistantResultExport&) = delete;
    AssistantResultExport& operator=(const AssistantResultExport&) = delete;
    // All strings/receipt buffers and independent load are prepared before this call.
    // No overwrite/copy/remove fallback. On success committed() latches before returning.
    void publish(const std::function<bool()>& current);
    bool committed() const noexcept;
    const QString& destination() const noexcept;
    const QJsonArray& files() const noexcept;
    edi::Project reopen() const;
 private:
    void prepare(const ImmutableAssistantResult& source, const QString& parent, const QString& leaf,
                 std::shared_ptr<const AssistantWorkingFolder> folder);
    struct State;
    std::unique_ptr<State> state_;
};
} // namespace edi_app
