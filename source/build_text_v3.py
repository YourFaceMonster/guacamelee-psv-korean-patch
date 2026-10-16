"""Correct PC-only button tokens and a few Vita-specific instructions."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import struct
from collections import Counter

from build_vita_korean import ROOT, WORK, build_entry, read_archive

SOURCE = ROOT / "03_PATCH" / "misc_ko_v2.dat"
OUTPUT = ROOT / "03_PATCH" / "misc_ko_v3.dat"
REPORT = WORK / "v3_report.json"
REVIEW = WORK / "v3_corrections.tsv"

# Use the token names found in the corresponding Vita Japanese entries.
TOKEN_FIXES = {
    "Press X": {"{CROSS}": "{MENUCONFIRM}"},
    "1Press Start": {"{FORCEDSTARTBUTTON}": "{START}"},
    "2Press Start": {"{FORCEDSTARTBUTTON}": "{START}"},
    "3Press Start": {"{FORCEDSTARTBUTTON}": "{START}"},
    "4Press Start": {"{FORCEDSTARTBUTTON}": "{START}"},
    "[X] Start": {"{CROSS}": "{MENUCONFIRM}"},
    "Mode:": {"{MENUY}": "{TRIANGLE}"},
    "[T] Mode": {"{MENUY}": "{TRIANGLE}"},
    "[L2]&[R2] Page Up/Down": {"{MENUPGUP}": "{L2}", "{MENUPGDN}": "{R2}"},
    "[X] Unlock ": {"{CROSS}": "{MENUCONFIRM}"},
    "[O] Return": {"{CIRCLE}": "{MENUCANCEL}"},
    "ViewMapTip": {"{TOGGLEMAP}": "{SELECT}"},
    "AimedThrowAction": {"방향 입력": "{LSTICK}"},
    "View Area-Map": {"{MAPCHOOSE}": "{B}"},
    "Return to Mini-Map": {"{TOGGLEMAPMODE}": "{Y}"},
    "View World Map": {"{TOGGLEMAPMODE}": "{Y}"},
    "BackB": {"{MENUCANCEL}": "{A}"},
    "NPC_Tutorial PAXHint04": {"{TOGGLEMAP}": "{L1}"},
    "NPC_XTabay_2": {"{R1}": "{R2}"},
    "UayChivo - WallFly - Part02": {"{LStickLeft}": "{LStickUp}"},
    "UayChivo - WallFly - Part04": {"{LStickLeft}": "{LStickUp}"},
    "Player2_Unlocked": {"{FORCEDSTARTBUTTON}": "{START}"},
    "Player2_Unlocked_PS3": {"{FORCEDSTARTBUTTON}": "{START}"},
    "NPC_Barrel_2": {"{TOGGLEMAP}": "{SELECT}"},
    "NPC_Barrel_3": {"{TOGGLEMAP}": "{SELECT}"},
    "XtabayDefeated3Vita": {"{R2}": "{R1}"},
    "[cross] Buy": {"{CROSS}": "{MENUCANCEL}"},
    "RestartChallengeTip": {"{TOGGLEMAP}": "{SELECT}"},
    "PassiveTutorial_Temple1_Roll03": {"{L2}": "{L3}"},
}

OVERRIDES = {
    "GenPress Start": "{START}를 누르세요",
    "BubbleInstructions": (
        "새 도전자가 나타났습니다!\\n\\n"
        "2인 플레이에 오신 것을 환영합니다.\\n"
        "토스타다를 참가시키려면 먼저 거품을 터뜨리세요.\\n\\n"
        "한 플레이어가 쓰러지고 다른 플레이어가 살아 있다면,\\n"
        "카운트다운이 0이 될 때까지 기다리세요.\\n"
        "그런 다음 {START}를 누르면 거품으로 부활합니다.\\n\\n"
        "두 플레이어가 모두 살아 있다면 언제든\\n"
        "{R1}을 눌러 거품으로 변할 수 있습니다."
    ),
    "WallGrabAction": "(벽을 향해) {Y}",
    "SuplexAction": "(잡은 후) {LSTICKLEFT}+{B}",
    "PassiveTutorial_Forest_Roll": "알림: {L2} 또는 {RSTICKLEFTRIGHT}를 사용해 공격을 피하세요.",
    "NPC_Tutorial WallCling": "벽에 매달리기 힘들면 {Y}를 눌러 벽에 붙어 있어.\\p다른 버튼은 누르지 마.",
    "Diablito10CrossPlay": (
        "정신 차려. 힘을 합쳐 보자고.\\n"
        "너만 남았어. 뒤처질 거야!\\p"
        "시간이 다가오고 있어. 도와줄 테니\\n"
        "한 사람은 {L1}을 누르고 다른 사람은\\n"
        "터치스크린을 쓸어 넘겨 봐."
    ),
}


def main() -> None:
    prefix, names, entries = read_archive(SOURCE)
    replacements = {}
    changes = []
    hit = Counter()
    for name in names:
        if not (name.lower().startswith("misc\\lang") and name.lower().endswith(".txt")):
            continue
        original = entries[name][1]
        lines = original.decode("utf-16").splitlines(keepends=True)
        head = lines[0].rstrip("\r\n").split("\t")
        if "Japanese" not in head:
            continue
        col = head.index("Japanese")
        for i in range(1, len(lines)):
            body = lines[i].rstrip("\r\n")
            ending = lines[i][len(body):]
            cells = body.split("\t")
            if len(cells) <= col:
                continue
            key = cells[0]
            before = cells[col]
            after = OVERRIDES.get(key, before)
            if key in TOKEN_FIXES:
                for old, new in TOKEN_FIXES[key].items():
                    if old not in after:
                        raise ValueError(f"Expected token missing: {name} {key} {old}")
                    after = after.replace(old, new)
            if after != before:
                cells[col] = after
                lines[i] = "\t".join(cells) + ending
                changes.append((name, key, before, after))
                hit[key] += 1
        updated = "".join(lines).encode("utf-16")
        if updated != original:
            replacements[name] = updated
    for key in set(TOKEN_FIXES) | set(OVERRIDES):
        if hit[key] != 1:
            raise ValueError(f"Expected one correction for {key}: {hit[key]}")
    records = []
    offsets = [0]
    for name in names:
        old_record, old_data = entries[name]
        record = build_entry(old_record[:9], replacements[name]) if name in replacements else old_record
        records.append(record)
        offsets.append(offsets[-1] + len(record))
    table_size = len(names) * 4 + 8
    with OUTPUT.open("wb") as f:
        f.write(prefix[:-table_size])
        f.write(prefix[-table_size:-table_size + 4])
        f.write(struct.pack("<" + "I" * len(offsets), *offsets))
        f.writelines(records)
    _, verify_names, verify = read_archive(OUTPUT)
    if verify_names != names:
        raise AssertionError("Name mismatch")
    for name in names:
        if verify[name][1] != replacements.get(name, entries[name][1]):
            raise AssertionError(f"Round trip mismatch: {name}")
    with REVIEW.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(("file", "key", "before", "after"))
        w.writerows(changes)
    report = {"corrected_rows": len(changes), "changed_files": len(replacements), "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

