// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QObject>
#include <QPointer>
#include <QString>
#include <cstdint>
#include <functional>
#include <memory>

namespace edi_app {
// The existing canonical history file's ordered background owner. No project,
// provider, tool permissions, retry timer or scientific work lives here.
class AssistantHistoryArchive final {
public:
    struct View {
        QString path;
        QJsonArray initial_rows, latest_rows;
        std::uint64_t accepted = 0, durable = 0, clear = 0, failure_revision = 0;
        bool loaded = false, includes_initial = false, pending = false, recovered = false;
        const char* failure_stage = nullptr;
    };
    using Notice = std::function<void(const View&)>;
    AssistantHistoryArchive(QObject*, QString requestedPath, Notice, bool provisional = false);
    /// Commit this candidate's receiver after its actual owner finished construction.
    /// A failed/uncommitted candidate never revokes the surviving prior writer.
    void activate();
    ~AssistantHistoryArchive();
    View view() const;
    // True means retained by the archive owner, never committed. The immutable
    // complete post-Clear snapshot can subsume an older pending revision.
    bool retain(QJsonArray, bool includesInitial, bool logicalClear = false) noexcept;
    void closeOwner() noexcept;
private:
    struct Control;
    std::shared_ptr<Control> control_;
    std::uint64_t owner_ = 0;
    QPointer<QObject> pending_receiver_;
    Notice pending_notice_;
    static void launch(const std::shared_ptr<Control>&) noexcept;
    static void drain(const std::shared_ptr<Control>&) noexcept;
    static void notify(const std::shared_ptr<Control>&) noexcept;
};
} // namespace edi_app
