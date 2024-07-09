# File: tello_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A simple hud program that can be run on a separate thread.
# Notes:
#   Update 4 July 2024:
#       Changed to multi-threaded single process.
#   Update 8 July 2024:
#       Revert to multiprocessing due to lack of thread safe display option

from .tello_drone import TelloDrone
from time import perf_counter, sleep
from pygame import display, draw, event, Surface, Vector2, QUIT, SRCALPHA, KEYDOWN, K_p
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from math import sin, cos, radians
from threading import Thread
import uuid
from cv2 import imwrite
import multiprocessing as mp
from queue import Empty

def __artificial_horizon(rad: int, pitch: int, roll: int, hud_base: Surface) -> Surface:
        """
        Renders an artificial horizon for the HUD.
        :param rad: HUD radius.
        :param pitch: Pitch of the Tello Drone in degrees.
        :param roll: Roll of the Tello Drone in degrees.
        :return: A surface containing the artificial horizon.
        """
        result = Surface((4 * rad, 4 * rad), SRCALPHA, 32)
        result.blit(hud_base, (0, 0))
        center = Vector2(result.get_width() // 2, result.get_height() // 2)
        # Draw roll lines
        left_ang = radians(180 + roll)
        left_vec = Vector2(cos(left_ang), sin(left_ang))
        left_start = left_vec * rad
        left_end = left_vec * (rad * 2)
        left_start = left_start + center
        left_end = left_end + center
        draw.line(result, (0, 200, 0), left_start, left_end, 3)
        right_ang = radians(roll)
        right_vec = Vector2(cos(right_ang), sin(right_ang))
        right_start = right_vec * rad
        right_end = right_vec * rad * 2
        right_start = right_start + center
        right_end = right_end + center
        draw.line(result, (0, 200, 0), right_start, right_end, 3)
        # Draw Pitch lines
        pitch = -pitch  # Line direction adjustment
        pitch_line_deg = 10
        pitch_lines = Surface((rad, rad), SRCALPHA)
        pixels_per_ang = 2
        start_angle = pitch - ((pitch_lines.get_height() // 2) // pixels_per_ang)
        pixel_start = pitch_line_deg - (start_angle % pitch_line_deg)
        pixel_start = pixel_start * pixels_per_ang
        angles = []
        for i in range(pixel_start, pitch_lines.get_height(), pitch_line_deg * pixels_per_ang):
            ang = start_angle + (i // pixels_per_ang)
            angles.append(ang)
            if ang % pitch_line_deg == 0:
                if ang != 0:
                    draw.line(pitch_lines, (0, 200, 0), (0, i), (pitch_lines.get_width(), i), 3)
                else:
                    draw.line(pitch_lines, (200, 0, 0), (0, i), (pitch_lines.get_width(), i), 3)
        line_adj = Vector2(-(pitch_lines.get_width() // 2), -(pitch_lines.get_height() // 2))
        center_pitch = center + line_adj
        # Current Pitch indicator
        indicator_height = pitch_lines.get_height() // 2
        draw.line(pitch_lines, (0, 0, 200), (0, indicator_height), (pitch_lines.get_width(), indicator_height), 3)
        result.blit(pitch_lines, center_pitch)
        return result

def hud_render_loop(state_q: mp.Queue, frame_q: mp.Queue, halt_q: mp.Queue):
    # Setup Pygame
    screen = display.set_mode((960, 720))
    display.set_caption("Tello HUD")
    # Setup
    hud_rad = 50
    hud_base = Surface((4 * hud_rad, 4 * hud_rad), SRCALPHA, 32)
    hud_center = Vector2(hud_base.get_width() // 2, hud_base.get_height() // 2)
    draw.circle(hud_base, (0, 0, 0, 100), hud_center, 2 * hud_rad)
    # Draw baselines
    draw.circle(hud_base, (0, 200, 0), hud_center, hud_rad, hud_rad // 10)
    # Roll baseline
    roll_baseline = Vector2(cos(0), sin(0))
    roll_start = (roll_baseline * hud_rad) + hud_center
    roll_end = (roll_baseline * (2 * hud_rad)) + hud_center
    draw.line(hud_base, (0, 200, 0), roll_start, roll_end, 6)
    roll_baseline - -roll_baseline
    roll_start = (roll_baseline * hud_rad) + hud_center
    roll_end = (roll_baseline * (2 * hud_rad)) + hud_center
    draw.line(hud_base, (0, 200, 0), roll_start, roll_end, 6)
    # Pitch indicator
    draw.line(hud_base, (0, 0, 220),
              (hud_center.x - hud_rad + (hud_rad // 10), hud_center.y),
              (hud_center.x - (hud_rad // 2), hud_center.y), 6)
    draw.line(hud_base, (0, 0, 220),
              (hud_center.x + (hud_rad // 2), hud_center.y),
              (hud_center.x + hud_rad - (hud_rad // 10), hud_center.y), 6)
    # Setup video loop basics
    frame_timer = perf_counter()
    frame_delta = 1 / 30
    event.set_allowed([QUIT, KEYDOWN])
    horizon_rad = 50
    horizon_size = 4 * horizon_rad
    horizon_placement = ((screen.get_width() - horizon_size) // 2, (screen.get_height() - horizon_size) // 2)
    hud_font = Font(get_default_font(), 20)
    running = True
    frame = None
    state = None
    while running and halt_q.empty():
        delta = perf_counter() - frame_timer
        if delta >= frame_delta:
            frame_timer = perf_counter()
            screen.fill((0, 0, 0, 255))
            try:
                frame = frame_q.get_nowait()
            except Empty:
                pass
            if frame is not None:
                screen.blit(frombuffer(frame.tobytes(), frame.shape[1::-1], "BGR"), (0, 0))
                try:
                    state = state_q.get_nowait()
                except Empty:
                    pass
                if state is not None:
                    fps_text = hud_font.render(f"FPS: {int(1 / delta):4}", True, (0, 200, 0), (0, 0, 0))
                    bat_text = hud_font.render(f"Battery: {state['bat']:4}", True, (0, 200, 0), (0, 0, 0))
                    height_text = hud_font.render(f"ToF: {state['tof']:4}", True, (0, 200, 0), (0, 0, 0))
                    horizon = __artificial_horizon(horizon_rad, int(state['pitch']), int(state['roll']), hud_base)
                    screen.blits([
                        (fps_text, (0, 0)),
                        (bat_text, (0, fps_text.get_height())),
                        (height_text, (bat_text.get_width(), fps_text.get_height())),
                        (horizon, horizon_placement)
                    ])
            else:
                init_text = hud_font.render("Initializing...", True, (0, 200, 0), (9, 0, 0))
                x = (screen.get_width() - init_text.get_width()) // 2
                y = (screen.get_height() - init_text.get_height()) // 2
                screen.blit(init_text, (x, y))
            display.flip()
            for _ in event.get(QUIT):
                running = False
            for evt in event.get(KEYDOWN):
                if evt.key == K_p:
                    filename = str(uuid.uuid4()) + '.jpg'
                    imwrite(filename, frame)
    display.quit()
    print("Done!")

class TelloHud:
    """
    A class for creating a HUD for the Tello which runs independent of the Tello.
    """
    def __init__(self, drone: TelloDrone):
        """
        TelloHUd constructor.
        :param drone: A valid TelloDrone object which provides both video and state information for the HUD.
        """
        self.drone = drone
        self.running = False
        self.hud_font = Font(get_default_font(), 20)
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_proc: mp.Process | None = None
        self.hud_fps = 30
        self.state_q: mp.Queue | None = None
        self.frame_q: mp.Queue | None = None
        self.halt_q: mp.Queue | None = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.state_q = mp.Queue()
        self.frame_q = mp.Queue()
        self.halt_q = mp.Queue()
        self.hud_proc = mp.Process(target=hud_render_loop, args=(self.state_q, self.frame_q, self.halt_q), daemon=True)
        self.hud_thread.start()

    def stop(self) -> None:
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
        while not self.state_q.empty():
            self.state_q.get()
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
                if self.state_q.empty():
                    self.state_q.put(self.drone.get_state())
        self.halt_q.put("HALT")
        self.hud_proc.join()
        while not self.state_q.empty():
            self.state_q.get()
        while not self.frame_q.empty():
            self.frame_q.get()
        while not self.halt_q.empty():
            self.halt_q.get()
        self.frame_q.close()
        self.state_q.close()
        self.halt_q.close()
        if self.hud_proc.is_alive():
            self.hud_proc.kill()
