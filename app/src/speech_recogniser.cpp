// SPDX-License-Identifier: BSD-3-Clause
#include "speech_recogniser.hpp"

#include <whisper.h>

#include <algorithm>
#include <climits>
#include <mutex>
#include <thread>

#if defined(__x86_64__) || defined(_M_X64)
#define EDI_VOICE_X86_64 1
#if defined(_MSC_VER) && !defined(__clang__)
#define EDI_VOICE_MSVC_CPUID 1
#include <intrin.h>
#else
#include <cpuid.h>
#endif
#endif

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

namespace {
std::atomic<int> opened_models{0};
}  // namespace

std::unique_ptr<SpeechRecogniser> SpeechRecogniser::load(const std::filesystem::path& model, std::string& error) {
    if (!cpu_supported()) {
        error = "This computer's processor cannot run the speech model: it needs AVX2.";
        return nullptr;
    }
    silence_engine_log();
    std::error_code status;
    if (!std::filesystem::is_regular_file(model, status)) {
        error = "The speech model is not installed.";
        return nullptr;
    }
    opened_models.fetch_add(1, std::memory_order_relaxed);
    auto parameters = whisper_context_default_params();
    parameters.use_gpu = false;
    // whisper takes UTF-8 and widens it itself on Windows, where path::string() would use the ANSI code page.
    const auto utf8 = model.u8string();
    const std::string path(utf8.begin(), utf8.end());
    auto* context = whisper_init_from_file_with_params(path.c_str(), parameters);
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

int SpeechRecogniser::loads() { return opened_models.load(std::memory_order_relaxed); }

std::unique_ptr<SpeechDetector> SpeechDetector::load(const std::filesystem::path& model, std::string& error) {
    if (!SpeechRecogniser::cpu_supported()) {
        error = "This computer's processor cannot run the speech model: it needs AVX2.";
        return nullptr;
    }
    silence_engine_log();
    std::error_code status;
    if (!std::filesystem::is_regular_file(model, status)) {
        error = "The speech detector is not installed.";
        return nullptr;
    }
    auto parameters = whisper_vad_default_context_params();
    parameters.n_threads = 1;
    parameters.use_gpu = false;
    const auto utf8 = model.u8string();
    const std::string path(utf8.begin(), utf8.end());
    auto* context = whisper_vad_init_from_file_with_params(path.c_str(), parameters);
    if (context == nullptr) {
        error = "The speech detector could not be read.";
        return nullptr;
    }
    std::unique_ptr<SpeechDetector> detector(new SpeechDetector(context));
    detector->reset();
    return detector;
}

SpeechDetector::SpeechDetector(whisper_vad_context* context) : context_(context) {}

SpeechDetector::~SpeechDetector() { whisper_vad_free(context_); }

// The streaming call keeps the model's state between calls and never clears it itself, and a new context starts with
// whatever its memory held: without this the same audio gave different results from run to run.
void SpeechDetector::reset() { whisper_vad_reset_state(context_); }

std::vector<float> SpeechDetector::probabilities(std::span<const float> samples) {
    // A part frame would be padded with zeros and heard as the start of a silence.
    const auto whole = samples.size() / frame_samples * frame_samples;
    if (whole == 0 || whole > static_cast<std::size_t>(INT_MAX))
        return {};
    if (!whisper_vad_detect_speech_no_reset(context_, samples.data(), static_cast<int>(whole)))
        return {};
    const float* probabilities = whisper_vad_probs(context_);
    return std::vector<float>(probabilities, probabilities + whisper_vad_n_probs(context_));
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

bool SpeechRecogniser::cpu_supported() {
#ifdef EDI_VOICE_X86_64
    static const bool supported = [] {
        const auto bit = [](unsigned int value, int n) { return ((value >> n) & 1U) != 0; };
        unsigned int leaf1 = 0;  // ECX of leaf 1
        unsigned int leaf7 = 0;  // EBX of leaf 7, subleaf 0
#ifdef EDI_VOICE_MSVC_CPUID
        int registers[4] = {};
        __cpuid(registers, 0);
        if (registers[0] < 7)
            return false;
        __cpuid(registers, 1);
        leaf1 = static_cast<unsigned int>(registers[2]);
        __cpuidex(registers, 7, 0);
        leaf7 = static_cast<unsigned int>(registers[1]);
#else
        unsigned int a = 0, b = 0, c = 0, d = 0;
        if (__get_cpuid(1, &a, &b, &c, &d) == 0)
            return false;
        leaf1 = c;
        if (__get_cpuid_count(7, 0, &a, &b, &c, &d) == 0)
            return false;
        leaf7 = b;
#endif
        // SSE4.2, AVX, FMA and F16C, and OSXSAVE, without which XGETBV below is an illegal instruction.
        if (!bit(leaf1, 20) || !bit(leaf1, 28) || !bit(leaf1, 12) || !bit(leaf1, 29) || !bit(leaf1, 27))
            return false;
        // AVX also needs the system to save the YMM registers: XCR0 bits 1 (SSE) and 2 (AVX).
#ifdef EDI_VOICE_MSVC_CPUID
        const auto enabled = static_cast<unsigned long long>(_xgetbv(0));
#else
        unsigned int low = 0, high = 0;
        __asm__ volatile("xgetbv" : "=a"(low), "=d"(high) : "c"(0U));
        const auto enabled = (static_cast<unsigned long long>(high) << 32U) | low;
#endif
        return (enabled & 6U) == 6U && bit(leaf7, 5) && bit(leaf7, 8);  // and AVX2 and BMI2
    }();
    return supported;
#else
    return true;
#endif
}

int SpeechRecogniser::threads() {
    // One core stays with the app: whisper's threads wait for each other by spinning, so one of them losing its core to
    // the window's drawing holds up every step (ADR-0107 §6).
    const unsigned available = std::thread::hardware_concurrency();
    return static_cast<int>(std::clamp(available > 1 ? available - 1 : 1U, 1U, 8U));
}

}  // namespace edi_app
