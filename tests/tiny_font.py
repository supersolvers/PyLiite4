"""Build a minimal TrueType font in memory, with a family name no system has, for testing font registration.

It has one glyph besides .notdef, a box for "A", and the tables FreeType and fontconfig need.
"""

import struct


def _checksum(data: bytes) -> int:
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(data) // 4}I", data)) & 0xFFFFFFFF


def _name_table(family: str) -> bytes:
    names = {1: family, 2: "Regular", 4: f"{family} Regular", 6: family.replace(" ", "") + "-Regular"}
    strings = [text.encode("utf-16-be") for text in names.values()]
    records, offset = b"", 0
    for name_id, data in zip(names, strings):
        # Windows, Unicode BMP, US English.
        records += struct.pack(">HHHHHH", 3, 1, 0x409, name_id, len(data), offset)
        offset += len(data)
    return struct.pack(">HHH", 0, len(names), 6 + 12 * len(names)) + records + b"".join(strings)


def tiny_font(family: str) -> bytes:
    """A TrueType font whose family is ``family``."""
    box = struct.pack(">hhhhh", 1, 50, 0, 450, 700) + struct.pack(">HH", 3, 0) + bytes([1, 1, 1, 1]) \
        + struct.pack(">4h", 50, 400, 0, -400) + struct.pack(">4h", 0, 0, 700, 0)
    box += b"\0" * (-len(box) % 4)
    cmap_format4 = struct.pack(">7H", 4, 32, 0, 4, 4, 1, 0) + struct.pack(">2H", 0x41, 0xFFFF) + b"\0\0" \
        + struct.pack(">2H", 0x41, 0xFFFF) + struct.pack(">2H", (1 - 0x41) & 0xFFFF, 1) + struct.pack(">2H", 0, 0)
    tables = {
        b"OS/2": struct.pack(">HhHHH11h10s4I4sHHHhhhHH2IhhHHH", 4, 500, 400, 5, 0, 650, 700, 0, 140, 650, 700, 0,
                             480, 50, 250, 0, bytes(10), 1, 0, 0, 0, b"TEST", 0x40, 0x41, 0x41, 800, -200, 0, 800,
                             200, 1, 0, 500, 700, 0, 0x20, 1),
        b"cmap": struct.pack(">HHHHI", 0, 1, 3, 1, 12) + cmap_format4,
        b"glyf": box,
        b"head": struct.pack(">IIIIHHqqhhhhHHhhh", 0x00010000, 0x00010000, 0, 0x5F0F3CF5, 0x000B, 1000, 0, 0,
                             0, 0, 500, 700, 0, 8, 2, 0, 0),
        b"hhea": struct.pack(">Ihhh H hhh hhh hhhh h H".replace(" ", ""), 0x00010000, 800, -200, 0, 600, 0, 0, 500,
                             1, 0, 0, 0, 0, 0, 0, 0, 2),
        b"hmtx": struct.pack(">HhHh", 500, 0, 600, 50),
        b"loca": struct.pack(">3H", 0, 0, len(box) // 2),
        b"maxp": struct.pack(">I14H", 0x00010000, 2, 4, 1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0),
        b"name": _name_table(family),
        b"post": struct.pack(">IIhhIIIII", 0x00030000, 0, -100, 50, 0, 0, 0, 0, 0),
    }
    count = len(tables)
    power = 1 << (count.bit_length() - 1)
    header = struct.pack(">IHHHH", 0x00010000, count, power * 16, power.bit_length() - 1, (count - power) * 16)
    directory, body = b"", b""
    offset = len(header) + 16 * count
    for tag in sorted(tables):
        data = tables[tag]
        directory += struct.pack(">4sIII", tag, _checksum(data), offset + len(body), len(data))
        body += data + b"\0" * (-len(data) % 4)
    return header + directory + body
