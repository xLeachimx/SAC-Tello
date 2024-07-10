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
#   Update 30 June 2024:
#       Changed to multi-threaded single process.

from threading import Thread
import numpy as np
from time import sleep, perf_counter
import cv2 as cv
import uuid

from .tello_cmd import TelloCmd
from .tello_state import TelloState
from .tello_video import TelloVideo


class TelloDrone:
    """A class for handling all Tello streams from a central object."""
    def __init__(self):
        """
        The TelloDrone class constructor. Does not automatically connect to the Tello Drone.
        """
        self.cmd = TelloCmd()
        self.state = TelloState()
        self.video = TelloVideo()
        
        # Internal variables
        self.state_update_thread = Thread(target=self.__state_update_thread, daemon=True)
        self.last_state = None
        self.video_update_thread = Thread(target=self.__video_update_thread, daemon=True)
        self.last_frame = None
        self.running = False

    # ==========================
    #   MANAGEMENT METHODS
    # ==========================
    
    def start(self) -> bool:
        """
        Initiates the connection to the Tello and all related streams.
        :return: Returns true if all connections are made, returns false otherwise.
        """
        self.running = True
        if self.cmd.connect() and self.cmd.stream_on():
            self.video.start()
            self.state.start()
            self.state_update_thread.start()
            self.video_update_thread.start()
            while self.last_frame is None and self.last_state is None:
                sleep(0.1)
            return True
        return False

    def close(self) -> None:
        """
        Closes all additional threads and streams. Writes out all applicable log files.
        :return: None.
        """
        self.running = False
        self.cmd.close()
        self.state.close()
        self.video.close()
        self.state_update_thread.join()
        self.video_update_thread.join()

    # ======================================
    # COMMAND METHODS
    # ======================================
   
    def takeoff(self) -> bool:
        """
        Sends the takeoff command to the Tello.
        :return: Returns true if command sent with no error, false otherwise.
        """
        return self.cmd.takeoff()

    def land(self) -> bool:
        """
        Sends the takeoff command to the Tello.
        :return: Returns true if command sent with no error, false otherwise.
        """
        return self.cmd.land()

    def up(self, val: int) -> bool:
        """
        Sends the command to raise the Tello by a specified distance (cm).
        :param val: The number of centimeters to raise the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.up(val)

    def down(self, val: int) -> bool:
        """
        Sends the command to lower the Tello by a specified distance (cm).
        :param val: The number of centimeters to lower the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.down(val)

    def left(self, val: int) -> bool:
        """
        Sends the command to strafe the Tello to the left by a specified distance (cm).
        :param val: The number of centimeters to strafe the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.left(val)

    def right(self, val: int) -> bool:
        """
        Sends the command to strafe the Tello to the right by a specified distance (cm).
        :param val: The number of centimeters to strafe the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.right(val)

    def forward(self, val: int) -> bool:
        """
        Sends the command to move the Tello forward by a specified distance (cm).
        :param val: The number of centimeters to move the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.forward(val)

    def backward(self, val: int) -> bool:
        """
        Sends the command to move the Tello backward by a specified distance (cm).
        :param val: The number of centimeters to move the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.backward(val)

    def rotate_cw(self, val: int) -> bool:
        """
        Sends the command to rotate (yaw) the Tello clockwise by a specified number of degrees.
        :param val: The number of degrees to rotate the Tello by. Must be in range [1, 360].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.rotate_cw(val)

    def rotate_ccw(self, val: int) -> bool:
        """
        Sends the command to rotate (yaw) the Tello counterclockwise by a specified number of degrees.
        :param val: The number of degrees to rotate the Tello by. Must be in range [1, 360].
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.rotate_ccw(val)

    def flip_left(self) -> bool:
        """
        Sends the command to flip the Tello to the left.
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.flip_left()

    def flip_right(self) -> bool:
        """
        Sends the command to flip the Tello to the right.
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.flip_right()

    def flip_forward(self) -> bool:
        """
        Sends the command to flip the Tello to forward.
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.flip_forward()

    def flip_backward(self) -> bool:
        """
        Sends the command to flip the Tello to backward.
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.flip_backward()

    def move(self, x: int, y: int, z: int, spd: int) -> bool:
        """
        Sends the command to move the Tello such that it is properly displaced (cm) in the given x, y, and z directions
        at the given speed. Values for x, y, and z cannot all simultaneously be in the range [-20, 20]
        :param x: The amount of displacement (cm) in the x (forward/backward) direction. Must be in range [-500, 500].
        :param y: The amount of displacement (cm) in the y (left/right) direction. Must be in range [-500, 500].
        :param z: The amount of displacement (cm) in the z (down/up) direction. Must be in range [-500, 500].
        :param spd: Speed to perform the move at (cm/s).
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.move(x, y, z, spd)

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, spd: int) -> bool:
        """
        Sends the command to move the Tello along a curve such that the final displacement (cm) is equal to x2, y2, z2
        and at some point during the move the curve passes through the displacement values of x1, y1, z1. Values for
        any x, y, and z cannot all simultaneously be in the range [-20, 20]. Arc radius must be between 50cm and 1000cm.
        :param x1: The x displacement to pass the curve through.
        :param y1: The y displacement to pass the curve through.
        :param z1: The z displacement to pass the curve through.
        :param x2: The x displacement to end movement at.
        :param y2: The y displacement to end movement at.
        :param z2: The z displacement to end movement at.
        :param spd: Speed to perform the move at (cm/s).
        :return: Returns true if the command succeeded, false otherwise.
        """
        return self.cmd.curve(x1, y1, z1, x2, y2, z2, spd)
    
    def emergency(self) -> None:
        """
        Send the Tello the emergency shutdown command, in triplicate. Does not wait for a response.
        :return: None
        """
        self.cmd.emergency()

    # ======================================
    # Info METHODS
    # ======================================
    
    def get_frame(self) -> np.ndarray | None:
        """
        Gets the last frame read from the Tello, if it exists.
        :return: Returns the last frame as a numpy array (openCV format.) If no frame exists returns None instead.
        """
        return self.last_frame

    def get_state(self) -> dict | None:
        """
        Gets the last state read from the Tello, if it exists.
        :return: Returns the last state as a dictionary (str -> str). If no state exists returns None instead.
        """
        return self.last_state

    def take_pic(self, name: str | None = None) -> str:
        """
        Takes the last frame and saves it to the file with the given name.
        :param name: String containing the filename to store the image at, if none one will be auto-generated.
        :return: The filename where the image was stored.
        """
        if name is None:
            name = str(uuid.uuid4()) + '.jpg'
        cv.imwrite(name, self.last_frame)
        return name

    # ======================================
    # PRIVATE METHODS
    # ======================================

    def __state_update_thread(self) -> None:
        """
        Thread for handling state extraction.
        :return: None.
        """
        while self.running:
            if self.state.has_state():
                self.last_state = self.state.get()
                sleep(1/60)

    def __video_update_thread(self) -> None:
        """
        Thread for handling video frame extraction.
        :return: None.
        """
        while self.running:
            if self.video.has_frame():
                self.last_frame = self.video.get()
                sleep(1/60)
