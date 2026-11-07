"""Relay Vaisala WXT520 messages from a serial port to the Komakallio weather API.

Python 3 (3.5+). Keeps running through serial and HTTP errors.
"""
import argparse
import json
import logging
import time

import requests
import serial

import wxt520


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/ttyUSB1',
                        help='serial device of the WXT520 (default: %(default)s)')
    parser.add_argument('--address', default='0',
                        help='WXT520 device address (default: %(default)s)')
    parser.add_argument('--url', default='http://localhost:9001/api/',
                        help='weather API endpoint (default: %(default)s)')
    parser.add_argument('--http-timeout', type=float, default=5.0)
    return parser.parse_args()


def to_payload(line):
    """Convert one raw WXT520 line to the JSON payload posted to the API, or None."""
    data = wxt520.WXT520.message_to_dict(line)
    if data is None:
        return None
    data[data['Type']] = data.pop('Data')
    return data


def open_wxt(port, address):
    delay = 1
    while True:
        try:
            return wxt520.WXT520(port, address=address, timeout=10)
        except (serial.SerialException, ValueError, OSError) as e:
            logging.warning('Cannot open WXT520 on %s: %s; retrying in %d s', port, e, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)


def post(url, payload, timeout):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code != 200:
            logging.error('API returned %d: %s', r.status_code, r.text[:200])
    except requests.RequestException as e:
        logging.error('Posting to %s failed: %s', url, e)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    wxt = open_wxt(args.port, args.address)
    logging.info('WXT520 open on %s', args.port)
    while True:
        try:
            line = wxt.readline()
        except (serial.SerialException, OSError) as e:
            logging.error('Serial error: %s; reopening', e)
            try:
                wxt.ser.close()
            except Exception:
                pass
            wxt = open_wxt(args.port, args.address)
            continue
        if not line:
            continue
        try:
            payload = to_payload(line)
        except (ValueError, KeyError, UnicodeDecodeError) as e:
            logging.warning('Skipping unparseable line %r: %s', line, e)
            continue
        if payload is None:
            continue
        logging.info(json.dumps(payload, sort_keys=True))
        post(args.url, payload, args.http_timeout)


if __name__ == '__main__':
    main()
