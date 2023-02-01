# File: __init__.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Purpose:
# Notes:


from tello_drone import TelloDrone
from face_recognizer import FaceRecognizer
from rc_tello import TelloRC


if __name__ == '__main__':
  import pygame as pg
  from time import perf_counter
  tello = TelloRC()
  tello.startup()
  pg.init()
  display = pg.display.set_mode(tello.get_res())
  running = True
  frame_delta = 1/25
  frame_start = perf_counter()
  while running:
    if (perf_counter() - frame_start) >= frame_delta:
      frame_start = perf_counter()
      for event in pg.event.get():
        if event.type == pg.QUIT:
          running = False
        elif event.type == pg.KEYDOWN:
          if event.key == pg.K_t:
            tello.takeoff()
          elif event.key == pg.K_l:
            tello.land()
          elif event.key == pg.K_BACKSPACE:
            tello.rc = [0, 0, 0, 0]
          elif event.key == pg.K_q:
            tello.rc[3] = 100
          elif event.key == pg.K_e:
            tello.rc[3] = -100
      img = tello.get_frame()
      if img is not None:
        img = pg.image.frombuffer(img.tobytes(), img.shape[1::-1], "BGR")
        display.blit(img, (0, 0))
        pg.display.flip()
  tello.close()
  pg.quit()
