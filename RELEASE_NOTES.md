## SmartProp Editor — 3D Viewport & Gizmo Updates

* **Dynamic Gizmo Scaling**: The 3D transform gizmo now maintains a constant, comfortable screen size at any zoom level.
* **Dual-Axis & Screen Translation**: Added a center dot handle for screen-plane movement and planar rectangles (`XY`, `XZ`, `YZ`) for dual-axis translation.
* **Local Space Translation**: Moving objects in Local coordinate space now accurately follows rotated local axes.
* **Smooth Multi-Turn Rotation**: Continuous 360°+ rotation tracking without flipping or jumping bugs, with rock-solid drag stability.
* **Toolbar Mode Buttons**: Added quick-toggle tool buttons on the 3D viewport toolbar for **Select (Q)**, **Move (W)**, **Rotate (E)**, and **Scale (R)**.
* **Clean Drag Feedback**: Resolved handle ghosting so preview widgets (rotator rings, locators) update cleanly in real-time during manipulation.
* **Smart Modifier Placement**: Translation modifiers are automatically placed before rotations so objects rotate in-place around their local position.