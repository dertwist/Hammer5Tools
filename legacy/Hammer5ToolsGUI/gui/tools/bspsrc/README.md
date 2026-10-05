# bspsrc

`bspsrc.exe` is a single self-contained build of **BSPSource**
(https://github.com/ata4/bspsrc, GPL-3.0) — the Source 1 `.bsp` → `.vmf`
decompiler SourcePorter uses for `.bsp` input. It bundles its own Java runtime,
so **no system Java is required**.

- **This `.exe` is a generated artifact**, not hand-written source. It is produced
  by [`../bspsrc-launcher`](../bspsrc-launcher); see that folder's `README.md` to
  rebuild or update to a newer BSPSource release.
- It ships next to the app: the build copies it to `tools\bspsrc\bspsrc.exe` in the
  output directory, and
  [`BspDecompiler`](../../src/SourcePorter.Core/Toolchain/BspDecompiler.cs)
  resolves it there.
- Usage mirrors the upstream CLI: `bspsrc.exe [OPTIONS] <bsp>...`, with
  `-o, --output=<path>` for the `.vmf` destination. Run `bspsrc.exe -h` for the
  full list.

On first run it extracts its bundled runtime to
`%LOCALAPPDATA%\SourcePorter\bspsrc\` and reuses it afterward.
