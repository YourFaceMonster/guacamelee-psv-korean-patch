"""Experimental font transplant for the Vita Korean text prototype.

PC Latin GFONT files contain the Korean glyphs used by the PC patch. This
trial substitutes them for Vita Japanese GFONT files to test compatibility.
The result is experimental and must be checked in Vita3K before use.
"""

from __future__ import annotations

import hashlib
import json
import struct

from build_vita_korean import PC, ROOT, WORK, OUTPUT, build_entry, read_archive


TRIAL = ROOT / "03_PATCH" / "misc_ko_font_trial.dat"
REPORT = WORK / "font_trial_report.json"


def main() -> None:
    prefix, names, vita = read_archive(OUTPUT)
    _, _, pc = read_archive(PC)
    pc_by_name = {name.lower(): data for name, data in pc.items()}
    replacements = {}
    details = []

    for name in names:
        low = name.lower()
        if not (low.startswith("fonts\\") and low.endswith(".japanese.fnt")):
            continue
        source_name = name[: -len("japanese.fnt")] + "latin.fnt"
        source = pc_by_name.get(source_name.lower())
        if source is None:
            raise ValueError(f"Missing PC Korean font: {source_name}")
        data = source[1]
        if not data.startswith(b"GFONT"):
            raise ValueError(f"Invalid PC GFONT: {source_name}")
        replacements[name] = data
        details.append({"vita_target": name, "pc_source": source_name, "bytes": len(data)})

    records = []
    offsets = [0]
    for name in names:
        original_record, _ = vita[name]
        new_data = replacements.get(name)
        record = build_entry(original_record[:9], new_data) if new_data is not None else original_record
        records.append(record)
        offsets.append(offsets[-1] + len(record))

    table_size = len(names) * 4 + 8
    with TRIAL.open("wb") as out:
        out.write(prefix[:-table_size])
        out.write(prefix[-table_size : -table_size + 4])
        out.write(struct.pack("<" + "I" * len(offsets), *offsets))
        out.writelines(records)

    _, new_names, new_entries = read_archive(TRIAL)
    if new_names != names:
        raise AssertionError("ARCV entry names changed")
    for name in names:
        expected = replacements.get(name, vita[name][1])
        if new_entries[name][1] != expected:
            raise AssertionError(f"ARCV round-trip mismatch: {name}")
    report = {
        "source_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(TRIAL.read_bytes()).hexdigest(),
        "output_bytes": TRIAL.stat().st_size,
        "font_count": len(replacements),
        "fonts": details,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "fonts"}, indent=2))


if __name__ == "__main__":
    main()

