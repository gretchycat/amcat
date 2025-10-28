# amcat Changelog

## v0.2.1 — Build Bugfix
- Fixed packaging issue with multiple top-level directories.
- Updated pyproject.toml to explicitly include only the `amcat` package.
- Adjusted license field for SPDX compliance.
- No functional code changes.

## v0.2.0 — Resource & Reference Release
- Added support for base64-embedded audio and MIDI blocks via ESC[MA;...]BEL.
- Added media caching for reusable sound and MIDI resources.
- Implemented playback-by-reference (ESC[MF play=<id>]).
- Introduced SynthEngine.play_midi_bytes() using FluidSynth.
- Added tests for inline MIDI and cache reuse.
- Added terminal-music-extension.md draft (repo-only spec).
- Bumped version to 0.2.0.
