# SmartProp evaluation source

Source: https://github.com/ValveResourceFormat/ValveResourceFormat
Revision: `5fb6e433b87cae3fe4bf76d7ff427fad00c43e38`.
License: MIT; see LICENSE.

`Core/Format/SmartProps/Evaluation/` contains the SmartProp evaluator and its
supporting classes from `ValveResourceFormat/Resource/ResourceTypes/SmartProp/`,
excluding the map evaluator. `SmartPropTransformMath.cs` contains the required
Euler-angle, matrix decomposition and Bezier methods from `EntityTransformHelper`
and `MathUtils`. The tests under `Tests/Hammer5Tools.Core.Tests/SmartProps/` are
adapted from the same revision's SmartProp tests, excluding map integration.

Adaptations use the Core namespace, file-scoped namespaces, internal visibility
and project formatting. The managed and NativeAOT projects compile the same
evaluator sources. Existing Core adapters still own cancellation, limits,
diagnostics, widgets and correction passes. Evaluation behavior is retained.

ValveResourceFormat parsing uses NuGet version `20.0.6980`; evaluation no longer
requires a custom ValveResourceFormat DLL. The upstream license is included in
published output as `licenses/ValveResourceFormat-SmartProps.txt` (under `bin/` in the arranged Windows package).
