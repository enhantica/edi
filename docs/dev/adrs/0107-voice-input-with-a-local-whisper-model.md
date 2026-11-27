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
   gui-components; `EDI_WHISPER_SRC` points at an unpacked copy for offline builds. It is built as a static library, CPU
   only, with `GGML_NATIVE` off so an installer runs on other machines than the build machine. On x86-64 it uses AVX2,
   FMA and F16C, present in Intel CPUs since 2013 and AMD since 2015; on Apple silicon ggml uses NEON and the Accelerate
   framework. ggml is built without run-time dispatch, so the app checks the processor itself (CPUID and the operating
   system's AVX state) and shows no microphone button where those instructions are missing. No GPU backend: Metal or
   CUDA would add shader or driver packaging for a speed the CPU already gives (§Speed). It is built with the assistant
   (`EDI_APP_ASSISTANT`), so it is in the desktop app and not in WebAssembly.
2. **Model.** The multilingual Whisper "small" model in whisper.cpp's format, quantized to q5_1:
   `ggml-small-q5_1.bin`, 190 085 487 bytes, SHA-256
   `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`. The owner chose small as the middle size: tiny
   and base make too many mistakes on technical words, medium and large are 0.5 to 1.1 GB and slow on a laptop CPU.
   `tools/deps/voice/models.json` pins its URL at a fixed commit of the Hugging Face repository
   `ggerganov/whisper.cpp`, its size and its hash; `tools/deps/voice/fetch.py` downloads it over HTTPS into a cache and
   refuses a file whose size or hash differs. Packaging downloads it; the app never downloads anything, and the model
   is never committed. Tests use the tiny q5_1 model (32 152 673 bytes) pinned in the same file.
3. **Optional component.** The installer component `org.easydiffraction.app.voice`, "Voice input for AI assistant",
   holds the model and a small manifest (`voice-model.json`: file name, size, SHA-256) under `share/edi/voice/`; on
   macOS this is beside the signed application bundle, like the assistant runtime. It is unticked by default and
   depends on EasyDiffraction. Its row on the folder page comes below the AI assistant rows, with its size; its sorting
   priority is 90, after the assistant's 100. Maintenance Tool's Change components page adds or removes it. The engine
   itself is part of the app on every desktop system, a few megabytes; without the component the app has no model, and
   with no model it shows no microphone button. At start the app checks that the manifest exists and that the model file
   has the stated size; packaging checks the staged model against the pin in `tools/deps/voice/models.json` and writes
   the manifest from that pin, and the installer's payload manifest checks it again. A change takes effect after a
   restart, as for the assistant.
4. **Audio and privacy.** Qt Multimedia's `QAudioSource` records from the default input at 16 kHz mono; when the device
   does not offer that format the app records in the device's format and converts to 16 kHz mono in memory. The
   samples stay in memory: they are never written to a file and never sent anywhere, and they are released when the
   text is ready or the recording is cancelled. A recording stops when the user presses the button again, after two
   seconds of silence following speech, or after two minutes. Only Qt Multimedia's audio input is used; its FFmpeg
   media plugin is not shipped. The run log (category `edi.voice`) records each step, why a recording stopped or was
   cancelled and how long recognition took, never audio or text.
5. **Permission.** On first use the app asks for Qt's `QMicrophonePermission`. The macOS bundle's Info.plist
   (`app/resources/macos/Info.plist.in`, given to CMake so Qt links its microphone permission plugin) declares
   `NSMicrophoneUsageDescription` ("EasyDiffraction uses the microphone only when you press the microphone button in
   the assistant, to turn your speech into text on this computer.") and the signed app has the
   `com.apple.security.device.audio-input` entitlement. Windows reports a blocked microphone through its privacy
   settings as a failed recording. Refused permission and a missing microphone each get one plain message in the
   message box's place, naming what the user can do.
6. **Recognition.** The recording is recognised in one pass after it stops, off the GUI thread on a thread pool of its
   own with one thread (ADR-0020's worker is for calculations), so recordings are recognised one at a time. A cancel
   before a job starts means its model is never opened, and the audio goes at once; a cancel during recognition stops
   whisper through its abort callback. A failure in the job, such as too little memory for the model, becomes the
   message. Whisper uses one thread fewer than the processor has cores, at most eight (§Speed): its threads wait for
   each other by spinning, so one losing its core to the app's own drawing would hold up every step (with every core,
   the app on a CI machine was still recognising the test clip after ten seconds, against 1.8 s without a window). The
   model path is handed to whisper as UTF-8, which it turns into a wide path on Windows, so an install folder outside
   the code page works. The text is inserted at the cursor in the
   message box and is never sent by itself; the user edits it and sends it as typed text. A recording belongs to the
   message box that started it: hiding the assistant, switching or clearing the conversation, or a disconnect cancels
   it, and a late result for another owner is dropped.
7. **Language.** English is the default for new settings: with detection on, the multilingual model wrote English
   speech in Cyrillic (the owner, 2026-11-27). The assistant preferences offer Detect first, then every language
   whisper.cpp lists, so the list cannot disagree with the model; it is the searchable combo box every long list uses
   (ADR-0017 §7). A saved choice keeps its value, and the bundled model stays multilingual.
8. **Composer button.** A round microphone button, the same component and size as the stop and send buttons, sits to
   their left. While listening it takes the accent colour and a cancel button appears beside it; Escape anywhere in
   the message box also cancels.
   While recognising it shows that it is busy; the cancel button and Escape stop it, and another press of the
   microphone does not, so a press just after the silence stop keeps the recording.

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
| small q5_1 on Apple silicon (below) | 2 | detected | | 9.7 s for 14 s of audio |

Loading the small model takes 0.2 to 0.3 s and 470 MB of memory, so the app loads it for each recording and frees it
after. Detecting the language costs a second encoder pass; a fixed language in the preferences takes it away. A
shorter encoder window (`audio_ctx`) halved the encoder time but made the model repeat the phrase, so it is not used.
On a GitHub-hosted Apple silicon runner (macos-15-arm64, 3 cores, so 2 threads; run 46043396853, 2026-11-27) the
app's own route recognised the 14 s recording of `tests/fixtures/assistant_voice/inaugural.wav` in 9.7 s with language
detection, loading the model included; a laptop with more cores uses more threads. CI never asserts a time.

## Licences

whisper.cpp and ggml are MIT. OpenAI released the Whisper code and model weights under MIT; the converted and quantized
files keep that licence. Qt Multimedia is LGPL-3.0 like the rest of Qt the desktop app links (ADR-0008); the app
ships its audio input only, not its FFmpeg media plugin. All three are rows in `DEPENDENCIES.md` with their texts in `THIRD-PARTY-NOTICES`.

## Consequences

- Users who want voice input download 190 MB more; everyone else gets the same online installer, apart from the engine's
  few megabytes in the app. The offline installer carries every component and grows by the model's 190 MB.
- The desktop build needs Qt Multimedia and downloads the whisper.cpp archive once per build directory.
- The installer and Maintenance Tool have one more row, on the assistant's page, and installer qualification runs with
  and without voice input. Qt Multimedia's media plugins are never deployed: Linux and Windows skip the plugin type, and
  on macOS `tools/installer/build.py` removes them and the libraries only they load; the bundle audit refuses FFmpeg.
- A development build on macOS is not an application bundle, so macOS refuses it the microphone and the message box
  says so; the installed bundle carries the usage text and the permission plugin.
- Tests never use a real microphone. Inside a pytest run the app takes a recorded clip, a model path and a simulated
  missing device or refused permission from `EDI_TEST_ASSISTANT_VOICE_*` variables
  (`tests/fixtures/assistant_voice/README.md`); pull request CI runs that journey and the recogniser test on the tiny
  model, and the installed app's smoke receipt recognises a second of silence with the shipped model.
- x86-64 CPUs older than AVX2 cannot use voice input and see no microphone button; the rest of the app is unaffected
  because whisper code runs only after that check.
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
