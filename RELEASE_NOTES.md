## 🔊 SoundEvent Editor
* Play internal `.vsnd` audio previews directly from memory (`QBuffer`) without disk cache writes or cache walks.
* Fixed missing waveform display for MP3-backed sound assets.
* Optimized `.vsnd` buffer conversions (1,200x speedup) and offloaded decoding to a background thread to eliminate UI freezes on selection.

## 🔧 Main App
* Minor UI/UX refactoring.
* Receive dev versions feature.
* Unreal Converter: fixed ghost actors in Blueprint conversion.