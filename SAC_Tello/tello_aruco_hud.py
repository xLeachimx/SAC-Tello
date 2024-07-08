# File: tello_aruco_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2024
# License: GNU GPLv3
# Created On: 05 Jul 2024
# Purpose:
# Notes:

from .tello_drone import TelloDrone
from .aruco_detector import ArucoDetector
from time import perf_counter
from pygame import display, draw, event, Rect, QUIT
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from threading import Thread


class TelloArucoHud:
    """
    Class for creating and displaying a HUD which overlays Tello Video footage with aruco marker detection.
    """
    def __init__(self, drone: TelloDrone, detector: ArucoDetector):
        """
        Constructor for the TelloArucoHud class. Does not automatically connect to Tello Drone or start display.
        :param drone: A valid TelloDrone object which has been started.
        :param detector: A valid ArucoDetector object.
        """
        self.drone = drone
        self.detector = detector
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
                    markers = self.detector.detect_markers(drone_frame)
                    for num, location, dist in markers:
                        rect = TelloArucoHud.__convert_rect(location)
                        draw.rect(screen, (0, 200, 0), rect, 5)
                        id_text = self.font.render(str(num) + "@" + str(round(dist)) + "cm", True, (0, 200, 0))
                        screen.blit(id_text, (rect.x, rect.y-id_text.get_height()-1))
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