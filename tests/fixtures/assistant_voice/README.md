# Assistant speech fixture

`inaugural.wav` is the public-domain excerpt of John F. Kennedy's 1961 inaugural
address from [whisper.cpp v1.8.2](https://github.com/ggml-org/whisper.cpp/blob/v1.8.2/samples/jfk.wav).
The [JFK Library transcript](https://www.jfklibrary.org/archives/other-resources/john-f-kennedy-speeches/inaugural-address-19610120)
is the reference. The original WAV is 352,078 bytes, 16 kHz mono signed 16-bit
PCM, and has SHA-256 `59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e`.

Stage [ggml-tiny-q5_1.bin](https://huggingface.co/ggerganov/whisper.cpp/blob/c521a4b02f422512d734391fdf08bb08c0862f68/ggml-tiny-q5_1.bin)
(MIT, 32,152,673 bytes) in `build/voice-models/` before running the desktop tests.
The test checks its SHA-256
before loading it. The tests perform no download. Installer tests use distinct
placeholder bytes for the release model so they can check component ownership
without a release build.

The native assistant test host receives the fixture through these test-only
environment variables:

| Variable | Value |
| --- | --- |
| `EDI_TEST_ASSISTANT_VOICE_MODEL` | Local model path, or a deliberately absent path |
| `EDI_TEST_ASSISTANT_VOICE_WAV` | Local input recording |
| `EDI_TEST_ASSISTANT_VOICE_CAPTURE` | `available`, `no-device`, or `permission-denied` |

The test host substitutes the microphone and permission boundary. The app's
recording state, recognition worker and composer use their usual paths.

The native fixture presses `assistant.voice`, observes `assistant.voiceIndicator`
and its dots, and cancels with Escape. With absent weights it checks the
`assistant.voiceMissing` note and the normal Send action.
