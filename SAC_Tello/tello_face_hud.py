# File: tello_face_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
# Notes:
#   Update 5 July 2024:
#       Changed to multi-threaded single process.

from .tello_drone import TelloDrone
from .face_recognition import FaceRecognizer
from time import perf_counter
from pygame import display, draw, event, Rect, QUIT
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from threading import Thread


class TelloFaceHud:
    """
    Class for creating and displaying a HUD which overlays Tello Video footage with face recognition.
    """
    def __init__(self, drone: TelloDrone, faces: FaceRecognizer):
        """
        Constructor for the TelloFaceHud class. Does not automatically connect to Tello Drone or start display.
        :param drone: A valid TelloDrone object which has been started.
        :param faces: A valid FaceRecognizer object.
        """
        self.drone = drone
        self.encoder = faces
        self.running = False
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_thread.daemon = True
        
        #pg reqs
        self.font = Font(get_default_font(), 16)
    
    def activate_hud(self):
        """
        Starts the HUD.
        :return: None
        """
        if self.running:
            return
        self.running = True
        self.hud_thread.start()
    
    def deactivate_hud(self):
        """
        Stops the HUD.
        :return: None
        """
        if not self.running:
            if self.hud_thread.is_alive():
                self.hud_thread.join()
            return
        self.running = False
        self.hud_thread.join()
    
    def is_active(self):
        """
        Checks if the HUD is currently active.
        :return: Returns true if the HUD is currently running.
        """
        return self.running
    
    def __hud_stream(self):
        """
        Private method which runs in its own thread to display the HUD.
        :return: None
        """
        # Setup Pygame
        screen = display.set_mode((1280, 720))
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
    def __convert_rect(rect: list[int]) -> Rect:
        """
        Converts the rectangle given by a FaceRecognizer object into a Pygame Rectangle.
        :param rect: A valid rectangle as given by a FaceRecognizer object.
        :return: Returns the equivalent Pygame rectangle.
        """
        return Rect(rect[0], rect[1], rect[3], rect[2])
    