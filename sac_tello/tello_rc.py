# File: tello_rc.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A class for handling a multi-processed tello drone using keyboard controls.
# Notes:


import multiprocessing as mp
import queue
from time import perf_counter
from math import log1p
import pygame as pg
import sys
from threading import Thread

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
        self.rcQ = mp.Queue()
        self.rc_confQ = mp.Queue()
        self.rc_process = mp.Process(target=tello_remote_loop, args=(self.rcQ, self.rc_confQ))
        self.rc_process.daemon = True
        
        # Setup state process
        self.state_haltQ = mp.Queue()
        self.state_recQ = mp.Queue()
        self.state_process = mp.Process(target=tello_state_loop, args=(self.state_haltQ, self.state_recQ))
        self.state_process.daemon = True
        self.state_thread = Thread(target=self.__state_thread)
        self.state_thread.daemon = True
        
        # Setup video process
        self.video_haltQ = mp.Queue()
        self.video_recQ = mp.Queue()
        self.video_process = mp.Process(target=tello_video_loop, args=(self.video_haltQ, self.video_recQ))
        self.video_process.daemon = True
        self.video_thread = Thread(target=self.__video_thread)
        self.video_thread.daemon = True
        
        # Internal variables
        self.current_rc = [0, 0, 0, 0]
        self.last_state = None
        self.last_frame = None
        self.running = False
        self.vel_timing = 10

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
        # Setup
        key_holds = {'w': 0, 's': 0, 'd': 0, 'a': 0, 'q': 0, 'e': 0, 'r': 0, 'f': 0}
        poll_timer = perf_counter()
        poll_delta = 1/30
        # Main Loop
        control_running = True
        pg.init()
        while control_running:
            delta = perf_counter() - poll_timer
            if delta >= poll_delta:
                # Check for events
                command_sent = False
                for event in pg.event.get(pg.KEYDOWN):
                    if event.key == pg.K_t:
                        command_sent = True
                        if not self.takeoff():
                            print("Problem with takeoff!")
                    elif event.key == pg.K_l:
                        command_sent = True
                        if not self.land():
                            print("Problem with landing!")
                    elif event.key == pg.K_ESCAPE:
                        command_sent = True
                        if not self.emergency():
                            print("Problem with emergency shutdown!")
                    elif event.key == pg.K_BACKSPACE:
                        control_running = False
                    elif event.key == pg.K_DELETE:
                        self.rcQ.put((0, 0, 0, 0))
                    elif event.key == pg.K_UP:
                        command_sent = True
                        if not self.flip_forward():
                            print("Problem with forward flip!")
                    elif event.key == pg.K_DOWN:
                        command_sent = True
                        if not self.flip_backward():
                            print("Problem with backward flip!")
                    elif event.key == pg.K_RIGHT:
                        command_sent = True
                        if not self.flip_right():
                            print("Problem with right flip!")
                    elif event.key == pg.K_LEFT:
                        command_sent = True
                        if not self.flip_left():
                            print("Problem with left flip!")
                if command_sent:
                    poll_timer = perf_counter()
                    continue
                # Deal with held keys
                key_state = pg.key.get_pressed()
                for key in key_holds:
                    if key_state[pg.key.key_code(key)]:
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
        except queue.Empty:
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
        except queue.Empty:
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
        except queue.Empty:
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
        except queue.Empty:
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
        except queue.Empty:
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
        except queue.Empty:
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
        except queue.Empty:
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
    def __clear_q(q: mp.Queue):
        try:
            while not q.empty():
                q.get_nowait()
        except queue.Empty:
            pass
        q.close()
    
    # Precond:
    #   t is a valid floating point value.
    #
    # Postcond:
    #   Returns the current velocity based on how long a key has  been pressed.
    def __vel_curve(self, t):
        return 100 * (log1p(t) / log1p(self.vel_timing))


if __name__ == '__main__':
    mp.freeze_support()
