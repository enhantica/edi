# 0107. Voice input with a local Whisper model

- **Status:** Proposed
- **Date:** 2026-11-27
- **Implementation:** ⬜ Not implemented
- **Priority:** Medium

## Context

Users asked to talk to the AI assistant instead of typing (edi #185). Typing a long question about a fit is slow, and
some users are faster at speaking than at writing English. The owner set the shape on 2026-11-27: a microphone button in
the assistant's message box, speech recognised on the user's own computer, and a model that is installed only by users
who choose it.

The assistant is desktop only (ADR-0057), so is voice input. The installer already has one optional component, the AI
assistant runtime, and shows its choices as rows on the folder page instead of a component tree (ADR-0071).

## Decision

1. **Engine.** [whisper.cpp](https://github.com/ggml-org/whisper.cpp) release `v1.9.6`, which includes ggml. CMake
   downloads the release archive once with `FetchContent` and checks its SHA-256
   (`7ab15dc88022d2425ad94dcffd8abbf1b6d7018089b4e48d6b40780738e0b445`), as `cmake/EdiGuiBase.cmake` does for
   gui-components; `EDI_WHISPER_SRC` points at an unpacked copy for offline builds. It is built as a static library,
   CPU only, with `GGML_NATIVE` off so an installer runs on other machines than the build machine. On x86-64 it uses
   AVX2, FMA and F16C, present in Intel CPUs since 2013 and AMD since 2015; on Apple silicon ggml uses NEON and the
   Accelerate framework. No GPU backend: Metal or CUDA would add shader or driver packaging for a speed the CPU already
   gives (§Speed). It is built with the assistant (`EDI_APP_ASSISTANT`), so it is in the desktop app and not in WebAssembly.
2. **Model.** The multilingual Whisper "small" model in whisper.cpp's format, quantized to q5_1:
   `ggml-small-q5_1.bin`, 190 085 487 bytes, SHA-256
   `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`. The owner chose small as the middle size: tiny
   and base make too many mistakes on technical words, medium and large are 0.5 to 1.1 GB and slow on a laptop CPU.
   `tools/deps/voice/models.json` pins its URL at a fixed commit of the Hugging Face repository
   `ggerganov/whisper.cpp`, its size and its hash; `tools/deps/voice/fetch.py` downloads it over HTTPS into a cache and
   refuses a file whose size or hash differs. Packaging downloads it; the app never downloads anything, and the model
   is never committed. Tests use the tiny q5_1 model (32 152 673 bytes) pinned in the same file.
3. **Optional component.** The installer component `org.easydiffraction.app.voice`, "Voice input", holds the model and
   a small manifest (`voice-model.json`: file name, size, SHA-256) under `share/edi/voice/`; on macOS this is beside
   the signed application bundle, like the assistant runtime. It is unticked by default and depends on EasyDiffraction.
   Its row on the folder page comes below the AI assistant rows, with its size; its sorting priority is 90, after the
   assistant's 100. Maintenance Tool's Change components page adds or removes it. The engine itself is part of the app
   on every desktop system, a few megabytes; without the component the app has no model, and with no model it shows no
   microphone button. At start the app checks that the manifest exists and that the model file has the stated size;
   the hash was checked when the installer was built and again by the installer's payload manifest. A change takes
   effect after a restart, as for the assistant.
4. **Audio and privacy.** Qt Multimedia's `QAudioSource` records from the default input at 16 kHz mono; when the device
   does not offer that format the app records in the device's format and converts to 16 kHz mono in memory. The
   samples stay in memory: they are never written to a file and never sent anywhere, and they are released when the
   text is ready or the recording is cancelled. A recording stops when the user presses the button again, after two
   seconds of silence following speech, or after two minutes. Only Qt Multimedia's audio input is used; its FFmpeg
   media plugin is not shipped.
5. **Permission.** On first use the app asks for Qt's `QMicrophonePermission`. The macOS bundle declares
   `NSMicrophoneUsageDescription` ("EasyDiffraction uses the microphone only when you press the microphone button in
   the assistant, to turn your speech into text on this computer.") and the signed app has the
   `com.apple.security.device.audio-input` entitlement. Windows reports a blocked microphone through its privacy
   settings as a failed recording. Refused permission and a missing microphone each get one plain message in the
   message box's place, naming what the user can do.
6. **Recognition.** The recording is recognised in one pass after it stops, off the GUI thread through
   `run_in_background` (ADR-0020's worker is for calculations). A cancel during recognition stops whisper through its
   abort callback. Whisper uses up to eight threads (§Speed). The text is inserted at the cursor in the message box and is never
   sent by itself; the user edits it and sends it as typed text.
7. **Language.** By default Whisper detects the language. The assistant preferences may fix it; the list of languages
   comes from whisper.cpp itself, so it cannot disagree with the model.
8. **Composer button.** A round microphone button, the same component and size as the stop and send buttons, sits to
   their left. While listening it takes the accent colour and a cancel button appears beside it; Escape also cancels.
   While recognising it shows that it is busy and stays cancellable.

## Speed

Measured on 2026-11-27 with whisper.cpp `v1.9.6` built as above (AVX2, no OpenMP) and its `whisper-cli`, on a shared
Intel Xeon (Cascade Lake) virtual machine, for a 15-second clip of the public-domain JFK sample that ships with
whisper.cpp, repeated to 15 s:

| Model | Threads | Language | Encoder | Total |
|---|---|---|---|---|
| small q5_1 | 4 | detected | 11.7 s (two passes) | 13.2 to 13.5 s (three runs) |
| small q5_1 | 8 | detected | 6.4 s (two passes) | 8.9 s |
| small q5_1 | 4 | English | 5.0 s | 7.6 s |
| small q5_1 | 8 | English | 2.8 s | 5.0 s |
| tiny q5_1 | 4 | detected | | 2.0 to 2.1 s (three runs) |

Loading the small model takes 0.2 to 0.3 s and 470 MB of memory, so the app loads it for each recording and frees it
after. Detecting the language costs a second encoder pass; a fixed language in the preferences takes it away. A
shorter encoder window (`audio_ctx`) halved the encoder time but made the model repeat the phrase, so it is not used.
Laptop processors run each thread faster than this virtual machine; a measurement on an Apple silicon laptop is still
to be added here. CI never asserts a time.

## Licences

whisper.cpp and ggml are MIT. OpenAI released the Whisper code and model weights under MIT; the converted and quantized
files keep that licence. Qt Multimedia is LGPL-3.0 like the rest of Qt the desktop app links (ADR-0008); the app
ships its audio input only, not its FFmpeg media plugin. All three are rows in `DEPENDENCIES.md` with their texts in `THIRD-PARTY-NOTICES`.

## Consequences

- Users who want voice input download 190 MB more; everyone else gets the same installer size, apart from the engine's
  few megabytes in the app.
- The desktop build needs Qt Multimedia and downloads the whisper.cpp archive once per build directory.
- The installer and Maintenance Tool have one more row, and installer qualification runs with and without voice input.
- x86-64 CPUs older than AVX2 cannot use voice input; the rest of the app is unaffected because whisper code runs only
  when the button is pressed.
- Recognition starts after the user stops speaking. Showing words while the user speaks is left for later.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Operating system dictation (macOS Speech, Windows speech recognition, nothing on Linux) | No Linux, a different quality and language set per system, and Windows' good recogniser is online. |
| A cloud speech service or the assistant provider's audio input | Sends the user's voice off the computer; the owner asked for local recognition. |
| Whisper tiny, base or medium, or large-v3-turbo | Tiny and base mistake technical words; medium (539 MB at q5_0) and large-v3-turbo (574 MB at q5_0) cost three times the download for a smaller gain than small gives over base. |
| Download the model when the user first presses the button | The app would need network access and a download it can verify at run time; an installer component keeps the app offline and lets Maintenance Tool remove the model. |
| Vosk or another engine | One model per language and text without punctuation; Whisper detects the language and writes sentences. |
| A conda package for the model, like `edi-assistant-runtime` | Puts 190 MB into every developer's `app` environment; a pinned file fetched only by packaging and tests is enough. |
| miniaudio for capture | One more vendored dependency; Qt already gives capture and the permission API. |
| Streaming partial text while speaking | More code and a busier message box; left for a later task. |
