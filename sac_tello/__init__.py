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
from math import log


if __name__ == '__main__':
    import pygame as pg
    from time import perf_counter
    from math import pow
    def vel_curve(t):
        return 100 * (log(t+1)/log(6))
    tello = TelloRC()
    tello.startup()
    pg.init()
    display = pg.display.set_mode(tello.get_res())
    running = True
    frame_delta = 1/25
    frame_start = perf_counter()
    key_holds = {'w':0, 's':0, 'd':0, 'a':0, 'q':0, 'e':0, 'up':0, 'down':0}
    while running:
        delta = (perf_counter() - frame_start)
        if delta >= frame_delta:
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
            key_state = pg.key.get_pressed()
            for key in key_holds:
                if key_state[pg.key.key_code(key)]:
                    key_holds[key] += delta
                else:
                    key_holds[key] = 0
                key_holds[key] = max(0, min(5, key_holds[key]))
            y = vel_curve(key_holds['w']) - vel_curve(key_holds['s'])
            x = vel_curve(key_holds['d']) - vel_curve(key_holds['a'])
            z = vel_curve(key_holds['up']) - vel_curve(key_holds['down'])
            rot = vel_curve(key_holds['e']) - vel_curve(key_holds['q'])
            tello.set_rc(x, y, z, rot)
            img = tello.get_frame()
            if img is not None:
                img = pg.image.frombuffer(img.tobytes(), img.shape[1::-1], "BGR")
                display.blit(img, (0, 0))
                pg.display.flip()
    tello.close()
    pg.quit()
