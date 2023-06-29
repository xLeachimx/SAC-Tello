# File: tello_face_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
# Notes:

from tello_drone import TelloDrone
from tello_rc import TelloRC
from face_encoder import FaceEncoder
from time import perf_counter, sleep
import pygame as pg
from threading import Thread


class TelloFaceHud:
    def __init__(self, drone: TelloDrone | TelloRC, faces: FaceEncoder):
        self.drone = drone
        self.encoder = faces
        self.running = False
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_thread.daemon = True
        
        #pg reqs
        self.font = pg.font.Font(pg.font.get_default_font(), 16)
    
    def activate_hud(self):
        if self.running:
            return
        self.running = True
        self.hud_thread.start()
    
    def deactivate_hud(self):
        if not self.running:
            if self.hud_thread.is_alive():
                self.hud_thread.join()
            return
        self.running = False
        self.hud_thread.join()
    
    def is_active(self):
        return self.running
    
    def __hud_stream(self):
        # Setup Pygame
        pg.display.init()
        screen = pg.display.set_mode((640, 480))
        pg.font.init()
        hud_font = pg.font.Font(pg.font.get_default_font(), 20)
        # Setup video loop basics
        frame_timer = perf_counter()
        frame_delta = 1 / 24
        while self.running:
            if (perf_counter() - frame_timer) > frame_delta:
                frame_timer = perf_counter()
                frame = self.drone.get_frame()
                if frame is not None:
                    frame = frame[0]
                    frame = pg.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "BGR")
                    screen.blit(frame, (0, 0))
                    # Detect Faces
                    faces = self.encoder.detect_faces(frame)
                    for name, location in faces:
                        rect = TelloFaceHud.__convert_rect(location)
                        pg.draw.rect(frame, (0, 200, 0), rect, 1)
                        name_text = self.font.render(name, True, (0, 200, 0))
                        frame.blit(name_text, (rect.x, rect.y-name_text.get_height()-1))
                pg.display.flip()
                for event in pg.event.get(pg.QUIT):
                    self.running = False
        pg.display.quit()
    
    @staticmethod
    def __convert_rect(rect):
        top_left = rect[3], rect[0]
        width_height = rect[1]-rect[2], rect[2]-rect[0]
        return pg.Rect(top_left, width_height)