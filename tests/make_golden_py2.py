# Python 2 only. Generates tests/fixtures/{lines.bin,golden.json} using the ORIGINAL
# Python 2 wxt520.py, so the Python 3 port can be checked against it.
#
#   python2 make_golden_py2.py <dir with original wxt520.py> <raw capture> <synthetic.txt> <outdir>
#
# synthetic.txt: message bodies without CRC, one per line; the CRC is appended here.
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
import wxt520  # the original Python 2 module

raw_path, synth_path, outdir = sys.argv[2], sys.argv[3], sys.argv[4]
lines = [l.strip() for l in open(raw_path, 'rb').read().split('\n') if l.strip()]
for body in open(synth_path).read().split('\n'):
    if body.strip():
        lines.append(body.strip() + wxt520.WXT520.crc16(body.strip()))

golden = []
for line in lines:
    if not wxt520.WXT520.check_crc(line + '\n'):
        golden.append(None)
        continue
    try:
        data = wxt520.WXT520.message_to_dict(line + '\n')
    except ValueError:
        golden.append('ValueError')
        continue
    if data is None:
        golden.append(None)
        continue
    data[data['Type']] = data.pop('Data')  # same transform as wxtserver.py
    golden.append(data)

with open(os.path.join(outdir, 'lines.bin'), 'wb') as f:
    f.write('\n'.join(lines) + '\n')
with open(os.path.join(outdir, 'golden.json'), 'w') as f:
    json.dump(golden, f, indent=1, sort_keys=True)
print('%d lines, %d payloads' % (len(lines), len([g for g in golden if isinstance(g, dict)])))
