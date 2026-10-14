// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <functional>
#include <memory>
#include "edi/assistant.hpp"

namespace edi::assistant::native {

/// Native SIWC connection (ADR-0038). Uses its own protected registrations, never another app's credentials.
/// Construct and call on the Qt event-loop thread. The sink must queue controller input rather than reenter it.
class ChatGptConnection {
   public:
    explicit ChatGptConnection(std::function<void(const JsonText&)> event_sink);
    ~ChatGptConnection();
    ChatGptConnection(const ChatGptConnection&) = delete;
    ChatGptConnection& operator=(const ChatGptConnection&) = delete;
    Reply sign_in();
    Reply connect_saved(std::string registration_id);
    Reply send(const JsonText& request);
    void cancel(std::string turn_id);
    void sign_out();
    JsonText state() const;

   private:
    struct State;
    std::unique_ptr<State> state_;
};
}  // namespace edi::assistant::native
