# ESP32-DATV – Linux helper scripts and test notes (DG7NDV)

> DRAFT – not yet pushed. Items marked **TODO** need your input.

**Deutsch weiter unten / English first.**

---

## English

### What this is

This is a fork of [SP8ESA/ESP32-DATV](https://github.com/SP8ESA/ESP32-DATV), a DVB-S/DVB-S2
transmitter for a bare ESP32-C3 (13 cm band, no external RF hardware).
All firmware and host code are the work of SP8ESA. This fork only adds small
Linux helper scripts and notes from my own tests with a LongMynd / Minitiouner receiver.

The original license (PolyForm Noncommercial 1.0.0) and copyright notice
(Copyright (c) 2026 SP8ESA) are unchanged. Noncommercial use only.

### Changes compared to upstream

Upstream commit used as base: `915e62d` ("Fix prolonged TX and RF startup/shutdown sequencing").
No firmware or Python source was modified. Added files:

| File | Purpose |
|---|---|
| `tx.sh` | Starts `host/tx_dvbs.py --test` with automatic port detection (only the Espressif USB-JTAG device is used, so PlutoSDR, tinySA or CH340 adapters are ignored). Defaults: 2403.75 MHz, 500 kBd, DVB-S2 QPSK, FEC 3/5, service name `DG7NDV`. Usage: `./tx.sh [FREQ_MHZ] [BAUD] [FEC] [extra tx_dvbs.py options]`. `PORT=/dev/ttyACM1 ./tx.sh` forces a port, `PPM=28 ./tx.sh` corrects the crystal error, `DVBS=1 ./tx.sh` selects DVB-S instead of DVB-S2. |
| `start1.sh` | Fixed example: 2403.75 MHz, 500 kBd, QPSK 3/5, port `/dev/ttyACM1`. |
| `test_333K.sh` | Test case for the symbol-rate problem below: 2370 MHz, 333 kBd, 8PSK 3/5. |
| `help.sh` | Prints `tx_dvbs.py --help`. |

| `sweep_test.py` | Frequency sweep: for each frequency it retunes the CYD spectrum viewer (`freq <MHz>`), starts `tx_dvbs.py` for a few seconds and evaluates the viewer's `[cf] ...` lines (median centre frequency, error in kHz, symbol rate). Example: `python3 sweep_test.py --viewer /dev/ttyUSB1 --tx-port /dev/ttyACM1 -f 2305 2403.75 2445`. Needs pyserial. **Transmits for real.** The default `--tx-dir` is my local path; change it with `--tx-dir`. |

Upstream `host/measure_spectra.py` is unchanged.

### Test setup

- **TX:** ESP32-C3 board with native USB Serial/JTAG, **TODO: board name/vendor**, on Linux, **TODO: distro**.
- **RX:** LongMynd with Minitiouner (**TODO: hardware version**) for decoding; for the frequency sweep a CYD spectrum viewer (3.3" ESP32-2432S028, see Related).
- **Frequency:** 2370 MHz and 2403.75 MHz, antenna: original antenna.
- **Licence:** operated by a licensed amateur (DG7NDV). Use a suitable output filter; DAC images are visible
  (see upstream spectra).

### Test scenario

1. Flash the firmware (upstream instructions) and start the transmitter: `./tx.sh 2403.75 500000 3/5`.
2. Set LongMynd to the same frequency, symbol rate, DVB-S2 and FEC.
3. Check for lock and a stable picture.
4. Repeat at lower symbol rates, e.g. `DVBS=1 PPM=28 ./tx.sh 2403.25 250000 1/2`.
5. Measure the carrier with `--cw` (e.g. with the CYD viewer) and correct the board's crystal error with `--ppm`.

### Results so far

Board: ESP32-C3 rev v0.4, 4 MB flash, 40 MHz crystal, firmware release v0.1.1 (built from `915e62d`).
Crystal error first estimated with the CYD viewer: about +36 ppm (about +85 kHz at 2370 MHz without correction).
Crystal error measured later with a GPS-referenced frequency counter (HP 5350, CW carrier at 2403.25 MHz): **+27 to +29 ppm**
(2403.31984 MHz read instead of 2403.249664 MHz without correction), drifting by about 1 ppm (2-3 kHz) while the board warms up.
The first estimate of +36 ppm came from the CYD viewer and was too high. The table below was recorded with `--ppm 36`, i.e. over-corrected
by roughly 7 ppm (about 17 kHz); `--ppm 28` is the better value. A retest with `--ppm 28` at 166 and 125 kBd gave the same result (see below).
Setup: 2403.25 MHz, `--ppm 36`, test pattern (`--test`), LongMynd/Minitiouner.

| Symbol rate | Mode / FEC | LongMynd |
|---|---|---|
| 500 kBd | DVB-S2 QPSK 3/4 | locks |
| 333 kBd | DVB-S2 QPSK 3/4 and 1/2 | signal visible, **no decode** |
| 333 kBd | **DVB-S 1/2** | locks |
| 250 kBd | DVB-S 1/2 | locks |
| 200 kBd | DVB-S 1/2 | locks |
| 166.7 kBd | DVB-S 1/2 | no lock (also with `--ppm 28`) |
| 125 kBd | DVB-S 1/2 | no lock (also with `--ppm 28`, `--ppm 28 --ifm 1`) |

So with DVB-S, FEC 1/2 and `--ppm 36` the limit on my board lies between 166 and 200 kBd.
Retest with the corrected `--ppm 28` (and `--ifm 1`, which moves the LO leakage out of the signal) changed nothing at 166 and 125 kBd: LongMynd shows only the level (about -50 dBm).
`--sps 32` at 125 kBd is rejected by the firmware (automatic SPS only).
Not yet tested: DVB-S without `--ppm` (is the correction needed for lock, or only DVB-S instead of DVB-S2?),
DVB-S2 at 250/200 kBd, and a round rate such as 180 kBd (166.7 kBd is rounded by the firmware and may not match the receiver setting exactly).

Possible causes for the DVB-S2 failure at low rates (not confirmed): uncalibrated I/Q (carrier leakage in the signal centre,
`cal.json` is zero), receiver acquisition at low symbol rates, different DAC loops. Upstream also reports lock problems at 66 kBd and below.

Practical notes:

- After an aborted run (second Ctrl+C during the FFmpeg shutdown) the board can stop radiating after a few seconds; unplugging and
  replugging the USB cable fixes it. Stop the transmitter with **one** Ctrl+C and wait for `TX END`.
- The CYD viewer resets when its serial port is opened and returns to 2406 MHz; send `freq <MHz>` only after about 12 s.
- Use `/dev/serial/by-id/usb-Espressif_...` instead of `/dev/ttyACM0`: the numbers change with the plug order.

### Related

- Original: https://github.com/SP8ESA/ESP32-DATV
- Receive-side spectrum viewer (my extended version): https://github.com/dg7ndv/ESP32-CYD-pocket-qo-100-spectrum-viewer
  (original by HB9IIU: https://github.com/HB9IIU/ESP32-CYD-pocket-qo-100-spectrum-viewer)
- **TODO:** video link.

---

## Deutsch

### Worum es geht

Dies ist ein Fork von [SP8ESA/ESP32-DATV](https://github.com/SP8ESA/ESP32-DATV), einem DVB-S/DVB-S2-Sender
auf Basis eines nackten ESP32-C3 (13-cm-Band, ohne externe HF-Hardware). Firmware und Host-Code stammen komplett
von SP8ESA. Dieser Fork ergänzt nur kleine Linux-Hilfsscripte und Notizen zu meinen Tests mit LongMynd / Minitiouner.

Die ursprüngliche Lizenz (PolyForm Noncommercial 1.0.0) und der Urheberhinweis (Copyright (c) 2026 SP8ESA)
bleiben unverändert. Nur nichtkommerzielle Nutzung.

### Änderungen gegenüber dem Original

Basis: Upstream-Commit `915e62d`. Firmware und Python-Quellen sind **nicht** verändert. Neu sind:

| Datei | Zweck |
|---|---|
| `tx.sh` | Startet `host/tx_dvbs.py --test` mit automatischer Portsuche (nur das Espressif-USB-JTAG-Gerät, also keine PlutoSDR/tinySA/CH340). Standard: 2403,75 MHz, 500 kBd, DVB-S2 QPSK, FEC 3/5, Service-Name `DG7NDV`. Aufruf: `./tx.sh [FREQ_MHZ] [BAUD] [FEC] [weitere Optionen]`. Mit `PORT=/dev/ttyACM1 ./tx.sh` wird ein Port vorgegeben, `PPM=28 ./tx.sh` korrigiert den Quarzfehler, `DVBS=1 ./tx.sh` wählt DVB-S statt DVB-S2. |
| `start1.sh` | Festes Beispiel: 2403,75 MHz, 500 kBd, QPSK 3/5, Port `/dev/ttyACM1`. |
| `test_333K.sh` | Testfall zum Symbolraten-Problem: 2370 MHz, 333 kBd, 8PSK 3/5. |
| `help.sh` | Zeigt `tx_dvbs.py --help`. |

| `sweep_test.py` | Frequenz-Durchlauf: stellt für jede Frequenz den CYD-Spektrum-Viewer um (`freq <MHz>`), startet `tx_dvbs.py` für einige Sekunden und wertet die `[cf] ...`-Zeilen des Viewers aus (Median der Mittenfrequenz, Fehler in kHz, Symbolrate). Beispiel: `python3 sweep_test.py --viewer /dev/ttyUSB1 --tx-port /dev/ttyACM1 -f 2305 2403.75 2445`. Braucht pyserial. **Sendet wirklich.** Der Standard für `--tx-dir` ist mein lokaler Pfad, mit `--tx-dir` änderbar. |

`host/measure_spectra.py` (Upstream) ist unverändert.

### Testaufbau

- **Sender:** ESP32-C3 mit nativem USB, **TODO: Boardname**, Linux **TODO: Distribution**.
- **Empfänger:** LongMynd mit Minitiouner (**TODO: Hardware-Version**) zum Decodieren; für den Frequenz-Durchlauf ein CYD-Spektrum-Viewer (3,3" ESP32-2432S028, siehe Verweise).
- **Frequenz:** 2370 MHz und 2403,75 MHz, Antenne: Originalantenne.
- **Lizenz:** Betrieb durch lizenzierten Funkamateur (DG7NDV). Ausgangsfilter verwenden, DAC-Spiegel sind sichtbar.

### Testablauf

1. Firmware flashen (Anleitung im Original), Sender starten: `./tx.sh 2403.75 500000 3/5`.
2. LongMynd auf gleiche Frequenz, Symbolrate, DVB-S2 und FEC stellen.
3. Lock und stabiles Bild prüfen.
4. Mit kleineren Symbolraten wiederholen, z. B. `DVBS=1 PPM=28 ./tx.sh 2403.25 250000 1/2`.
5. Träger mit `--cw` ausmessen (z. B. mit dem CYD-Viewer) und den Quarzfehler des Boards mit `--ppm` korrigieren.

### Bisherige Ergebnisse

Board: ESP32-C3 Rev. v0.4, 4 MB Flash, 40-MHz-Quarz, Firmware Release v0.1.1 (aus `915e62d`).
Quarzfehler zuerst mit dem CYD-Viewer geschätzt: etwa +36 ppm (ohne Korrektur etwa +85 kHz bei 2370 MHz).
Quarzfehler später mit GPS-referenziertem Frequenzzähler gemessen (HP 5350, CW-Träger auf 2403,25 MHz): **+27 bis +29 ppm**
(2403,31984 MHz statt 2403,249664 MHz ohne Korrektur), dabei Drift von etwa 1 ppm (2-3 kHz) während das Board warm wird.
Die erste Schätzung von +36 ppm stammte vom CYD-Viewer und war zu hoch. Die Tabelle unten wurde mit `--ppm 36` aufgenommen, also um etwa 7 ppm
(rund 17 kHz) überkorrigiert; `--ppm 28` ist der bessere Wert. Ein erneuter Test mit `--ppm 28` bei 166 und 125 kBd brachte dasselbe Ergebnis (siehe unten).
Aufbau: 2403,25 MHz, `--ppm 36`, Testbild (`--test`), LongMynd/Minitiouner.

| Symbolrate | Modus / FEC | LongMynd |
|---|---|---|
| 500 kBd | DVB-S2 QPSK 3/4 | Lock |
| 333 kBd | DVB-S2 QPSK 3/4 und 1/2 | Signal sichtbar, **kein Decode** |
| 333 kBd | **DVB-S 1/2** | Lock |
| 250 kBd | DVB-S 1/2 | Lock |
| 200 kBd | DVB-S 1/2 | Lock |
| 166,7 kBd | DVB-S 1/2 | kein Lock (auch mit `--ppm 28`) |
| 125 kBd | DVB-S 1/2 | kein Lock (auch mit `--ppm 28`, `--ppm 28 --ifm 1`) |

Mit DVB-S, FEC 1/2 und `--ppm 36` liegt die Grenze auf meinem Board also zwischen 166 und 200 kBd.
Ein erneuter Test mit korrektem `--ppm 28` (und `--ifm 1`, das den Trägerrest aus dem Signal schiebt) änderte bei 166 und 125 kBd nichts: LongMynd zeigt nur den Pegel (etwa -50 dBm).
`--sps 32` bei 125 kBd lehnt die Firmware ab (nur automatische SPS).
Noch nicht getestet: DVB-S ohne `--ppm` (ist die Korrektur für den Lock nötig, oder nur DVB-S statt DVB-S2?),
DVB-S2 bei 250/200 kBd und eine glatte Rate wie 180 kBd (166,7 kBd rundet die Firmware, der Empfänger passt evtl. nicht exakt).

Mögliche Ursachen für den DVB-S2-Ausfall bei kleinen Raten (nicht bestätigt): nicht kalibrierte I/Q-Werte (Trägerrest in der Mitte,
`cal.json` ist null), Einrasten des Empfängers bei kleinen Symbolraten, andere DAC-Schleifen. Das Original meldet ebenfalls Lock-Probleme ab 66 kBd abwärts.

Praktische Hinweise:

- Nach einem abgebrochenen Lauf (zweites Strg+C während des FFmpeg-Shutdowns) kann das Board nach wenigen Sekunden nicht mehr
  strahlen; USB-Kabel abziehen und wieder anstecken hilft. Den Sender mit **einem** Strg+C beenden und auf `TX END` warten.
- Der CYD-Viewer startet neu, wenn sein serieller Port geöffnet wird, und springt auf 2406 MHz zurück; `freq <MHz>` erst nach etwa 12 s senden.
- `/dev/serial/by-id/usb-Espressif_...` statt `/dev/ttyACM0` verwenden: die Nummern ändern sich mit der Steckreihenfolge.

### Verweise

- Original: https://github.com/SP8ESA/ESP32-DATV
- Empfangsseite, Spektrum-Anzeige (meine erweiterte Version): https://github.com/dg7ndv/ESP32-CYD-pocket-qo-100-spectrum-viewer
  (Original von HB9IIU: https://github.com/HB9IIU/ESP32-CYD-pocket-qo-100-spectrum-viewer)
- **TODO:** Link zum Video.

73 de DG7NDV
