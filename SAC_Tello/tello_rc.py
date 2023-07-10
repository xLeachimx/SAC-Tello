# File: tello_rc.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A class for handling a multi-processed tello drone using keyboard controls.
# Notes:


from multiprocessing import Queue, Process
from queue import Empty
from time import perf_counter
from math import log1p
from pygame import display, draw, Surface, Vector2, QUIT, SRCALPHA
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from pygame import KEYDOWN, QUIT, K_l, K_t, K_DELETE, K_BACKSPACE, K_ESCAPE
from pygame import K_UP, K_DOWN, K_LEFT, K_RIGHT
from pygame.key import get_pressed, key_code
from pygame import event as pg_event
from threading import Thread
from math import sin, cos, radians

from .tello_remote import tello_remote_loop
from .tello_state import tello_state_loop
from .tello_video import tello_video_loop


class TelloRC:
    # Precond:
    #   The computer creating the TelloDrone instance is connected to the Tello's Wi-Fi.
    #
    # Postcond:
    #   Sets up a connection with the Tello Drone.
    def __init__(self):
        # Setup command process
        self.rcQ = Queue()
        self.rc_confQ = Queue()
        self.rc_process = Process(target=tello_remote_loop, args=(self.rcQ, self.rc_confQ))
        
        # Setup state process
        self.state_haltQ = Queue()
        self.state_recQ = Queue()
        self.state_process = Process(target=tello_state_loop, args=(self.state_haltQ, self.state_recQ))
        self.state_thread = Thread(target=self.__state_thread)
        
        # Setup video process
        self.video_haltQ = Queue()
        self.video_recQ = Queue()
        self.video_process = Process(target=tello_video_loop, args=(self.video_haltQ, self.video_recQ))
        self.video_thread = Thread(target=self.__video_thread)
        
        # Internal variables
        self.current_rc = [0, 0, 0, 0]
        self.last_state = None
        self.last_frame = None
        self.running = False
        self.vel_timing = 10

        self.hud_font = Font(get_default_font(), 20)
        # self.hud_thread.daemon = True
        # Create base visuals for hud
        self.hud_rad = 50
        self.hud_base = Surface((4 * self.hud_rad, 4 * self.hud_rad), SRCALPHA, 32)
        hud_center = Vector2(self.hud_base.get_width() // 2, self.hud_base.get_height() // 2)
        draw.circle(self.hud_base, (0, 0, 0, 100), hud_center, 2 * self.hud_rad)
        # Draw baselines
        draw.circle(self.hud_base, (0, 200, 0), hud_center, self.hud_rad, self.hud_rad // 10)
        # Roll baseline
        roll_baseline = Vector2(cos(0), sin(0))
        roll_start = (roll_baseline * self.hud_rad) + hud_center
        roll_end = (roll_baseline * (2 * self.hud_rad)) + hud_center
        draw.line(self.hud_base, (0, 200, 0), roll_start, roll_end, 6)
        roll_baseline - -roll_baseline
        roll_start = (roll_baseline * self.hud_rad) + hud_center
        roll_end = (roll_baseline * (2 * self.hud_rad)) + hud_center
        draw.line(self.hud_base, (0, 200, 0), roll_start, roll_end, 6)
        # Pitch indicator
        draw.line(self.hud_base, (0, 0, 220),
                  (hud_center.x - self.hud_rad + (self.hud_rad // 10), hud_center.y),
                  (hud_center.x - (self.hud_rad // 2), hud_center.y), 6)
        draw.line(self.hud_base, (0, 0, 220),
                  (hud_center.x + (self.hud_rad // 2), hud_center.y),
                  (hud_center.x + self.hud_rad - (self.hud_rad // 10), hud_center.y), 6)

    # ==========================
    #   MANAGEMENT METHODS
    # ==========================

    # Precond:
    #   None.
    #
    # Postcond:
    #   Starts the TelloRC object.
    #   Connects to the Tello.
    #   Connects to all streams and begins all processes.
    #   Returns True if all processes have been started.
    def start(self):
        self.running = True
        self.rc_process.start()
        self.state_thread.start()
        self.state_process.start()
        self.video_thread.start()
        self.video_process.start()
        return True
    
    def control(self):
        # Setup Pygame
        screen = display.set_mode((960, 720))
        display.set_caption("Tello HUD")
        # Setup
        key_holds = {'w': 0, 's': 0, 'd': 0, 'a': 0, 'q': 0, 'e': 0, 'r': 0, 'f': 0}
        poll_timer = perf_counter()
        poll_delta = 1/30
        pg_event.set_allowed([KEYDOWN])
        # Main Loop
        control_running = True
        while control_running:
            delta = perf_counter() - poll_timer
            if delta >= poll_delta:
                self.__hud_update(screen)
                poll_timer = perf_counter()
                # Check for events
                command_sent = False
                for event in pg_event.get(KEYDOWN, QUIT):
                    if event.type == QUIT:
                        control_running = False
                    if event.type == KEYDOWN:
                        if event.key == K_t:
                            command_sent = True
                            if not self.takeoff():
                                print("Problem with takeoff!")
                        elif event.key == K_l:
                            command_sent = True
                            if not self.land():
                                print("Problem with landing!")
                        elif event.key == K_ESCAPE:
                            command_sent = True
                            if not self.emergency():
                                print("Problem with emergency shutdown!")
                        elif event.key == K_BACKSPACE:
                            control_running = False
                        elif event.key == K_DELETE:
                            self.rcQ.put((0, 0, 0, 0))
                        elif event.key == K_UP:
                            command_sent = True
                            if not self.flip_forward():
                                print("Problem with forward flip!")
                        elif event.key == K_DOWN:
                            command_sent = True
                            if not self.flip_backward():
                                print("Problem with backward flip!")
                        elif event.key == K_RIGHT:
                            command_sent = True
                            if not self.flip_right():
                                print("Problem with right flip!")
                        elif event.key == K_LEFT:
                            command_sent = True
                            if not self.flip_left():
                                print("Problem with left flip!")
                if command_sent:
                    poll_timer = perf_counter()
                    continue
                # Deal with held keys
                key_state = get_pressed()
                for key in key_holds:
                    if key_state[key_code(key)]:
                        key_holds[key] += delta
                    else:
                        key_holds[key] -= delta
                    key_holds[key] = max(0, min(self.vel_timing, key_holds[key]))
                y = self.__vel_curve(key_holds['w']) - self.__vel_curve(key_holds['s'])
                x = self.__vel_curve(key_holds['d']) - self.__vel_curve(key_holds['a'])
                z = self.__vel_curve(key_holds['r']) - self.__vel_curve(key_holds['f'])
                rot = self.__vel_curve(key_holds['e']) - self.__vel_curve(key_holds['q'])
                if self.rcQ.empty():
                    self.rcQ.put((int(x), int(y), int(z), int(rot)))
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Closes down communication with the drone and writes the log to a file.
    def close(self):
        self.running = False
        if self.state_thread.is_alive():
            self.state_thread.join()
        if self.video_thread.is_alive():
            self.video_thread.join()
        if self.video_process.is_alive():
            self.video_haltQ.put("halt")
            TelloRC.__clear_q(self.video_recQ)
            self.video_process.join()
        if self.state_process.is_alive():
            self.state_haltQ.put("halt")
            TelloRC.__clear_q(self.state_recQ)
            self.state_process.join()
        if self.rc_process.is_alive():
            self.rcQ.put("halt")
            TelloRC.__clear_q(self.rc_confQ)
            self.rc_process.join()

    # ======================================
    # COMMAND METHODS
    # ======================================
    # Section Notes:
    #   All commands check to see if the drone has been connected and put into SDK mode before sending commands.

    # Precond:
    #   None.
    #
    # Postcond
    #   Sends the takeoff command.
    #   If a non-okay response is given returns False, otherwise returns true.
    def takeoff(self):
        self.rcQ.put("takeoff")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond
    #   Sends the land command.
    #   If a non-okay response is given returns False, otherwise returns true.
    def land(self):
        self.rcQ.put("land")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends the emergency command, in triplicate. Does not wait for response.
    def emergency(self):
        self.rcQ.put("emergency")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip l command to the command queue.
    def flip_left(self):
        self.rcQ.put("flip l")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip r command to the command queue.
    def flip_right(self):
        self.rcQ.put("flip r")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip f command to the command queue.
    def flip_forward(self):
        self.rcQ.put("flip f")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip b command to the command queue.
    def flip_backward(self):
        self.rcQ.put("flip b")
        try:
            conf = self.rc_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        return True

    # ======================================
    # Info METHODS
    # ======================================

    # Precond:
    #   None.
    #
    # Postcond:
    #   Returns the last frame taken by the Tello.
    #   Returns None if the stream is off.
    def get_frame(self):
        return self.last_frame

    # Precond:
    #   None.
    #
    # Postcond:
    #   Returns the last state received from the Tello as a dictionary.
    def get_state(self):
        return self.last_state

    # ======================================
    # PRIVATE METHODS
    # ======================================

    # Precond:
    #   None.
    #
    # Postcond:
    #   Thread handling state extraction..
    def __state_thread(self):
        while self.running:
            self.last_state = self.state_recQ.get()

    # Precond:
    #   None.
    #
    # Postcond:
    #   Thread handling video extraction.
    def __video_thread(self):
        while self.running:
            self.last_frame = self.video_recQ.get()

    # Precond:
    #   q is a valid mp.Queue object.
    #
    # Postcond:
    #   Clears the q and closes it.
    def __clear_q(q: Queue):
        try:
            while not q.empty():
                q.get_nowait()
        except Empty:
            pass
        q.close()
    
    # Precond:
    #   t is a valid floating point value.
    #
    # Postcond:
    #   Returns the current velocity based on how long a key has  been pressed.
    def __vel_curve(self, t):
        return 100 * (log1p(t) / log1p(self.vel_timing))

    def __hud_update(self, screen):
        # Setup video loop basics
        horizon_rad = 50
        horizon_size = 4 * horizon_rad
        horizon_placement = ((screen.get_width() - horizon_size) // 2, (screen.get_height() - horizon_size) // 2)
        screen.fill((0, 0, 0, 255))
        if self.last_frame is not None:
            screen.blit(frombuffer(self.last_frame.tobytes(), self.last_frame.shape[1::-1], "BGR"), (0, 0))
            if self.last_state is not None:
                bat_text = self.hud_font.render(f"Battery: {self.last_state['bat']:4}", True, (0, 200, 0), (0, 0, 0))
                height_text = self.hud_font.render(f"ToF: {self.last_state['tof']:4}", True, (0, 200, 0), (0, 0, 0))
                horizon = self.__artificial_horizon(horizon_rad, int(self.last_state['pitch']), int(self.last_state['roll']))
                screen.blits([
                    (bat_text, (0, 0)),
                    (height_text, (0, bat_text.get_height())),
                    (horizon, horizon_placement)
                ])
        else:
            init_text = self.hud_font.render("Initializing...", True, (0, 200, 0), (9, 0, 0))
            x = (screen.get_width() - init_text.get_width()) // 2
            y = (screen.get_height() - init_text.get_height()) // 2
            screen.blit(init_text, (x, y))
        display.flip()

    def __artificial_horizon(self, rad: int, pitch: int, roll: int):
        result = Surface((4 * rad, 4 * rad), SRCALPHA, 32)
        result.blit(self.hud_base, (0, 0))
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
