// SPDX-License-Identifier: BSD-3-Clause
#include "native_chatgpt_provider.hpp"

namespace edi_app {

NativeChatGptProvider::NativeChatGptProvider(std::function<void(const edi::assistant::JsonText&)> eventSink,
                                             edi::assistant::native::NativeDependencies dependencies, QObject* parent)
    : AssistantProvider(parent),
      connection_(std::make_unique<edi::assistant::native::ChatGptConnection>(std::move(eventSink),
                                                                              std::move(dependencies))) {}

NativeChatGptProvider::~NativeChatGptProvider() = default;

void NativeChatGptProvider::poll() { connection_->poll(); }
edi::assistant::Reply NativeChatGptProvider::sign_in() { return connection_->sign_in(); }
edi::assistant::Reply NativeChatGptProvider::connect_saved(const std::string& registrationId) {
    return connection_->connect_saved(registrationId);
}
edi::assistant::Reply NativeChatGptProvider::send(const edi::assistant::JsonText& request) {
    return connection_->send(request);
}
void NativeChatGptProvider::cancel(const std::string& turnId) { connection_->cancel(turnId); }
void NativeChatGptProvider::sign_out() { connection_->sign_out(); }
edi::assistant::JsonText NativeChatGptProvider::state() const { return connection_->state(); }

}  // namespace edi_app
