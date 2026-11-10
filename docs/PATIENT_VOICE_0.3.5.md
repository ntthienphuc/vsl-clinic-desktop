# Patient word readout in VSL Clinic 0.3.5

Each newly recognized patient word appears immediately on the doctor screen and enters a single audio queue. The queue reads the exact recognized label, without adding symptoms or using the paraphrased sentence. A repeated sign with a new result ID is read again; repeated snapshots, word confirmation and turn completion do not replay old results. Uncertain words are preceded by the spoken cue “Chưa chắc”.

The bundled bank covers all 400 recognition labels. Audio is prepared ahead of time from fixed dictionary text; the desktop app only plays local WAV files. No additional voice installation, internet connection, model inference or API account is required at runtime. Google Translate TTS supplies the fixed build-time audio; original files and provenance are retained locally. See `THIRD_PARTY_NOTICES.md` for the generated assets' scope.

Playback runs at 0.9× with pitch preserved. The first word does not wait for the 1.5-second turn endpoint. Following words are queued if audio is already playing, rather than overlapping or accelerating speech. Text updates are independent of audio and remain immediate. A speaker button beside the live word panel enables or mutes readout. An audio error leaves the text intact and shows a retry message.

Before playing audio, the doctor microphone stream is cancelled synchronously, including pending PCM and the ASR connection. Live dictation resumes after readout and a 600 ms echo guard, unless the doctor explicitly muted the microphone. Doctors should wait for readout to finish before speaking; speech begun during this brief pause is not recorded. Patient video recognition continues throughout.

New sessions, changed video sources, disconnection, or stopping the conversation cancel queued audio. Opening or reconnecting the doctor screen never reads the previous conversation history aloud. A manually corrected word is shown immediately but is not automatically read a second time.

The current 400-label recognizer, PhoWhisper model, avatar bank and supported sentence templates are unchanged. The Windows package includes the existing engine, all previous runtime assets, the voice bank and the enlarged 16:9 UI. Keep the entire `win-unpacked` folder together.

Validation uses fixed prerecorded signs and a synthetic silent microphone. It checks sequential audio, immediate word display, audio output activity, microphone pause/resume, and no network requests during readout. This does not establish live signer accuracy or room-specific microphone/speaker performance.
