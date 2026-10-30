#!/usr/bin/env bash
# Einfacher Sender-Start mit automatischer Portsuche (ESP32-C3, Espressif USB-JTAG).
# Aufruf: ./tx.sh [FREQ_MHZ] [BAUD] [FEC] [weitere tx_dvbs.py-Optionen ...]
#   ./tx.sh                      -> 2403.75 MHz, 500000 Bd, FEC 3/5 (Testbild)
#   ./tx.sh 2370 333000 3/5      -> andere Frequenz/Symbolrate
#   ./tx.sh 2403.75 500000 3/5 --seconds 30
# Port festlegen statt suchen: PORT=/dev/ttyACM1 ./tx.sh
# Quarzfehler des Boards korrigieren (mein C3: ca. +36 ppm): PPM=28 ./tx.sh 2403.25 250000 1/2
# DVB-S statt DVB-S2 (bei kleinen Symbolraten bei mir zuverlaessiger): DVBS=1 PPM=28 ./tx.sh 2403.25 250000 1/2
# ACHTUNG: sendet wirklich (13 cm, Antenne/Last anschliessen, nur im Rahmen der Lizenz).
set -euo pipefail
cd "$(dirname "$0")"

FREQ="${1:-2403.75}"
BAUD="${2:-500000}"
FEC="${3:-3/5}"
shift $(( $# < 3 ? $# : 3 ))

PPM="${PPM:-0}"
if [ "${DVBS:-0}" = "1" ]; then MODE_ARGS=(); else MODE_ARGS=(--dvbs2 --mod qpsk); fi

if [ -z "${PORT:-}" ]; then
    # Nur das Espressif-Geraet nehmen, nicht PlutoSDR/tinySA/CH340 an anderen ttyACM/ttyUSB.
    PORT="$(ls /dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_*-if00 2>/dev/null | head -n1 || true)"
fi
if [ -z "$PORT" ]; then
    echo "Kein ESP32-C3 (Espressif USB JTAG) gefunden. Vorhandene Ports:" >&2
    ls /dev/serial/by-id 2>/dev/null >&2 || true
    exit 1
fi
echo "Port: $PORT  |  $FREQ MHz, $BAUD Bd, FEC $FEC, ppm $PPM, ${MODE_ARGS[*]:-DVB-S}"

exec python3 host/tx_dvbs.py --test --port "$PORT" --freq "$FREQ" --baud "$BAUD" \
    "${MODE_ARGS[@]}" --fec "$FEC" --ppm "$PPM" --service-name DG7NDV "$@"
