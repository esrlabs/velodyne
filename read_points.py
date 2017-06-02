import msgpack
import sys
import dpkt
import json
import time
from velodyne import StatusState, process_frame, calc_coords


if len(sys.argv) < 4:
  print('usage: python {} <pcap_file> <out_file> <cal_file>'.format(sys.argv[0]))
  exit()

in_file = sys.argv[1]
out_file = sys.argv[2]
cal_file = sys.argv[3]

points = []
status = StatusState()

print('using calibration file '+cal_file)
with open(cal_file, 'r') as f:
  calibration_vals = json.load(f)


def firing_data_callback(laser_idx, rot_pos, dist, intensity):
  vals = calibration_vals[laser_idx]
  coords = calc_coords(dist, rot_pos, vals)
  if coords != (0, 0, 0):
    points.append(coords)


print('reading packets from '+in_file)
with open(in_file, 'rb') as f:
  reader = dpkt.pcap.Reader(f)

  frame_index = 0
  last_t = time.time() 

  for ts, buf in reader:
    eth = dpkt.ethernet.Ethernet(buf)
    data = eth.data.data.data
    process_frame(data, 0, status, firing_data_callback)

    frame_index += 1
    if frame_index % 1000 == 0:
      t = time.time()
      print('processing frames: ' + str(frame_index) + ' fps: '+str(int(1000/(t - last_t))))
      last_t = t


print('writing data to '+out_file)

with open(out_file, 'wb') as f:
  msgpack.pack(points, f)

print('done')
