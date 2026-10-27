// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <cstdint>

namespace edi::assistant {
/// Working-record, protocol/identity and presentation constants (ADR-0054/0056).
/// Historical work totals are not task/output/history/admission quotas; actual
/// streaming and retained once evidence must not abort merely by growing.
struct Limits final {
    static constexpr std::uint64_t message_bytes = 1048576;
    static constexpr std::uint64_t json_depth = 64;
    static constexpr std::uint64_t id_bytes = 256;
    static constexpr std::uint64_t error_bytes = 512;
    static constexpr std::uint64_t stream_wire_bytes = 8388608;
    static constexpr std::uint64_t stream_retained_bytes = 4194304;
    static constexpr std::uint64_t stream_events = 8192;
    static constexpr std::uint64_t stream_items = 256;
    static constexpr std::uint64_t stream_calls = 64;
    static constexpr std::uint64_t history_bytes = 2097152;
    static constexpr std::uint64_t history_entries = 1024;
    static constexpr std::uint64_t replay_bytes = 4194304;
    static constexpr std::uint64_t replay_items = 512;
    static constexpr std::uint64_t completed_calls = 512;
    static constexpr std::uint64_t completed_call_bytes = 2097152;
    static constexpr std::uint64_t context_bytes = 1048576;
    static constexpr std::uint64_t request_bytes = 8388608;
    static constexpr std::uint64_t ui_history_bytes = 2097152;
    static constexpr std::uint64_t ui_messages = 512;
    static constexpr std::uint64_t http_header_bytes = 16384;
    static constexpr std::uint64_t http_headers = 64;
    static constexpr std::uint64_t http_json_bytes = 1048576;
    static constexpr std::uint64_t http_chunk_bytes = 65536;
    static constexpr std::uint64_t http_operations = 4;
    static constexpr std::uint64_t callback_bytes = 16384;
    static constexpr std::uint64_t callback_sockets = 4;
    static constexpr std::uint64_t record_bytes = 1048576;
    static constexpr std::uint64_t retained_record_bytes = 2097152;
    static constexpr std::uint64_t registrations = 32;
    static constexpr std::uint64_t models = 128;
    static constexpr std::uint64_t model_options = 16;
    static constexpr std::uint64_t jwk_keys = 64;
    static constexpr std::uint64_t sign_in_ms = 300000;
    static constexpr std::uint64_t http_json_ms = 30000;
    // Assistant task lifetime is unlimited. Individual transport/bootstrap requests retain their own bounds.
    static constexpr std::uint64_t inference_idle_ms = 0;
    static constexpr std::uint64_t inference_total_ms = 0;
    static constexpr std::uint64_t revoke_ms = 10000;
    static constexpr std::uint64_t callback_ms = 10000;
    static constexpr std::uint64_t question_options = 5;
    static constexpr std::uint64_t question_text_bytes = 4096;
    static constexpr std::uint64_t question_option_label_bytes = 256;
    static constexpr std::uint64_t question_option_description_bytes = 1024;
    static constexpr std::uint64_t question_answer_bytes = 4096;
};
}
