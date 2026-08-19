# SL3 の Z80 ターゲット(main.hex)を CP/M 環境(RunCPM)で実際に実行するための
# 実行専用コンテナ。アセンブル/リンク(dotnet + N80.dll/LK80.dll)はホスト側で
# 行い、このイメージは生成済みの .hex を読み込んで動かすことだけを担当する。

FROM debian:12-slim AS builder

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends git build-essential unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# バージョンを固定して再現性を確保する
ARG RUNCPM_REF=master
RUN git clone -q https://github.com/MockbaTheBorg/RunCPM /opt/RunCPM \
    && cd /opt/RunCPM && git checkout -q "${RUNCPM_REF}"

WORKDIR /opt/RunCPM/RunCPM
RUN make posix build

FROM debian:12-slim

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends python3 unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /cpm
COPY --from=builder /opt/RunCPM/RunCPM/RunCPM /cpm/RunCPM
COPY --from=builder /opt/RunCPM/DISK/A0.zip /cpm/A0.zip
RUN mkdir -p /cpm/A/0 && unzip -q /cpm/A0.zip -d /cpm/A/0 && rm /cpm/A0.zip

COPY hex2com.py /cpm/hex2com.py
COPY entrypoint.sh /cpm/entrypoint.sh
RUN chmod +x /cpm/entrypoint.sh

ENTRYPOINT ["/cpm/entrypoint.sh"]
