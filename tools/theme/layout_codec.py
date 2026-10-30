"""Public LYT1 field order and encoder, extracted from the device theme tools."""
import struct

PAGE_NAMES = ['Boot', 'Welcome', 'Menu', 'Apps', 'Settings', 'Wireless', 'System', 'Diagnostics', 'DiagnosticLive', 'DiagnosticIo', 'DiagnosticDisplay', 'DiagnosticAudio', 'DiagnosticServices', 'DiagnosticStorage', 'Wifi', 'WifiNetworks', 'WifiKeyboard', 'WifiPortal', 'Bluetooth', 'InstallMethods', 'Experimental', 'Installer', 'LanguageSelect', 'ThemeSelect', 'WifiConnecting', 'WifiFailed', 'Screensaver', 'InstallAP', 'InstallLAN', 'InstallUSB', 'InstallSuccess', 'PowerOff']
SLOT_NAMES = ['Content', 'Title', 'Art', 'Hero', 'Detail', 'Note', 'Footer', 'Clock', 'Minutes', 'Date']
METRIC_NAMES = ['RowHeight', 'HeadingRowHeight', 'HeaderHeight', 'RowRadius', 'IconWidth', 'IconHeight', 'IconX', 'TextX', 'RowInset', 'FocusTabWidth', 'TitleFont', 'ValueFont', 'HeaderFont', 'BodyFont', 'HeroFont', 'ClockSpacing', 'ClockAlign', 'DateAlign', 'PageMotionMs', 'SelectionMotionMs', 'HeaderIconX', 'HeaderIconY', 'KeyboardBorder', 'KeyboardRadius', 'KeyboardInset', 'KeyboardGap', 'VolumeEditHeight', 'TimeoutEditHeight', 'BackRowHeight', 'FocusPadding', 'Reserved30', 'Reserved31']
ELEMENT_NAMES = ['Wifi', 'Battery', 'Volume', 'BatteryFill', 'VolumeTrack', 'VolumeSpeaker', 'VolumeValue', 'VolumeThumb']
COLOR_NAMES = ['background', 'gradient', 'accent', 'accent_dim', 'text', 'muted', 'warning', 'depth_base', 'icon', 'value', 'selected_text', 'divider', 'yellow', 'red', 'success', 'title_backplate', 'status_foreground', 'status_inactive', 'charging', 'volume_frame', 'volume_track', 'volume_fill', 'volume_foreground', 'key_wave', 'rain_background', 'rain_head', 'rain_trail', 'home_art_blue', 'home_art_red', 'home_art_yellow', 'screensaver_art_blue', 'screensaver_art_red', 'screensaver_art_yellow']

def pack_layout(layout: dict) -> bytes:
    data = bytearray(struct.pack("<I6H", 0x3154594c, 1, 2968, 32, 10, layout["flags"], 0))
    for appearance in ("dark", "light"):
        data.extend(struct.pack("<33I", *(layout[appearance][name] for name in COLOR_NAMES)))
    data.extend(struct.pack("<32h", *(layout["metrics"][name] for name in METRIC_NAMES)))
    for name in ELEMENT_NAMES:
        data.extend(struct.pack("<4h", *layout["elements"][name]))
    for name in PAGE_NAMES:
        for slot in SLOT_NAMES:
            data.extend(struct.pack("<4h", *layout["pages"][name][slot]))
    if len(data) != 2968:
        raise ValueError(f"LYT1 size mismatch: {len(data)}")
    return bytes(data)
