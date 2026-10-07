# Loading Editor MP4 runtime

- FFMediaToolkit: NuGet 4.8.1, MIT, upstream commit `935d411aa9deaabf6a52b565dd1a76a14d80a6f5`.
  https://github.com/radek-k/FFMediaToolkit
- Native runtime: NuGet `FFmpeg.LGPL` 20241101.1.0, LGPL 3 or later.
  https://www.nuget.org/packages/FFmpeg.LGPL/20241101.1.0
  https://github.com/IOL0ol1/FFmpeg.Publisher
- Native FFmpeg version: `N-117676-g87068b9600-20241031`, using FFmpeg 7 ABI
  (`avcodec`/`avformat` 61, `avutil` 59, `swscale` 8, `swresample` 5).
  https://github.com/FFmpeg/FFmpeg/tree/87068b9600
  Build provenance: https://github.com/BtbN/FFmpeg-Builds
- The shared build disables GPL/nonfree components, includes OpenH264, and
  statically links its external dependencies. The DLLs remain separately
  replaceable under `ffmpeg/win-x64` beside the managed assemblies.

Core references FFMediaToolkit and copies only the Windows x64 native DLLs from
the pinned package. No runtime download, FFmpeg executable, or system install is
used. Published application assembly paths put these files under
`bin/ffmpeg/win-x64`. GIF and WebP remain ImageSharp exports.

MP4 frames are streamed through ImageSharp pixel buffers to OpenH264 at 2 FPS.
The first frame determines the even output dimensions. Later images are padded
to the same dimensions while preserving their aspect ratio. Low, Medium and High
use target bitrates of 2, 5 and 10 Mbit/s respectively. Encoding and finalization
run on a worker; cancellation or input failures discard the staged output.

Native ABI upgrades must update the FFMediaToolkit bindings and native package
together and rerun the encoding/decoding regression test and publish check.
