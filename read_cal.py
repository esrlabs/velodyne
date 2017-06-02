import json
import pprint
import sys
import dpkt
from velodyne import StatusState, process_frame, calc_coords


if len(sys.argv) < 3:
  print('usage: python {} <pcap_file> <out_file>'.format(sys.argv[0]))
  exit()

in_file = sys.argv[1]
out_file = sys.argv[2]


def firing_data_callback(laser_idx, rot_pos, dist, intensity):
  pass

status = StatusState()

print('reading calibration from '+in_file)
with open(in_file, 'rb') as f:
  reader = dpkt.pcap.Reader(f)

  for ts, buf in reader:
    eth = dpkt.ethernet.Ethernet(buf)
    data = eth.data.data.data
    process_frame(data, 0, status, firing_data_callback)
    if len(status.lasers[63].values) > 0:
      break

lasers_cal = [status.lasers[l].values for l in range(64)]

#pprint.PrettyPrinter().pprint(lasers_cal)

print('writing calibration to '+out_file)
with open(out_file, 'w') as f:
  json.dump(lasers_cal, f, sort_keys=True, indent=4)

