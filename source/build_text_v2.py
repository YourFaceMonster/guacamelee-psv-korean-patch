"""Complete more Vita Korean strings while retaining the proven font trial."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import struct
from collections import Counter, defaultdict

from build_vita_korean import PC, ROOT, WORK, read_archive, build_entry


SOURCE = ROOT / "03_PATCH" / "misc_ko_font_trial.dat"
OUTPUT = ROOT / "03_PATCH" / "misc_ko_v2.dat"
REPORT = WORK / "v2_report.json"
REVIEW = WORK / "v2_additions.tsv"
HANGUL = re.compile("[가-힣]")

# Prefixes are checked for a unique match within their specified file.
MANUAL = {
    ("langGeneral.txt", "This game saves data automatically"): "이 게임은 진행 상황을 특정 지점에서 자동으로 저장합니다.\\n\\n저장 아이콘이 표시되는 동안 전원을 끄지 마세요.",
    ("langGeneral.txt", "Please adjust your video settings"): "화면 표시 영역을 조정하세요.\\n\\n{DPAD}로 화살표가 모두 보이도록 조정하세요.\\n\\n{MENUCONFIRM}을 누르면 결정합니다.",
    ("langGeneral.txt", '"The installed game is corrupted.'): "설치된 게임 데이터가 손상되었습니다.\\n게임을 종료하고 삭제한 뒤 다시 설치해 주세요.",
    ("langGeneral.txt", '"There is not enough available space in the HDD.\\nTo create data,'): "저장 공간이 부족합니다.\\n데이터를 만들려면 %ls 이상의 공간이 필요합니다.\\n\\n게임을 종료하고 공간을 확보해 주세요.",
    ("langGeneral.txt", "Screen Settings"): "화면 설정",
    ("langGeneral.txt", '"There is not enough available space in the HDD.\\nWould you like'): "저장 공간이 부족합니다.\\n저장을 다시 시도하시겠습니까?\\n\\n다시 시도하지 않으면 진행 상황이 저장되지 않습니다.",
    ("langGeneral.txt", '"No existing save file found.'): "기존 저장 데이터가 없습니다.\\n불러오기를 다시 시도하시겠습니까?\\n\\n다시 시도하지 않으면 새 저장 데이터가 만들어집니다.",
    ("langGeneral.txt", '"The save file appears to be corrupt.'): "저장 데이터가 손상된 것 같습니다.\\n불러오기를 다시 시도하시겠습니까?\\n\\n다시 시도하지 않으면 다음 저장 시 기존 데이터가 덮어쓰입니다.",
    ("langGeneral.txt", '"An error occurred while loading the save file.'): "저장 데이터를 불러오는 중 오류가 발생했습니다.\\n다시 시도하시겠습니까?\\n\\n다시 시도하지 않으면 다음 저장 시 기존 데이터가 덮어쓰입니다.",
    ("langGeneral.txt", '"An error occurred while creating the save file.'): "저장 데이터를 만드는 중 오류가 발생했습니다.\\n다시 시도하시겠습니까?\\n\\n다시 시도하지 않으면 진행 상황이 저장되지 않습니다.",
    ("langGeneral.txt", "This game supports PlayStation Home Rewards"): "이 게임은 PlayStation®Home 보상을 지원합니다.\\n\\n보상을 받으려면 PlayStation®Home을 설치해 주세요.",
    ("langGeneral.txt", "Hold [S] +- 10"): "{SQUARE} 길게 누르기: +/- 10",
    ("langGeneral.txt", "Hold [T] +- 100"): "{TRIANGLE} 길게 누르기: +/- 100",
    ("langGeneral.txt", "OnlineUploadNotAllowed"): "다른 사용자의 저장 데이터를 불러왔습니다.\\n클라우드에 업로드할 수 없습니다.",
    ("langGeneral.txt", "OnlineDownloadNoData"): "클라우드에 저장 데이터가 없습니다.",
    ("langCutscenes.txt", '"Before he was'): "칼라카가 되기 전,",
    ("langCutscenes.txt", '"he was'): "카를로스는 '엘 차로'로 불렸습니다.",
    ("langCutscenes.txt", '"People called him'): "사람들은 그를 차레리아의 최고수라 불렀습니다.",
    ("langCutscenes.txt", '"Only one event'): "단 하나, '라 그란 차레아다'만은\\n그의 손에 닿지 않았습니다.",
    ("langCutscenes.txt", '"In exchange for his soul'): "카를로스는 영혼을 대가로\\n그 대회에서 우승했습니다.",
    ("langCutscenes.txt", '"Carlos felt cheated'): "하지만 그토록 원하던 영광을 얻지 못한\\n카를로스는 속았다고 느꼈습니다.",
    ("langCutscenes.txt", '"With my help'): "내 도움으로 카를로스는 악마를 수탉으로 만들었지요…",
    ("langDemo.txt", "Demo_Guacamelee_Thanks"): "과카밀리! 체험판을\\n플레이해 주셔서 감사합니다.",
    ("langDemo.txt", "Demo_Guacamelee_BuyGame"): "정식판에서는 이런 모험을 즐길 수 있습니다!",
    ("langDemo.txt", "Demo_Guacamelee_BulletCoOp"): "- 오프라인 협동 플레이(PlayStation®3판 전용)",
    ("langDemo.txt", "Demo_Guacamelee_BulletExplore"): "- 멕시코풍 세계 곳곳 탐험",
    ("langDemo.txt", "Demo_Guacamelee_BulletCombat"): "- 통쾌한 레슬링 액션",
    ("langDemo.txt", "Demo_Guacamelee_BulletDimensions"): "- 도전적인 퍼즐 스테이지",
    ("langDemo.txt", "Demo_Guacamelee_BulletChickens"): "- 모두가 사랑하는 닭이 잔뜩!",
    ("langDemo.txt", "Demo_Guacamelee_BulletCrossBuy"): "- 크로스 바이 지원! 한 번 사면 두 버전 모두",
    ("langDemo.txt", "Demo_Guacamelee_BulletCrossSave"): "- 크로스 세이브 지원! 진행 상황을 이어서",
    ("langGeneral.txt", "Game Title"): "과카밀리!",
    ("langGeneral.txt", "JapaneseLang"): "한국어",
    ("langGeneral.txt", "GuacShopConfirmPrice"): "\\n금액: $",
    ("langGeneral.txt", "Bonus Orb Money"): "보너스 오브 금액",
    ("langGeneral.txt", "Orb Pickup Radius"): "오브 획득 범위",
    ("langGeneral.txt", "OlmecHeadbuttAction"): "{B} (공중에서도 가능)",
    ("langGeneral.txt", "RoosterUppercutAction"): "{LSTICKUP}+{B} (공중에서도 가능)",
    ("langGeneral.txt", "DashingDerpderpAction"): "{LSTICKRIGHT}+{B} (공중에서도 가능)",
    ("langGeneral.txt", "swfRooster Uppercut"): "루스터 어퍼컷",
    ("langGeneral.txt", "swfOlmec's Headbutt"): "올멕 헤드버트",
    ("langGeneral.txt", "swfFrog Slam"): "프로그 슬램",
    ("langGeneral.txt", "swfDashing Derpderp"): "파워 펀치",
    ("langGeneral.txt", "swfGoat Climb"): "염소 등반",
    ("langGeneral.txt", "swfGoat Fly"): "염소 비행",
    ("langGeneral.txt", "swfDas Boot"): "다스 부트",
    ("langGeneral.txt", "swfPiledriver"): "파일드라이버",
    ("langGeneral.txt", "swfSuplex"): "수플렉스",
    ("langGeneral.txt", "swfNo Power"): "능력 없음",
    ("langGeneral.txt", "swfPollo Power"): "닭의 힘",
    ("langGeneral.txt", "swfDimension Swap"): "차원 전환",
    ("langGeneral.txt", "swfGoat Jump"): "염소 점프",
    ("langGeneral.txt", "swfWall Grab"): "벽 매달리기",
    ("langGeneral.txt", "swfDouble Jump"): "이단 점프",
    ("langPatch02.txt", "Infierno_NPC_GOld"): "여기선 처리할 서류가 산더미라\\n탑의 고문실이 낡아 버렸어.\\p사업가 기질이 있는 엘 디아블로가\\n그곳을 기묘한 오락 시설로 바꿔 놨지.",
    ("langPatch02.txt", "Infierno_NPC_HOld"): "여기에도 규칙이 있어!\\p공적상을 정해진 수만큼 신청하지 않으면\\n아무도 엘 디아블로를 만날 수 없지!\\p그런 체계가 없으면 온통 난장판이 될 거야!\\p여긴 저승, 엘 인피에르노야!\\n엄연한 사업장이라고!",
    ("langPatch02.txt", "Infierno_Diablo_AOld"): "내 사무실에 온 걸 환영하네, 루차도르.\\p보다시피 모든 게 엉망이지.\\p칼라카 때문에 서류 업무가 골칫거리가 됐어!\\n놈을 물리쳐 준다면 내 정당한 영역의\\n지배권을 되찾는 데 도움이 되겠지.\\p지금까지의 활약은 인상적이었어.\\p선물을 주고 싶을 만큼 말이지.\\p이 상자 안에 든 건 전부 자네 거야.",
    ("langPatch02.txt", "Infierno_Diablo_BOld"): "업무가 이렇게 밀린 적은 단 한 번도 없었어!\\p칼라카는 반드시 대가를 치를 거야!\\p…\\p하지만 자네 세계에 무슨 일이 생기든\\n나와는 상관없네.",
    ("langPatch02.txt", "Dynamite_Salesman_Intro2old"): "사람들 말로는 예전에 이곳이 고대의 신비한 장소,\\n차크 몰의 숨겨진 영역 중 하나로 통했다더군.\\p하지만 보다시피 폐허가 됐어!\\n엄청난 힘이 있어야 가능한 일이지.\\p여기서 무슨 일이 있었는지는 아무도 몰라.\\n칼라카가 저승에서 탈출할 때\\n직접 부쉈다는 소문도 들었어!\\p엘 디아블로의 영역으로 곧장 이어지는 길을\\n남겼다니… 생각만 해도 무섭군.",
}

TOKEN_FIXES = {
    "NoCostumeAttributesP2": {"{A}": "{START}"},
    "NoCostumeAttributesP1": {"{A}": "{START}"},
    "[triangle] Buy": {"{MENUY}": "{TRIANGLE}"},
}


def main() -> None:
    prefix, names, vita_entries = read_archive(SOURCE)
    _, _, pc_entries = read_archive(PC)
    global_korean: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pc_name, (_, data) in pc_entries.items():
        if not (pc_name.lower().startswith("misc\\lang") and pc_name.lower().endswith(".txt")):
            continue
        if pc_name.lower() == "misc\\langlist.txt":
            continue
        lines = data.decode("utf-16").splitlines()
        head = lines[0].split("\t")
        if "English" not in head:
            continue
        english = head.index("English")
        for line in lines[1:]:
            cells = line.split("\t")
            if cells[0] and len(cells) > english and HANGUL.search(cells[english]):
                global_korean[cells[0]].append((pc_name, cells[english]))

    missing_rows = list(csv.DictReader((WORK / "unmatched_vita_rows.tsv").open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    missing = {(row["file"].lower(), row["key"]) for row in missing_rows}
    replacements = {}
    review = []
    counts = Counter()
    used_manual = Counter()

    for name in names:
        if not (name.lower().startswith("misc\\lang") and name.lower().endswith(".txt")) or name.lower() == "misc\\langlist.txt":
            continue
        original = vita_entries[name][1]
        lines = original.decode("utf-16").splitlines(keepends=True)
        head = lines[0].rstrip("\r\n").split("\t")
        if "Japanese" not in head:
            continue
        japanese = head.index("Japanese")
        file_basename = name.split("\\")[-1]
        for i in range(1, len(lines)):
            line = lines[i]
            body = line.rstrip("\r\n")
            ending = line[len(body) :]
            cells = body.split("\t")
            if len(cells) <= japanese or not cells[0]:
                continue
            key, before = cells[0], cells[japanese]
            if HANGUL.search(before):
                continue
            korean = None
            source = ""
            if (name.lower(), key) in missing:
                choices = global_korean.get(key, [])
                values = {value for _, value in choices}
                if len(values) == 1:
                    korean = next(iter(values))
                    source = ", ".join(sorted({pc_name for pc_name, _ in choices}))
                    for old_token, new_token in TOKEN_FIXES.get(key, {}).items():
                        korean = korean.replace(old_token, new_token)
                    counts["cross_file_pc_rows"] += 1
            matches = [(prefix, value) for (filename, prefix), value in MANUAL.items() if filename == file_basename and key.startswith(prefix)]
            if matches:
                if len(matches) != 1:
                    raise ValueError(f"Ambiguous manual override: {name} {key}")
                manual_prefix, korean = matches[0]
                used_manual[(file_basename, manual_prefix)] += 1
                source = "manual"
                counts["manual_rows"] += 1
            if korean is None or korean == before:
                continue
            cells[japanese] = korean
            lines[i] = "\t".join(cells) + ending
            review.append((name, key, before, korean, source))
        updated = "".join(lines).encode("utf-16")
        if updated != original:
            replacements[name] = updated

    for key in MANUAL:
        if used_manual[key] != 1:
            raise ValueError(f"Manual override was used {used_manual[key]} times: {key}")

    records = []
    offsets = [0]
    for name in names:
        old_record, _ = vita_entries[name]
        new_data = replacements.get(name)
        record = build_entry(old_record[:9], new_data) if new_data is not None else old_record
        records.append(record)
        offsets.append(offsets[-1] + len(record))
    table_size = len(names) * 4 + 8
    with OUTPUT.open("wb") as file:
        file.write(prefix[:-table_size])
        file.write(prefix[-table_size : -table_size + 4])
        file.write(struct.pack("<" + "I" * len(offsets), *offsets))
        file.writelines(records)
    _, new_names, new_entries = read_archive(OUTPUT)
    if new_names != names:
        raise AssertionError("ARCV names changed")
    for name in names:
        if new_entries[name][1] != replacements.get(name, vita_entries[name][1]):
            raise AssertionError(f"Round-trip mismatch: {name}")
    counts["changed_files"] = len(replacements)
    counts["added_rows"] = len(review)
    counts["output_bytes"] = OUTPUT.stat().st_size
    counts["output_sha256"] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    REPORT.write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")
    with REVIEW.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(("file", "key", "previous_japanese", "korean", "source"))
        writer.writerows(review)
    print(json.dumps(counts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

