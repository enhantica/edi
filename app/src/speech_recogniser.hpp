// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SPEECH_RECOGNISER_HPP
#define EDI_APP_SPEECH_RECOGNISER_HPP

#include <atomic>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <vector>

struct whisper_context;
struct whisper_vad_context;

namespace edi_app {

/// Turns recorded speech into text with a whisper.cpp model on this computer (ADR-0107).
///
/// The input is mono audio at `sample_rate` as floats in [-1, 1]. `recognise` blocks for the whole recording, so the
/// caller runs it off the GUI thread. One recogniser is used by one thread at a time; it holds no audio after a call.
class SpeechRecogniser {
public:
    static constexpr int sample_rate = 16000;

    struct Result {
        std::string text;      ///< The recognised text, trimmed; empty when nothing was said.
        std::string language;  ///< The language code whisper used, such as "en".
        bool cancelled = false;
        std::string error;     ///< Why recognition failed; empty on success and on cancel.
    };

    struct Language {
        std::string code;  ///< "en", "de", ...
        std::string name;  ///< whisper's English name, such as "english".
    };

    /// Loads the model file. Returns null and sets `error` when the file is missing or not a whisper model, or when
    /// this processor cannot run the engine.
    static std::unique_ptr<SpeechRecogniser> load(const std::filesystem::path& model, std::string& error);

    /// How many times this process has opened a model file; a test checks that a cancelled recognition opens none.
    static int loads();

    /// The processor has the instructions the engine is built for. On x86-64 that is AVX2 and its companions, with no
    /// fallback at run time (cmake/EdiWhisper.cmake), so nothing may call into the engine where this is false.
    static bool cpu_supported();

    ~SpeechRecogniser();
    SpeechRecogniser(const SpeechRecogniser&) = delete;
    SpeechRecogniser& operator=(const SpeechRecogniser&) = delete;

    /// Recognises `samples`. `language` is a code from `languages()`, or empty or "auto" to let the model detect it.
    /// Setting `cancel` from another thread stops the work soon; the result then has `cancelled` set and no text.
    Result recognise(std::span<const float> samples, const std::string& language, std::atomic<bool>* cancel = nullptr);

    /// The languages the engine knows, in its own order.
    static std::vector<Language> languages();

    /// The threads recognition uses: one fewer than the cores, at least one and at most eight (ADR-0107 §6).
    static int threads();

private:
    explicit SpeechRecogniser(whisper_context* context);
    whisper_context* context_;
};

/// Tells speech from other sound with whisper.cpp's voice activity detector, the Silero model (ADR-0107 §8).
///
/// It reads `frame_samples` at a time and keeps what it heard between calls, so a recording is fed as it arrives;
/// `reset` starts a new one. It runs in a millisecond or less per frame, on the caller's thread.
class SpeechDetector {
public:
    static constexpr int frame_samples = 512;

    /// Loads the detector model. Returns null and sets `error` when the file is missing or not a detector model, or
    /// when this processor cannot run the engine.
    static std::unique_ptr<SpeechDetector> load(const std::filesystem::path& model, std::string& error);

    ~SpeechDetector();
    SpeechDetector(const SpeechDetector&) = delete;
    SpeechDetector& operator=(const SpeechDetector&) = delete;

    /// Forgets the recording so far.
    void reset();

    /// The probability of speech in each frame of `samples`, whose size is a multiple of `frame_samples`; empty if the
    /// engine fails.
    std::vector<float> probabilities(std::span<const float> samples);

private:
    explicit SpeechDetector(whisper_vad_context* context);
    whisper_vad_context* context_;
};

}  // namespace edi_app

#endif  // EDI_APP_SPEECH_RECOGNISER_HPP
