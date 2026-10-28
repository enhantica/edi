// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QObject>
#include <QPointer>
#include <QString>
#include <vector>
#include <utility>
#include <cstdint>
#include <functional>
#include <memory>

namespace edi_app {
QJsonArray merge_assistant_history(const QJsonArray& initial,const QJsonArray& current);
// The existing canonical history file's ordered background owner. No project,
// provider, tool permissions, retry timer or scientific work lives here.
class AssistantHistoryArchive final {
    struct Control;
public:
    struct View {
        QString path;
        QJsonArray initial_rows, latest_rows;
        std::uint64_t accepted = 0, durable = 0, clear = 0, failure_revision = 0;
        bool loaded = false, includes_initial = false, pending = false, recovered = false;
        const char* failure_stage = nullptr;
        bool working = false;
    };
    using Notice = std::function<void(const View&)>;
    class ClearBarrier {
    public:
        ClearBarrier(ClearBarrier&&) noexcept = default;
        ClearBarrier& operator=(ClearBarrier&&) noexcept;
        ~ClearBarrier();
        View view() const;
        std::uint64_t revision() const noexcept { return revision_; }
        bool retry() noexcept;
    private:
        friend class AssistantHistoryArchive;
        ClearBarrier(std::shared_ptr<Control> state,std::uint64_t revision):state_(std::move(state)),revision_(revision) {}
        std::shared_ptr<Control> state_;
        std::uint64_t revision_=0;
    };
    /// Clear the actual archive owners, including accepted writes not yet on disk and known recovery targets.
    /// The returned barriers do not take any normal history writer's owner token.
    static std::vector<ClearBarrier> clearCaches(QObject*,Notice);
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
    std::shared_ptr<Control> control_;
    std::uint64_t owner_ = 0;
    QPointer<QObject> pending_receiver_;
    Notice pending_notice_;
    static void launch(const std::shared_ptr<Control>&) noexcept;
    static void drain(const std::shared_ptr<Control>&) noexcept;
    static void notify(const std::shared_ptr<Control>&) noexcept;
};
} // namespace edi_app
