## Loading Screen Editor

* Screenshots are now taken from Hammer's saved editor cameras (Window > Saved Cameras) by default. A setting in Preferences switches back to `point_camera` entities.
* A map without cameras now shows a warning explaining how to add them, instead of sending commands that take no shots.
* Existing loading-screen shots are no longer deleted when the map has no cameras.
* Maps are read about 2.5x faster when taking screenshots, importing a VMAP into the SmartProp Editor, or creating an addon from a map.

## SmartProp Editor

* Added the Random Color Tint Color operator and the Material Attributes filter.
* Added Trace To Point and Trace To Line properties, gradient colors for Material Tint, and the No Roll option for Place On Path.
* Added Color Selection Mode and Orientation Mode variables.
* Direction variables are now saved as `DirectionVector`, the class CS2 expects. Files using the old name still open.
* Removed operators that CS2 does not have, and dropped the "not verified" warning from elements that are now confirmed.

## Unreal Porter

* Fixed exported SmartProps using selection criteria that CS2 does not support, so choice and expression conditions now work in Hammer.

