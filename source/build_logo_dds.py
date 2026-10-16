"""Prepare localized Vita BC1/BC3 DDS payloads without changing archive data."""

from pathlib import Path
from PIL import Image
import io
import json
import struct

ROOT = Path(__file__).resolve().parent


def morton(x: int, y: int, width: int, height: int) -> int:
    n = min(width.bit_length() - 1, height.bit_length() - 1)
    out = 0
    for bit in range(n):
        out |= ((y >> bit) & 1) << (2 * bit)
        out |= ((x >> bit) & 1) << (2 * bit + 1)
    out |= (x >> n) << (2 * n)
    out |= (y >> n) << (2 * n + max(0, width.bit_length() - 1 - n))
    return out


def untile(data: bytes, w: int, h: int, block_size: int) -> bytes:
    bw, bh = w // 4, h // 4
    out = bytearray(len(data))
    for y in range(bh):
        for x in range(bw):
            src = morton(x, y, bw, bh) * block_size
            dst = (y * bw + x) * block_size
            out[dst:dst + block_size] = data[src:src + block_size]
    return bytes(out)


def tile(data: bytes, w: int, h: int, block_size: int) -> bytes:
    bw, bh = w // 4, h // 4
    out = bytearray(len(data))
    for y in range(bh):
        for x in range(bw):
            src = (y * bw + x) * block_size
            dst = morton(x, y, bw, bh) * block_size
            out[dst:dst + block_size] = data[src:src + block_size]
    return bytes(out)


def build(src_name: str, dst_name: str, png_name: str, w: int, h: int, fmt: str) -> dict:
    old = (ROOT / src_name).read_bytes()
    header, old_payload = old[:128], old[128:]
    block_size = 16 if fmt == "DXT5" else 8
    sizes = []
    ww, hh = w, h
    while ww >= 8 and hh >= 4:
        sizes.append((ww, hh, ww * hh * block_size // 16))
        ww //= 2
        hh //= 2
    if sum(size for _, _, size in sizes) != len(old_payload):
        raise ValueError(f"Unexpected mip chain: {src_name} {sizes} vs {len(old_payload)}")
    # Prove the tiling transform is byte reversible on the original texture.
    pos = 0
    for ww, hh, size in sizes:
        piece = old_payload[pos:pos + size]
        if tile(untile(piece, ww, hh, block_size), ww, hh, block_size) != piece:
            raise AssertionError(f"Tiling round trip failed: {src_name} {ww}x{hh}")
        pos += size
    image = Image.open(ROOT / png_name).convert("RGBA" if fmt == "DXT5" else "RGB")
    payload = bytearray()
    for ww, hh, size in sizes:
        mip = image.resize((ww, hh), Image.Resampling.LANCZOS)
        memory = io.BytesIO()
        mip.save(memory, format="DDS", pixel_format=fmt)
        linear = memory.getvalue()[128:]
        if len(linear) != size:
            raise AssertionError(f"Encoder size mismatch: {dst_name} {ww}x{hh} {len(linear)} != {size}")
        payload.extend(tile(linear, ww, hh, block_size))
    output = header + payload
    if len(output) != len(old):
        raise AssertionError("Output size differs from original")
    (ROOT / dst_name).write_bytes(output)
    # Decode the generated base level as an independent visual QA image.
    preview_header = bytearray(header)
    struct.pack_into("<II", preview_header, 12, h, w)
    struct.pack_into("<I", preview_header, 28, 1)
    base = sizes[0][2]
    decoded = Image.open(io.BytesIO(bytes(preview_header) + untile(payload[:base], w, h, block_size)))
    decoded.load()
    decoded.save(ROOT / dst_name.replace(".dds", "_preview.png"))
    return {"file": dst_name, "bytes": len(output), "mips": len(sizes), "base_size": [w, h]}


def main():
    noflame = Image.open(ROOT / "guac_korean_logo_noflame_generated.png").convert("RGBA")
    noflame.thumbnail((504, 210), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    canvas.alpha_composite(noflame, ((512 - noflame.width) // 2, (256 - noflame.height) // 2))
    canvas.save(ROOT / "guac_korean_logo_noflame_canvas.png")
    result = [
        build("guac_logo_noflame.dds", "guac_logo_noflame_ko.dds", "guac_korean_logo_noflame_canvas.png", 512, 256, "DXT5"),
        build("guac_main_tilte_screen.dds", "guac_main_tilte_screen_ko.dds", "guac_korean_title_screen_generated.png", 1024, 512, "DXT1"),
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

