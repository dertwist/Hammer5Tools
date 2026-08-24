# Hammer5Tools Native ABI

`Hammer5Tools.Native` publishes `Hammer5Tools.Native.dll` as a NativeAOT shared
library. The ABI version is returned by `h5t_core_abi_version`; callers must
reject versions they do not support.

All request buffers are UTF-8 and are borrowed for the duration of a call.
Successful calls return `0`. Failures return a negative status and a UTF-8 JSON
error payload. Every non-null output buffer is owned by the library and must be
released exactly once with `h5t_core_release`.

Evaluation accepts an optional cancellation handle created with
`h5t_core_create_cancellation`. Cancellation is observed before evaluation,
during nested-resource resolution, and before result projection. Release the
handle with `h5t_core_release_cancellation` after the call completes.

The SmartProp evaluation result is JSON containing primitive `models` and
`diagnostics` arrays. Transforms are row-major arrays of sixteen numbers.
