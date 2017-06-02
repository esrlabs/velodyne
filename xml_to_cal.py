import sys
import json
import xml.etree.ElementTree as ET


if len(sys.argv) < 3:
  print('usage: python {} <xml_file> <out_file>'.format(sys.argv[0]))
  exit()

in_file = sys.argv[1]
out_file = sys.argv[2]

print('reading calibration from '+in_file)
tree = ET.parse(in_file)
root = tree.getroot()

def get_val(e, tag_name):
  return e.find(tag_name).text

val = []

for i in range(64):
  val.append({})

for i, d in enumerate(root.find('DB').find('points_').findall('item')):
  px = d.find('px')
  id_ = get_val(px, 'id_')
  assert(int(id_) == i)
  val[i]['rotational_correction'] = float(get_val(px, 'rotCorrection_'))
  val[i]['vertical_correction'] = float(get_val(px, 'vertCorrection_'))
  val[i]['distance_far_correction'] = float(get_val(px, 'distCorrection_'))
  val[i]['distance_correction_x'] = float(get_val(px, 'distCorrectionX_'))
  val[i]['distance_correction_y'] = float(get_val(px, 'distCorrectionY_'))
  val[i]['vertical_offset_correction'] = float(get_val(px, 'vertOffsetCorrection_'))
  val[i]['horizontal_offset_correction'] = float(get_val(px, 'horizOffsetCorrection_'))
  val[i]['focal_distance'] = float(get_val(px, 'focalDistance_'))
  val[i]['focal_slope'] = float(get_val(px, 'focalSlope_'))


for i, d in enumerate(root.find('DB').find('minIntensity_').findall('item')):
  val[i]['min_intensity'] = d.text


for i, d in enumerate(root.find('DB').find('maxIntensity_').findall('item')):
  val[i]['max_intensity'] = d.text


print('writing calibration to '+out_file)
with open(out_file, 'w') as f:
  json.dump(val, f, sort_keys=True, indent=4)
