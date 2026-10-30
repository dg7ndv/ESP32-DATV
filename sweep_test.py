#!/usr/bin/env python3
"""Frequenz-Durchlauf: ESP32-DATV-Sender (tx_dvbs.py) gegen den CYD-Spektrum-Viewer.

Fuer jede Frequenz: Viewer per `freq <MHz>` umstellen, Sender fuer ein paar Sekunden
starten und die vom Viewer ausgegebene `[cf] ...`-Zeile auswerten (Median).

Beispiel:
  ./sweep_test.py --viewer /dev/ttyUSB1 --tx-port /dev/ttyACM1
  ./sweep_test.py --viewer /dev/ttyUSB1 --tx-port /dev/ttyACM1 -f 2305 2403.75 2445
Achtung: Das sendet wirklich (Amateurfunk, 13 cm, Antenne/Last anschliessen).
Braucht pyserial (z. B. das .venv aus flash.sh).
"""
import argparse
import re
import statistics
import subprocess
import time

import serial

ap = argparse.ArgumentParser()
ap.add_argument("--viewer", required=True, help="serieller Port des CYD, z. B. /dev/ttyUSB1")
ap.add_argument("--tx-port", required=True, help="Port des ESP32-DATV-Senders, z. B. /dev/ttyACM1")
ap.add_argument("--tx-dir", default="/home/dg7ndv/sdr/Esp32-atv/ESP32-DATV")
ap.add_argument("-f", "--freqs", type=float, nargs="+",
                default=[2310.0, 2350.0, 2380.0, 2403.75, 2420.0, 2445.0],
                help="Sendefrequenzen in MHz (2300..2450)")
ap.add_argument("--baud", default="500000")
ap.add_argument("--fec", default="3/5")
ap.add_argument("--seconds", type=int, default=22, help="Sendedauer pro Frequenz")
a = ap.parse_args()

viewer = serial.Serial(a.viewer, 115200, timeout=0.3)
time.sleep(14)  # the CYD resets when the port is opened (about 12 s boot), otherwise freq is lost
for f in a.freqs:
    centre = int(round(f))
    viewer.write(f"freq {centre}\n".encode())
    tx = subprocess.Popen(
        ["python3", "host/tx_dvbs.py", "--test", "--port", a.tx_port, "--freq", str(f),
         "--baud", a.baud, "--dvbs2", "--mod", "qpsk", "--fec", a.fec,
         "--service-name", "DG7NDV", "--seconds", str(a.seconds)],
        cwd=a.tx_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(9)  # Anlauf des Senders
    viewer.reset_input_buffer()
    t0, buf = time.time(), ""
    while time.time() - t0 < a.seconds - 11:
        buf += viewer.read(500).decode(errors="replace")
    cf = [float(m) for m in re.findall(r"\[cf\] ([\d.]+) MHz", buf)]
    sr = [int(m) for m in re.findall(r"sr=(\d+)", buf)]
    if cf:
        med = statistics.median(cf)
        print(f"TX {f:8.3f} | Viewer-Mitte {centre} | CF {med:.3f} "
              f"(Fehler {1000 * (med - f):+.0f} kHz) | SR {statistics.median(sr):.0f} | n={len(cf)}",
              flush=True)
    else:
        print(f"TX {f:8.3f} | Viewer-Mitte {centre} | keine Erkennung", flush=True)
    try:
        tx.wait(timeout=40)
    except subprocess.TimeoutExpired:
        tx.terminate()
    time.sleep(2)
viewer.write(b"freq 2406\n")
