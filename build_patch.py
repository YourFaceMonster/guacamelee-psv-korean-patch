"""Build the PCSG00369 Korean rePatch files from user-supplied archives.

The repository intentionally contains no commercial game or translation archives.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
EXPECTED = {
    "vita_misc": "cf454adbce9b1a17d9f2f2aa7cec1810c791a419a2699473cb9fdbd3da99ea0c",
    "vita_resources": "3af47ee792d341e46c2da4f5b77a44998b9394f97da3d414fe211543bc62f121",
    "pc_korean_misc": "9a3ae2b5b3f1305c37d11401b1c12d3e4b06cbaa195c1c26afb9142dd9fc8d10",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vita-misc", type=Path, required=True, help="Original Japanese PCSG00369 misc.dat")
    parser.add_argument("--vita-resources", type=Path, required=True, help="Original Japanese PCSG00369 resources.dat")
    parser.add_argument("--pc-korean-misc", type=Path, required=True, help="GuacameleeSTCE_kor_1.1 misc.dat")
    parser.add_argument("--output", type=Path, default=ROOT / "build", help="Output directory")
    args = parser.parse_args()

    inputs = {
        "vita_misc": args.vita_misc.resolve(),
        "vita_resources": args.vita_resources.resolve(),
        "pc_korean_misc": args.pc_korean_misc.resolve(),
    }
    for name, path in inputs.items():
        if not path.is_file():
            parser.error(f"Missing {name}: {path}")
    for name, expected in EXPECTED.items():
        actual = sha256(inputs[name])
        if actual != expected:
            parser.error(f"Unexpected {name} SHA-256: {actual}. Use the original PCSG00369 archive.")

    output = args.output.resolve()
    if output == ROOT or output == SOURCE or ROOT in output.parents and output.name == "source":
        parser.error("Output must not overwrite the repository source files")
    work = output / "work"
    assets = work / "logo_assets"
    patch = output / "rePatch" / "PCSG00369"
    assets.mkdir(parents=True, exist_ok=True)
    patch.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(SOURCE))

    import build_vita_korean as text1

    text1.WORK = work
    text1.VITA = inputs["vita_misc"]
    text1.PC = inputs["pc_korean_misc"]
    text1.OUTPUT = work / "misc_ko_text_prototype.dat"
    text1.REPORT = work / "transfer_report.json"
    text1.ROWS = work / "transfer_review.tsv"
    text1.UNMATCHED = work / "unmatched_vita_rows.tsv"
    text1.main()

    import build_font_trial as font

    font.OUTPUT = text1.OUTPUT
    font.PC = inputs["pc_korean_misc"]
    font.TRIAL = work / "misc_ko_font_trial.dat"
    font.REPORT = work / "font_trial_report.json"
    font.main()

    import build_text_v2 as text2

    text2.WORK = work
    text2.PC = inputs["pc_korean_misc"]
    text2.SOURCE = font.TRIAL
    text2.OUTPUT = work / "misc_ko_v2.dat"
    text2.REPORT = work / "v2_report.json"
    text2.REVIEW = work / "v2_additions.tsv"
    text2.main()

    import build_text_v3 as text3

    text3.WORK = work
    text3.SOURCE = text2.OUTPUT
    text3.OUTPUT = patch / "misc.dat"
    text3.REPORT = work / "v3_report.json"
    text3.REVIEW = work / "v3_corrections.tsv"
    text3.main()

    _, _, resources = text1.read_archive(inputs["vita_resources"])
    names = {
        "guac_logo_noflame.dds": r".\Projects\Guac\meshes\textures\guac_logo_noflame.dds",
        "guac_main_tilte_screen.dds": r".\Projects\Guac\meshes\textures\guac_main_tilte_screen.dds",
    }
    for local_name, archive_name in names.items():
        (assets / local_name).write_bytes(resources[archive_name][1])
    for image_name in ("guac_korean_logo_noflame_generated.png", "guac_korean_title_screen_generated.png"):
        shutil.copyfile(ROOT / "images" / image_name, assets / image_name)

    import build_logo_dds as logo

    logo.ROOT = assets
    logo.main()

    import build_resources_ko as resource_builder

    resource_builder.WORK = work
    resource_builder.SOURCE = inputs["vita_resources"]
    resource_builder.OUTPUT = patch / "resources.dat"
    resource_builder.ASSETS = assets
    resource_builder.REPLACEMENTS = {
        names["guac_logo_noflame.dds"]: assets / "guac_logo_noflame_ko.dds",
        names["guac_main_tilte_screen.dds"]: assets / "guac_main_tilte_screen_ko.dds",
    }
    resource_builder.main()

    for name in ("misc.dat", "resources.dat"):
        path = patch / name
        print(f"{path}: {path.stat().st_size:,} bytes, SHA-256 {sha256(path)}")


if __name__ == "__main__":
    main()

