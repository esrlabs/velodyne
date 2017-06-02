import math

def read_uint8(data, idx):
  return data[idx]


def read_sint8(data, idx):
  val = read_uint8(data, idx)
  return val-256 if val > 127 else val


def read_uint16(data, idx):
  return data[idx] + data[idx+1]*256


def read_sint16(data, idx):
  val = read_uint16(data, idx)
  return val-2**16 if val > 2**15-1 else val


def read_uint32(data, idx):
  return data[idx] + data[idx+1]*256 + data[idx+2]*256*256 + data[idx+3]*256*256*256


_RotSinTab = {}
_RotCosTab = {}

for i in range(360*100):
  _RotSinTab[i/100] = math.sin(math.radians(i/100))
  _RotCosTab[i/100] = math.cos(math.radians(i/100))


class LaserState:

  def __init__(self):
    self.raw_bytes = [None]*4*7
    self.values = {}

  def convert(self):
    self.values['vertical_correction'] = read_sint16(self.raw_bytes, 1)/100
    self.values['rotational_correction'] = read_sint16(self.raw_bytes, 3)/100
    self.values['distance_far_correction'] = read_sint16(self.raw_bytes, 5)/10
    self.values['distance_correction_x'] = read_sint16(self.raw_bytes, 7)/10
    self.values['distance_correction_y'] = read_sint16(self.raw_bytes, 9)/10
    self.values['vertical_offset_correction'] = read_sint16(self.raw_bytes, 11)/10
    self.values['horizontal_offset_correction'] = read_sint16(self.raw_bytes, 13)/10
    self.values['focal_distance'] = read_sint16(self.raw_bytes, 15)/10
    self.values['focal_slope'] = read_sint16(self.raw_bytes, 17)/10
    self.values['min_intensity'] = read_uint8(self.raw_bytes, 19)
    self.values['max_intensity'] = read_uint8(self.raw_bytes, 20)


class StatusState:

  def __init__(self):
    self.frame_idx = None
    self.block_idx = None
    self.laser_idx = None
    self.block_bytes = [None]*7
    # 65 bytes, index starting at 1
    self.raw_bytes = [None]*66
    self.values = {}
    self.lasers = [LaserState() for i in range(64)]

  def convert(self):
    for l in self.lasers:
      l.convert()
    self.values['checksum'] = read_uint16(self.raw_bytes, 64)


def read_firing_data(data, idx, fd_callback):
  block_id = read_uint16(data, idx)
  # 0xeeff is upper block, 0xddff is lower block
  assert block_id == 0xeeff or block_id == 0xddff
  idx += 2
  rot_pos = read_uint16(data, idx)/100
  idx += 2

  for l in range(32):
    dist = read_uint16(data, idx)
    idx += 2
    inten = read_uint8(data, idx)
    idx += 1
    # upper laser block ids range from 0 to 31, lower from 32 to 63
    laser_idx = l + (32 if block_id == 0xddff else 0)
    fd_callback(laser_idx, rot_pos, dist, inten)


def process_block(state):

  if state.block_bytes[0:5] == [ord('U'), ord('N'), ord('I'), ord('T'), ord('#')]:
    state.block_idx = 0
    state.raw_bytes[15] = state.block_bytes[5]
    state.raw_bytes[16] = state.block_bytes[6]

  elif state.block_idx is not None:
    state.block_idx += 1

    if state.block_idx < 64*4+1:
      if (state.block_idx-1)%4 == 0:
        state.laser_idx = state.block_bytes[0]
        #print('Laser:' + str(state.laser_idx))
      idx = ((state.block_idx-1)%4)*7
      state.lasers[state.laser_idx].raw_bytes[idx:idx+7] = state.block_bytes

    else:
      idx = 45 + (state.block_idx-(64*4+1))*7
      state.raw_bytes[idx:idx+7] = state.block_bytes

      # on last block
      if state.block_idx == (1+64*4+3)-1:
        state.convert()


def process_status_byte(type, value, state):

  if type == ord('H'):
    state.frame_idx = 1

  if state.frame_idx is not None:

    if state.frame_idx <= 9:
      state.raw_bytes[state.frame_idx] = value

    else:
      state.block_bytes[state.frame_idx-10] = value

      if state.frame_idx == 16:
        #print(state.block_idx)
        process_block(state)

    state.frame_idx += 1


def process_frame(data, idx, status, fd_callback):

  for b in range(12):
    read_firing_data(data, idx, fd_callback)
    idx += 100

  gps_timestamp = read_uint32(data, idx)
  idx += 4
  status_type = read_uint8(data, idx)
  idx += 1
  status_value = read_uint8(data, idx)
  process_status_byte(status_type, status_value, status)


def calc_coords(dist, rot, cal):
  # factor cm to m
  VLS_DIM_SCALE = 100
  # factor distance value to cm
  DistLSB = 0.2

  if dist == 0:
    return (0, 0, 0)

  if not '_cos_vert_corr' in cal:
    cal['_cos_vert_corr'] = math.cos(math.radians(cal['vertical_correction']))
    cal['_sin_vert_corr'] = math.sin(math.radians(cal['vertical_correction']))
    cal['_cos_rot_corr'] = math.cos(math.radians(cal['rotational_correction']))
    cal['_sin_rot_corr'] = math.sin(math.radians(cal['rotational_correction']))
    cal['_hor_off_corr'] = cal['horizontal_offset_correction']/VLS_DIM_SCALE
    cal['_vert_off_corr'] = cal['vertical_offset_correction']/VLS_DIM_SCALE
    cal['_dist_corr_x_fact'] = (cal['distance_far_correction']-cal['distance_correction_x'])/(2504-240)
    cal['_dist_corr_y_fact'] = (cal['distance_far_correction']-cal['distance_correction_y'])/(2504-193)

  distancel = DistLSB * dist
  distance = distancel+ cal['distance_far_correction']

  cosRotAngle = _RotCosTab[rot]*cal['_cos_rot_corr'] + _RotSinTab[rot]*cal['_sin_rot_corr']
  sinRotAngle = _RotSinTab[rot]*cal['_cos_rot_corr'] - _RotCosTab[rot]*cal['_sin_rot_corr']

  hOffsetCorr = cal['_hor_off_corr']
  vOffsetCorr = cal['_vert_off_corr']


  xyDistance = distance * cal['_cos_vert_corr']
  xx = xyDistance * sinRotAngle
  yy = xyDistance * cosRotAngle

  if xx<0: xx = -xx
  if yy<0: yy = -yy

  distanceCorrX = cal['_dist_corr_x_fact']*(xx-240)+cal['distance_correction_x']
  distanceCorrY = cal['_dist_corr_y_fact']*(yy-193)+cal['distance_correction_y']


  if distancel > 2500:
    distanceCorrX = cal['distance_far_correction']
    distanceCorrY = distanceCorrX

  distancel /= VLS_DIM_SCALE
  distanceCorrX /= VLS_DIM_SCALE
  distanceCorrY /= VLS_DIM_SCALE

  distance = distancel+distanceCorrX
  xyDistance = distance * cal['_cos_vert_corr']

  x = xyDistance * sinRotAngle - hOffsetCorr * cosRotAngle

  distance = distancel+distanceCorrY
  xyDistance = distance * cal['_cos_vert_corr']

  y = xyDistance * cosRotAngle + hOffsetCorr * sinRotAngle
  z = distance * cal['_sin_vert_corr'] + vOffsetCorr

  return (x, y, z)

