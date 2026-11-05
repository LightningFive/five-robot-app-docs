# Indexed theme fonts — ABI 4 candidate

Status: host-tested development interface, not a frozen SDK/release. System
version candidate 2.0.32; XAPP API 2.16 and format 1 remain unchanged by this
theme-only change. New visual assets require user review before packaging.

## Compatibility and ownership

Theme ABI 1–3 retain their loaders and FNT2 layout. ABI 4 requires native scene
version 3; ABI/version mismatches reject installation. FNT3 is a theme-internal
resource, not a reinterpretation of an APP's existing font API. The theme
renderer owns no task, audio resource or full-font allocation. APP font fallback
remains supported for characters absent from the selected theme bank.

The package cap stays **4 MiB**, with no partition change. Each FNT3 bank is at
most 2 MiB / 24,576 codepoints. The runtime uses a sorted index and seeks only
the requested glyph. Its decoded glyph cache remains 4 KiB; the extra packed
index memo fields add 256 bytes to the native core (20,712 bytes on host).
This is not the total UI heap budget. Image caches remain optional and separate.

## Lossless mask rows (ABI 4 candidate)

Native scene version 3 also accepts image asset kind 6 for constant-colour
artwork. ABI 1–3 never accept this encoding. Layout: tile width/height u16,
R/G/B u8, reserved u8=0, then `height+1` contiguous u32 row offsets and bounded
row runs. Runs use the same control byte as RGBA rows, but carry one A8 byte
per repeated/literal pixel. Nonzero alpha reconstructs the header RGB; zero
alpha reconstructs transparent black. No alpha quantization is permitted.

The converter chooses this encoding only after verifying every original RGBA
pixel can be reconstructed exactly and the result is smaller. Multi-colour
images retain their existing encoding. Rendering uses the existing RGBA row
scratch and compressed-image cache; no persistent memory, full-image decoder,
task, or audio ownership changes are introduced. Dimensions, row offsets,
reserved bytes, exact run lengths, terminal offsets, node references and ABI
compatibility are checked by all three validators.

`tools/theme/compact_native_masks.py SOURCE OUTPUT` creates a new package
with refreshed checksums and a conversion report; it never overwrites its
input. The approved R7/common-font candidate shrinks from 4,059,324 to
3,225,205 bytes (397 masks; 834,119 bytes saved). Host verification includes
105 codec boundaries, 13 valid/corrupt packages across Python/C++/browser,
1,680 full and clipped frames with exact RGB565 equality, six live ShellUi
golden frames, 248 injected read failures, and 91 legacy transition checks.
An equal-render IO sample reads 337,245 versus 213,753 bytes. This is not a
device frame-rate or installation-acceptance claim.

## FNT3 wire layout (little endian)

The 24-byte font header retains FNT2 metrics: magic `FNT3`, version 1, header
bytes 24, count u16, line height u16, baseline i16, reserved u16 = 0, bitmap
offset u32, total bytes u32. Bitmap offset is exactly `24 + count * 20`.

Each 20-byte entry: codepoint u32, relative payload offset u32, advance u16,
width u8, height u8, x/y bearings i16, stored bytes u16, codec u16. Entries are
strictly sorted, unique and contiguous. Surrogates/control codepoints, invalid
metrics, overflowing spans, trailing data and unknown codecs reject the bank.

Codec 0 stores packed A4 pixels, high nibble first. Codec 1 stores byte runs:
the control byte's low 7 bits plus one give run length; high bit set means
repeat the following byte, otherwise copy that many literal bytes. Each glyph
is independently decoded. Maximum encoded span 516 bytes, decoded span 512
bytes. The decoder requires exact input/output extents; no history or global
dictionary. Image-row scratch is reused while drawing text, not concurrently.

## Completeness and failure behavior

Version 3 preserves the version-2 system recipe IDs and requires all 140
slots. It validates mandatory default symbols, clock/battery/date bindings,
four visible app-row bindings/icons, installer status/detail and AI pairing/
chat/recording fields. Both languages of every literal must be covered by the
referenced font, including literals that have pre-rendered image variants.
This does not imply every arbitrary future APP name fits every font bank.

Container CRC/SHA, resource graph, glyph runs and semantic completeness are
checked independently. Python authoring, browser installation and device C++
parsers apply the same new restrictions. Runtime I/O/decompression failure is
sticky until reload and uses the existing safe-theme recovery path; it is not
treated as an ordinary missing character or a partially successful render.

## Measured candidate and remaining gates

The development converter preserves every original glyph's metrics/pixels,
compresses each existing subset independently and extends explicitly selected
banks. Current Pixel Purple fixture extends bank 11 at 22px with GB2312 common
characters and supported symbols: 7,541 total glyphs, 1,621,790-byte bank.
The complete fixture is 4,128,942 bytes. Other sizes retain their existing
subsets; this is not a promise of full Chinese coverage at every size.

Host evidence:

- 7,541 glyphs match independent source rasterization or the original FNT2
  bytes. Cold reads are at most 516 bytes; immediate warm requests read zero.
- 1,026 compression boundary/roundtrip cases.
- 21 valid/adversarial packages checked with repaired outer SHA/CRC so tests
  reach semantic validation: all three parsers agree.
- 140 original rendered pages match prior output at 0/4/16 KiB image-cache
  budgets; dynamic UI, sticky failures and 91 legacy theme transitions pass.

Fixtures/reports: `build/system-integrity-api217-20261103/font3/`.
Reproduction: `tools/xapp/test_indexed_theme.py --help` and
`tools/theme/extend_native_fonts.py --help`.

Release gates still pending: new icon review, font redistribution notice,
device cold/warm latency and four-board combined market/theme/audio tests.
The source font's hash is recorded by the converter; its local directory has
no license notice. Do not publish the extended-font package before resolving
that notice. No firmware, theme or SDK release is claimed by host tests.
