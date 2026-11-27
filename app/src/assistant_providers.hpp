// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include "assistant_provider.hpp"

namespace edi_app {

/// The provider for an account (ADR-0108 §1): ChatGPT's Codex runtime, Claude or GitHub Copilot.
/// Returns null for a provider whose runtime this build does not offer.
std::unique_ptr<AssistantProvider> make_assistant_provider(const AssistantAccountRef& account, QObject* parent,
                                                           std::shared_ptr<const void> releaseOwner);

}  // namespace edi_app
