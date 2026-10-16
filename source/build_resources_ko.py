"""Replace the two Japanese title-logo textures in the Vita resources ARCV."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from build_vita_korean import ROOT, WORK, build_entry, read_archive

SOURCE = ROOT / "input" / "vita" / "resources.dat"
OUTPUT = ROOT / "03_PATCH" / "resources_ko_title_trial.dat"
ASSETS = WORK / "logo_assets"
REPLACEMENTS = {
    r".\Projects\Guac\meshes\textures\guac_logo_noflame.dds": ASSETS / "guac_logo_noflame_ko.dds",
    r".\Projects\Guac\meshes\textures\guac_main_tilte_screen.dds": ASSETS / "guac_main_tilte_screen_ko.dds",
}


def main():
    prefix, names, entries = read_archive(SOURCE)
    actual = {name.lower(): name for name in names}
    replacement_bytes = {}
    for requested, path in REPLACEMENTS.items():
        name = actual.get(requested.lower())
        if not name:
            raise KeyError(f"Archive resource not found: {requested}")
        old = entries[name][1]
        new = path.read_bytes()
        if len(new) != len(old) or old[:128] != new[:128]:
            raise ValueError(f"Texture header or size changed: {name}")
        replacement_bytes[name] = new
    records, offsets = [], [0]
    for name in names:
        old_record, _ = entries[name]
        record = build_entry(old_record[:9], replacement_bytes[name]) if name in replacement_bytes else old_record
        records.append(record)
        offsets.append(offsets[-1] + len(record))
    table_size = len(names) * 4 + 8
    with OUTPUT.open("wb") as file:
        file.write(prefix[:-table_size])
        file.write(prefix[-table_size:-table_size + 4])
        file.write(struct.pack("<" + "I" * len(offsets), *offsets))
        file.writelines(records)
    _, verified_names, verified_entries = read_archive(OUTPUT)
    if verified_names != names:
        raise AssertionError("Resource file names changed")
    for name in names:
        if verified_entries[name][1] != replacement_bytes.get(name, entries[name][1]):
            raise AssertionError(f"Resource mismatch after round trip: {name}")
    report = {
        "original_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "entries": len(names),
        "changed": list(replacement_bytes),
        "output_bytes": OUTPUT.stat().st_size,
    }
    (WORK / "resources_ko_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

