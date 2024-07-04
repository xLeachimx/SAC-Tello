# File: tello_cmd.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 26 Jun 2023
# Purpose:
#   A class and function for managing sending commands to a Tello in a separate process.
# Notes:
#   Update 30 June 2024:
#       Changed to multi-threaded single process.

from multiprocessing import Queue
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter
from datetime import datetime
from queue import Empty
import os


class TelloCmd:
    """
    Class for handling sending commands to a Tello. Also logs commands sent.
    """
    
    def __init__(self):
        """
        TelloCmd constructor. Does not automatically connect to the Tello.
        """
        # Addresses
        self.local_addr = ('', 8889)
        self.tello_addr = ('192.168.10.1', 8889)
        
        # Setup channels
        self.send_channel = socket(AF_INET, SOCK_DGRAM)
        self.send_channel.bind(self.local_addr)
        
        self.stop = True
        self.connected = False
        
        # Setup receiving thread
        self.receive_thread = Thread(target=self.__receive)
        self.receive_thread.daemon = True
        
        # Setup logs
        self.log = []
        self.MAX_TIME_OUT = 10  # measured in seconds
    
    def connect(self) -> bool:
        """
        Attempts to connect to the Tello drone.
        :return: Returns true if the connection succeeded, false otherwise.
        """
        self.stop = False
        self.receive_thread.start()
        if self.__connect(5):
            return True
        return False
    
    # ======================================
    # COMMAND METHODS
    # ======================================
    # Section Notes:
    #   All commands check to see if the drone has been connected and put into SDK mode before sending commands.
    
    def takeoff(self) -> bool:
        """
        Sends the takeoff command to the Tello.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("takeoff")
        return res is not None and res == 'ok'
    
    def land(self) -> bool:
        """
        Sends the land command to the Tello.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("land")
        return res is not None and res == 'ok'
    
    def up(self, val: int) -> bool:
        """
        Sends the command to raise the Tello by a specified distance (cm).
        :param val: The number of centimeters to raise the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("up " + str(val))
        return res is not None and res == 'ok'
    
    def down(self, val: int) -> bool:
        """
        Sends the command to lower the Tello by a specified distance (cm).
        :param val: The number of centimeters to lower the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("down " + str(val))
        return res is not None and res == 'ok'
    
    def right(self, val: int) -> bool:
        """
        Sends the command to strafe the Tello to the right by a specified distance (cm).
        :param val: The number of centimeters to strafe the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("right " + str(val))
        return res is not None and res == 'ok'
    
    def left(self, val: int) -> bool:
        """
        Sends the command to strafe the Tello to the left by a specified distance (cm).
        :param val: The number of centimeters to strafe the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("left " + str(val))
        return res is not None and res == 'ok'
    
    def forward(self, val: int) -> bool:
        """
        Sends the command to move the Tello forward by a specified distance (cm).
        :param val: The number of centimeters to move the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("forward " + str(val))
        return res is not None and res == 'ok'
    
    def backward(self, val: int) -> bool:
        """
        Sends the command to move the Tello backward by a specified distance (cm).
        :param val: The number of centimeters to move the Tello by. Must be in range [20, 500].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("back " + str(val))
        return res is not None and res == 'ok'
    
    def rotate_cw(self, val: int) -> bool:
        """
        Sends the command to rotate (yaw) the Tello clockwise by a specified number of degrees.
        :param val: The number of degrees to rotate the Tello by. Must be in range [1, 360].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(1, 361):
            return False
        res = self.__send("cw " + str(val))
        return res is not None and res == 'ok'
    
    def rotate_ccw(self, val: int) -> bool:
        """
        Sends the command to rotate (yaw) the Tello counterclockwise by a specified number of degrees.
        :param val: The number of degrees to rotate the Tello by. Must be in range [1, 360].
        :return: Returns true if the command succeeded, false otherwise.
        """
        val = int(val)
        if not self.connected or val not in range(1, 361):
            return False
        res = self.__send("ccw " + str(val))
        return res is not None and res == 'ok'
    
    def flip_left(self) -> bool:
        """
        Sends the command to flip the Tello to the left.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("flip l")
        return res is not None and res == 'ok'
    
    def flip_right(self) -> bool:
        """
        Sends the command to flip the Tello to the right.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("flip r")
        return res is not None and res == 'ok'
    
    def flip_forward(self) -> bool:
        """
        Sends the command to flip the Tello to forward.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("flip f")
        return res is not None and res == 'ok'
    
    def flip_backward(self) -> bool:
        """
        Sends the command to flip the Tello to backward.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("flip b")
        return res is not None and res == 'ok'
    
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
        x = int(x)
        y = int(y)
        z = int(z)
        spd = int(spd)
        if (not self.connected) or (not (20 < max(abs(x), abs(y), abs(z)) < 500)) or (spd not in range(10, 101)):
            return False
        coord_str = ' '.join([str(x), str(y), str(z), str(spd)])
        res = self.__send("go " + coord_str)
        return res is not None and res == 'ok'
    
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
        p1 = (int(x1), int(y1), int(z1))
        p2 = (int(x2), int(y2), int(z2))
        spd = int(spd)
        in_range = True
        for coord in p1:
            in_range = in_range and (20 <= abs(coord) <= 500)
        for coord in p2:
            in_range = in_range and (20 <= abs(coord) <= 500)
        if (not self.connected) or not in_range or (spd not in range(10, 61)):
            return False
        coord_str = list(map(str, p1)) + list(map(str, p2)) + [str(spd)]
        coord_str = ' '.join(coord_str)
        res = self.__send("curve " + coord_str)
        return res is not None and res == 'ok'
    
    def emergency(self) -> None:
        """
        Send the Tello the emergency shutdown command, in triplicate. Does not wait for a response.
        :return: None
        """
        for _ in range(3):
            self.__send_nowait("emergency")
    
    def stream_on(self) -> bool:
        """
        Sends the Tello the command to turn on it's streaming video.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("streamon")
        return res is not None and res == 'ok'
    
    def stream_off(self) -> bool:
        """
        Sends the Tello the command to turn off it's streaming video.
        :return: Returns true if the command succeeded, false otherwise.
        """
        if not self.connected:
            return False
        res = self.__send("streamoff")
        return res is not None and res == 'ok'
    
    def close(self, fldr: str = "logs") -> None:
        """
        Closes the TelloCmd object which writes out all log data and disconnects the Tello drone. If the drone is not
        connected this method does nothing.
        :param fldr: A string containing the path (relative or absolute) to the directory where the log should be
        written. Defaults to: logs/
        :return: None
        """
        if not self.connected:
            return
        self.connected = False
        self.stop = True
        self.send_channel.close()
        self.receive_thread.join()
        t = datetime.now()
        log_name = os.path.join(fldr, t.strftime("%Y-%m-%d_%H-%M-%S") + '-cmd.log')
        if not os.path.exists(fldr):
            os.mkdir(fldr)
        with open(log_name, 'w') as fout:
            count = 0
            for entry in self.log:
                print("Message[" + str(count) + "]:", entry[0], file=fout)
                print("Response[" + str(count) + "]:", entry[1], file=fout)
                count += 1
    
    # ======================================
    # PRIVATE METHODS
    # ======================================
    
    def __connect(self, attempts: int = 5) -> bool:
        """
        A private method handling connecting to the Tello drone and setting it to SDK mode.
        :param attempts: The number of attempts to make to connect before giving up. (default: 5)
        :return: Returns true if the connection was made, false otherwise.
        """
        for _ in range(attempts):
            res = self.__send("command")
            if res is not None and res == 'ok':
                self.connected = True
                return True
        return False
    
    def __send(self, msg: str) -> str | None:
        """
        A private method for sending a string message to the Tello drone.
        :param msg: The message to send.
        :return: Returns the string response from the Tello. If an error or timeout occurs returns none.
        """
        self.log.append([msg, None])
        self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
        # Response wait loop
        start = perf_counter()
        while self.log[-1][1] is None:
            if (perf_counter() - start) > self.MAX_TIME_OUT:
                self.log[-1][1] = "TIMED OUT"
                return None
        return self.log[-1][1]
    
    def __send_nowait(self, msg: str) -> None:
        """
        A private method for sending a string message to the Tello drone, does not wait for a response.
        :param msg: The message to send.
        :return: None.
        """
        self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
    
    def __receive(self) -> None:
        """
        A private method which waits for messages from the Tello drone. This is meant to be run as the target of a
        thread.
        :return: None.
        """
        while not self.stop:
            try:
                response, ip = self.send_channel.recvfrom(1024)
                response = response.decode('utf-8')
                self.log[-1][1] = response.strip()
            except OSError as exc:
                if not self.stop:
                    print("Caught exception socket.error : %s" % exc)
            except UnicodeDecodeError as dec:
                if not self.stop:
                    self.log[-1][1] = "Decode Error"
                    print("Caught exception Unicode 0xcc error.")
