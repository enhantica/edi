# Assistant speech fixture

`inaugural.wav` is the public-domain excerpt of John F. Kennedy's 1961 inaugural
address from [whisper.cpp v1.8.2](https://github.com/ggml-org/whisper.cpp/blob/v1.8.2/samples/jfk.wav).
The [JFK Library transcript](https://www.jfklibrary.org/archives/other-resources/john-f-kennedy-speeches/inaugural-address-19610120)
is the reference. The original WAV is 352,078 bytes, 16 kHz mono signed 16-bit
PCM, and has SHA-256 `59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e`.

`classroom-noise.wav` is room noise with no speech in it: a ceiling light and
ventilation in a chemistry lecture room, recorded on 2024-08-27. It is an excerpt of
[Geräusche aus einem Chemie-Lehrsaal 20240827 C1003.wav](https://commons.wikimedia.org/wiki/File:Ger%C3%A4usche_aus_einem_Chemie-Lehrsaal_20240827_C1003.wav)
by PantheraLeo1359531, Wikimedia Commons, under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), cut and converted to
16 kHz mono signed 16-bit PCM.

Stage [ggml-tiny-q5_1.bin](https://huggingface.co/ggerganov/whisper.cpp/blob/c521a4b02f422512d734391fdf08bb08c0862f68/ggml-tiny-q5_1.bin)
(MIT, 32,152,673 bytes) and the Silero speech detector
[ggml-silero-v6.2.0.bin](https://huggingface.co/ggml-org/whisper-vad/blob/9ffd54a1e1ee413ddf265af9913beaf518d1639b/ggml-silero-v6.2.0.bin)
(MIT, 885,098 bytes) in `build/voice-models/` before running the desktop tests:
`pixi run voice-models --test` downloads both and checks them against
`tools/deps/voice/models.json`. The test checks the model's SHA-256
before loading it. The C++ voice tests read both from there, or from
`EDI_VOICE_TEST_MODEL` and `EDI_VOICE_TEST_DETECTOR`. The tests perform no download. Installer tests use distinct
placeholder bytes for the release model so they can check component ownership
without a release build.

The native assistant test host receives the fixture through these test-only
environment variables:

| Variable | Value |
| --- | --- |
| `EDI_TEST_ASSISTANT_VOICE_MODEL` | Local model path, or a deliberately absent path |
| `EDI_TEST_ASSISTANT_VOICE_WAV` | Local input recording |
| `EDI_TEST_ASSISTANT_VOICE_CAPTURE` | `available`, `no-device`, or `permission-denied` |
| `EDI_TEST_ASSISTANT_VOICE_DETECTOR` | Local detector path; without it the app takes the `ggml-silero-*.bin` beside the model |

The test host substitutes the microphone and permission boundary. The app's
recording state, recognition worker and composer use their usual paths.

The native fixture presses `assistant.voice`, observes `assistant.voiceIndicator`
and its dots, and cancels with Escape. With absent weights it checks the
`assistant.voiceMissing` note and the normal Send action.
