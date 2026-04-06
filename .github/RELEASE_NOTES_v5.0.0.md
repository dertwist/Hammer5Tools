## 📄 Dev versions

* Every commit now triggers an automatic build of the application at this link: [https://github.com/dertwist/Hammer5Tools/releases/tag/dev](https://github.com/dertwist/Hammer5Tools/releases/tag/dev)

## ✏️ SmartProp Editor

- Added `Material` variable type
- Added `Material replacement` property
- Added undo/redo support for variable additions, deletions, and edits (choices have limited undo history support)
- Added drag-and-drop reorder support for modifiers and selection criteria
- Improved property undo with incremental updates instead of full rebuilds
- Extended variable handling in choices to support `string` and `vector3d` types
- Added warning property for unverified functionality
- Optimized property widget pooling and completion cache handling
- Implemented asynchronous property frame initialization and batch processing

## 🔊 SoundEvent Editor

- Added a history dock for visualizing the undo/redo action history
- Added a soundevent player widget
- Added **Internal Soundevent Explorer** with context menu integration (copy, play, preview)
- Added multi-select support in the explorer with a context menu for copying asset names
- Added bulk paste for file paths from clipboard in the Files property
- Added duplicate sound events command
- Enhanced undo functionality with property deletion tracking
- Minor fixes and tooltips improvements
- Added clipboard paste and expand/collapse functionality to the property editor

## 🖼️ Loading Editor

- Added SVG rescaling functionality with fixed output dimensions
- Added new checkbox and tips UI for SVG rescaling
