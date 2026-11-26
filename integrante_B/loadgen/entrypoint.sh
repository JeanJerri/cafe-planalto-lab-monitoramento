#!/bin/sh
set -u

DELAY="${STARTUP_DELAY:-5}"
echo "[loadgen] Aguardando ${DELAY}s para estabilizacao da rede e dos servicos..."
sleep "${DELAY}"

while true; do
    echo "[loadgen] Iniciando carga k6 -> ${TARGET_URL:-http://loja.cafeplanalto.lab} (${TARGET_RPS:-10} req/s)"
    k6 run --no-usage-report /loadgen/script.js || true
    echo "[loadgen] k6 finalizado; reiniciando em 2s..."
    sleep 2
done
