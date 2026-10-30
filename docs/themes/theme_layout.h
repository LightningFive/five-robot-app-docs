#pragma once

#include <cstddef>
#include <cstdint>
#include <initializer_list>

namespace x622 {

// LYT1 is a bounded data schema, not a scripting or LVGL-object language.
// All integers are little endian. Rectangles are local to their page content,
// except Content/Title and the eight global elements, which are screen-local.
constexpr uint32_t kThemeLayoutMagic = 0x3154594c;
constexpr uint16_t kThemeLayoutVersion = 1;
constexpr size_t kThemePageCount = 32;
constexpr size_t kThemeColorCount = 33;
enum class ThemeSlot : uint8_t {
    Content, Title, Art, Hero, Detail, Note, Footer, Clock, Minutes, Date, Count
};
enum class ThemeElement : uint8_t {
    Wifi, Battery, Volume, BatteryFill, VolumeTrack, VolumeSpeaker,
    VolumeValue, VolumeThumb, Count
};
enum class ThemeMetric : uint8_t {
    RowHeight, HeadingRowHeight, HeaderHeight, RowRadius, IconWidth, IconHeight,
    IconX, TextX, RowInset, FocusTabWidth, TitleFont, ValueFont, HeaderFont,
    BodyFont, HeroFont, ClockSpacing, ClockAlign, DateAlign, PageMotionMs,
    SelectionMotionMs, HeaderIconX, HeaderIconY, KeyboardBorder, KeyboardRadius,
    KeyboardInset, KeyboardGap, VolumeEditHeight, TimeoutEditHeight,
    BackRowHeight, FocusPadding, Reserved30, Reserved31, Count
};
constexpr uint16_t kThemeClockStacked = 1;
constexpr uint16_t kThemeFocusTab = 2;
// A skin can keep preference editing inside its normal row (title above,
// live value/slider below) instead of expanding/reflowing the entire page.
constexpr uint16_t kThemeInlineEditors = 4;

#pragma pack(push, 1)
struct ThemeRect { int16_t x, y, width, height; };
struct ThemeLayout {
    uint32_t magic;
    uint16_t version, bytes;
    uint16_t page_count, slot_count;
    uint16_t flags, reserved;
    // Exact order of shell_theme::Palette: 27 scalar inks + home/saver 3 each.
    uint32_t dark[kThemeColorCount], light[kThemeColorCount];
    int16_t metrics[static_cast<unsigned>(ThemeMetric::Count)];
    ThemeRect elements[static_cast<unsigned>(ThemeElement::Count)];
    ThemeRect pages[kThemePageCount][static_cast<unsigned>(ThemeSlot::Count)];
};
#pragma pack(pop)
static_assert(sizeof(ThemeLayout) == 2968, "Theme layout ABI changed");

// Shared by both package verification and renderer. Values must fit the
// 240px device, including deliberate clipped illustrations at page edges.
inline bool ValidateThemeLayout(const ThemeLayout& value) {
    if (value.magic != kThemeLayoutMagic || value.version != kThemeLayoutVersion ||
        value.bytes != sizeof(value) || value.page_count != kThemePageCount ||
        value.slot_count != static_cast<unsigned>(ThemeSlot::Count) ||
        value.reserved || (value.flags & ~(kThemeClockStacked | kThemeFocusTab | kThemeInlineEditors))) return false;
    for (const auto* colors : {value.dark, value.light})
        for (unsigned i = 0; i < kThemeColorCount; ++i)
            if (colors[i] > 0xffffff) return false;
    const auto metric = [&](ThemeMetric key) { return value.metrics[static_cast<unsigned>(key)]; };
    // Validate before the renderer narrows values or uses them in arithmetic.
    // A malformed layout is rejected, never silently clamped into a new style.
    constexpr int16_t bounds[static_cast<unsigned>(ThemeMetric::Count)][2] = {
        {40,60}, {30,60}, {24,72}, {0,24}, {1,48}, {1,48}, {0,80}, {32,180},
        {0,16}, {0,48}, {12,28}, {12,28}, {12,28}, {12,28}, {12,28}, {-8,16},
        {0,2}, {0,2}, {0,1000}, {0,1000}, {0,80}, {0,48}, {0,2}, {0,16},
        {0,16}, {0,8}, {60,120}, {40,120}, {24,60}, {0,8}, {0,0}, {0,0}
    };
    for (unsigned i = 0; i < static_cast<unsigned>(ThemeMetric::Count); ++i)
        if (value.metrics[i] < bounds[i][0] || value.metrics[i] > bounds[i][1]) return false;
    if (2 * metric(ThemeMetric::FocusPadding) >= metric(ThemeMetric::RowHeight)) return false;
    const auto valid_rect = [](const ThemeRect& r) {
        return r.width >= 0 && r.height >= 0 && r.width <= 240 && r.height <= 240 &&
            r.x >= -240 && r.x <= 240 && r.y >= -240 && r.y <= 240;
    };
    for (const auto& r : value.elements) if (!valid_rect(r)) return false;
    for (const auto& page : value.pages) for (const auto& r : page) if (!valid_rect(r)) return false;
    const auto visible = [](const ThemeRect& r) { return r.width > 0 && r.height > 0; };
    // ABI page ordinals 1=Welcome and 26=Screensaver have mandatory live clock
    // and date. Optional/unused art (e.g. language selection) may remain zero.
    for (unsigned page : {1u,26u}) {
        for (unsigned slot : {static_cast<unsigned>(ThemeSlot::Content),
                              static_cast<unsigned>(ThemeSlot::Clock),
                              static_cast<unsigned>(ThemeSlot::Date)})
            if (!visible(value.pages[page][slot])) return false;
        if ((value.flags & kThemeClockStacked) &&
            !visible(value.pages[page][static_cast<unsigned>(ThemeSlot::Minutes)])) return false;
    }
    for (auto key : {ThemeElement::Wifi, ThemeElement::Battery}) {
        const auto& r = value.elements[static_cast<unsigned>(key)];
        if (!visible(r) || r.x < 0 || r.y < 0 || r.x+r.width > 240 || r.y+r.height > 240) return false;
    }
    for (auto key : {ThemeElement::Volume, ThemeElement::BatteryFill, ThemeElement::VolumeTrack,
                    ThemeElement::VolumeValue, ThemeElement::VolumeThumb})
        if (!visible(value.elements[static_cast<unsigned>(key)])) return false;
    // The FOLIO reference deliberately has no speaker in its home HUD.
    // Optional decorative speaker is disabled by a zero-area rectangle.
    const auto& speaker = value.elements[static_cast<unsigned>(ThemeElement::VolumeSpeaker)];
    if ((speaker.width == 0) != (speaker.height == 0)) return false;
    const auto& fill = value.elements[static_cast<unsigned>(ThemeElement::BatteryFill)];
    const auto& battery = value.elements[static_cast<unsigned>(ThemeElement::Battery)];
    if (fill.x < 0 || fill.y < 0 || fill.x+fill.width > battery.width ||
        fill.y+fill.height > battery.height) return false;
    for (unsigned key : {static_cast<unsigned>(ThemeMetric::TitleFont),
                        static_cast<unsigned>(ThemeMetric::ValueFont),
                        static_cast<unsigned>(ThemeMetric::HeaderFont),
                        static_cast<unsigned>(ThemeMetric::BodyFont),
                        static_cast<unsigned>(ThemeMetric::HeroFont)}) {
        const int px = value.metrics[key];
        if (px != 12 && px != 16 && px != 18 && px != 20 && px != 28) return false;
    }
    return value.metrics[30] == 0 && value.metrics[31] == 0;
}

} // namespace x622
