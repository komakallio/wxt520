"""Tests for the WXT520 driver. Runs on Python 3.5+ with only the standard library + pyserial.

Fixtures (tests/fixtures/):
  lines.bin    raw lines captured from the Komakallio WXT520 (2026-11-07), plus synthetic
               rain and invalid-value lines whose CRCs were computed by the original
               Python 2 code
  golden.json  for each line, the payload the original Python 2 wxtserver would have
               posted (null = skipped, "ValueError" = original code raised)
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import wxt520  # noqa: E402
import wxtserver  # noqa: E402

FIXTURES = os.path.join(HERE, 'fixtures')


def load_lines():
    with open(os.path.join(FIXTURES, 'lines.bin'), 'rb') as f:
        return [l for l in f.read().split(b'\n') if l.strip()]


def load_golden():
    with open(os.path.join(FIXTURES, 'golden.json')) as f:
        return json.load(f)


def py3_payload(line):
    """What the new code posts for a line: same rules as the old server loop."""
    line = line + b'\n'
    if not wxt520.WXT520.check_crc(line):
        return None
    try:
        return wxtserver.to_payload(line)
    except ValueError:
        return 'ValueError'


class TestCrc(unittest.TestCase):
    def test_all_captured_lines_pass_crc(self):
        for line in load_lines():
            self.assertTrue(wxt520.WXT520.check_crc(line + b'\r\n'), line)

    def test_corrupted_line_fails_crc(self):
        line = load_lines()[0]
        broken = line.replace(b'=', b':', 1)
        self.assertFalse(wxt520.WXT520.check_crc(broken))

    def test_crc_accepts_str_and_bytes(self):
        self.assertEqual(wxt520.WXT520.crc16('0r2,Ta=5.4C'), wxt520.WXT520.crc16(b'0r2,Ta=5.4C'))
        self.assertIsInstance(wxt520.WXT520.crc16(b'x'), bytes)


class TestParsing(unittest.TestCase):
    def test_identical_to_python2_output(self):
        lines, golden = load_lines(), load_golden()
        self.assertEqual(len(lines), len(golden))
        for line, expected in zip(lines, golden):
            self.assertEqual(py3_payload(line), expected, line)

    def test_ptu_values(self):
        line = next(l for l in load_lines() if l.startswith(b'0r2'))
        payload = py3_payload(line)
        self.assertEqual(payload['Type'], 'PTU')
        self.assertEqual(payload['PTU']['Temperature']['Ambient'][1], 'C')
        self.assertEqual(payload['PTU']['Pressure'][1], 'hPa')
        self.assertEqual(payload['PTU']['Humidity'][1], '%')

    def test_every_message_type_covered(self):
        types = {p['Type'] for p in load_golden() if isinstance(p, dict)}
        self.assertEqual(types, {'Wind', 'PTU', 'Rain', 'Status'})

    def test_unknown_message_type_is_skipped(self):
        msg = b'0r9,Xx=1.0M'
        line = msg + wxt520.WXT520.crc16(msg) + b'\r\n'
        self.assertIsNone(wxtserver.to_payload(line))


if __name__ == '__main__':
    unittest.main()
