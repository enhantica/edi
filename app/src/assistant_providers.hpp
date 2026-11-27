// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include "assistant_provider.hpp"

namespace edi_app {

/// The MCP call timeout edi gives a runtime for its tools: a fit or a question may take hours, and edi itself sets
/// no total limit on them, so one day plus a minute (ADR-0108 §3).
inline constexpr quint64 assistant_tool_timeout_ms = 24ull * 60 * 60 * 1000 + 60ull * 1000;

/// Whether a GitHub Copilot session may receive user input. Neither ACP nor the pinned CLI reads back a session's
/// effective tools, so this stays false until the owner decides what proves them (ADR-0108, open question 1).
inline constexpr bool assistant_copilot_input_open = false;

/// The provider for an account (ADR-0108 §1): ChatGPT's Codex runtime, Claude or GitHub Copilot.
/// Returns null for a provider whose runtime this build does not offer.
std::unique_ptr<AssistantProvider> make_assistant_provider(const AssistantAccountRef& account, QObject* parent,
                                                           std::shared_ptr<const void> releaseOwner);

/// The provider's display name (ChatGPT, Claude, GitHub Copilot) and the company that receives the data.
QString assistant_provider_name(AssistantProviderId id);
QString assistant_provider_company(AssistantProviderId id);

/// The runtime a provider starts: the developer override when set (an absolute executable), else the bundled one,
/// else empty when that runtime is not installed. Throws when an override is set but unusable.
QString assistant_provider_executable(AssistantProviderId id);

/// True when the provider's runtime is installed and this build can drive it.
bool assistant_provider_available(AssistantProviderId id) noexcept;

}  // namespace edi_app
