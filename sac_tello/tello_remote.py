# File: tello_remote.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A class and function for handling a multi-processed rc tello controller.
# Notes:

from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter
import multiprocessing as mp
import datetime
import os


def tello_remote_loop(rc_q: mp.Queue, conf_q: mp.Queue):
    # Create a management object
    manager = TelloRemote()
    res = manager.startup()
    conf_q.put((res, 'startup'))
    if not res:
        return
    running = True
    while running:
        pass
    rc_q.close()
    manager.close()
    

class TelloRemote:
    def __init__(self):
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
        
        # Setup rc "hearbeat" thread
        self.re_beat_thread = Thread(target=self.__rc_beat)
        self.re_beat_thread.daemon = True
    
        # Setup logs
        self.log = []
        self.rc = [0, 0, 0, 0]
        self.MAX_TIME_OUT = 10  # measured in seconds
        self.rc_tick = 5
        self.waiting = False
        self.last_beat = perf_counter()
    
    def startup(self):
        self.stop = False
        self.receive_thread.start()
        self.re_beat_thread.start()
        if self.__connect(5):
            return True
        return False
    
    # ======================================
    # COMMAND METHODS
    # ======================================

    # Precond:
    #   The value to set the forward throttle to.
    #
    # Postcond:
    #   Set forward throttle.
    def set_x(self, val):
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[1]:
            self.rc[1] = nv
            self.__send_rc()

    # Precond:
    #   The value to set the right throttle to.
    #
    # Postcond:
    #   Set right throttle.
    def set_y(self, val):
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[1]:
            self.rc[0] = nv
            self.__send_rc()

    # Precond:
    #   The value to set the vertical throttle to.
    #
    # Postcond:
    #   Set vertical throttle.
    def set_z(self, val):
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[1]:
            self.rc[2] = nv
            self.__send_rc()

    # Precond:
    #   The value to set the rotation throttle to.
    #
    # Postcond:
    #   Set rotation throttle.
    def set_rot(self, val):
        nv = min(max(-100, int(val)), 100)
        if nv != self.rc[1]:
            self.rc[3] = nv
            self.__send_rc()

    # Precond:
    #   x, y, z, and rot are numberic calues indicating the rc settings.
    #
    # Postcond:
    #   Updates the rc and sends the command if anything has changed.
    def set_rc(self, x, y, z, rot):
        nx = min(max(-100, int(x)), 100)
        ny = min(max(-100, int(y)), 100)
        nz = min(max(-100, int(z)), 100)
        nrot = min(max(-100, int(rot)), 100)
        if [nx, ny, nz, nrot] != self.rc:
            self.rc = [nx, ny, nz, nrot]
            self.__send_rc()

    # Precond:
    #   None.
    #
    # Postcond
    #   Sends the takeoff command.
    #   If a non-okay response is given returns False, otherwise returns true.
    def takeoff(self):
        if not self.connected:
            return False
        res = self.__send("takeoff")
        return res is not None and res == 'ok'

    # Precond:
    #   None.
    #
    # Postcond
    #   Sends the land command.
    #   If a non-okay response is given returns False, otherwise returns true.
    def land(self):
        if not self.connected:
            return False
        res = self.__send("land")
        return res is not None and res == 'ok'

    # Precond:
    #   None.
    #
    # Postcond:
    #   Flips the drone left.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def flip_left(self):
        if not self.connected:
            return False
        res = self.__send("flip l")
        return res is not None and res == 'ok'

    # Precond:
    #   None.
    #
    # Postcond:
    #   Flips the drone right.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def flip_right(self):
        if not self.connected:
            return False
        res = self.__send("flip r")
        return res is not None and res == 'ok'

    # Precond:
    #   None.
    #
    # Postcond:
    #   Flips the drone forward.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def flip_forward(self):
        if not self.connected:
            return False
        res = self.__send("flip f")
        return res is not None and res == 'ok'

    # Precond:
    #   None.
    #
    # Postcond:
    #   Flips the drone backward.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def flip_backward(self):
        if not self.connected:
            return False
        res = self.__send("flip b")
        return res is not None and res == 'ok'
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends the emergency command, in triplicate. Does not wait for response.
    def emergency(self):
        for _ in range(3):
            self.__send_nowait("emergency")
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends a command to the Tello turning its video stream on.
    def stream_on(self):
        res = self.__send("streamon")
        return res is not None and res == 'ok'
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends a command to the Tello turing its video stream off.
    def stream_off(self):
        res = self.__send("streamoff")
        return res is not None and res == 'ok'
    
    # Precond:
    #   fldr is a string containing the path to the folder to place the log file.
    #
    # Postcond:
    #   Closes down communication with the drone and writes the log to a file.
    def close(self, fldr: str = "logs"):
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
    
    # Precond:
    #   attempts is the number of times to try and connect.
    #
    # Postcond:
    #   Checks connection to the drone by sending a message to
    #     switch the drone into SDK mode.
    #   Returns true if the connection was made.
    #   Returns false if there was a problem connecting and attempts were
    #       exceeded.
    def __connect(self, attempts=5):
        for _ in range(attempts):
            res = self.__send("command")
            if res is not None and res == 'ok':
                self.connected = True
                return True
        return False
    
    # Precond:
    #   mess is a string containing the message to send.
    #
    # Postcond:
    #   Sends the given message to the Tello.
    #   Returns the response string if the message was received.
    #   Returns None if the message failed.
    def __send(self, msg):
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
    
    # Precond:
    #   mess is a string containing the message to send.
    #
    # Postcond:
    #   Sends the given message to the Tello.
    #   Does not wait for a response.
    #   Used (internally) only for sending the emergency signal (which is sent
    #       in triplicate.)
    def __send_nowait(self, msg):
        self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
        return None
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Receives messages from the Tello and logs them.
    def __receive(self):
        while not self.stop:
            try:
                response, ip = self.send_channel.recvfrom(1024)
                response = response.decode('utf-8')
                self.log[-1][1] = response.strip()
            except OSError as exc:
                if not self.stop:
                    print("Caught exception socket.error : %s" % exc)

    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends RC messages to the tello based on internal throttle numbers.
    def __send_rc(self):
        cmd = 'rc ' + ' '.join(map(str, self.rc))
        self.last_beat = perf_counter()
        self.__send_nowait(cmd)

    # Precond:
    #   None.
    #
    # Postcond:
    #   Sends RC messages to the tello based on internal throttle numbers.
    def __rc_beat(self):
        if (perf_counter() - self.last_beat) > self.rc_tick and not self.waiting:
            cmd = 'rc ' + ' '.join(map(str, self.rc))
            self.__send_nowait(cmd)