# File: tello_hud.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A simple hud program that can be run on a separate thread.
# Notes:

from tello_drone import TelloDrone
from tello_rc import TelloRC
from time import perf_counter, sleep
import pygame as pg
from math import sin, cos, radians
from threading import Thread


class TelloHud:
    def __init__(self, drone: TelloDrone | TelloRC):
        self.drone = drone
        self.running = False
        self.hud_thread = Thread(target=self.__hud_stream)
        self.hud_thread.daemon = True
        # Create base visuals for hud
        self.hud_rad = 50
        self.hud_base = pg.Surface((4*self.hud_rad, 4*self.hud_rad), pg.SRCALPHA, 32)
        hud_center = self.BasicVec(self.hud_base.get_width() // 2, self.hud_base.get_height() // 2)
        pg.draw.circle(self.hud_base, (0, 0, 0, 100), hud_center.to_tuple(), 2*self.hud_rad)
        # Draw baselines
        pg.draw.circle(self.hud_base, (0, 200, 0), hud_center.to_tuple(), self.hud_rad, self.hud_rad // 10)
        # Roll baseline
        roll_baseline = self.BasicVec(cos(0), sin(0))
        roll_start = roll_baseline.scale(self.hud_rad).add(hud_center)
        roll_end = roll_baseline.scale(2 * self.hud_rad).add(hud_center)
        pg.draw.line(self.hud_base, (0, 200, 0), roll_start.to_tuple(), roll_end.to_tuple(), 6)
        roll_start = roll_baseline.neg().scale(self.hud_rad).add(hud_center)
        roll_end = roll_baseline.neg().scale(2 * self.hud_rad).add(hud_center)
        pg.draw.line(self.hud_base, (0, 200, 0), roll_start.to_tuple(), roll_end.to_tuple(), 6)
    
    def activate_hud(self):
        if self.running:
            return
        self.running = True
        self.hud_thread.start()
        sleep(5)
        
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
        frame_delta = 1/24
        while self.running:
            if (perf_counter() - frame_timer) > frame_delta:
                frame_timer = perf_counter()
                frame = self.drone.get_frame()
                if frame is not None:
                    frame = frame[0]
                    frame = pg.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "BGR")
                    screen.blit(frame, (0, 0))
                state = self.drone.get_state()
                if state is not None:
                    state = state[0]
                    bat_text = hud_font.render(f"Battery: {state['bat']:4}", True, (0, 200, 0), (0, 0, 0))
                    screen.blit(bat_text, (0, 0))
                    height_text = hud_font.render(f"ToF: {state['tof']:4}", True, (0, 200, 0), (0, 0, 0))
                    screen.blit(height_text, (0, bat_text.get_height()))
                    horizon = self.__artificial_horizon(50, int(state['pitch']), int(state['roll']))
                    horizon_pos = (screen.get_width() - horizon.get_width())//2, (screen.get_height() - horizon.get_height())//2
                    screen.blit(horizon, horizon_pos)
                pg.display.flip()
                for event in pg.event.get(pg.QUIT):
                    self.running = False
        pg.display.quit()
        
    def __artificial_horizon(self, rad: int, pitch:int, roll: int):
        result = pg.surface.Surface((4*rad, 4*rad), pg.SRCALPHA, 32)
        result.blit(self.hud_base, (0, 0))
        center = self.BasicVec(result.get_width() // 2, result.get_height() // 2)
        # Draw roll lines]
        left_ang = radians(180 + roll)
        left_vec = self.BasicVec(cos(left_ang), sin(left_ang))
        left_start = left_vec.scale(rad)
        left_end = left_vec.scale(rad*2)
        left_start = left_start.add(center)
        left_end = left_end.add(center)
        pg.draw.line(result, (0, 200, 0), left_start.to_tuple(), left_end.to_tuple(), 3)
        right_ang = radians(roll)
        right_vec = self.BasicVec(cos(right_ang), sin(right_ang))
        right_start = right_vec.scale(rad)
        right_end = right_vec.scale(rad * 2)
        right_start = right_start.add(center)
        right_end = right_end.add(center)
        pg.draw.line(result, (0, 200, 0), right_start.to_tuple(), right_end.to_tuple(), 3)
        # Draw Pitch lines
        pitch = -pitch # Line direction adjustment
        pitch_line_deg = 10
        pitch_lines = pg.Surface((rad, rad), pg.SRCALPHA)
        pixels_per_ang = 2
        start_angle = pitch - ((pitch_lines.get_height()//2)//pixels_per_ang)
        pixel_start = pitch_line_deg - (start_angle % pitch_line_deg)
        pixel_start = pixel_start * pixels_per_ang
        angles = []
        for i in range(pixel_start, pitch_lines.get_height(), pitch_line_deg*pixels_per_ang):
            ang = start_angle + (i // pixels_per_ang)
            angles.append(ang)
            if ang % pitch_line_deg == 0:
                if ang != 0:
                    pg.draw.line(pitch_lines, (0, 200, 0), (0, i), (pitch_lines.get_width(), i), 3)
                else:
                    pg.draw.line(pitch_lines, (200, 0, 0), (0, i), (pitch_lines.get_width(), i), 3)
        center_pitch = center.add((-(pitch_lines.get_width()//2), -(pitch_lines.get_height()//2)))
        # Current Pitch indicator
        indicator_height = pitch_lines.get_height()//2
        pg.draw.line(pitch_lines, (0, 0, 200), (0, indicator_height), (pitch_lines.get_width(), indicator_height), 3)
        result.blit(pitch_lines, center_pitch.to_tuple())
        return result
    
    class BasicVec:
        def __init__(self, x, y):
            self.x = x
            self.y = y
        
        def add(self, other):
            if type(other) == TelloHud.BasicVec:
                return TelloHud.BasicVec(self.x+other.x, self.y+other.y)
            elif type(other) == tuple:
                return TelloHud.BasicVec(self.x+other[0], self.y+other[1])
            
        def scale(self, n):
            return TelloHud.BasicVec(self.x*n, self.y*n)
        
        def neg(self):
            return TelloHud.BasicVec(-self.x, -self.y)
        
        def to_tuple(self):
            return self.x, self.y
            