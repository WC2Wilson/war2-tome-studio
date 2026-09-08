#!/usr/bin/env python3
"""Warcraft II TOME Studio.

Dependency-free Tkinter editor for the Warcraft II TOME.1-.4
resource containers.  It preserves resource bytes unless a record is edited.
"""
from __future__ import annotations

import io
import csv
import math
import os
import re
import shutil
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from maindat_names import MAINDAT_NAMES


APP_NAME = "Warcraft II TOME Studio"
FORMAT_TAG = 25

# Names confirmed by REZDAT.H in the Warcraft II source tree.  The repetitive
# dialog records after 3032 are named separately below where useful.
REZ_NAMES = {
    3000: "Human dialog graphics", 3001: "Orc dialog graphics",
    3002: "CD icon", 3003: "Human 128x144 dialog background",
    3004: "Orc 128x144 dialog background", 3005: "Human 144x128 dialog background",
    3006: "Orc 144x128 dialog background", 3007: "Human 192x128 dialog background",
    3008: "Orc 192x128 dialog background", 3009: "Human 144x64 dialog background",
    3010: "Orc 144x64 dialog background", 3011: "Human 176x176 dialog background",
    3012: "Orc 176x176 dialog background", 3013: "Title menu picture",
    3014: "Title menu palette", 3015: "Chatroom picture", 3016: "Chatroom palette",
    3017: "Human act palette", 3018: "Orc act palette",
    3019: "Human act I picture", 3020: "Orc act I picture",
    3021: "Human act II picture", 3022: "Orc act II picture",
    3023: "Human act III picture", 3024: "Orc act III picture",
    3025: "Human act IV picture", 3026: "Orc act IV picture",
    3027: "Credits palette", 3028: "Credits picture",
    3029: "Human victory picture", 3030: "Orc victory picture",
    3031: "Human victory palette", 3032: "Orc victory palette",
    3033: "Textbox dialog", 3034: "Infobox dialog", 3035: "Infobox 2 dialog",
    3036: "Sidebox dialog", 3037: "Status portrait dialog", 3038: "Status button dialog",
    3039: "F10 status dialog", 3040: "Title dialog", 3041: "Main menu dialog",
    3042: "Multiplayer dialog", 3043: "New campaign dialog", 3044: "Game menu dialog",
    3045: "Help menu dialog", 3046: "Abort menu dialog", 3047: "Options dialog",
    3048: "Sound dialog", 3049: "Interface dialog", 3050: "Speed dialog",
    3051: "Quit dialog", 3052: "Restart dialog", 3053: "Return to chatroom dialog",
    3054: "Custom game confirmation", 3055: "Surrender dialog", 3056: "Quit to menu dialog",
    3057: "Victory dialog", 3058: "Defeat dialog", 3059: "2-player mission stats",
    3060: "4-player mission stats", 3061: "6-player mission stats", 3062: "8-player mission stats",
    3063: "Save game dialog", 3064: "Load game dialog", 3065: "Load title dialog",
    3066: "Ally filter dialog", 3067: "Message filter dialog", 3068: "OK/Cancel dialog",
    3069: "Large OK dialog", 3070: "OK dialog", 3071: "Cancel dialog",
    3072: "Direct-link dialog", 3073: "Modem dialog", 3074: "Modem configuration dialog",
    3075: "View/join game dialog", 3076: "Network wait dialog", 3077: "Tips dialog",
    3078: "Connect dialog", 3079: "Copy protection dialog", 3080: "Chat MJ dialog",
    3081: "Objectives dialog", 3082: "Human dispatch dialog", 3083: "Orc dispatch dialog",
    3084: "Credits dialog", 3085: "Timeout dialog", 3086: "Help dialog",
    3087: "Game-name dialog", 3088: "Act interlude dialog", 3089: "File filter dialog",
    3090: "Finale dialog", 3091: "Patch icon", 3092: "Patched chat dialog",
    3093: "Beyond the Dark Portal credits palette", 3094: "Beyond the Dark Portal credits picture",
    3095: "Beyond the Dark Portal credits dialog",
    3096: "Expansion human act I", 3097: "Expansion orc act I",
    3098: "Expansion human act II", 3099: "Expansion orc act II",
    3100: "Expansion human act III", 3101: "Expansion orc act III",
    3102: "Expansion human act IV", 3103: "Expansion orc act IV",
}


def resource_name(resource_id: int) -> str:
    if resource_id in REZ_NAMES:
        return REZ_NAMES[resource_id]
    if 1000 <= resource_id <= 1527:
        symbol = MAINDAT_NAMES.get(resource_id)
        if symbol:
            return symbol.replace("_", " ").title()
        inferred = (
            (1048, 1071, "Campaign GRP/header resource"),
            (1076, 1079, "Veteran campaign GRP/header resource"),
            (1083, 1108, "Multiplayer map resource"),
            (1111, 1112, "Attract/demo resource"),
            (1139, 1158, "Cursor resource"),
            (1202, 1217, "OPL2 music resource"),
            (1219, 1234, "OPL3 music resource"),
            (1257, 1276, "Expansion campaign GRP/header resource"),
        )
        for first, last, label in inferred:
            if first <= resource_id <= last:
                return f"{label} {resource_id - first + 1}"
        return "Unlabeled MAINDAT resource"
    if resource_id == 2000:
        return "Load Custom menu strings"
    if resource_id == 2001:
        return "Sound-bank marker"
    fixed = {
        2002: "Human victory narration", 2003: "Orc victory narration",
        2004: "Human veteran I victory", 2005: "Human veteran II victory",
        2006: "Orc veteran I victory", 2007: "Orc veteran II victory",
        2008: "Orc veteran III victory",
    }
    if resource_id in fixed:
        return fixed[resource_id]
    if 2009 <= resource_id <= 2064:
        n = resource_id - 2009
        return f"Human campaign mission {n // 4 + 1}, narration {n % 4 + 1}"
    if 2065 <= resource_id <= 2068:
        return f"Human veteran narration {resource_id - 2064}"
    if 2069 <= resource_id <= 2109:
        n = resource_id - 2069
        return f"Orc campaign narration {n // 4 + 1}.{n % 4 + 1}"
    if resource_id == 4000:
        return "Textbox strings"
    if resource_id == 4001:
        return "Units, commands, upgrades, spells and status strings"
    if 4099 <= resource_id <= 4122:
        side = "Human" if (resource_id - 4099) % 2 == 0 else "Orc"
        return f"{side} expansion campaign briefing"
    if resource_id == 4123:
        return "Credits"
    if resource_id in (4125, 4126):
        return "CD insertion/copy-protection text"
    return ""


def lzss_unpack(data: bytes) -> bytes | None:
    """Decode Blizzard GDS LZSS (source: GDS/LZSS.C)."""
    if len(data) < 5:
        return None
    header = struct.unpack_from("<I", data)[0]
    if header >> 24 != 0x20:
        return None
    wanted = header & 0xFFFFFF
    source = memoryview(data)[4:]
    ring = bytearray(4096)
    output = bytearray()
    src = flags = ring_dst = 0
    try:
        while len(output) < wanted:
            flags >>= 1
            if not flags & 0x100:
                flags = source[src] | 0xFF00
                src += 1
            if flags & 1:
                value = source[src]
                src += 1
                output.append(value)
                ring[ring_dst] = value
                ring_dst = (ring_dst + 1) & 0xFFF
            else:
                token = source[src] | (source[src + 1] << 8)
                src += 2
                length = (token >> 12) + 3
                ring_src = token & 0xFFF
                for _ in range(min(length, wanted - len(output))):
                    value = ring[ring_src]
                    ring_src = (ring_src + 1) & 0xFFF
                    output.append(value)
                    ring[ring_dst] = value
                    ring_dst = (ring_dst + 1) & 0xFFF
        return bytes(output)
    except (IndexError, ValueError):
        return None


def unpack_resource(data: bytes) -> tuple[bytes, str]:
    decoded = lzss_unpack(data)
    if decoded is not None:
        return decoded, "GDS LZSS"
    if len(data) >= 4 and struct.unpack_from("<I", data)[0] == len(data) - 4:
        inner = data[4:]
        # A leading length is part of the string-table format itself, but is
        # merely an outer wrapper for WAV, bitmap and palette resources.
        if inner.startswith(b"RIFF") or bitmap_info(inner) or palette_rgb(inner):
            return inner, "size wrapper"
    return data, "none"


def bitmap_info(data: bytes) -> tuple[int, int, bytes] | None:
    if len(data) < 5:
        return None
    width, height = struct.unpack_from("<HH", data)
    if not width or not height or width > 4096 or height > 4096:
        return None
    size = width * height
    if len(data) - 4 != size:
        return None
    return width, height, data[4:]


def palette_rgb(data: bytes) -> list[tuple[int, int, int]] | None:
    if len(data) != 768:
        return None
    scale = 4 if max(data, default=0) <= 63 else 1
    return [(min(255, data[i] * scale), min(255, data[i + 1] * scale), min(255, data[i + 2] * scale))
            for i in range(0, 768, 3)]


@dataclass
class GrpFrame:
    dx: int
    dy: int
    width: int
    height: int
    offset: int


@dataclass
class GrpImage:
    width: int
    height: int
    frames: list[GrpFrame]


def parse_grp(data: bytes) -> GrpImage | None:
    """Recognize the original Warcraft II PC GRP header."""
    if len(data) < 14:
        return None
    count, width, height = struct.unpack_from("<HHH", data)
    header_end = 6 + count * 8
    if not (1 <= count <= 512 and 1 <= width <= 512 and 1 <= height <= 512 and header_end <= len(data)):
        return None
    frames = []
    for number in range(count):
        dx, dy, fw, fh, offset = struct.unpack_from("<BBBBI", data, 6 + number * 8)
        if not fw or not fh or dx + fw > width + 1 or dy + fh > height + 1:
            return None
        if offset < header_end or offset + fh * 2 > len(data):
            return None
        frames.append(GrpFrame(dx, dy, fw, fh, offset & 0x7FFFFFFF))
    group = GrpImage(width, height, frames)
    try:
        decode_grp_frame(data, frames[0])
        if len(frames) > 1:
            decode_grp_frame(data, frames[-1])
    except (ValueError, struct.error):
        return None
    return group


def decode_grp_frame(data: bytes, frame: GrpFrame) -> bytes:
    """Decode Warcraft II scanline RLE; index 0 is transparent."""
    result = bytearray(frame.width * frame.height)
    for y in range(frame.height):
        row_offset = struct.unpack_from("<H", data, frame.offset + y * 2)[0]
        source = frame.offset + row_offset
        x = 0
        guard = 0
        while x < frame.width:
            if source >= len(data) or guard > frame.width * 4 + 32:
                raise ValueError(f"Invalid GRP RLE in scanline {y}")
            guard += 1
            command = data[source]
            source += 1
            if command & 0x80:
                x += command & 0x7F
            elif command & 0x40:
                count = command & 0x3F
                if not count or source >= len(data) or x + count > frame.width:
                    raise ValueError(f"Invalid GRP repeat in scanline {y}")
                result[y * frame.width + x:y * frame.width + x + count] = bytes((data[source],)) * count
                source += 1
                x += count
            else:
                count = command
                if not count or source + count > len(data) or x + count > frame.width:
                    raise ValueError(f"Invalid GRP literal in scanline {y}")
                result[y * frame.width + x:y * frame.width + x + count] = data[source:source + count]
                source += count
                x += count
        if x != frame.width:
            raise ValueError(f"GRP scanline {y} overran its width")
    return bytes(result)


def render_grp_canvas(data: bytes, group: GrpImage, frame_number: int) -> bytes:
    frame = group.frames[frame_number]
    pixels = decode_grp_frame(data, frame)
    canvas = bytearray(group.width * group.height)
    for y in range(frame.height):
        dest = (frame.dy + y) * group.width + frame.dx
        source = y * frame.width
        canvas[dest:dest + frame.width] = pixels[source:source + frame.width]
    return bytes(canvas)


def parse_pud(data: bytes) -> list[tuple[str, bytes]] | None:
    """Parse Warcraft II's chunked PUD map container."""
    if not data.startswith(b"TYPE"):
        return None
    chunks = []
    offset = 0
    while offset + 8 <= len(data):
        tag_bytes = data[offset:offset + 4]
        if not all(32 <= value < 127 for value in tag_bytes):
            return None
        size = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + size
        if end > len(data):
            return None
        chunks.append((tag_bytes.decode("ascii"), data[offset + 8:end]))
        offset = end
    return chunks if chunks and offset == len(data) else None


def pud_minimap(data: bytes) -> tuple[int, int, bytes] | None:
    chunks = parse_pud(data)
    if not chunks:
        return None
    lookup = {tag: payload for tag, payload in chunks}
    dims = lookup.get("DIM ") or lookup.get("DIM")
    mtxm = lookup.get("MTXM")
    if not dims or len(dims) < 4 or not mtxm:
        return None
    width, height = struct.unpack_from("<HH", dims)
    if not width or not height or len(mtxm) < width * height * 2:
        return None
    pixels = bytearray(width * height)
    for i in range(width * height):
        tile = struct.unpack_from("<H", mtxm, i * 2)[0]
        pixels[i] = (tile >> 4) & 0xFF
    return width, height, bytes(pixels)


def pud_palette() -> list[tuple[int, int, int]]:
    # Diagnostic terrain palette: stable groups make transitions visible even
    # before applying the era-specific tileset artwork.
    colors = []
    bases = ((40, 100, 38), (24, 82, 130), (130, 105, 48), (85, 65, 38),
             (35, 105, 85), (130, 58, 42), (95, 95, 95), (145, 120, 75))
    for value in range(256):
        r, g, b = bases[(value >> 5) & 7]
        shade = (value & 31) - 15
        colors.append((max(0, min(255, r + shade * 2)),
                       max(0, min(255, g + shade * 2)),
                       max(0, min(255, b + shade * 2))))
    return colors


def detected_resource_name(resource_id: int, kind: str, unpacked: bytes) -> str:
    # MAINDAT.H came from a different build layout than the supplied classic
    # TOME.1.  Its symbols are useful research clues, but are not valid names
    # for these numeric archive slots.  TOME.1 therefore uses only facts that
    # can be verified from the resource payload itself.
    if 1000 <= resource_id <= 1527:
        if resource_id == 1299 and kind == "8-bit indexed bitmap":
            return "Warcraft II title screen"
        if resource_id == 1300 and kind == "256-color palette":
            return "Warcraft II title screen palette"
        if kind == "Warcraft II PUD map":
            chunks = parse_pud(unpacked) or []
            lookup = {tag: payload for tag, payload in chunks}
            title_bytes = lookup.get("DESC") or lookup.get("NAME")
            title = title_bytes.rstrip(b"\0").decode("latin-1", "replace").strip() if title_bytes else ""
            return f"PUD map — {title}" if title else f"PUD map {resource_id}"
        if kind == "Warcraft II GRP sprites":
            grp = parse_grp(unpacked)
            detail = f" — {len(grp.frames)} frames, {grp.width}×{grp.height}" if grp else ""
            return f"GRP sprites {resource_id}{detail}"
        if kind == "8-bit indexed bitmap":
            bitmap = bitmap_info(unpacked)
            detail = f" — {bitmap[0]}×{bitmap[1]}" if bitmap else ""
            return f"Indexed bitmap {resource_id}{detail}"
        if kind == "256-color palette":
            return f"Palette {resource_id}"
        if kind == "XMI music":
            return f"XMI music {resource_id}"
        if kind == "WAVE audio":
            return f"WAVE audio {resource_id}"
        if kind == "String/dialog table":
            table = parse_string_table(unpacked)
            return f"String table {resource_id} — {len(table.entries) if table else 0} entries"
        return f"Resource {resource_id} — {kind}"
    source = resource_name(resource_id)
    if kind == "Warcraft II PUD map":
        chunks = parse_pud(unpacked) or []
        lookup = {tag: payload for tag, payload in chunks}
        title_bytes = lookup.get("DESC") or lookup.get("NAME")
        title = title_bytes.rstrip(b"\0").decode("latin-1", "replace").strip() if title_bytes else ""
        detected = f"PUD map — {title}" if title else "PUD map"
        if source and "Map" not in source:
            return f"{detected} [header: {source}]"
        return title and detected or source or detected
    if kind == "Warcraft II GRP sprites" and source and not any(word in source for word in ("Grp", "Hdr", "Cursor", "Bmp", "Font", "Frame", "Icon")):
        return f"GRP sprites [header: {source}]"
    return source


def human_size(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def hexdump(data: bytes, limit: int = 65536) -> str:
    clipped = data[:limit]
    lines = []
    for offset in range(0, len(clipped), 16):
        row = clipped[offset:offset + 16]
        hx = " ".join(f"{b:02X}" for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{offset:08X}  {hx:<47}  {asc}")
    if len(data) > limit:
        lines.append(f"\n... preview limited to {human_size(limit)} of {human_size(len(data))}")
    return "\n".join(lines)


def printable_strings(data: bytes, minimum: int = 4) -> list[tuple[int, str]]:
    pattern = rb"[\x20-\x7E]{%d,}" % minimum
    return [(m.start(), m.group().decode("ascii")) for m in re.finditer(pattern, data)]


def detect_kind(data: bytes) -> str:
    unpacked, packing = unpack_resource(data)
    return detect_unpacked_kind(unpacked, packing)


def detect_unpacked_kind(unpacked: bytes, packing: str = "none") -> str:
    probe = unpacked[:96]
    if b"RIFF" in probe and b"WAVE" in probe:
        return "WAVE audio"
    if probe.startswith(b"FORM") and b"XDIR" in probe:
        return "XMI music"
    if probe.startswith(b"FORM"):
        return "IFF/FORM data"
    if unpacked.startswith(b"\x10\x00\x00\x00"):
        return "TIM image"
    if bitmap_info(unpacked):
        return "8-bit indexed bitmap"
    if palette_rgb(unpacked):
        return "256-color palette"
    if parse_pud(unpacked):
        return "Warcraft II PUD map"
    if parse_grp(unpacked):
        return "Warcraft II GRP sprites"
    if parse_string_table(unpacked) is not None:
        return "String/dialog table"
    if len(unpacked) == 1:
        return "Marker"
    strings = printable_strings(unpacked[:2048], 8)
    if strings:
        return "Packed data + text" if packing != "none" else "Data + text"
    return f"{packing} binary" if packing != "none" else "Binary data"


@dataclass
class StringEntry:
    raw: bytes

    @property
    def has_hotkey(self) -> bool:
        return len(self.raw) >= 3 and self.raw[1] == 0x01 and 32 <= self.raw[0] < 127

    @property
    def hotkey(self) -> str:
        return chr(self.raw[0]).upper() if self.has_hotkey else ""

    @property
    def text(self) -> str:
        body = self.raw[2:] if self.has_hotkey else self.raw
        # 04 <character> 01 marks the highlighted accelerator in WC2 labels.
        body = re.sub(rb"\x04(.)\x01", rb"\1", body, flags=re.DOTALL)
        return "".join(chr(b) if b in (9, 10, 13) or b >= 32 else f"<{b:02X}>" for b in body)


@dataclass
class StringTable:
    entries: list[StringEntry]
    prefix: bytes = b""
    separators: list[bytes] | None = None
    trailing: bytes = b""

    def build(self) -> bytes:
        count = len(self.entries)
        separators = self.separators if self.separators is not None and len(self.separators) == count else [b""] * count
        cursor = 2 + count * 2 + len(self.prefix)
        offsets = []
        strings = bytearray()
        for entry, separator in zip(self.entries, separators):
            if cursor > 0xFFFF:
                raise ValueError("String table exceeds its 16-bit offset limit")
            offsets.append(cursor)
            strings.extend(entry.raw)
            strings.append(0)
            strings.extend(separator)
            cursor += len(entry.raw) + 1 + len(separator)
        payload = bytearray(struct.pack("<H", count))
        if offsets:
            payload.extend(struct.pack(f"<{count}H", *offsets))
        payload.extend(self.prefix)
        payload.extend(strings)
        payload.extend(self.trailing)
        return struct.pack("<I", len(payload)) + payload


def parse_string_table(data: bytes) -> StringTable | None:
    if len(data) < 6:
        return None
    declared, count = struct.unpack_from("<IH", data)
    if declared + 4 > len(data) or count > 4096 or 6 + count * 2 > len(data):
        return None
    if count == 0:
        return StringTable([]) if declared == 2 else None
    offsets = list(struct.unpack_from(f"<{count}H", data, 6))
    payload = data[4:4 + declared]
    header_end = 2 + count * 2
    if offsets != sorted(offsets) or offsets[0] < header_end or offsets[-1] >= len(payload):
        return None
    entries = []
    separators = []
    prefix = payload[header_end:offsets[0]]
    last_end = header_end
    for number, start in enumerate(offsets):
        end = payload.find(b"\0", start)
        if end < 0:
            return None
        entries.append(StringEntry(payload[start:end]))
        next_start = offsets[number + 1] if number + 1 < len(offsets) else len(payload)
        if end + 1 > next_start:
            return None
        separators.append(payload[end + 1:next_start] if number + 1 < len(offsets) else b"")
        last_end = max(last_end, end + 1)
    return StringTable(entries, prefix, separators, payload[last_end:])


def encode_hotkey_text(text: str, hotkey: str, enabled: bool) -> bytes:
    raw_text = text.encode("latin-1", "replace")
    if not enabled:
        return raw_text
    if not hotkey or len(hotkey) != 1 or not hotkey.isprintable():
        raise ValueError("A hotkey entry requires one printable hotkey character")
    target = hotkey.casefold()
    position = next((i for i, ch in enumerate(text) if ch.casefold() == target), -1)
    if position < 0:
        raise ValueError(f"Hotkey {hotkey!r} does not occur in the displayed text")
    before = text[:position].encode("latin-1", "replace")
    marked = text[position].encode("latin-1", "replace")
    after = text[position + 1:].encode("latin-1", "replace")
    return hotkey.lower().encode("latin-1") + b"\x01" + before + b"\x04" + marked + b"\x01" + after


class TomeArchive:
    def __init__(self, path: Path, format_tag: int, base_id: int, resources: list[bytes]):
        self.path = path
        self.format_tag = format_tag
        self.base_id = base_id
        self.resources = resources
        self.dirty = False
        self._decode_cache: dict[int, tuple[bytes, str, str]] = {}

    def decoded(self, index: int) -> tuple[bytes, str, str]:
        cached = self._decode_cache.get(index)
        if cached is None:
            unpacked, packing = unpack_resource(self.resources[index])
            cached = (unpacked, packing, detect_unpacked_kind(unpacked, packing))
            self._decode_cache[index] = cached
        return cached

    def invalidate_cache(self):
        self._decode_cache.clear()

    @classmethod
    def load(cls, path: str | Path) -> "TomeArchive":
        path = Path(path)
        data = path.read_bytes()
        if len(data) < 8:
            raise ValueError("File is too small to be a TOME archive")
        tag, count, base_id = struct.unpack_from("<IHH", data)
        if tag != FORMAT_TAG:
            raise ValueError(f"Unexpected TOME format tag {tag}; expected {FORMAT_TAG}")
        table_end = 8 + count * 4
        if count == 0 or table_end > len(data):
            raise ValueError("Invalid resource count or offset table")
        offsets = list(struct.unpack_from(f"<{count}I", data, 8))
        if offsets[0] < table_end or offsets != sorted(offsets) or offsets[-1] >= len(data):
            raise ValueError("Invalid or non-monotonic resource offsets")
        ends = offsets[1:] + [len(data)]
        resources = [data[start:end] for start, end in zip(offsets, ends)]
        return cls(path, tag, base_id, resources)

    def build(self) -> bytes:
        count = len(self.resources)
        if not (1 <= count <= 0xFFFF):
            raise ValueError("TOME must contain 1 to 65,535 resources")
        position = 8 + count * 4
        offsets = []
        for resource in self.resources:
            offsets.append(position)
            position += len(resource)
            if position > 0xFFFFFFFF:
                raise ValueError("TOME exceeds its 32-bit offset limit")
        header = struct.pack("<IHH", self.format_tag, count, self.base_id)
        return header + struct.pack(f"<{count}I", *offsets) + b"".join(self.resources)

    def save(self, destination: str | Path, backup: bool = True) -> None:
        destination = Path(destination)
        output = self.build()
        if backup and destination.exists() and destination.resolve() == self.path.resolve():
            backup_path = destination.with_suffix(destination.suffix + ".bak")
            shutil.copy2(destination, backup_path)
        temp = destination.with_name(destination.name + ".tmp")
        temp.write_bytes(output)
        check = TomeArchive.load(temp)
        if check.base_id != self.base_id or check.resources != self.resources:
            temp.unlink(missing_ok=True)
            raise ValueError("Post-write validation failed")
        os.replace(temp, destination)
        self.path = destination
        self.dirty = False


class Workbench(tk.Tk):
    BG = "#17191d"
    PANEL = "#20242a"
    FIELD = "#111318"
    FG = "#e6e8eb"
    MUTED = "#9aa3ad"
    ACCENT = "#d7a62a"

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1450x880")
        self.minsize(1050, 680)
        self.configure(bg=self.BG)
        self.archives: list[TomeArchive] = []
        self.current_archive: TomeArchive | None = None
        self.current_index: int | None = None
        self.current_table: StringTable | None = None
        self.current_unpacked: bytes | None = None
        self.current_packing = "none"
        self.preview_photo = None
        self.preview_ppm: bytes | None = None
        self.preview_bitmap: tuple[int, int, bytes] | None = None
        self.preview_grp: GrpImage | None = None
        self.preview_pud: tuple[int, int, bytes] | None = None
        self._palette_cache = None
        self.audio_temp: Path | None = None
        self._style()
        self._menu()
        self._ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=self.BG, foreground=self.FG, fieldbackground=self.FIELD)
        s.configure("TFrame", background=self.BG)
        s.configure("Panel.TFrame", background=self.PANEL)
        s.configure("TLabel", background=self.BG, foreground=self.FG)
        s.configure("Muted.TLabel", foreground=self.MUTED)
        s.configure("Title.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.ACCENT)
        s.configure("TButton", background="#303640", foreground=self.FG, padding=(8, 5))
        s.map("TButton", background=[("active", "#414955")])
        s.configure("Treeview", background=self.FIELD, foreground=self.FG, fieldbackground=self.FIELD, rowheight=24)
        s.configure("Treeview.Heading", background="#303640", foreground=self.FG)
        s.map("Treeview", background=[("selected", "#5b4616")])
        s.configure("TNotebook", background=self.BG, borderwidth=0)
        s.configure("TNotebook.Tab", background="#2b3037", foreground=self.FG, padding=(12, 7))
        s.map("TNotebook.Tab", background=[("selected", "#4a3a18")])
        s.configure("TCheckbutton", background=self.BG, foreground=self.FG)
        s.configure("TEntry", fieldbackground=self.FIELD, foreground=self.FG)

    def _menu(self):
        menu = tk.Menu(self, tearoff=False, bg=self.PANEL, fg=self.FG)
        file_menu = tk.Menu(menu, tearoff=False, bg=self.PANEL, fg=self.FG)
        file_menu.add_command(label="Open TOME...", command=self.open_files, accelerator="Ctrl+O")
        file_menu.add_command(label="Open TOME folder...", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_current, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menu.add_cascade(label="File", menu=file_menu)
        res = tk.Menu(menu, tearoff=False, bg=self.PANEL, fg=self.FG)
        res.add_command(label="Extract selected (decoded)...", command=self.extract_selected)
        res.add_command(label="Extract selected raw/packed...", command=self.extract_raw_selected)
        res.add_command(label="Extract all decoded...", command=self.extract_all_decoded)
        res.add_command(label="Replace selected...", command=self.replace_selected)
        res.add_command(label="Add resource...", command=self.add_resource)
        res.add_command(label="Delete selected", command=self.delete_resource)
        menu.add_cascade(label="Resource", menu=res)
        help_menu = tk.Menu(menu, tearoff=False, bg=self.PANEL, fg=self.FG)
        help_menu.add_command(label="About / format notes", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)
        self.bind("<Control-o>", lambda _e: self.open_files())
        self.bind("<Control-s>", lambda _e: self.save_current())

    def _ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(9, 4))
        ttk.Label(toolbar, text="TOME Studio", style="Title.TLabel").pack(side="left", padx=(0, 18))
        for text, command in (("Open", self.open_files), ("Save", self.save_current),
                              ("Extract", self.extract_selected), ("Replace", self.replace_selected)):
            ttk.Button(toolbar, text=text, command=command).pack(side="left", padx=3)
        self.search_var = tk.StringVar()
        ttk.Label(toolbar, text="Filter:").pack(side="left", padx=(24, 5))
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=28)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda _e: self.refresh_resources())
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Create .bak when overwriting", variable=self.backup_var).pack(side="right")

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=5)
        left = ttk.Frame(paned)
        middle = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(middle, weight=3)
        paned.add(right, weight=4)

        ttk.Label(left, text="Open archives", style="Title.TLabel").pack(anchor="w", pady=(0, 5))
        self.archive_list = tk.Listbox(left, bg=self.FIELD, fg=self.FG, selectbackground="#6b531b",
                                       borderwidth=0, highlightthickness=1, highlightbackground="#343a43")
        self.archive_list.pack(fill="both", expand=True)
        self.archive_list.bind("<<ListboxSelect>>", self.on_archive_select)

        ttk.Label(middle, text="Resources", style="Title.TLabel").pack(anchor="w", pady=(0, 5))
        cols = ("index", "id", "name", "offset", "size", "kind")
        self.resources_tree = ttk.Treeview(middle, columns=cols, show="headings", selectmode="browse")
        widths = (50, 60, 210, 85, 75, 135)
        for col, width in zip(cols, widths):
            self.resources_tree.heading(col, text=col.upper())
            self.resources_tree.column(col, width=width, anchor="w", stretch=col == "kind")
        self.resources_tree.pack(fill="both", expand=True)
        self.resources_tree.bind("<<TreeviewSelect>>", self.on_resource_select)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.info_tab = ttk.Frame(self.notebook)
        self.strings_tab = ttk.Frame(self.notebook)
        self.hex_tab = ttk.Frame(self.notebook)
        self.text_tab = ttk.Frame(self.notebook)
        self.graphics_tab = ttk.Frame(self.notebook)
        self.audio_tab = ttk.Frame(self.notebook)
        self.campaign_tab = ttk.Frame(self.notebook)
        self.analysis_tab = ttk.Frame(self.notebook)
        self.table_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.info_tab, text="Details")
        self.notebook.add(self.graphics_tab, text="Graphics viewer")
        self.notebook.add(self.audio_tab, text="Audio catalog")
        self.notebook.add(self.campaign_tab, text="Campaign / text reader")
        self.notebook.add(self.strings_tab, text="Structured strings / hotkeys")
        self.notebook.add(self.analysis_tab, text="Unknown analyzer")
        self.notebook.add(self.table_tab, text="Binary table viewer")
        self.notebook.add(self.hex_tab, text="Hex")
        self.notebook.add(self.text_tab, text="Printable text")
        self._details_tab()
        self._graphics_tab()
        self._audio_tab()
        self._campaign_tab()
        self._strings_tab()
        self.analysis_text = self._make_text(self.analysis_tab, font=("Consolas", 10))
        self._table_tab()
        self.hex_text = self._make_text(self.hex_tab, font=("Consolas", 9))
        self.printable_text = self._make_text(self.text_tab, font=("Consolas", 10))

        self.status_var = tk.StringVar(value="Open TOME.1, TOME.2, TOME.3, or TOME.4 to begin.")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", anchor="w").pack(fill="x", padx=12, pady=(0, 8))

    def _make_text(self, parent, **kwargs):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        wrap = kwargs.pop("wrap", "none")
        text = tk.Text(frame, bg=self.FIELD, fg=self.FG, insertbackground=self.FG, wrap=wrap,
                       borderwidth=0, **kwargs)
        sy = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        text.pack(fill="both", expand=True)
        return text

    def _details_tab(self):
        top = ttk.Frame(self.info_tab)
        top.pack(fill="x", padx=12, pady=12)
        self.detail_vars = {name: tk.StringVar(value="—") for name in
                            ("Archive", "Resource ID", "Index", "Offset", "Size", "Detected type", "Audio")}
        for row, (name, var) in enumerate(self.detail_vars.items()):
            ttk.Label(top, text=name + ":", style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=3)
            ttk.Label(top, textvariable=var).grid(row=row, column=1, sticky="w", padx=10, pady=3)
        buttons = ttk.Frame(self.info_tab)
        buttons.pack(fill="x", padx=10, pady=5)
        ttk.Button(buttons, text="Play WAVE", command=self.play_audio).pack(side="left", padx=3)
        ttk.Button(buttons, text="Stop audio", command=self.stop_audio).pack(side="left", padx=3)
        ttk.Button(buttons, text="Extract decoded", command=self.extract_selected).pack(side="left", padx=3)
        ttk.Button(buttons, text="Extract raw", command=self.extract_raw_selected).pack(side="left", padx=3)
        ttk.Button(buttons, text="Replace", command=self.replace_selected).pack(side="left", padx=3)

    def _graphics_tab(self):
        bar = ttk.Frame(self.graphics_tab)
        bar.pack(fill="x", padx=8, pady=7)
        ttk.Label(bar, text="Palette:").pack(side="left")
        self.palette_var = tk.StringVar(value="Automatic")
        self.palette_combo = ttk.Combobox(bar, textvariable=self.palette_var, state="readonly", width=38)
        self.palette_combo.pack(side="left", padx=5)
        self.palette_combo.bind("<<ComboboxSelected>>", lambda _e: self.render_graphic())
        ttk.Label(bar, text="Zoom:").pack(side="left", padx=(16, 4))
        self.zoom_var = tk.IntVar(value=1)
        ttk.Spinbox(bar, from_=1, to=8, textvariable=self.zoom_var, width=4,
                    command=self.render_graphic).pack(side="left")
        ttk.Label(bar, text="Frame:").pack(side="left", padx=(12, 4))
        self.frame_var = tk.IntVar(value=0)
        self.frame_spin = ttk.Spinbox(bar, from_=0, to=0, textvariable=self.frame_var, width=5,
                                      command=self.render_graphic)
        self.frame_spin.pack(side="left")
        ttk.Button(bar, text="Previous graphic", command=lambda: self.step_graphic(-1)).pack(side="left", padx=(16, 3))
        ttk.Button(bar, text="Next graphic", command=lambda: self.step_graphic(1)).pack(side="left", padx=3)
        ttk.Button(bar, text="Export PPM...", command=self.export_ppm).pack(side="right")
        ttk.Button(bar, text="Export all frames...", command=self.export_all_frames).pack(side="right", padx=3)
        self.graphic_info = tk.StringVar(value="Select an indexed bitmap resource.")
        ttk.Label(self.graphics_tab, textvariable=self.graphic_info, style="Muted.TLabel").pack(fill="x", padx=10)
        frame = ttk.Frame(self.graphics_tab)
        frame.pack(fill="both", expand=True, padx=7, pady=7)
        self.graphic_canvas = tk.Canvas(frame, bg="#090a0c", highlightthickness=0)
        sy = ttk.Scrollbar(frame, orient="vertical", command=self.graphic_canvas.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=self.graphic_canvas.xview)
        self.graphic_canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.graphic_canvas.pack(fill="both", expand=True)

    def _campaign_tab(self):
        top = ttk.Frame(self.campaign_tab)
        top.pack(fill="x", padx=8, pady=7)
        ttk.Label(top, text="Long strings and campaign briefings in the selected resource.", style="Muted.TLabel").pack(side="left")
        ttk.Button(top, text="Previous text", command=lambda: self.step_text(-1)).pack(side="right", padx=3)
        ttk.Button(top, text="Next text", command=lambda: self.step_text(1)).pack(side="right", padx=3)
        self.campaign_text = self._make_text(self.campaign_tab, font=("Segoe UI", 11), wrap="word")

    def _audio_tab(self):
        top = ttk.Frame(self.audio_tab)
        top.pack(fill="x", padx=8, pady=7)
        ttk.Label(top, text="WAVE narration/speech and XMI music found in every open archive.", style="Muted.TLabel").pack(side="left")
        ttk.Button(top, text="Play selected WAVE", command=self.play_catalog_audio).pack(side="right", padx=3)
        ttk.Button(top, text="Go to resource", command=self.goto_catalog_audio).pack(side="right", padx=3)
        cols = ("archive", "id", "name", "type", "duration", "stored")
        self.audio_tree = ttk.Treeview(self.audio_tab, columns=cols, show="headings", selectmode="browse")
        for col, title, width in (("archive", "ARCHIVE", 75), ("id", "ID", 60),
                                  ("name", "SOURCE NAME", 310), ("type", "TYPE", 90),
                                  ("duration", "DURATION", 90), ("stored", "STORED SIZE", 90)):
            self.audio_tree.heading(col, text=title)
            self.audio_tree.column(col, width=width, stretch=col == "name")
        self.audio_tree.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        self.audio_tree.bind("<Double-1>", lambda _e: self.goto_catalog_audio())

    def _table_tab(self):
        bar = ttk.Frame(self.table_tab)
        bar.pack(fill="x", padx=8, pady=7)
        self.table_width_var = tk.IntVar(value=1)
        self.table_columns_var = tk.IntVar(value=16)
        self.table_offset_var = tk.IntVar(value=0)
        self.table_signed_var = tk.BooleanVar(value=False)
        ttk.Label(bar, text="Element bytes:").pack(side="left")
        ttk.Combobox(bar, textvariable=self.table_width_var, values=(1, 2, 4), state="readonly", width=4).pack(side="left", padx=4)
        ttk.Label(bar, text="Columns:").pack(side="left", padx=(10, 2))
        ttk.Spinbox(bar, from_=1, to=32, textvariable=self.table_columns_var, width=5).pack(side="left")
        ttk.Label(bar, text="Start offset:").pack(side="left", padx=(10, 2))
        ttk.Entry(bar, textvariable=self.table_offset_var, width=9).pack(side="left")
        ttk.Checkbutton(bar, text="Signed", variable=self.table_signed_var).pack(side="left", padx=8)
        ttk.Button(bar, text="Refresh", command=self.render_binary_table).pack(side="left", padx=3)
        ttk.Button(bar, text="Export CSV...", command=self.export_binary_table).pack(side="right", padx=3)
        self.table_holder = ttk.Frame(self.table_tab)
        self.table_holder.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        self.table_tree = None

    def binary_rows(self, limit: int | None = 512):
        data = self.current_unpacked or b""
        width = int(self.table_width_var.get())
        columns = max(1, min(32, int(self.table_columns_var.get())))
        offset = max(0, int(self.table_offset_var.get()))
        fmt = {1: "b" if self.table_signed_var.get() else "B",
               2: "h" if self.table_signed_var.get() else "H",
               4: "i" if self.table_signed_var.get() else "I"}[width]
        row_size = width * columns
        rows = []
        maximum = len(data) if limit is None else min(len(data), offset + limit * row_size)
        for row_start in range(offset, maximum, row_size):
            values = []
            for pos in range(row_start, min(row_start + row_size, len(data)), width):
                if pos + width > len(data): break
                values.append(struct.unpack_from("<" + fmt, data, pos)[0])
            rows.append((row_start, values))
        return columns, rows

    def render_binary_table(self):
        for child in self.table_holder.winfo_children():
            child.destroy()
        try:
            columns, rows = self.binary_rows()
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Table settings", str(exc))
            return
        names = ("offset",) + tuple(f"c{i}" for i in range(columns))
        tree = ttk.Treeview(self.table_holder, columns=names, show="headings")
        tree.heading("offset", text="OFFSET")
        tree.column("offset", width=90, stretch=False)
        for i in range(columns):
            tree.heading(f"c{i}", text=str(i))
            tree.column(f"c{i}", width=72, stretch=False, anchor="e")
        sy = ttk.Scrollbar(self.table_holder, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(self.table_holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        for row_start, values in rows:
            tree.insert("", "end", values=(f"0x{row_start:08X}", *values))
        self.table_tree = tree

    def export_binary_table(self):
        if self.current_unpacked is None:
            return
        path = filedialog.asksaveasfilename(initialfile="resource_table.csv", defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path: return
        columns, rows = self.binary_rows(limit=None)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["offset", *[f"column_{i}" for i in range(columns)]])
            for offset, values in rows:
                writer.writerow([f"0x{offset:08X}", *values])

    def _strings_tab(self):
        pane = ttk.Panedwindow(self.strings_tab, orient="vertical")
        pane.pack(fill="both", expand=True, padx=6, pady=6)
        list_frame = ttk.Frame(pane)
        edit_frame = ttk.Frame(pane)
        pane.add(list_frame, weight=4)
        pane.add(edit_frame, weight=2)
        cols = ("n", "hotkey", "text", "raw")
        self.string_tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        for col, title, width in (("n", "#", 45), ("hotkey", "HOTKEY", 70),
                                  ("text", "DISPLAYED TEXT", 430), ("raw", "RAW BYTES", 250)):
            self.string_tree.heading(col, text=title)
            self.string_tree.column(col, width=width, stretch=col in ("text", "raw"))
        self.string_tree.pack(fill="both", expand=True)
        self.string_tree.bind("<<TreeviewSelect>>", self.on_string_select)
        self.hotkey_enabled = tk.BooleanVar()
        self.hotkey_var = tk.StringVar()
        ttk.Checkbutton(edit_frame, text="Encoded hotkey/accelerator", variable=self.hotkey_enabled).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(edit_frame, text="Hotkey:").grid(row=0, column=1, padx=(12, 3))
        ttk.Entry(edit_frame, textvariable=self.hotkey_var, width=5).grid(row=0, column=2, sticky="w")
        ttk.Label(edit_frame, text="Displayed text:").grid(row=1, column=0, sticky="nw", pady=4)
        self.string_edit = tk.Text(edit_frame, height=5, bg=self.FIELD, fg=self.FG, insertbackground=self.FG, wrap="word")
        self.string_edit.grid(row=2, column=0, columnspan=4, sticky="nsew")
        edit_frame.columnconfigure(3, weight=1)
        edit_frame.rowconfigure(2, weight=1)
        controls = ttk.Frame(edit_frame)
        controls.grid(row=3, column=0, columnspan=4, sticky="ew", pady=6)
        ttk.Button(controls, text="Apply string", command=self.apply_string).pack(side="left", padx=3)
        ttk.Button(controls, text="Add string", command=self.add_string).pack(side="left", padx=3)
        ttk.Button(controls, text="Delete string", command=self.delete_string).pack(side="left", padx=3)
        ttk.Label(controls, text="Control bytes outside recognized hotkey markup are shown as <XX> and preserved until edited.",
                  style="Muted.TLabel").pack(side="left", padx=12)

    def open_files(self):
        paths = filedialog.askopenfilenames(title="Open Warcraft II TOME archives",
                                            filetypes=[("TOME archives", "TOME.*"), ("All files", "*.*")])
        self._load_paths(paths)

    def open_folder(self):
        folder = filedialog.askdirectory(title="Choose folder containing TOME files")
        if folder:
            paths = sorted(Path(folder).glob("TOME.*"))
            self._load_paths(paths)

    def _load_paths(self, paths):
        errors = []
        for path in paths:
            try:
                archive = TomeArchive.load(path)
                existing = next((i for i, a in enumerate(self.archives) if a.path.resolve() == archive.path.resolve()), None)
                if existing is None:
                    self.archives.append(archive)
                else:
                    self.archives[existing] = archive
            except Exception as exc:
                errors.append(f"{Path(path).name}: {exc}")
        self._palette_cache = None
        self.refresh_archives()
        if self.archives and not self.archive_list.curselection():
            self.archive_list.selection_set(0)
            self.on_archive_select()
        if errors:
            messagebox.showerror("Could not open some files", "\n".join(errors))
        self.refresh_audio_catalog()

    def refresh_archives(self):
        selected = self.archives.index(self.current_archive) if self.current_archive in self.archives else 0
        self.archive_list.delete(0, "end")
        for archive in self.archives:
            mark = "*" if archive.dirty else ""
            self.archive_list.insert("end", f"{archive.path.name}{mark}\n  base {archive.base_id} · {len(archive.resources)} resources")
        if self.archives:
            self.archive_list.selection_set(min(selected, len(self.archives) - 1))

    def on_archive_select(self, _event=None):
        selection = self.archive_list.curselection()
        if not selection:
            return
        self.current_archive = self.archives[selection[0]]
        self.current_index = None
        self.status_var.set(f"Analyzing {len(self.current_archive.resources)} resources in {self.current_archive.path.name}...")
        self.update_idletasks()
        self.refresh_resources()
        self.status_var.set(f"{self.current_archive.path} — base ID {self.current_archive.base_id}")

    def resource_offsets(self) -> list[int]:
        if not self.current_archive:
            return []
        position = 8 + len(self.current_archive.resources) * 4
        result = []
        for data in self.current_archive.resources:
            result.append(position)
            position += len(data)
        return result

    def refresh_resources(self, select_index: int | None = None):
        self.resources_tree.delete(*self.resources_tree.get_children())
        archive = self.current_archive
        if not archive:
            return
        query = self.search_var.get().strip().casefold()
        offsets = self.resource_offsets()
        for index, data in enumerate(archive.resources):
            rid = archive.base_id + index
            unpacked, packing, kind = archive.decoded(index)
            name = detected_resource_name(rid, kind, unpacked)
            haystack = f"{index} {rid} {name} {kind} {len(data)}".casefold()
            if query and query not in haystack:
                continue
            iid = str(index)
            self.resources_tree.insert("", "end", iid=iid,
                                       values=(index, rid, name, f"0x{offsets[index]:08X}", human_size(len(data)), kind))
        if select_index is not None and self.resources_tree.exists(str(select_index)):
            self.resources_tree.selection_set(str(select_index))
            self.resources_tree.see(str(select_index))
            self.on_resource_select()

    def on_resource_select(self, _event=None):
        selection = self.resources_tree.selection()
        if not selection or not self.current_archive:
            return
        index = int(selection[0])
        self.current_index = index
        data = self.current_archive.resources[index]
        unpacked, packing, kind = self.current_archive.decoded(index)
        self.current_unpacked, self.current_packing = unpacked, packing
        offsets = self.resource_offsets()
        self.detail_vars["Archive"].set(self.current_archive.path.name)
        rid = self.current_archive.base_id + index
        name = detected_resource_name(rid, kind, unpacked)
        self.detail_vars["Resource ID"].set(f"{rid}" + (f" — {name}" if name else ""))
        self.detail_vars["Index"].set(str(index))
        self.detail_vars["Offset"].set(f"0x{offsets[index]:08X}")
        self.detail_vars["Size"].set(f"{len(data):,} bytes ({human_size(len(data))})")
        self.detail_vars["Detected type"].set(kind)
        self.detail_vars["Audio"].set(self.audio_description(unpacked))
        self.set_text(self.hex_text, hexdump(unpacked))
        strings = printable_strings(unpacked)
        self.set_text(self.printable_text, "\n".join(f"0x{o:08X}  {s}" for o, s in strings) or "No printable ASCII strings found.")
        self.current_table = parse_string_table(unpacked)
        self.refresh_string_table()
        self.refresh_graphic()
        self.refresh_campaign()
        self.refresh_analysis(data, unpacked, packing, rid, name, kind)
        self.render_binary_table()
        self.status_var.set(f"Resource {self.current_archive.base_id + index} · {kind} · {human_size(len(data))}")

    @staticmethod
    def set_text(widget: tk.Text, value: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    @staticmethod
    def audio_description(data: bytes) -> str:
        start = data.find(b"RIFF", 0, 96)
        if start < 0:
            return "—"
        try:
            with wave.open(io.BytesIO(data[start:]), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
                return f"{duration:.2f}s, {wav.getnchannels()} ch, {wav.getsampwidth() * 8}-bit, {wav.getframerate()} Hz"
        except (wave.Error, EOFError):
            return "RIFF/WAVE signature (unsupported header)"

    def palette_resources(self) -> list[tuple[str, list[tuple[int, int, int]], int]]:
        if self._palette_cache is not None:
            return self._palette_cache
        result = []
        for archive in self.archives:
            for index, packed in enumerate(archive.resources):
                rid = archive.base_id + index
                raw, _packing, kind = archive.decoded(index)
                pal = palette_rgb(raw)
                if pal:
                    result.append((f"{rid} — {detected_resource_name(rid, kind, raw) or 'Palette'}", pal, rid))
        self._palette_cache = result
        return result

    @staticmethod
    def automatic_palette_id(rid: int) -> int | None:
        # Main-data graphics generally use their era's palette.
        if 1000 <= rid <= 1013: return 1002
        if 1014 <= rid <= 1025: return 1018
        if 1026 <= rid <= 1037: return 1002
        if 1038 <= rid <= 1183: return 1002
        if 1252 <= rid <= 1378: return 1300
        if rid == 3013: return 3014
        if rid == 3015: return 3016
        if rid in (3019, 3021, 3023, 3025): return 3017
        if rid in (3020, 3022, 3024, 3026): return 3018
        if rid in (3028,): return 3027
        if rid == 3029: return 3031
        if rid == 3030: return 3032
        if rid in (3094, 3096, 3098, 3100, 3102): return 3093
        if rid in (3097, 3099, 3101, 3103): return 3093
        return None

    def selected_palette(self, rid: int) -> tuple[list[tuple[int, int, int]], str]:
        palettes = self.palette_resources()
        choice = self.palette_var.get()
        wanted = self.automatic_palette_id(rid) if choice == "Automatic" else None
        if choice not in ("Automatic", "Grayscale"):
            try: wanted = int(choice.split("—", 1)[0].strip())
            except ValueError: wanted = None
        if wanted is not None:
            for label, palette, palette_id in palettes:
                if palette_id == wanted:
                    return palette, label
        return [(i, i, i) for i in range(256)], "Grayscale (no paired palette found)"

    @staticmethod
    def make_ppm(width: int, height: int, pixels: bytes, palette: list[tuple[int, int, int]]) -> bytes:
        rgb = bytearray(width * height * 3)
        out = 0
        for value in pixels:
            r, g, b = palette[value]
            rgb[out:out + 3] = bytes((r, g, b))
            out += 3
        return f"P6\n{width} {height}\n255\n".encode("ascii") + rgb

    def refresh_graphic(self):
        self.preview_bitmap = bitmap_info(self.current_unpacked or b"")
        self.preview_pud = pud_minimap(self.current_unpacked or b"") if not self.preview_bitmap else None
        self.preview_grp = parse_grp(self.current_unpacked or b"") if not (self.preview_bitmap or self.preview_pud) else None
        self.frame_var.set(0)
        self.frame_spin.configure(to=max(0, len(self.preview_grp.frames) - 1) if self.preview_grp else 0)
        palettes = self.palette_resources()
        values = ["Automatic", "Grayscale"] + [label for label, _pal, _rid in palettes]
        self.palette_combo["values"] = values
        if self.palette_var.get() not in values:
            self.palette_var.set("Automatic")
        self.render_graphic()

    def render_graphic(self):
        self.graphic_canvas.delete("all")
        self.preview_photo = None
        self.preview_ppm = None
        if not (self.preview_bitmap or self.preview_grp or self.preview_pud) or not self.current_archive or self.current_index is None:
            self.graphic_info.set("This resource is not a recognized bitmap, PUD map, or Warcraft II GRP sprite set.")
            return
        palette = None
        if self.preview_bitmap:
            width, height, pixels = self.preview_bitmap
            frame_note = ""
        elif self.preview_pud:
            width, height, pixels = self.preview_pud
            frame_note = " — diagnostic MTXM minimap"
            palette = pud_palette()
        else:
            assert self.preview_grp is not None and self.current_unpacked is not None
            frame_number = max(0, min(len(self.preview_grp.frames) - 1, int(self.frame_var.get())))
            self.frame_var.set(frame_number)
            width, height = self.preview_grp.width, self.preview_grp.height
            try:
                pixels = render_grp_canvas(self.current_unpacked, self.preview_grp, frame_number)
            except ValueError as exc:
                self.graphic_info.set(str(exc))
                return
            frame = self.preview_grp.frames[frame_number]
            frame_note = f" — frame {frame_number + 1}/{len(self.preview_grp.frames)} ({frame.width}×{frame.height} at {frame.dx},{frame.dy})"
        rid = self.current_archive.base_id + self.current_index
        if palette is None:
            palette, palette_label = self.selected_palette(rid)
        else:
            palette_label = "Diagnostic terrain colors"
        ppm = self.make_ppm(width, height, pixels, palette)
        self.preview_ppm = ppm
        try:
            photo = tk.PhotoImage(data=ppm, format="PPM")
            zoom = max(1, min(8, int(self.zoom_var.get())))
            if zoom > 1:
                photo = photo.zoom(zoom, zoom)
            self.preview_photo = photo
            self.graphic_canvas.create_image(0, 0, image=photo, anchor="nw")
            self.graphic_canvas.configure(scrollregion=(0, 0, width * zoom, height * zoom))
            kind = self.current_archive.decoded(self.current_index)[2]
            label = detected_resource_name(rid, kind, self.current_unpacked or b"") or "Indexed graphic"
            self.graphic_info.set(f"{label} — {width}×{height}{frame_note} — {palette_label}")
        except tk.TclError as exc:
            self.graphic_info.set(f"Tk could not render this PPM preview: {exc}")

    def step_graphic(self, direction: int):
        if not self.current_archive or self.current_index is None:
            return
        count = len(self.current_archive.resources)
        for distance in range(1, count + 1):
            index = (self.current_index + direction * distance) % count
            raw, _packing, _kind = self.current_archive.decoded(index)
            if bitmap_info(raw) or parse_grp(raw) or pud_minimap(raw):
                self.refresh_resources(index)
                self.notebook.select(self.graphics_tab)
                return

    def export_ppm(self):
        if not self.preview_ppm or not self.current_archive or self.current_index is None:
            messagebox.showinfo("No graphic", "Select a recognized indexed bitmap first.")
            return
        rid = self.current_archive.base_id + self.current_index
        path = filedialog.asksaveasfilename(initialfile=f"resource_{rid}.ppm", defaultextension=".ppm",
                                            filetypes=[("Portable pixmap", "*.ppm")])
        if path:
            Path(path).write_bytes(self.preview_ppm)

    def export_all_frames(self):
        if not self.preview_grp or not self.current_unpacked or not self.current_archive or self.current_index is None:
            messagebox.showinfo("No GRP", "Select a Warcraft II GRP sprite resource first.")
            return
        folder = filedialog.askdirectory(title="Export every GRP frame as PPM")
        if not folder: return
        rid = self.current_archive.base_id + self.current_index
        palette, _ = self.selected_palette(rid)
        destination = Path(folder)
        exported = 0
        for number, frame in enumerate(self.preview_grp.frames):
            pixels = render_grp_canvas(self.current_unpacked, self.preview_grp, number)
            ppm = self.make_ppm(self.preview_grp.width, self.preview_grp.height, pixels, palette)
            (destination / f"resource_{rid}_frame_{number:03d}.ppm").write_bytes(ppm)
            exported += 1
        self.status_var.set(f"Exported {exported} GRP frames from resource {rid} to {folder}")

    def refresh_campaign(self):
        if not self.current_table:
            self.set_text(self.campaign_text, "No recognized text table in this resource.")
            return
        sections = []
        for i, entry in enumerate(self.current_table.entries):
            text = entry.text.strip()
            if text:
                sections.append(f"[{i}]" + (f"  Hotkey: {entry.hotkey}" if entry.hotkey else "") + f"\n{text}")
        self.set_text(self.campaign_text, "\n\n".join(sections) or "No non-empty strings.")

    def refresh_audio_catalog(self):
        if not hasattr(self, "audio_tree"):
            return
        self.audio_tree.delete(*self.audio_tree.get_children())
        for archive_number, archive in enumerate(self.archives):
            for index, packed in enumerate(archive.resources):
                raw, _packing, kind = archive.decoded(index)
                probe = raw[:96]
                is_wave = b"RIFF" in probe and b"WAVE" in probe
                is_xmi = probe.startswith(b"FORM") and b"XDIR" in probe
                if not (is_wave or is_xmi):
                    continue
                rid = archive.base_id + index
                duration = self.audio_description(raw) if is_wave else "sequence"
                iid = f"{archive_number}:{index}"
                self.audio_tree.insert("", "end", iid=iid,
                                       values=(archive.path.name, rid, detected_resource_name(rid, kind, raw),
                                               "WAVE" if is_wave else "XMI", duration,
                                               human_size(len(packed))))

    def catalog_selection(self) -> tuple[int, int] | None:
        selection = self.audio_tree.selection()
        if not selection:
            return None
        try:
            return tuple(int(v) for v in selection[0].split(":", 1))
        except (ValueError, IndexError):
            return None

    def goto_catalog_audio(self):
        selected = self.catalog_selection()
        if not selected:
            return
        archive_number, index = selected
        self.archive_list.selection_clear(0, "end")
        self.archive_list.selection_set(archive_number)
        self.archive_list.see(archive_number)
        self.on_archive_select()
        self.refresh_resources(index)

    def play_catalog_audio(self):
        selected = self.catalog_selection()
        if not selected:
            return
        archive_number, index = selected
        archive = self.archives[archive_number]
        raw, _packing, _kind = archive.decoded(index)
        if not (b"RIFF" in raw[:96] and b"WAVE" in raw[:96]):
            messagebox.showinfo("XMI sequence", "XMI playback is not provided by Windows winsound. Extract the resource for an XMI/MIDI player.")
            return
        self.current_unpacked = raw
        self.play_audio()

    def step_text(self, direction: int):
        if not self.current_archive or self.current_index is None:
            return
        count = len(self.current_archive.resources)
        for distance in range(1, count + 1):
            index = (self.current_index + direction * distance) % count
            raw, _packing, _kind = self.current_archive.decoded(index)
            table = parse_string_table(raw)
            if table and any(len(e.text) >= 30 for e in table.entries):
                self.refresh_resources(index)
                self.notebook.select(self.campaign_tab)
                return

    def refresh_analysis(self, packed: bytes, unpacked: bytes, packing: str, rid: int, name: str, kind: str):
        def entropy(blob: bytes) -> float:
            if not blob: return 0.0
            counts = [0] * 256
            for value in blob: counts[value] += 1
            return -sum((n / len(blob)) * math.log2(n / len(blob)) for n in counts if n)
        ratio = len(packed) / len(unpacked) if unpacked else 0
        sigs = []
        for signature in (b"RIFF", b"WAVE", b"FORM", b"XDIR", b"XMID", b"TIM", b"TEXTBOX"):
            at = unpacked.find(signature)
            if at >= 0: sigs.append(f"{signature.decode('ascii')}: 0x{at:X}")
        text = (
            f"Resource ID       {rid}\nSource name       {name or 'Not mapped yet'}\n"
            f"Classification    {kind}\nPacking            {packing}\n"
            f"Stored size        {len(packed):,} bytes\nDecoded size       {len(unpacked):,} bytes\n"
            f"Stored/decoded     {ratio:.3f}\nStored entropy     {entropy(packed):.4f} bits/byte\n"
            f"Decoded entropy    {entropy(unpacked):.4f} bits/byte\n"
            f"First 32 decoded   {unpacked[:32].hex(' ').upper()}\n"
            f"Known signatures   {', '.join(sigs) if sigs else 'None'}\n\n"
            "Interpretation\n"
            "--------------\n"
        )
        if packing == "GDS LZSS":
            text += "Decoded with the 4096-byte ring-buffer LZSS algorithm from GDS/LZSS.C.\n"
        if kind == "XMI music":
            text += "This is Miles/SOS Extended MIDI (FORM/XDIR/XMID), not a bitmap.\n"
        elif kind == "8-bit indexed bitmap":
            info = bitmap_info(unpacked)
            text += f"Bitmap payload is {info[0]}×{info[1]} indexed pixels with a separate palette.\n"
        elif kind == "256-color palette":
            text += "Palette is 256 RGB triples; 6-bit channels are expanded to 8-bit for preview.\n"
        elif kind == "String/dialog table":
            table = parse_string_table(unpacked)
            text += f"Recognized indexed table with {len(table.entries) if table else 0} entries.\n"
        elif kind == "Warcraft II GRP sprites":
            group = parse_grp(unpacked)
            text += (f"Original Warcraft II GRP with {len(group.frames)} frames on a "
                     f"{group.width}×{group.height} canvas. Scanlines use skip/repeat/literal RLE.\n")
        elif kind == "Warcraft II PUD map":
            chunks = parse_pud(unpacked) or []
            text += "PUD chunks:\n"
            for tag, payload in chunks:
                detail = ""
                if tag in ("DIM ", "DIM") and len(payload) >= 4:
                    detail = f" ({struct.unpack_from('<H', payload)[0]}×{struct.unpack_from('<H', payload, 2)[0]})"
                elif tag in ("DESC", "TYPE"):
                    detail = " " + payload.rstrip(b"\0").decode("latin-1", "replace")[:120]
                text += f"  {tag!r:<8} {len(payload):>8,} bytes{detail}\n"
        else:
            text += "Structure is not fully decoded yet; offsets, entropy and signatures above help group related records.\n"
        self.set_text(self.analysis_text, text)

    def refresh_string_table(self, select: int | None = None):
        self.string_tree.delete(*self.string_tree.get_children())
        if not self.current_table:
            return
        for i, entry in enumerate(self.current_table.entries):
            raw = entry.raw.hex(" ").upper()
            if len(raw) > 100:
                raw = raw[:97] + "..."
            self.string_tree.insert("", "end", iid=str(i), values=(i, entry.hotkey, entry.text, raw))
        if select is not None and self.string_tree.exists(str(select)):
            self.string_tree.selection_set(str(select))
            self.string_tree.see(str(select))
            self.on_string_select()

    def on_string_select(self, _event=None):
        selection = self.string_tree.selection()
        if not selection or not self.current_table:
            return
        entry = self.current_table.entries[int(selection[0])]
        self.hotkey_enabled.set(entry.has_hotkey)
        self.hotkey_var.set(entry.hotkey)
        self.string_edit.delete("1.0", "end")
        self.string_edit.insert("1.0", entry.text)

    def apply_string(self):
        selection = self.string_tree.selection()
        if not selection or not self.current_table or self.current_index is None or not self.current_archive:
            messagebox.showinfo("Select a string", "Select a structured string entry first.")
            return
        index = int(selection[0])
        try:
            raw = encode_hotkey_text(self.string_edit.get("1.0", "end-1c"), self.hotkey_var.get(), self.hotkey_enabled.get())
            self.current_table.entries[index] = StringEntry(raw)
            self.current_archive.resources[self.current_index] = self.current_table.build()
            self.current_archive.invalidate_cache()
            self.current_archive.dirty = True
            self.refresh_string_table(index)
            self.refresh_resources(self.current_index)
            self.refresh_archives()
            self.status_var.set("String updated in memory. Save the archive to write it to disk.")
        except Exception as exc:
            messagebox.showerror("Cannot update string", str(exc))

    def add_string(self):
        if not self.current_table or self.current_index is None or not self.current_archive:
            messagebox.showinfo("Not a string table", "The selected resource is not a recognized string/dialog table.")
            return
        self.current_table.entries.append(StringEntry(b"New string"))
        if self.current_table.separators is not None:
            self.current_table.separators.append(b"")
        self.current_archive.resources[self.current_index] = self.current_table.build()
        self.current_archive.invalidate_cache()
        self.current_archive.dirty = True
        self.refresh_string_table(len(self.current_table.entries) - 1)
        self.refresh_archives()

    def delete_string(self):
        selection = self.string_tree.selection()
        if not selection or not self.current_table or self.current_index is None or not self.current_archive:
            return
        index = int(selection[0])
        if not messagebox.askyesno("Delete string", f"Delete string entry {index}? This can change indices used by game code."):
            return
        del self.current_table.entries[index]
        if self.current_table.separators is not None:
            del self.current_table.separators[index]
        self.current_archive.resources[self.current_index] = self.current_table.build()
        self.current_archive.invalidate_cache()
        self.current_archive.dirty = True
        self.refresh_string_table(min(index, len(self.current_table.entries) - 1))
        self.refresh_archives()

    def selected_data(self):
        if self.current_archive is None or self.current_index is None:
            return None
        return self.current_archive.resources[self.current_index]

    @staticmethod
    def safe_export_stem(rid: int, name: str | None) -> str:
        label = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "resource").strip("._-")
        return f"resource_{rid}_{(label or 'resource')[:80]}"

    def automatic_export_palette(self, rid: int) -> list[tuple[int, int, int]]:
        wanted = self.automatic_palette_id(rid)
        if wanted is not None:
            for _label, palette, palette_id in self.palette_resources():
                if palette_id == wanted:
                    return palette
        return [(value, value, value) for value in range(256)]

    def decoded_export(self, archive: TomeArchive, index: int) -> tuple[str, bytes, str]:
        """Return a useful filename and decoded, directly consumable payload."""
        rid = archive.base_id + index
        unpacked, packing, kind = archive.decoded(index)
        name = detected_resource_name(rid, kind, unpacked) or resource_name(rid)
        stem = self.safe_export_stem(rid, name)
        extension = {
            "WAVE audio": ".wav", "XMI music": ".xmi",
            "Warcraft II PUD map": ".pud", "Warcraft II GRP sprites": ".grp",
            "TIM image": ".tim", "256-color palette": ".pal",
            "IFF/FORM data": ".iff", "String/dialog table": ".txt",
        }.get(kind, ".dat")
        payload = unpacked
        if kind == "WAVE audio":
            start = unpacked.find(b"RIFF", 0, 96)
            if start >= 0:
                payload = unpacked[start:]
        elif kind == "8-bit indexed bitmap":
            bitmap = bitmap_info(unpacked)
            if bitmap:
                width, height, pixels = bitmap
                payload = self.make_ppm(width, height, pixels, self.automatic_export_palette(rid))
                extension = ".ppm"
        elif kind == "String/dialog table":
            table = parse_string_table(unpacked)
            if table is not None:
                lines = []
                for number, entry in enumerate(table.entries):
                    hotkey = f"  Hotkey: {entry.hotkey}" if entry.has_hotkey else ""
                    lines.append(f"[{number:04d}]{hotkey}\n{entry.text}\n")
                payload = "\n".join(lines).encode("utf-8")
        return stem + extension, payload, f"{kind}; packing={packing}"

    def extract_selected(self):
        if self.current_archive is None or self.current_index is None:
            messagebox.showinfo("Select a resource", "Select a resource to extract.")
            return
        filename, payload, description = self.decoded_export(self.current_archive, self.current_index)
        suffix = Path(filename).suffix
        path = filedialog.asksaveasfilename(initialfile=filename, defaultextension=suffix,
                                            filetypes=[("Decoded resource", f"*{suffix}"), ("All files", "*.*")])
        if not path:
            return
        Path(path).write_bytes(payload)
        rid = self.current_archive.base_id + self.current_index
        self.status_var.set(f"Extracted decoded resource {rid} ({description}) to {path}")

    def extract_raw_selected(self):
        data = self.selected_data()
        if data is None or self.current_archive is None or self.current_index is None:
            messagebox.showinfo("Select a resource", "Select a resource to extract.")
            return
        rid = self.current_archive.base_id + self.current_index
        path = filedialog.asksaveasfilename(initialfile=f"resource_{rid}_packed.bin", defaultextension=".bin",
                                            filetypes=[("Raw packed resource", "*.bin"), ("All files", "*.*")])
        if not path:
            return
        Path(path).write_bytes(data)
        self.status_var.set(f"Extracted exact stored bytes for resource {rid} to {path}")

    def extract_all_decoded(self):
        if self.current_archive is None:
            messagebox.showinfo("Open an archive", "Open and select the archive to extract.")
            return
        parent = filedialog.askdirectory(title=f"Extract every decoded resource from {self.current_archive.path.name}")
        if not parent:
            return
        archive = self.current_archive
        folder = Path(parent) / f"{archive.path.name}_decoded"
        folder.mkdir(parents=True, exist_ok=True)
        rows = []
        failures = []
        for index, stored in enumerate(archive.resources):
            rid = archive.base_id + index
            try:
                filename, payload, description = self.decoded_export(archive, index)
                (folder / filename).write_bytes(payload)
                unpacked, packing, kind = archive.decoded(index)
                display_name = detected_resource_name(rid, kind, unpacked) or ""
                header_reference = resource_name(rid) or "" if 1000 <= rid <= 1527 else ""
                rows.append((index, rid, display_name, header_reference, kind, packing,
                             len(stored), len(unpacked), filename, description))
            except Exception as exc:
                failures.append(f"{rid}: {exc}")
        with (folder / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(("index", "resource_id", "verified_name", "unverified_header_reference",
                             "detected_type", "packing",
                             "stored_bytes", "decoded_bytes", "filename", "notes"))
            writer.writerows(rows)
        if failures:
            (folder / "extraction_errors.txt").write_text("\n".join(failures), encoding="utf-8")
            messagebox.showwarning("Extraction completed with errors",
                                   f"Exported {len(rows)} resources to {folder}. {len(failures)} failed; see extraction_errors.txt.")
        else:
            messagebox.showinfo("Extraction complete", f"Exported all {len(rows)} decoded resources to:\n{folder}")
        self.status_var.set(f"Exported {len(rows)} decoded resources from {archive.path.name} to {folder}")

    def replace_selected(self):
        if self.current_archive is None or self.current_index is None:
            messagebox.showinfo("Select a resource", "Select a resource to replace.")
            return
        path = filedialog.askopenfilename(title="Choose replacement resource", filetypes=[("All files", "*.*")])
        if not path:
            return
        new_data = Path(path).read_bytes()
        old_data = self.current_archive.resources[self.current_index]
        # TOME.3 stores a four-byte outer payload length before RIFF.
        if new_data.startswith(b"RIFF") and old_data.find(b"RIFF", 0, 16) == 4:
            new_data = struct.pack("<I", len(new_data)) + new_data
        self.current_archive.resources[self.current_index] = new_data
        self.current_archive.invalidate_cache()
        self.current_archive.dirty = True
        self.refresh_resources(self.current_index)
        self.refresh_archives()
        self.status_var.set("Resource replaced in memory. Save to rebuild all offsets and write the archive.")

    def add_resource(self):
        if not self.current_archive:
            return
        path = filedialog.askopenfilename(title="Resource to append", filetypes=[("All files", "*.*")])
        if not path:
            return
        data = Path(path).read_bytes()
        self.current_archive.resources.append(data)
        self.current_archive.invalidate_cache()
        self.current_archive.dirty = True
        self.refresh_resources(len(self.current_archive.resources) - 1)
        self.refresh_archives()

    def delete_resource(self):
        if self.current_archive is None or self.current_index is None:
            return
        rid = self.current_archive.base_id + self.current_index
        if not messagebox.askyesno("Delete resource", f"Delete resource {rid}?\n\nEvery following resource ID will shift. This may break source-code references."):
            return
        del self.current_archive.resources[self.current_index]
        self.current_archive.invalidate_cache()
        self.current_archive.dirty = True
        next_index = min(self.current_index, len(self.current_archive.resources) - 1)
        self.current_index = None
        self.refresh_resources(next_index)
        self.refresh_archives()

    def save_current(self):
        if not self.current_archive:
            return
        try:
            self.current_archive.save(self.current_archive.path, self.backup_var.get())
            self.refresh_archives()
            self.status_var.set(f"Saved and validated {self.current_archive.path}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def save_as(self):
        if not self.current_archive:
            return
        path = filedialog.asksaveasfilename(initialfile=self.current_archive.path.name,
                                            filetypes=[("TOME archives", "TOME.*"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.current_archive.save(path, False)
            self.refresh_archives()
            self.status_var.set(f"Saved and validated {path}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def play_audio(self):
        data = self.current_unpacked
        if data is None:
            return
        start = data.find(b"RIFF", 0, 96)
        if start < 0:
            messagebox.showinfo("Not WAVE audio", "The selected resource does not contain a RIFF/WAVE stream.")
            return
        try:
            import winsound
            self.stop_audio()
            fd, name = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            self.audio_temp = Path(name)
            self.audio_temp.write_bytes(data[start:])
            winsound.PlaySound(str(self.audio_temp), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except ImportError:
            messagebox.showinfo("Playback", "Built-in playback is available on Windows. Extract the WAV to play it here.")
        except Exception as exc:
            messagebox.showerror("Playback failed", str(exc))

    def stop_audio(self):
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except (ImportError, RuntimeError):
            pass
        if self.audio_temp:
            try:
                self.audio_temp.unlink(missing_ok=True)
            except OSError:
                pass
            self.audio_temp = None

    def show_about(self):
        messagebox.showinfo(APP_NAME,
            "Warcraft II TOME archive editor\n\n"
            "Header: uint32 tag 25, uint16 count, uint16 base ID, uint32 offsets[count].\n"
            "Resource ID = base ID + index. Saves rebuild every offset and validate by reopening.\n\n"
            "Hotkey labels use: lowercase accelerator, 01, displayed text with 04 <highlighted letter> 01.\n"
            "The editor displays that as separate Hotkey and Displayed Text fields.")

    def on_close(self):
        dirty = [a.path.name for a in self.archives if a.dirty]
        if dirty and not messagebox.askyesno("Unsaved changes", "Discard unsaved changes in:\n\n" + "\n".join(dirty)):
            return
        self.stop_audio()
        self.destroy()


def main():
    app = Workbench()
    app.mainloop()


if __name__ == "__main__":
    main()
