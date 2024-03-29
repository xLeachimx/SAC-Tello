# File: tello_cmd.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 26 Jun 2023
# Purpose:
#   A class and function for managing sending commands to a Tello in a separate process.
# Notes:
#   This is intended for use in a multiprocessing capacity.
#   Start by running tello_command_loop as the target of a Process object.
#
#   Two multiprocessing queues are used:
#       cmd_q: Used by the parent to send commands to the Tello.
#              Commands should be sent as a single string.
#       conf_q: Used by the child to send confirmation of completion/failure to parent.
#               Messages in queue are (boolean, string) pairs.
#               boolean indicates success/failure, string give setails.
#
#   Commands (case insensitive) accepted:
#       halt: Stops the process and closes the management object.
#       takeoff: Makes the Tello takeoff.
#       land: Makes the Tello land.
#       up <dist>: Moves the Tello up to <dist> cm above ground level.
#       down <dist>: Moves the Tello down to <dist> cm above ground level.
#       left <dist>: Moves the Tello left <dist> cm.
#       right <dist>:  Moves the Tello right <dist> cm.
#       forward <dist>:  Moves the Tello forward <dist> cm.
#       backward <dist>:  Moves the Tello backward <dist> cm.
#       rotates [cw, ccw] <deg>: Rotates the Tello <deg> degrees [cw, ccw].
#       flip [f, b, l, r]: Flips the drone in a direction ([f, b, l, r]).
#       move <x> <y> <z> <spd>: Moves the Tello by the given (x, y, z) in cm at speed spd.
#       stream [on, off]: Turns the Tello video stream [on, off].
#       emergency: send command to shut down Tello (no confirmation).

from multiprocessing import Queue
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter
from datetime import datetime
from queue import Empty
import os


def tello_command_loop(cmd_q: Queue, conf_q: Queue):
    # Create a management object
    manager = TelloCmd()
    res = manager.startup()
    conf_q.put((res, 'startup'))
    if not res:
        return
    running = True
    while running:
        try:
            cmd = str(cmd_q.get(False)).lower()
            cmd = cmd.split(' ')
            # Paring the send commands
            try:
                if cmd[0] == "halt":
                    running = False
                elif cmd[0] == "takeoff":
                    res = manager.takeoff()
                    conf_q.put((res, 'takeoff'))
                elif cmd[0] == "land":
                    res = manager.land()
                    conf_q.put((res, 'land'))
                elif cmd[0] == "up":
                    res = manager.up(int(cmd[1]))
                    conf_q.put((res, 'up'))
                elif cmd[0] == "down":
                    res = manager.down(int(cmd[1]))
                    conf_q.put((res, 'down'))
                elif cmd[0] == "left":
                    res = manager.left(int(cmd[1]))
                    conf_q.put((res, 'left'))
                elif cmd[0] == "right":
                    res = manager.right(int(cmd[1]))
                    conf_q.put((res, 'right'))
                elif cmd[0] == "forward":
                    res = manager.forward(int(cmd[1]))
                    conf_q.put((res, 'forward'))
                elif cmd[0] == "backward":
                    res = manager.backward(int(cmd[1]))
                    conf_q.put((res, 'backward'))
                elif cmd[0] == "rotate":
                    res = False
                    if cmd[1] == 'cw':
                        res = manager.rotate_cw(int(cmd[2]))
                    elif cmd[1] == 'ccw':
                        res = manager.rotate_ccw(int(cmd[2]))
                    conf_q.put((res, 'rotate ' + cmd[1]))
                elif cmd[0] == "flip":
                    res = False
                    if cmd[1] == 'f':
                        res = manager.flip_forward()
                    elif cmd[1] == 'b':
                        res = manager.flip_backward()
                    elif cmd[1] == 'l':
                        res = manager.flip_left()
                    elif cmd[1] == 'r':
                        res = manager.flip_right()
                elif cmd[0] == "go":
                    res = manager.move(int(cmd[1]),
                                       int(cmd[2]),
                                       int(cmd[3]),
                                       int(cmd[4]))
                    conf_q.put((res, 'move'))
                elif cmd[0] == "curve":
                    res = manager.curve(int(cmd[1]),
                                        int(cmd[2]),
                                        int(cmd[3]),
                                        int(cmd[4]),
                                        int(cmd[5]),
                                        int(cmd[6]),
                                        int(cmd[7]))
                    conf_q.put((res, 'curve'))
                elif cmd[0] == "stream":
                    if cmd[1] == "on":
                        res = manager.stream_on()
                        conf_q.put((res, 'stream on'))
                    elif cmd[1] == "off":
                        res = manager.stream_on()
                        conf_q.put((res, 'stream off'))
                elif cmd[0] == "emergency":
                    manager.emergency()
                    conf_q.put((True, "Emergency"))
                else:
                    conf_q.put((False, "Unknown"))
            except ValueError:
                conf_q.put((False, 'Invalid Argument'))
        except Empty:
            pass
    try:
        while not cmd_q.empty():
            cmd_q.get_nowait()
    except Empty:
        pass
    cmd_q.close()
    manager.close()
    

# Class for handling sending Tello commands and logging data.
class TelloCmd:
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
    
        # Setup logs
        self.log = []
        self.MAX_TIME_OUT = 10  # measured in seconds
        
    def startup(self):
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
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone up to val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def up(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("up " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone down to val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def down(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("down " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone right val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def right(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("right " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone left val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def left(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("left " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone forward val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def forward(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("forward " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Moves the drone backward val centimeters.
    #   Returns False if the command could not be sent for any reason.
    def backward(self, val):
        if not self.connected or val not in range(20, 501):
            return False
        res = self.__send("back " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Rotates the drone clockwise val degrees.
    #   Returns False if the command could not be sent for any reason.
    def rotate_cw(self, val):
        if not self.connected or val not in range(1, 361):
            return False
        res = self.__send("cw " + str(val))
        return res is not None and res == 'ok'

    # Precond:
    #   val is an integer representing the amount to move
    #
    # Postcond:
    #   Rotates the drone counterclockwise val degrees.
    #   Returns False if the command could not be sent for any reason.
    def rotate_ccw(self, val):
        if not self.connected or val not in range(1, 361):
            return False
        res = self.__send("ccw " + str(val))
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
    #   x the amount to move in the x-axis.
    #   y the amount to move in the y-axis.
    #   z the amount to move in the z-axis.
    #   spd is the speed of movement
    #
    # Postcond:
    #   Moves the drone by the given x, y, and z values.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def move(self, x, y, z, spd):
        if (not self.connected) or (not (20 < max(abs(x), abs(y), abs(z)) < 500)) or (spd not in range(10, 101)):
            return False
        coord_str = ' '.join([str(x), str(y), str(z), str(spd)])
        res = self.__send("go " + coord_str)
        return res is not None and res == 'ok'

    # Precond:
    #   x1 the x coordinate of the point to curve through.
    #   y1 the y coordinate of the point to curve through.
    #   z1 the z coordinate of the point to curve through.
    #   x2 the final amount to move in the x-axis.
    #   y2 the final amount to move in the y-axis.
    #   z2 the final amount to move in the z-axis.
    #   spd is the speed of movement
    #
    # Postcond:
    #   Moves the drone in a curve defined by the current and two given
    #   coordinates.
    #   Returns False if the command could not be sent or executed for any
    #       reason.
    def curve(self, x1, y1, z1, x2, y2, z2, spd):
        p1 = (x1, y1, z1)
        p2 = (x2, y2, z2)
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
        return res is not None and res =='ok'
    
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
        while self.log[-1][1] is None:
            if (perf_counter() - start) > self.MAX_TIME_OUT:
                self.log[-1][1] = "TIMED OUT"
                return None
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
            except UnicodeDecodeError as dec:
                if not self.stop:
                    self.log[-1][1] = "Decode Error"
                    print("Caught exception Unicode 0xcc error.")