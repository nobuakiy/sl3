#!/usr/bin/env python3
"""Intel HEX (.hex) を CP/M の .COM 形式(ORG 0x100からの生バイナリ)に変換する。

外部ライブラリに依存しない最小実装。SL3のZ80ターゲットはコードを
ORG 0x0100 に配置するため、0x100 から書き込まれた最終アドレスまでを
そのまま切り出せば CP/M が実行できる .COM バイナリになる。
"""
import sys

COM_ORIGIN = 0x100


def load_intel_hex(path: str) -> bytearray:
    image = bytearray(0x10000)
    written = set()
    base = 0
    with open(path, "r", encoding="ascii") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if not line.startswith(":"):
                raise ValueError(f"Invalid Intel HEX line: {line!r}")
            data = bytes.fromhex(line[1:])
            length, addr_hi, addr_lo, rec_type = data[0], data[1], data[2], data[3]
            addr = (addr_hi << 8) | addr_lo
            payload = data[4:4 + length]

            if rec_type == 0x00:  # データレコード
                full_addr = base + addr
                for i, b in enumerate(payload):
                    a = (full_addr + i) & 0xFFFF
                    image[a] = b
                    written.add(a)
            elif rec_type == 0x01:  # EOF
                break
            elif rec_type == 0x02:  # Extended Segment Address
                base = (payload[0] << 8 | payload[1]) << 4
            elif rec_type == 0x04:  # Extended Linear Address
                base = (payload[0] << 8 | payload[1]) << 16
            # それ以外のレコード種別は無視する

    if not written:
        raise ValueError("HEX file contains no data records")

    max_addr = max(written)
    if max_addr < COM_ORIGIN:
        raise ValueError(f"No data found at/after 0x{COM_ORIGIN:04X} (CP/M TPA start)")
    return image[COM_ORIGIN:max_addr + 1]


def main() -> None:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.hex> <output.com>", file=sys.stderr)
        sys.exit(1)

    binary = load_intel_hex(sys.argv[1])
    with open(sys.argv[2], "wb") as f:
        f.write(binary)
    print(f"Wrote {len(binary)} bytes to {sys.argv[2]} (origin 0x{COM_ORIGIN:04X})")


if __name__ == "__main__":
    main()
