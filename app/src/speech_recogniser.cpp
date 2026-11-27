// SPDX-License-Identifier: BSD-3-Clause
#include "speech_recogniser.hpp"

#include <whisper.h>

#include <algorithm>
#include <climits>
#include <mutex>
#include <thread>

namespace edi_app {

namespace {

// whisper.cpp and ggml print their progress to stderr; the app reports failures through the result instead.
void quiet_log(enum ggml_log_level, const char*, void*) {}

void silence_engine_log() {
    static std::once_flag once;
    std::call_once(once, [] { whisper_log_set(quiet_log, nullptr); });
}

bool abort_requested(void* data) {
    const auto* cancel = static_cast<const std::atomic<bool>*>(data);
    return cancel != nullptr && cancel->load(std::memory_order_relaxed);
}

std::string trimmed(const std::string& text) {
    const auto space = [](unsigned char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; };
    auto first = std::find_if_not(text.begin(), text.end(), space);
    auto last = std::find_if_not(text.rbegin(), text.rend(), space).base();
    return first < last ? std::string(first, last) : std::string();
}

}  // namespace

std::unique_ptr<SpeechRecogniser> SpeechRecogniser::load(const std::filesystem::path& model, std::string& error) {
    silence_engine_log();
    std::error_code status;
    if (!std::filesystem::is_regular_file(model, status)) {
        error = "The speech model is not installed.";
        return nullptr;
    }
    auto parameters = whisper_context_default_params();
    parameters.use_gpu = false;
    auto* context = whisper_init_from_file_with_params(model.string().c_str(), parameters);
    if (context == nullptr) {
        error = "The speech model could not be read.";
        return nullptr;
    }
    return std::unique_ptr<SpeechRecogniser>(new SpeechRecogniser(context));
}

SpeechRecogniser::SpeechRecogniser(whisper_context* context) : context_(context) {}

SpeechRecogniser::~SpeechRecogniser() { whisper_free(context_); }

SpeechRecogniser::Result SpeechRecogniser::recognise(std::span<const float> samples, const std::string& language,
                                                     std::atomic<bool>* cancel) {
    Result result;
    if (samples.empty())
        return result;
    if (samples.size() > static_cast<std::size_t>(INT_MAX)) {
        result.error = "The recording is too long.";
        return result;
    }
    const bool detect = language.empty() || language == "auto";
    if (!detect && whisper_lang_id(language.c_str()) < 0) {
        result.error = "The speech language is not known to the model.";
        return result;
    }
    auto parameters = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    parameters.n_threads = threads();
    parameters.language = detect ? "auto" : language.c_str();
    parameters.translate = false;
    parameters.no_context = true;
    parameters.no_timestamps = true;
    parameters.print_progress = false;
    parameters.print_realtime = false;
    parameters.print_special = false;
    parameters.print_timestamps = false;
    parameters.suppress_nst = true;  // no "[music]" or "(coughs)" in the message box
    parameters.abort_callback = abort_requested;
    parameters.abort_callback_user_data = cancel;
    const int status = whisper_full(context_, parameters, samples.data(), static_cast<int>(samples.size()));
    if (cancel != nullptr && cancel->load()) {
        result.cancelled = true;
        return result;
    }
    if (status != 0) {
        result.error = "The speech could not be recognised.";
        return result;
    }
    std::string text;
    const int segments = whisper_full_n_segments(context_);
    for (int i = 0; i < segments; ++i) {
        if (const char* segment = whisper_full_get_segment_text(context_, i))
            text += segment;
    }
    result.text = trimmed(text);
    if (const char* code = whisper_lang_str(whisper_full_lang_id(context_)))
        result.language = code;
    return result;
}

std::vector<SpeechRecogniser::Language> SpeechRecogniser::languages() {
    std::vector<Language> list;
    for (int id = 0; id <= whisper_lang_max_id(); ++id) {
        const char* code = whisper_lang_str(id);
        const char* name = whisper_lang_str_full(id);
        if (code != nullptr && name != nullptr)
            list.push_back({code, name});
    }
    return list;
}

int SpeechRecogniser::threads() {
    const unsigned available = std::thread::hardware_concurrency();
    return static_cast<int>(std::clamp(available, 1U, 8U));
}

}  // namespace edi_app
