# File: tello_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A simple hud program that can be run on a separate thread.
# Notes:

from tello_drone import TelloDrone
from time import perf_counter
import pygame as pg


def hud_stream(drone: TelloDrone):
    # Setup Pygame
    pg.display.init()
    screen = pg.display.set_mode((640, 480))
    pg.font.init()
    hud_font = pg.font.Font(pg.font.get_default_font(), 20)
    # Setup video loop basics
    running = True
    frame_timer = perf_counter()
    frame_delta = 1/30
    while running:
        if (perf_counter() - frame_timer) > frame_delta:
            frame_timer = perf_counter()
            frame = drone.get_frame()
            if frame is not None:
                frame = frame[0]
                frame = pg.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "BGR")
                screen.blit(frame, (0, 0))
            state = drone.get_state()
            if state is not None:
                state = state[0]
                bat_text = hud_font.render(f"Battery: {state['bat']:4}", True, (0, 200, 0), (0, 0, 0))
                screen.blit(bat_text, (0, 0))
                height_text = hud_font.render(f"Height: {state['tof']:4}", True, (0, 200, 0), (0, 0, 0))
                screen.blit(height_text, (0, bat_text.get_height()))
            pg.display.flip()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
    pg.display.quit()