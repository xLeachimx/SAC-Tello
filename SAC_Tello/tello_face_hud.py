# File: tello_face_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
# Notes:
#   Update 5 July 2024:
#       Changed to multi-threaded single process.
#   Update 8 July 2024:
#       Revert to multiprocessing due to lack of thread safe display option

from .tello_drone import TelloDrone
from .face_recognition import FaceRecognizer
from time import perf_counter, sleep
from pygame import display, draw, event, Rect, QUIT
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from threading import Thread
import multiprocessing as mp
from queue import Empty

def __convert_rect(rect: list[int]) -> Rect:
        """
        Converts the rectangle given by a FaceRecognizer object into a Pygame Rectangle.
        :param rect: A valid rectangle as given by a FaceRecognizer object.
        :return: Returns the equivalent Pygame rectangle.
        """
        return Rect(rect[0], rect[1], rect[3], rect[2])
def face_hud_render_loop(frame_q: mp.Queue, halt_q: mp.Queue, encoder: FaceRecognizer):
    # Setup Pygame
    screen = display.set_mode((960, 720))
    display.set_caption("Tello HUD")
    font = Font(get_default_font(), 16)
    # Setup video loop basics
    frame_timer = perf_counter()
    frame_delta = 1 / 30
    running = True
    drone_frame = None
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
                faces = encoder.detect_faces(drone_frame)
                for name, location in faces:
                    rect = __convert_rect(location)
                    draw.rect(screen, (0, 200, 0), rect, 5)
                    name_text = font.render(name, True, (0, 200, 0))
                    screen.blit(name_text, (rect.x, rect.y-name_text.get_height()-1))
            display.flip()
            for _ in event.get(QUIT):
                running = False
    display.quit()

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
        self.hud_proc: mp.Process | None = None
        self.frame_q: mp.Queue | None = None
        self.halt_q: mp.Queue | None = None
        self.hud_fps = 30

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
        self.hud_proc = mp.Process(target=face_hud_render_loop, args=(self.frame_q, self.halt_q, self.encoder),
                                   daemon=True)
        self.hud_thread.start()
    
    def stop(self) -> None:
        """
        Stops the HUD.
        :return: None
        """
        self.running = False
        self.hud_thread.join()
    
    def is_active(self) -> bool:
        """
        Checks if the HUD is currently active.
        :return: Returns true if the HUD is currently running.
        """
        return self.running
    
    def __hud_stream(self) -> None:
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
        while not self.frame_q.empty():
            self.frame_q.get()
        while not self.halt_q.empty():
            self.halt_q.get()
        self.frame_q.close()
        self.halt_q.close()
        if self.hud_proc.is_alive():
            self.hud_proc.kill()