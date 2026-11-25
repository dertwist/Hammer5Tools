## Hammer5Tools 6.0.9

### Audio & SoundEvent Editor
* Fixed deadlocks and crashes when quickly switching between audio files
* Fixed MP3 decoding, MP3 noise in the Wave Editor, and VU meter levels/resetting
* Fixed `WaveEditor` file-locking (`PermissionError`) when playing after edits and cleaned up temporary WAV files on tab close
* Fixed `0%` system/mixer volume handling, disconnected-device fallback, and `QAudioOutput`/COM leaks
* Fixed crashes on addon switch (`SoundEventEditor` explorer, `PropertiesWindow` focus/selection, and `soundevents_cache` collisions)
* Made internal soundevent previews read-only and added `.ogg` preview support in Explorer
* Improved `.vsnd`/`.vsndevts` VPK reading and caching in Core

### MapBuilder
* Fixed compiler crash exit code overflow

### CLI & Automation
* Removed the MCP server in favor of CLI.
* Added `SKILL.md` and `AUTOMATION.md` with CLI, Core DLL, and Source 2 format docs
