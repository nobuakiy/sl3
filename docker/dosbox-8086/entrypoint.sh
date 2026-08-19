#!/bin/sh
set -e

SRC_DIR="${SRC_DIR:-/src}"
EXE_NAME="${1:-output.exe}"

if [ ! -f "$SRC_DIR/$EXE_NAME" ]; then
    echo "error: $SRC_DIR/$EXE_NAME not found" >&2
    echo "usage: docker run -v <dir_with_exe>:/src sl3-dosbox-8086 [output.exe]" >&2
    exit 1
fi

CONF=$(mktemp)
cat > "$CONF" << EOF
[autoexec]
mount c $SRC_DIR
c:
$EXE_NAME > SL3_OUT.TXT
exit
EOF

xvfb-run -a dosbox -conf "$CONF" -c exit >/dev/null 2>&1
cat "$SRC_DIR/SL3_OUT.TXT"
rm -f "$SRC_DIR/SL3_OUT.TXT" "$CONF"
