# File: tello_drone.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Purpose:
#   A basic method of controlling a Tello Drone and allowing a video feed.
#
# Notes:
#   Some code inspired/borrowed from: github.com/dji-sdk/Tello-Python/

from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import time
from datetime import datetime
import cv2


class TelloDrone:
  # Precond:
  #   The computer creating the TelloDrone instance is connected to the Tello's Wi-Fi.
  #
  # Postcond:
  #   Sets up a connection with the Tello Drone.
  def __init__(self):
    # Addresses
    self.local_addr = ('', 8889)
    self.tello_addr = ('192.168.10.1', 8889)
    
    # Setup channels
    self.send_channel = socket(AF_INET, SOCK_DGRAM)
    self.send_channel.bind(self.local_addr)
    
    # Setup receiving thread
    self.receive_thread = Thread(target=self.__receive)
    self.receive_thread.daemon = True
    self.stop = False
    self.receive_thread.start()
    
    self.log = []
    self.MAX_TIME_OUT = 10  # measured in seconds
    
    # Connecting the video
    self.video_connect_str = 'udp://192.168.10.1:11111'
    self.video_stream = None
    self.video_thread = Thread(target=self.__receive_video)
    self.video_thread.daemon = True
    self.last_frame = None
    self.stream_active = False
    self.frame_width = 0
    self.frame_height = 0
    
    # Connecting to current state information
    self.state_addr = ('192.168.10.1', 8890)
    self.local_state_addr = ('', 8890)
    self.state_channel = socket(AF_INET, SOCK_DGRAM)
    self.state_channel.bind(self.local_state_addr)
    self.last_state = None
    
    self.receive_state_thread = Thread(target=self.__receive_state)
    self.receive_state_thread.daemon = True
    self.receive_state_thread.start()
    
    # Connection/Drone Accounting
    self.pos = [0, 0, 0]  # Measured in cm, not in use
    self.yaw = 0  # The important rotation
    self.connected = False
    
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
  #   Returns False if the command could not be sent or executed for any reason.
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
  #   Returns False if the command could not be sent or executed for any reason.
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
  #   Returns False if the command could not be sent or executed for any reason.
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
  #   Returns False if the command could not be sent or executed for any reason.
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
  #   Returns False if the command could not be sent or executed for any reason.
  def move(self, x, y, z, spd):
    if not self.connected or not (20 < max(abs(x), abs(y), abs(z)) < 500) or spd not in range(10, 101):
      return False
    coord_str = ' '.join([str(x), str(y), str(z)])
    res = self.__send("go " + coord_str)
    return res is not None and res == 'ok'
  
  # ======================================
  # VIDEO METHODS
  # ======================================

  # Precond:
  #   None.
  #
  # Postcond:
  #   Turns the video stream on.
  #   Returns False if the command could not be sent or executed for any reason.
  def stream_on(self):
    if not self.connected:
      return False
    res = self.__send("streamon")
    if res is not None and res == 'ok':
      # Set up the video stream
      self.stream_active = True
      self.video_stream = cv2.VideoCapture(self.video_connect_str)
      self.video_stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
      self.frame_width = self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH)
      self.frame_height = self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
      self.video_thread.start()
      return True
    return False

  # Precond:
  #   None.
  #
  # Postcond:
  #   Turns the video stream off.
  #   Returns False if the command could not be sent or executed for any reason.
  def stream_off(self):
    if not self.connected:
      return False
    # Stop video feed if needed
    if self.stream_active:
      self.stream_active = False
      self.video_thread.join()
      self.video_stream = None
      self.last_frame = None
    res = self.__send("streamoff")
    return res is not None and res == 'ok'
  
  # Precond:
  #   None.
  #
  # Postcond:
  #   Returns the last frame taken by the Tello.
  #   Returns None if the stream is off.
  def get_frame(self):
    return self.last_frame
  
  # ======================================
  # MANAGEMENT METHODS
  # ======================================
  
  # Precond:
  #   attempts is the number of times to try and connect.
  #
  # Postcond:
  #   Checks connection to the drone by sending a message to
  #     switch the drone into SDK mode.
  #   Returns true if the connection was made.
  #   Returns false if there was a problem connecting and attempts were exceeded.
  def connect(self, attempts=5):
    for _ in range(attempts):
      res = self.__send("Command")
      if res is not None and res == 'ok':
        self.connected = True
        self.stream_on()
        return True
    return False
  
  # Precond:
  #   None.
  #
  # Postcond:
  #   Returns the last response received, if it exists.
  def last_response(self):
    if len(self.log) == 0:
      return None
    return self.log[-1][1]
  
  # Precond:
  #   None.
  #
  # Postcond:
  #   Returns the last state received from the Tello as a dictionary.
  def state(self):
    return self.last_state
  
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
  #   Closes down communication with the drone and writes the log to a file.
  def close(self):
    self.connected = False
    self.stop = True
    if self.stream_active:
      self.stream_active = False
      self.video_thread.join()
      self.last_frame = None
      self.video_stream = None
    self.send_channel.close()
    self.state_channel.close()
    self.receive_thread.join()
    self.receive_state_thread.join()
    t = datetime.now()
    log_name = t.strftime("%Y-%m-%d-%X") + '.log'
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
  #   mess is a string containing the message to send.
  #
  # Postcond:
  #   Sends the given message to the Tello.
  #   Returns the response string if the message was received.
  #   Returns None if the message failed.
  def __send(self, msg):
    self.log.append([msg, None])
    self.send_channel.sendto(msg.encode('utf-8', self.tello_addr))
    # Response wait loop
    start = time()
    while self.log[-1][1] is None:
      now = time()
      if (now-start) > self.MAX_TIME_OUT:
        self.log[-1][1] = "TIMED OUT"
        return None
    return self.log[-1][1]

  # Precond:
  #   mess is a string containing the message to send.
  #
  # Postcond:
  #   Sends the given message to the Tello.
  #   Does not wait for a response.
  #   Used (internally) only for sending the emergency signal (which is sent in triplicate.)
  def __send_nowait(self, msg):
    self.log.append([msg, None])
    self.send_channel.sendto(msg.encode('utf-8', self.tello_addr))
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
        response = response.strip()
        self.log[-1][1] = response.strip()
      except OSError as exc:
        if not self.stop:
          print("Caught exception socket.error : %s" % exc)

  # Precond:
  #   None.
  #
  # Postcond:
  #   Receives video messages from the Tello and logs them.
  def __receive_video(self):
    while not self.stop and self.stream_active:
      ret, img = self.video_stream.read()
      if ret:
        self.last_frame = img
    self.video_stream.release()
    cv2.destroyAllWindows()

  # Precond:
  #   None.
  #
  # Postcond:
  #   Receives states messages from the Tello and logs them.
  def __receive_state(self):
    while not self.stop:
      try:
        response, ip = self.state_channel.recvfrom(1024)
        response = response.decode('utf-8')
        response = response.strip()
        vals = response.split(';')
        state = {}
        for item in vals:
          if item == '':
            continue
          label, val = item.split(':')
          state[label] = val
        self.last_state = state
      except OSError as exc:
        if not self.stop:
          print("Caught exception socket.error : %s" % exc)