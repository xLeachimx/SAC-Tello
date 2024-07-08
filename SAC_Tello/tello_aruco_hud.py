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
import pygame as pg
from pygame import display, draw, event, Rect, QUIT
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from threading import Thread
from queue import Empty
import multiprocessing as mp

def __convert_rect(rect: list[int]) -> Rect:
        """
        Converts the rectangle given by a ArucoDetector object into a Pygame Rectangle.
        :param rect: A valid rectangle as given by a ArucoDectector object.
        :return: Returns the equivalent Pygame rectangle.
        """
        return Rect(rect[1], rect[0], rect[3], rect[2])
def aruco_hud_render_loop(frame_q: mp.Queue, halt_q: mp.Queue):
    # Setup Pygame
    screen = display.set_mode((960, 720))
    display.set_caption("Tello HUD")
    font = Font(get_default_font(), 16)
    # Setup video loop basics
    frame_timer = perf_counter()
    frame_delta = 1 / 30
    running = True
    drone_frame = None
    detector = ArucoDetector()
    while running and halt_q.empty():
        if (perf_counter() - frame_timer) > frame_delta:
            frame_timer = perf_counter()
            try:
                drone_frame = frame_q.get_nowait()
            except Empty:
                pass
            if drone_frame is not None:
                frame = frombuffer(drone_frame.tobytes(), drone_frame.shape[1::-1], "BGR")
                screen.blit(frame, (0, 0))
                # Detect Faces
                markers = detector.detect_markers(drone_frame)
                for num, location, dist in markers:
                    rect = __convert_rect(location)
                    draw.rect(screen, (0, 200, 0), rect, 5)
                    id_text = font.render(str(num) + "@" + str(round(dist)) + "cm", True, (0, 200, 0))
                    screen.blit(id_text, (rect.x, rect.y-id_text.get_height()-1))
            display.flip()
            for _ in event.get(QUIT):
                running = False
    display.quit()


class TelloArucoHud:
    """
    Class for creating and displaying a HUD which overlays Tello Video footage with aruco marker detection.
    """
    def __init__(self, drone: TelloDrone):
        """
        Constructor for the TelloArucoHud class. Does not automatically connect to Tello Drone or start display.
        :param drone: A valid TelloDrone object which has been started.
        """
        self.drone = drone
        self.running = False
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_thread.daemon = True
        self.hud_thread.daemon = True
        self.hud_proc: mp.Process | None = None
        self.frame_q: mp.Queue | None = None
        self.halt_q: mp.Queue | None = None
        self.hud_fps = 30
        
        #pg reqs
        self.font = Font(get_default_font(), 16)
    
    def start(self) -> None:
        """
        Starts the HUD.
        :return: None
        """
        if self.running:
            return
        self.running = True
        self.frame_q = mp.Queue()
        self.halt_q = mp.Queue()
        self.hud_proc = mp.Process(target=aruco_hud_render_loop, args=(self.frame_q, self.halt_q),
                                   daemon=True)
        self.hud_thread.start()
    
    def stop(self) -> None:
        """
        Stops the HUD.
        :return: None
        """
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
        # Empty the queues and flush the system
        while not self.frame_q.empty():
            self.frame_q.get()
        while not self.halt_q.empty():
            self.halt_q.get()
        timer = perf_counter()
        if self.hud_proc is not None:
            self.hud_proc.start()
        while self.running:
            delta = perf_counter() - timer
            if delta > 1/self.hud_fps:
                timer = perf_counter()
                if self.frame_q.empty():
                    self.frame_q.put(self.drone.get_frame())
        self.halt_q.put("HALT")
        self.hud_proc.join(3)
        if self.hud_proc.is_alive():
            self.hud_proc.kill()