# File: tello_face_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
# Notes:

from .tello_drone import TelloDrone
from .tello_rc import TelloRC
from .face_encoder import FaceEncoder
from time import perf_counter
from pygame import display, draw, event, Rect, DOUBLEBUF, OPENGLBLIT, QUIT
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from threading import Thread


class TelloFaceHud:
    def __init__(self, drone: TelloDrone | TelloRC, faces: FaceEncoder):
        self.drone = drone
        self.encoder = faces
        self.running = False
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_thread.daemon = True
        
        #pg reqs
        self.font = Font(get_default_font(), 16)
    
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
        screen = display.set_mode((960, 720))
        display.set_caption("Tello HUD")
        # Setup video loop basics
        frame_timer = perf_counter()
        frame_delta = 1 / 30
        while self.running:
            if (perf_counter() - frame_timer) > frame_delta:
                frame_timer = perf_counter()
                drone_frame = self.drone.get_frame()
                if drone_frame is not None:
                    frame = frombuffer(drone_frame.tobytes(), drone_frame.shape[1::-1], "BGR")
                    screen.blit(frame, (0, 0))
                    # Detect Faces
                    faces = self.encoder.detect_faces(drone_frame)
                    for name, location in faces:
                        rect = TelloFaceHud.__convert_rect(location)
                        draw.rect(screen, (0, 200, 0), rect, 5)
                        name_text = self.font.render(name, True, (0, 200, 0))
                        screen.blit(name_text, (rect.x, rect.y-name_text.get_height()-1))
                display.flip()
                for _ in event.get(QUIT):
                    self.running = False
        display.quit()
    
    @staticmethod
    def __convert_rect(rect):
        left = rect[3]
        top = rect[0]
        width = rect[1]-rect[3]
        height = rect[2]-rect[0]
        return Rect(left, top, width, height)
    