# File: tello_drone.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Redesigned On: 26 Jun 2023
# Purpose:
#   A basic method of controlling a Tello Drone and allowing a video feed.
#
# Notes:
#   Some code inspired/borrowed from: github.com/dji-sdk/Tello-Python/


# import multiprocessing as mp
from multiprocessing import Process, Queue
from queue import Empty
from time import sleep
from sys import stderr
from threading import Thread

from .tello_cmd import tello_command_loop
from .tello_state import tello_state_loop
from .tello_video import tello_video_loop


class TelloDrone:
    # Precond:
    #   The computer creating the TelloDrone instance is connected to the Tello's Wi-Fi.
    #
    # Postcond:
    #   Sets up a connection with the Tello Drone.
    def __init__(self):
        # Setup command process
        self.cmdQ = Queue(2)
        self.cmd_confQ = Queue(2)
        self.cmd_process = Process(target=tello_command_loop, args=(self.cmdQ, self.cmd_confQ))
        self.cmd_thread = Thread(target=self.__cmd_thread)
        
        # Setup state process
        self.state_haltQ = Queue(2)
        self.state_recQ = Queue(2)
        self.state_process = Process(target=tello_state_loop, args=(self.state_haltQ, self.state_recQ))
        self.state_thread = Thread(target=self.__state_thread)

        # Setup video process
        self.video_haltQ = Queue(2)
        self.video_recQ = Queue(2)
        self.video_process = Process(target=tello_video_loop, args=(self.video_haltQ, self.video_recQ))
        self.video_thread = Thread(target=self.__video_thread)
        
        # Internal variables
        self.commandQ = []
        self.commandQ_limit = 100
        self.last_state = None
        self.last_frame = None
        self.running = False

    # ==========================
    #   MANAGEMENT METHODS
    # ==========================
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Starts the TelloDrone object.
    #   Connects to the Tello.
    #   Connects to all streams and begins all processes.
    #   Returns True if all processes have been started.
    def start(self):
        self.running = True
        self.commandQ = []
        self.cmd_thread.start()
        self.cmd_process.start()
        # Check to see if connection worked.
        try:
            conf = self.cmd_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False

        # Start the video stream
        self.cmdQ.put("stream on")
        try:
            conf = self.cmd_confQ.get(block=True, timeout=5)
            if not conf[0]:
                return False
        except Empty:
            return False
        self.state_thread.start()
        self.state_process.start()
        self.video_thread.start()
        self.video_process.start()
        return True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Closes down communication with the drone and writes the log to a file.
    def close(self):
        self.running = False
        if self.cmd_thread.is_alive():
            self.cmd_thread.join()
        if self.state_thread.is_alive():
            self.state_thread.join()
        if self.video_thread.is_alive():
            self.video_thread.join()
        if self.video_process.is_alive():
            self.video_haltQ.put("halt")
            TelloDrone.__clear_q(self.video_recQ)
            self.video_process.join()
        if self.state_process.is_alive():
            self.state_haltQ.put("halt")
            TelloDrone.__clear_q(self.state_recQ)
            self.state_process.join()
        if self.cmd_process.is_alive():
            self.cmdQ.put("halt")
            TelloDrone.__clear_q(self.cmd_confQ)
            self.cmd_process.join()
        
    # Precond:
    #   None.
    #
    # Postcond:
    #   Waits until all commands are complete.
    def complete(self):
        while len(self.commandQ) > 0:
            sleep(1)

    # ======================================
    # COMMAND METHODS
    # ======================================
   
    # Precond:
    #   None.
    #
    # Postcond
    #   Adds takeoff command to the command queue.
    def takeoff(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("takeoff")
            return True
        return False

    # Precond:
    #   None.
    #
    # Postcond
    #   Adds land command to the command queue.
    def land(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("land")
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds up command to the command queue.
    def up(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("up " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds down command to the command queue.
    def down(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("down " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds left command to the command queue.
    def left(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("left " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds right command to the command queue.
    def right(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("right " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds forward command to the command queue.
    def forward(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("forward " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds backward command to the command queue.
    def backward(self, val):
        if val not in range(20, 501):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("backward " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds rotate cw command to the command queue.
    def rotate_cw(self, val):
        if val not in range(1, 361):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("rotate cw " + str(val))
            return True
        return False

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Adds rotate ccw command to the command queue.
    def rotate_ccw(self, val):
        if val not in range(1, 361):
            return False
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("rotate ccw " + str(val))
            return True
        return False

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip l command to the command queue.
    def flip_left(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("flip l")
            return True
        return False

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip r command to the command queue.
    def flip_right(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("flip r")
            return True
        return False

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip f command to the command queue.
    def flip_forward(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("flip f")
            return True
        return False

    # Precond:
    #   None.
    #
    # Postcond:
    #   Adds flip b command to the command queue.
    def flip_backward(self):
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("flip b")
            return True
        return False

    # Precond:
    #   x the amount to move in the x-axis.
    #   y the amount to move in the y-axis.
    #   z the amount to move in the z-axis.
    #   spd is the speed of movement
    #
    # Postcond:
    #   Adds the move command to the command queue.
    def move(self, x, y, z, spd):
        if not (20 < max(abs(x), abs(y), abs(z)) < 500) or spd not in range(10, 101):
            return False
        coord_str = ' '.join([str(x), str(y), str(z), str(spd)])
        if len(self.commandQ) < self.commandQ_limit:
            self.commandQ.append("go " + coord_str)
            return True
        return False

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

    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends the emergency command, in triplicate. Does not wait for response.
    def emergency(self):
        for _ in range(3):
            self.cmdQ.put("emergency")

    # ======================================
    # PRIVATE METHODS
    # ======================================

    # Precond:
    #   None.
    #
    # Postcond:
    #   Thread handling command execution.
    def __cmd_thread(self):
        while self.running:
            if len(self.commandQ) > 0 and self.cmdQ.empty():
                self.cmdQ.put(self.commandQ.pop(0))
                conf = self.cmd_confQ.get()
                if not conf[0]:
                    print("Problem executing command ", conf[1], file=stderr)

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
    @staticmethod
    def __clear_q(q: Queue):
        try:
            while not q.empty():
                q.get_nowait()
        except Empty:
            pass
        q.close()