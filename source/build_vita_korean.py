"""Port Korean text from the PC STCE patch into the Japanese Vita archive.

The source archives are read only. This script writes a reviewable prototype
archive and a transfer report; it does not install anything into Vita3K.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "02_WORK"
VITA = ROOT / "input" / "vita" / "misc.dat"
PC = ROOT / "input" / "pc_korean" / "misc.dat"
OUTPUT = ROOT / "03_PATCH" / "misc_ko_text_prototype.dat"
REPORT = WORK / "transfer_report.json"
ROWS = WORK / "transfer_review.tsv"
UNMATCHED = WORK / "unmatched_vita_rows.tsv"
HANGUL = re.compile("[가-힣]")


def size_from_header(header: bytes) -> int:
    assert len(header) == 9
    return int.from_bytes(header[4:9], "little") >> 3 & 0xFFFFFFFF


def header_with_size(header: bytes, size: int) -> bytes:
    assert 0 <= size <= 0xFFFFFFFF
    field = int.from_bytes(header[4:9], "little")
    field = (field & ~((0xFFFFFFFF) << 3)) | (size << 3)
    return header[:4] + field.to_bytes(5, "little")


def read_entry(stream: io.BufferedReader) -> tuple[bytes, bytes]:
    start = stream.tell()
    header = stream.read(9)
    if len(header) != 9:
        raise ValueError("Truncated ARCV entry header")
    size = size_from_header(header)
    blocks = (size + 0xFFFF) // 0x10000
    sizes_raw = stream.read(blocks * 2)
    if len(sizes_raw) != blocks * 2:
        raise ValueError("Truncated ARCV block table")
    compressed_sizes = struct.unpack("<" + "H" * blocks, sizes_raw) if blocks else ()
    chunks = []
    for index, compressed_size in enumerate(compressed_sizes):
        length = compressed_size or min(0x10000, size - 0x10000 * index)
        data = stream.read(length)
        if len(data) != length:
            raise ValueError("Truncated ARCV data")
        chunks.append(zlib.decompress(data, -15) if compressed_size else data)
    unpacked = b"".join(chunks)
    if len(unpacked) != size:
        raise ValueError(f"ARCV size mismatch: {len(unpacked)} != {size}")
    end = stream.tell()
    stream.seek(start)
    raw = stream.read(end - start)
    return raw, unpacked


def build_entry(old_header: bytes, data: bytes) -> bytes:
    sizes = []
    payloads = []
    for start in range(0, len(data), 0x10000):
        chunk = data[start : start + 0x10000]
        compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = compressor.compress(chunk) + compressor.flush()
        if len(compressed) >= len(chunk) or len(compressed) > 0xFFFF:
            sizes.append(0)
            payloads.append(chunk)
        else:
            sizes.append(len(compressed))
            payloads.append(compressed)
    return (
        header_with_size(old_header, len(data))
        + struct.pack("<" + "H" * len(sizes), *sizes)
        + b"".join(payloads)
    )


def read_archive(path: Path) -> tuple[bytes, list[str], dict[str, tuple[bytes, bytes]]]:
    with path.open("rb") as stream:
        header = stream.read(10)
        if header[:6] != b"ARCV\x00\x01":
            raise ValueError(f"Unexpected ARCV signature/version: {path}")
        _, names_data = read_entry(stream)
        count = struct.unpack_from("<I", names_data)[0]
        names = [name.decode("utf-8") for name in names_data[count + 8 :].split(b"\x00") if name]
        if len(names) != count:
            raise ValueError(f"ARCV file count mismatch: {len(names)} != {count}")
        table = stream.read(count * 4 + 8)
        prefix = header + (path.read_bytes()[10 : stream.tell()])
        offsets = struct.unpack_from("<" + "I" * (count + 1), table, 4)
        entries = {}
        data_start = stream.tell()
        for index, name in enumerate(names):
            if stream.tell() - data_start != offsets[index]:
                raise ValueError(f"ARCV offset mismatch: {path} {name}")
            entries[name] = read_entry(stream)
        if stream.tell() - data_start != offsets[-1]:
            raise ValueError(f"ARCV final offset mismatch: {path}")
        if stream.read():
            raise ValueError(f"Unexpected trailing ARCV data: {path}")
        return prefix, names, entries


def main() -> None:
    vita_prefix, vita_names, vita_entries = read_archive(VITA)
    _, _, pc_entries = read_archive(PC)
    pc_by_name = {name.lower(): entry for name, entry in pc_entries.items()}
    replacements: dict[str, bytes] = {}
    review: list[tuple[str, str, str, str, str]] = []
    unmatched: list[tuple[str, str, str]] = []
    stats = Counter()

    for name in vita_names:
        if not (name.lower().startswith("misc\\lang") and name.lower().endswith(".txt")):
            continue
        if name.lower() == "misc\\langlist.txt":
            continue
        pc_entry = pc_by_name.get(name.lower())
        if pc_entry is None:
            continue
        original = vita_entries[name][1]
        pc_data = pc_entry[1]
        if not (original.startswith(b"\xff\xfe") and pc_data.startswith(b"\xff\xfe")):
            raise ValueError(f"Unexpected text encoding: {name}")
        vita_lines = original.decode("utf-16").splitlines(keepends=True)
        pc_lines = pc_data.decode("utf-16").splitlines()
        vita_head = vita_lines[0].rstrip("\r\n").split("\t")
        pc_head = pc_lines[0].split("\t")
        if "Japanese" not in vita_head or "English" not in pc_head:
            raise ValueError(f"Unexpected language columns: {name}")
        japanese_col = vita_head.index("Japanese")
        english_col = pc_head.index("English")
        pc_rows: dict[str, list[list[str]]] = defaultdict(list)
        for line in pc_lines[1:]:
            cells = line.split("\t")
            if cells[0]:
                pc_rows[cells[0]].append(cells)
        key_positions = Counter()
        for index in range(1, len(vita_lines)):
            line = vita_lines[index]
            body = line.rstrip("\r\n")
            ending = line[len(body) :]
            cells = body.split("\t")
            key = cells[0]
            if not key:
                continue
            occurrence = key_positions[key]
            key_positions[key] += 1
            matches = pc_rows.get(key, [])
            if not matches:
                stats["unmatched_vita_rows"] += 1
                unmatched.append((name, key, cells[japanese_col] if len(cells) > japanese_col else ""))
                continue
            pc_cells = matches[min(occurrence, len(matches) - 1)]
            if len(pc_cells) <= english_col or len(cells) <= japanese_col:
                stats["malformed_rows"] += 1
                continue
            korean = pc_cells[english_col]
            if not HANGUL.search(korean):
                stats["matched_without_hangul"] += 1
                continue
            old = cells[japanese_col]
            cells[japanese_col] = korean
            vita_lines[index] = "\t".join(cells) + ending
            stats["transferred_rows"] += 1
            review.append((name, key, str(occurrence + 1), old, korean))
        changed = "".join(vita_lines).encode("utf-16")
        if changed != original:
            replacements[name] = changed
            stats["changed_files"] += 1

    # The Japanese region is the only enabled locale in this Vita release.
    # Label it Korean in the language menu using the Korean PC patch text.
    stats["source_vita_sha256"] = hashlib.sha256(VITA.read_bytes()).hexdigest()
    stats["source_pc_sha256"] = hashlib.sha256(PC.read_bytes()).hexdigest()
    stats["replacement_bytes"] = sum(len(x) for x in replacements.values())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records = []
    offsets = [0]
    for name in vita_names:
        old_raw, _ = vita_entries[name]
        new_data = replacements.get(name)
        record = build_entry(old_raw[:9], new_data) if new_data is not None else old_raw
        records.append(record)
        offsets.append(offsets[-1] + len(record))
    table_size = len(vita_names) * 4 + 8
    with OUTPUT.open("wb") as out:
        out.write(vita_prefix[:-table_size])
        out.write(vita_prefix[-table_size:-table_size + 4])
        out.write(struct.pack("<" + "I" * len(offsets), *offsets))
        out.writelines(records)

    _, result_names, result_entries = read_archive(OUTPUT)
    if result_names != vita_names:
        raise AssertionError("Repacked entry names changed")
    for name in vita_names:
        expected = replacements.get(name, vita_entries[name][1])
        if result_entries[name][1] != expected:
            raise AssertionError(f"Round-trip mismatch: {name}")
    stats["output_sha256"] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    stats["output_bytes"] = OUTPUT.stat().st_size
    REPORT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    with ROWS.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(("file", "key", "occurrence", "original_japanese", "korean"))
        writer.writerows(review)
    with UNMATCHED.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(("file", "key", "original_japanese"))
        writer.writerows(unmatched)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

