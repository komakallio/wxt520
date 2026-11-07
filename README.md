# wxt520
Python class for interfacing with Vaisala WXT520 over serial port.

Requires Python 3.5+ with `pyserial` and `requests` (Debian/Raspbian: `python3-serial`, `python3-requests`).

## Relay server

`wxtserver.py` reads the WXT520 in ASCII automatic mode and posts every message to the Komakallio weather API.

    python3 wxtserver.py --port /dev/ttyUSB1 --url http://localhost:9001/api/

It keeps running through serial errors (reopens the port with back-off), API errors (logs and continues) and unparseable lines (skips them).

## Tests

    python3 -m unittest discover -s tests -v

`tests/fixtures/lines.bin` holds raw lines captured from the Komakallio WXT520, plus synthetic rain and invalid-value lines. `tests/fixtures/golden.json` is what the original Python 2 code produced for the same lines (generated with `tests/make_golden_py2.py`), so the port is checked to post identical data.
