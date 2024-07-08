# File: tello_remote.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A class and function for handling a multi-processed rc tello controller.
# Notes:
#   Update 4 July 2024:
#       Changed to multi-threaded single process.
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter


class TelloRemote:
    """A class for handling controlling the Tello Drone via RC controls."""
    
    def __init__(self):
        """Constructor for TelloRemote that sets up connection to Tello Drone. Does not connect automatically."""
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
        self.rc = [0, 0, 0, 0]
        self.MAX_TIME_OUT = 10  # measured in seconds
        self.rc_tick = 10
        self.waiting = False
    
    def connect(self) -> bool:
        """
        Connects to the Tello drone.
        :return: Returns true if the connection was successful, false otherwise.
        """
        self.stop = False
        self.receive_thread.start()
        if self.__connect(5):
            self.stream_on()
            return True
        return False
    
    def waiting_for_complete(self):
        """
        Checks if the drone is currently beyond rc control while completing another action.
        :return: Returns true if another action is controlling the drone, false otherwise.
        """
        return self.waiting
    
    # ======================================
    # COMMAND METHODS
    # ======================================

    def set_x(self, val: int) -> None:
        """
        Sets the x value of the rc and sends the updated value. Does not modify other rc values.
        :param val: The value to set for the x (-left/+right) value on the rc.
        :return: None
        """
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[0]:
            self.rc[0] = nv
            self.__send_rc()

    def set_y(self, val: int) -> None:
        """
        Sets the y value of the rc and sends the updated value. Does not modify other rc values.
        :param val: The value to set for the y (-backward/+forward) value on the rc.
        :return: None
        """
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[0]:
            self.rc[0] = nv
            self.__send_rc()

    def set_z(self, val: int) -> None:
        """
        Sets the z value of the rc and sends the updated value. Does not modify other rc values.
        :param val: The value to set for the z (-down/+up) value on the rc.
        :return: None
        """
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[2]:
            self.rc[2] = nv
            self.__send_rc()

    def set_rot(self, val: int) -> None:
        """
        Sets the yaw value of the rc and sends the updated value. Does not modify other rc values.
        :param val: The value to set for the yaw (-ccw/+cw) value on the rc.
        :return: None
        """
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[3]:
            self.rc[3] = nv
            self.__send_rc()

    def set_rc(self, x: int, y: int, z: int, yaw: int) -> None:
        """
        Sets all rc params to the provided values.
        :param x: The value to set for the x (-left/+right) value on the rc.
        :param y: The value to set for the y (-backward/+forward) value on the rc.
        :param z: The value to set for the z (-down/+up) value on the rc.
        :param yaw: The value to set for the x (-ccw/+cw) value on the rc.
        :return: None
        """
        nx = min(max(-100, int(x)), 100)
        ny = min(max(-100, int(y)), 100)
        nz = min(max(-100, int(z)), 100)
        nyaw = min(max(-100, int(yaw)), 100)
        if [nx, ny, nz, nyaw] != self.rc:
            self.rc = [nx, ny, nz, nyaw]
            self.__send_rc()
    
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
        res = self.__send("streamon")
        return res is not None and res == 'ok'
    
    def stream_off(self) -> bool:
        """
        Sends the Tello the command to turn off it's streaming video.
        :return: Returns true if the command succeeded, false otherwise.
        """
        res = self.__send("streamoff")
        return res is not None and res == 'ok'
    
    def close(self):
        """
        Closes the TelloRemove object and ceases communication with the Tello Drone.
        :return: None
        """
        self.stop = True
        self.send_channel.close()
        if self.receive_thread.is_alive():
            self.receive_thread.join()
    
    # ======================================
    # PRIVATE METHODS
    # ======================================
    
    def __connect(self, attempts=5) -> bool:
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
    
    def __send(self, msg) -> str | None:
        """
        A private method for sending a string message to the Tello drone.
        :param msg: The message to send.
        :return: Returns the string response from the Tello. If an error or timeout occurs returns none.
        """
        self.log.append([msg, None])
        self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
        # Response wait loop
        start = perf_counter()
        self.waiting = True
        while self.log[-1][1] is None:
            if (perf_counter() - start) > self.MAX_TIME_OUT:
                self.log[-1][1] = "TIMED OUT"
                self.waiting = False
                return None
        self.waiting = False
        return self.log[-1][1]
    
    def __send_nowait(self, msg):
        """
        A private method for sending a string message to the Tello drone, does not wait for a response.
        :param msg: The message to send.
        :return: None.
        """
        self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
        return None
    
    def __receive(self):
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
                    print("Caught exception Unicode 0xcc error.")

    def __send_rc(self) -> None:
        """
        Priovate method dedicated to sending updated rc values to the Tello Drone.
        :return: None
        """
        cmd = 'rc ' + ' '.join(map(str, self.rc))
        self.__send_nowait(cmd)