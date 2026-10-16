// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QByteArray>
#include <QString>
#include <QTemporaryDir>
#include <functional>
#include <memory>
#include "edi/model.hpp"

namespace edi_app {
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
// Rechecks the real loader's declared mode before any ProjectViewModel/cache construction.
void check_assistant_result_mode(const edi::Project& project);

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
    struct State;
    std::unique_ptr<State> state_;
};
} // namespace edi_app
