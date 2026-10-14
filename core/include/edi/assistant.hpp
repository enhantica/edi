// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <string_view>

#include "edi/edit.hpp"
#include "edi/model.hpp"
#include "edi/worker.hpp"

namespace edi::assistant {

using JsonText = std::string;

/// A synchronous acknowledgement. Refusals carry a stable code and JSON object describing the field or reason.
struct Reply {
    bool ok = false;
    std::string code;
    JsonText value = "{}";
};

/// The attached project's session identity and monotonic admitted-write revision.
struct Revision {
    std::string project_id;
    std::uint64_t revision = 0;
};

/// Owner-thread services. Callbacks must not reenter the controller; queue the next command instead.
struct Hooks {
    std::function<void(const JsonText&)> event;
    std::function<void(const JsonText&)> provider_request;
    std::function<std::string(const edi::Edit&, bool structural)> apply;
    std::function<std::uint64_t()> monotonic_ms;
};

/// Shared conversation, approval and trial policy (ADR-0037). The worker outlives this owner-thread object.
class Controller {
   public:
    Controller(edi::work::Worker& worker, Hooks hooks);
    ~Controller();
    Controller(const Controller&) = delete;
    Controller& operator=(const Controller&) = delete;
    /// Borrow a project under a fresh nonempty session ID, or detach with nullptr and an empty ID.
    Reply attach(edi::Project* project, std::string project_id);
    Revision revision() const;
    /// Notify a manual edit, undo, save/readback or publication outside this controller.
    void notify_changed();
    /// Admit a trusted UI action. Provider traffic must use provider_event, never this entry.
    Reply user_command(const JsonText& command);
    /// Admit a normalized provider event; partial arguments never enter this boundary.
    Reply provider_event(const JsonText& event);
    JsonText state() const;
    JsonText context() const;
    /// Check deadlines on the owner thread, driven by the host event loop.
    void poll();
    /// Revoke execution and request cancellation; worker settlement arrives separately.
    void cancel();

   private:
    struct State;
    std::shared_ptr<State> state_;
};

/// Incremental Responses SSE decoder. Emits public inference items only, without account/project authority.
class OpenAiStream {
   public:
    using Sink = std::function<void(const JsonText&)>;
    OpenAiStream(std::string turn_id, std::string request_id, Sink sink);
    ~OpenAiStream();
    OpenAiStream(const OpenAiStream&) = delete;
    OpenAiStream& operator=(const OpenAiStream&) = delete;
    Reply feed(std::string_view bytes);
    Reply finish();

   private:
    struct State;
    std::unique_ptr<State> state_;
};

}  // namespace edi::assistant
