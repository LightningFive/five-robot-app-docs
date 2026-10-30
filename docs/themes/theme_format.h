#pragma once

#include <cstddef>
#include <cstdint>

namespace x622 {

// Data-only skin ABI. No executable entries, filenames or brand-logo slot.
constexpr uint16_t kThemeFormatVersion = 1;
constexpr uint16_t kThemeEngineAbi = 1;
constexpr uint16_t kThemePresentationAbi = 2; // Engine 2 also accepts unchanged ABI-1 packages.
constexpr uint16_t kThemeNativeAbi = 3; // Bounded native scene composition; XApp ABI is unchanged.
constexpr uint16_t kThemeMaximumEngineAbi = kThemeNativeAbi;
// Engine negotiation is independent of the unchanged theme/1 transport framing.
constexpr size_t kThemeHeaderSize = 256;
constexpr size_t kThemeMaximumResources = 256;
constexpr uint32_t kThemeMaximumPackageBytes = 4u * 1024u * 1024u;
constexpr uint32_t kThemeMaximumLayoutBytes = 4096;
constexpr uint32_t kThemeAppearanceDark = 1u;
constexpr uint32_t kThemeAppearanceLight = 2u;
constexpr char kThemeActivePath[] = "/xapp/.theme-active.xtheme";
constexpr char kThemeBackupPath[] = "/xapp/.theme-backup.xtheme";
constexpr uint32_t kThemeIconBase = 0x100;
constexpr uint32_t kThemeArtBase = 0x200; // 0x200 is deliberately forbidden (brand).
constexpr uint32_t kThemeControlBase = 0x300;
constexpr uint32_t kThemeBatteryBase = 0x400;
constexpr uint32_t kThemeStateBase = 0x500;
constexpr uint32_t kThemeClockDigitBase = 0x600;
constexpr uint32_t kThemeHomeClockDigitBase = 0x800; // Optional separate native home-size glyph bank.
constexpr uint32_t kThemeLayoutResource = 1;
constexpr uint32_t kThemePresentationResource = 2;
constexpr uint32_t kThemeNativeResource = 3;
constexpr uint32_t kThemeFontBase = 0x900;
constexpr unsigned kThemeMaximumFonts = 8;
constexpr uint32_t kThemeMaximumPresentationBytes = 4096;
// ABI 1 mandatory images per declared appearance: icons 100..116, art
// 201..20b, controls 300..309, battery 400/402/403, states 500..502 and
// clock 600+ASCII("0123456789:-"). Light also requires preview 505.
// Terminal 401 is optional when included in frame 400. Charging 403 may be
// transparent when the reference has no separate charging mark. KeySkin
// 503/504 are optional simple rectangular controls, not claimed icon artwork.

enum class ThemeResourceFormat : uint16_t {
    A8 = 1,
    Rgb565A8 = 2, // Interleaved little-endian RGB565 + A8, three bytes per pixel.
    Rgb565 = 3,
    Layout = 4,
    Font = 5,
    Presentation = 6,
    NativeScene = 7,
};

#pragma pack(push, 1)
struct ThemeHeader {
    char magic[4];
    uint16_t format_version;
    uint16_t header_size;
    uint32_t total_size;
    uint16_t engine_abi;
    uint16_t resource_entry_size;
    uint32_t supported_appearances;
    uint16_t width;
    uint16_t height;
    uint32_t index_offset;
    uint32_t resource_count;
    uint32_t layout_offset;
    uint32_t layout_size;
    char theme_id[32];
    char display_name[48];
    char version[16];
    uint8_t payload_sha256[32];
    uint8_t reserved[84];
    uint32_t header_crc32;
};

struct ThemeResource {
    uint32_t id;
    uint16_t format;
    uint16_t flags; // Bit 0 dark, bit 1 light; zero means shared.
    uint16_t width;
    uint16_t height;
    uint32_t offset;
    uint32_t size;
    uint32_t crc32;
    uint32_t reserved[2];
};
#pragma pack(pop)

static_assert(sizeof(ThemeHeader) == kThemeHeaderSize, "Theme header ABI changed");
static_assert(sizeof(ThemeResource) == 32, "Theme resource ABI changed");

} // namespace x622
