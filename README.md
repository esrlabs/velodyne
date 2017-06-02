# Velodyne Lidar Python Library

This code currently supports model HDL 64E S2 only.


# Prerequisites

Python, tested with Python 3.5

pip install dpkt
pip install json
pip install msgpack
pip install pyglet


# Calibration Data

The calibration data can either be read from the device (transmitted in-band with the 
measurement data) or from the XML file provided with the device.
Calibration data is stored in a JSON file for all further usage.

To read from the device use:

    python read_cal.py <.pcap file> <json file>

To read from XML do:

    python xml_to_cal.py <XML file> <json file>


# Measurement

`read_points.py` converts a pcap trace into a msgpack file holding the measurement points

    python read_points.py <.pcap file> <msgpack file> <calibration json file>

The message pack data is an array of 3-tupels (x,y,z).


# Visualization

`visualize.py` visualizes the message pack points file:

    python visualize.py msgpack <msgpack file> <start point index> <end point index>

You probably want to use the start and end point indices to narrow
down the number of plotted points to about one revolution of the lidar.
(at 600 rpm this is about 133300 points)

Use cursor keys to rotate the view, shift and cursor keys to pan, ctrl and up down to zoom
Click on a point to mark it and output it's 3d coordiantes.
Click on a second point to output the distance from the first point.


# License

The MIT License.
