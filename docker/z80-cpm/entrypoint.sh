#!/bin/sh
set -e

HEX_FILE="${1:-/src/main.hex}"
COM_NAME="${2:-SL3PROG}"

if [ ! -f "$HEX_FILE" ]; then
    echo "error: hex file not found: $HEX_FILE" >&2
    echo "usage: docker run -v <build_dir>:/src sl3-z80-cpm [/src/main.hex]" >&2
    exit 1
fi

python3 /cpm/hex2com.py "$HEX_FILE" "/cpm/A/0/${COM_NAME}.COM"

cd /cpm
printf '%s\nEXIT\n' "$COM_NAME" | ./RunCPM
