# File: tello_rc.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A class for handling a multi-processed tello drone using keyboard controls.
# Notes:
#   Update 4 July 2024:
#       Changed to multi-threaded single process.

from time import perf_counter
from math import log1p
from pygame import display, draw, Surface, Vector2, SRCALPHA
from pygame.font import Font, get_default_font
from pygame.image import frombuffer
from pygame import KEYDOWN, QUIT, K_l, K_t, K_DELETE, K_BACKSPACE, K_ESCAPE
from pygame import K_UP, K_DOWN, K_LEFT, K_RIGHT
from pygame.key import get_pressed, key_code
from pygame import event as pg_event
from threading import Thread
from math import sin, cos, radians

from .tello_remote import TelloRemote
from .tello_state import TelloState
from .tello_video import TelloVideo


class TelloRC:
    """
    A class for controlling a Tello Drone using RC controls via keyboard controls.
    """
    def __init__(self):
        """
        Constructor for the TelloRC class. Does not automatically connect to the Tello Drone.
        """
        self.remote = TelloRemote()
        self.video = TelloVideo()
        self.state = TelloState()
        
        # Internal variables
        self.current_rc = [0, 0, 0, 0]
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

    def start(self) -> bool:
        """
        Connects to the Tello Drone.
        :return: Returns true if the connection was successful, false otherwise.
        """
        self.running = True
        if self.remote.connect() and self.remote.stream_on():
            self.video.start()
            self.state.start()
            return True
        return False
    
    def control(self) -> None:
        """
        Starts the process of controlling the Tello Drone by keyboard RC control, including display of the video feed
        and artificial horizon. Must be called AFTER start.
        :return: None
        """
        # Setup Pygame
        screen = display.set_mode((960, 720))
        display.set_caption("Tello HUD")
        # Setup
        key_holds = {'w': 0, 's': 0, 'd': 0, 'a': 0, 'q': 0, 'e': 0, 'r': 0, 'f': 0}
        poll_timer = perf_counter()
        poll_delta = 1/30
        pg_event.set_allowed([KEYDOWN, QUIT])
        # Main Loop
        control_running = True
        self.remote.stream_on()
        while control_running:
            delta = perf_counter() - poll_timer
            if delta >= poll_delta:
                self.__hud_update(screen)
                poll_timer = perf_counter()
                # Check for events
                for event in pg_event.get(KEYDOWN, QUIT):
                    if event.type == QUIT:
                        control_running = False
                    if event.type == KEYDOWN:
                        if event.key == K_t:
                            self.remote.takeoff()
                        elif event.key == K_l:
                            self.remote.land()
                        elif event.key == K_UP:
                            self.remote.flip_forward()
                        elif event.key == K_DOWN:
                            self.remote.flip_backward()
                        elif event.key == K_RIGHT:
                            self.remote.flip_right()
                        elif event.key == K_LEFT:
                            self.remote.flip_left()
                        elif event.key == K_ESCAPE:
                            self.remote.emergency()
                            control_running = False
                        elif event.key == K_BACKSPACE:
                            control_running = False
                        elif event.key == K_DELETE:
                            self.remote.set_rc(0, 0, 0, 0)
                # Deal with held keys
                key_state = get_pressed()
                for key in key_holds:
                    if key_state[key_code(key)]:
                        key_holds[key] += delta
                    else:
                        key_holds[key] -= delta
                    key_holds[key] = max(0, min(self.vel_timing, key_holds[key]))
                y = int(self.__vel_curve(key_holds['w']) - self.__vel_curve(key_holds['s']))
                x = int(self.__vel_curve(key_holds['d']) - self.__vel_curve(key_holds['a']))
                z = int(self.__vel_curve(key_holds['r']) - self.__vel_curve(key_holds['f']))
                rot = int(self.__vel_curve(key_holds['e']) - self.__vel_curve(key_holds['q']))
                self.remote.set_rc(x, y, z, rot)

    def close(self) -> None:
        """
        Closes communication with the Tello Drone.
        :return: None
        """
        self.running = False
        self.state.close()
        self.video.close()
        self.remote.close()
    
    def __vel_curve(self, t: float) -> float:
        """
        Converts a time (s) into a throttle value.
        :param t: A floating point number representing the number of seconds.
        :return: A floating point value representing the throttle setting based on how long a control has been pressed.
        """
        return 100 * (log1p(t) / log1p(self.vel_timing))

    def __hud_update(self, screen: Surface) -> None:
        """
        Updates the HUD graphic so that it represents the current video feed and state from the Tello Drone.
        :param screen: The pygame surface of the display.
        :return: None
        """
        last_state = self.state.get()
        last_frame = self.video.get()
        if last_frame is None or last_state is None:
            return
        # Setup video loop basics
        horizon_rad = 50
        horizon_size = 4 * horizon_rad
        horizon_placement = ((screen.get_width() - horizon_size) // 2, (screen.get_height() - horizon_size) // 2)
        screen.fill((0, 0, 0, 255))
        if last_frame is not None:
            screen.blit(frombuffer(last_frame.tobytes(), last_frame.shape[1::-1], "BGR"), (0, 0))
            if last_state is not None:
                bat_text = self.hud_font.render(f"Battery: {last_state['bat']:4}", True, (0, 200, 0), (0, 0, 0))
                height_text = self.hud_font.render(f"ToF: {last_state['tof']:4}", True, (0, 200, 0), (0, 0, 0))
                horizon = self.__artificial_horizon(horizon_rad, int(last_state['pitch']), int(last_state['roll']))
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

    def __artificial_horizon(self, rad: int, pitch: int, roll: int) -> Surface:
        """
        Renders an artificial horizon for the HUD.
        :param rad: HUD radius.
        :param pitch: Pitch of the Tello Drone in degrees.
        :param roll: Roll of the Tello Drone in degrees.
        :return: A surface containing the artificial horizon.
        """
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
