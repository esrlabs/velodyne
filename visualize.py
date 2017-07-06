import sys
import math
import msgpack
import pyglet
from pyglet.gl import *
from pyglet.window import key
from ctypes import pointer, sizeof

INCREMENT = 5
PAN_INC = 0.2

if len(sys.argv) < 3:
  print('usage: python {} (msgpack|fixed) <in_file> [<start_point> [<end_point>]]'.format(sys.argv[0]))
  exit()

in_kind = sys.argv[1]
in_file = sys.argv[2]

start_point = 0
end_point = -1

if len(sys.argv) > 3:
  start_point = int(sys.argv[3])
  if len(sys.argv) > 4:
    end_point = int(sys.argv[4])

if not in_kind in ['msgpack', 'fixed']:
  print('input kind must be either "msgpack" or "fixed"')
  exit()


def read_sint32(data, idx):
  val = data[idx+0]*256*256*256 + data[idx+1]*256*256 + data[idx+2]*256 + data[idx+3] 
  return val-2**32 if val > 2**31-1 else val


def read_uint32(data, idx):
  return data[idx+0]*256*256*256 + data[idx+1]*256*256 + data[idx+2]*256 + data[idx+3] 


def read_binary_points(fn):
  points = []
  with open(fn, 'rb') as f:
    while True:
      p_data = f.read(13)
      if len(p_data) < 13:
        break
      if p_data[0:9] == b'\xff\xff\xff\xff\xff\xff\xff\xff\xff':
        ts = read_uint32(p_data, 9)
      else:
        x = read_sint32(p_data, 0)/1000
        y = read_sint32(p_data, 4)/1000
        z = read_sint32(p_data, 8)/1000
        points.append([x,y,z])
  return points


points = None

if in_kind == 'fixed':
  points = read_binary_points(in_file)

else:
  with open(in_file, 'rb') as f:
    points = msgpack.unpack(f)
    print(len(points))

print('points in file: '+str(len(points)))

points = points[start_point:end_point]
print('points to plot: '+str(len(points)))

vertices = (GLfloat*(3*len(points)))()
for i, p in enumerate(points):
  vertices[i*3:i*3+3] = p


def draw_axes():
   glBegin(GL_LINES)
   glColor3f(0.5, 0.5, 0.5)
   glVertex3f(0, 0, 0)
   glVertex3f(100, 0, 0)
   glVertex3f(0, 0, 0)
   glVertex3f(0, 100, 0)
   glVertex3f(0, 0, 0)
   glVertex3f(0, 0, 100)
   glEnd()


def draw_crosshair(factor=1.0):
   glScalef(factor, factor, factor)
   glBegin(GL_LINES)
   glColor3f(1.0, 0.0, 0.0)
   glVertex3f(-2, 0, 0)
   glVertex3f(-1, 0, 0)
   glVertex3f(2, 0, 0)
   glVertex3f(1, 0, 0)
   glVertex3f(0, -2, 0)
   glVertex3f(0, -1, 0)
   glVertex3f(0, 2, 0)
   glVertex3f(0, 1, 0)
   glVertex3f(0, 0, -2)
   glVertex3f(0, 0, -1)
   glVertex3f(0, 0, 2)
   glVertex3f(0, 0, 1)
   glEnd()


def draw_crosshair_at(x, y, z, size):
   glPushMatrix()
   glTranslatef(x, y, z)
   draw_crosshair(size)
   glPopMatrix()


vp = (GLint * 4)()
pmat = (GLdouble * 16)()
mvmat = (GLdouble * 16)()


def find_precise_coords(x, y, z, col):
   for dx in range(10):
     for dy in range(10):
       idx = dy*10+dx 
       if z[idx] < 1.0:
         return (x+dx, y+dy, z[idx])
   return None


def screen_to_3d(x, y):
   z = (GLfloat * 100)()

   glReadPixels(x-5, y-5, 10, 10, GL_DEPTH_COMPONENT, GL_FLOAT, z)

   col = (GLubyte * (3*100))()
   glReadPixels(x-5, y-5, 10, 10, GL_RGB, GL_UNSIGNED_BYTE, col)
   
   prec_coords = find_precise_coords(x-5, y-5, z, col)
   
   if prec_coords is None:
     return None

   px = (GLdouble)()
   py = (GLdouble)()
   pz = (GLdouble)()

   gluUnProject( *prec_coords, mvmat, pmat, vp, px, py, pz);

   return (px.value, py.value, pz.value)


class Window(pyglet.window.Window):

   xRotation = yRotation = 30  
   xTranslate = zTranslate = 0
   zoom = 1
   mouse_marker = last_mouse_marker = None

   def __init__(self, width, height, title=''):
       super(Window, self).__init__(width, height, title)
       glClearColor(0, 0, 0, 1)
       glEnable(GL_DEPTH_TEST)  

   def on_draw(self):
       self.clear()

       glPushMatrix()

       draw_crosshair()
       glRotatef(self.xRotation, 1, 0, 0)
       glRotatef(self.yRotation, 0, 1, 0)
       zoom = 20*self.zoom
       glScalef(zoom,zoom,zoom)
       glTranslatef(self.xTranslate, 0, self.zTranslate)
       draw_axes()

       glPushMatrix()
       glRotatef(-90, 1, 0, 0)

       glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
       glGetDoublev(GL_PROJECTION_MATRIX, pmat)
       glGetIntegerv(GL_VIEWPORT, vp)
 
       if self.mouse_marker is not None:
         draw_crosshair_at(*self.mouse_marker, 1/zoom)

       glEnableClientState(GL_VERTEX_ARRAY);
       glVertexPointer(3, GL_FLOAT, 0, pointer(vertices));

       glColor3f(1.0, 1.0, 1.0)
       glDrawArrays(GL_POINTS, 0, len(points));

       glDisableClientState(GL_VERTEX_ARRAY);

       glPopMatrix()
       glPopMatrix()


   def on_mouse_press(self, x, y, button, modifiers):
       self.mouse_marker = screen_to_3d(x, y)
       print(self.mouse_marker)
       if self.mouse_marker is not None and self.last_mouse_marker is not None:
         dx = self.mouse_marker[0] - self.last_mouse_marker[0]
         dy = self.mouse_marker[1] - self.last_mouse_marker[1]
         dz = self.mouse_marker[2] - self.last_mouse_marker[2]
         print('dist: '+str(math.sqrt(dx**2 + dy**2 + dz**2)))
       self.last_mouse_marker = self.mouse_marker


   def on_resize(self, width, height):
       glViewport(0, 0, width, height)

       # using Projection mode
       glMatrixMode(GL_PROJECTION)
       glLoadIdentity()

       aspectRatio = width / height
       gluPerspective(35, aspectRatio, 1, 1000)

       glMatrixMode(GL_MODELVIEW)
       glLoadIdentity()
       glTranslatef(0, 0, -400)


   def on_key_press(self, symbol, modifiers):
       if modifiers & key.MOD_SHIFT:
           if symbol == key.LEFT:
             self.xTranslate += math.cos(math.radians(self.yRotation))*PAN_INC
             self.zTranslate += math.sin(math.radians(self.yRotation))*PAN_INC
           if symbol == key.RIGHT:
             self.xTranslate -= math.cos(math.radians(self.yRotation))*PAN_INC
             self.zTranslate -= math.sin(math.radians(self.yRotation))*PAN_INC
           if symbol == key.UP:
             self.xTranslate += math.cos(math.radians(self.yRotation+90))*PAN_INC
             self.zTranslate += math.sin(math.radians(self.yRotation+90))*PAN_INC
           if symbol == key.DOWN:
             self.xTranslate -= math.cos(math.radians(self.yRotation+90))*PAN_INC
             self.zTranslate -= math.sin(math.radians(self.yRotation+90))*PAN_INC
       elif modifiers & key.MOD_CTRL:
           if symbol == key.DOWN:
             self.zoom -= 0.1
           if symbol == key.UP:
             self.zoom += 0.1
       else:
           if symbol == key.LEFT:
             self.yRotation -= INCREMENT
           if symbol == key.RIGHT:
             self.yRotation += INCREMENT
           if symbol == key.UP:
             self.xRotation -= INCREMENT
           if symbol == key.DOWN:
             self.xRotation += INCREMENT

            
if __name__ == '__main__':
   Window(1600, 900, 'Point Cloud Visualization')
   pyglet.app.run()

