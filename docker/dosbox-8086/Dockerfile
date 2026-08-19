# SL3 の 8086 ターゲット(output.exe)を実際の DOS 環境(DOSBox)で実行するための
# 実行専用コンテナ。アセンブル/リンク(nasm + alink + PRINTF.obj/PRINT.obj)は
# ホスト側で行い、このイメージは生成済みの .exe を読み込んで動かすことだけを担当する。

FROM debian:12-slim

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends dosbox xvfb xauth ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /dos
COPY entrypoint.sh /dos/entrypoint.sh
RUN chmod +x /dos/entrypoint.sh

ENTRYPOINT ["/dos/entrypoint.sh"]
