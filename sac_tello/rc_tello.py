# File: rc_tello.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 31 Jan 2023
# Purpose:
#   A simple interface for controlling the Tello via RC commands.
# Notes:


from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import time, sleep
from datetime import datetime
import cv2

class TelloRC:
  # Precond:
  #   The computer creating the TelloRC instance is connected to the Tello's Wi-Fi.
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

    self.stop = True
    self.connected = False

    # Setup RC sending thread
    self.send_thread = Thread(target=self.__send_rc)
    self.send_thread.daemon = True

    # Setup receiving thread
    self.receive_thread = Thread(target=self.__receive)
    self.receive_thread.daemon = True

    # Setup logs
    self.log = []
    self.rc_log = []
    self.MAX_TIME_OUT = 10  # measured in seconds
    self.rc_sleep = 0.03  # how long the rc command sleeps between sends (seconds)

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

    # Set up RC accounting
    self.rc = [0, 0, 0, 30]

  def startup(self):
    self.stop = False
    self.receive_thread.start()
    if self.__connect(5) and self.stream_on():
      self.send_thread.start()
      self.receive_state_thread.start()
      return True
    return False

  # ======================================
  # COMMAND METHODS
  # ======================================
  # Section Notes:
  #   All commands check to see if the drone has been connected and put into SDK mode before sending commands.

  # Precond:
  #   The value to set the forward throttle to.
  #
  # Postcond:
  #   Set forward throttle.
  def set_x(self, val):
    self.rc[1] = min(max(-100, int(val)), 100)

  # Precond:
  #   The value to set the right throttle to.
  #
  # Postcond:
  #   Set right throttle.
  def set_y(self, val):
    self.rc[0] = min(max(-100, int(val)), 100)

  # Precond:
  #   The value to set the vertical throttle to.
  #
  # Postcond:
  #   Set vertical throttle.
  def set_z(self, val):
    self.rc[3] = min(max(-100, int(val)), 100)

  # Precond:
  #   The value to set the rotation throttle to.
  #
  # Postcond:
  #   Set rotation throttle.
  def set_rot(self, val):
    self.rc[4] = min(max(-100, int(val)), 100)

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
      if not self.stream_active:
          self.stream_active = True
          self.video_stream = cv2.VideoCapture(self.video_connect_str)
          self.video_stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
          self.frame_width = self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH)
          self.frame_height = self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
          print(self.video_stream.get(cv2.CAP_PROP_FPS))
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

  # Precond:
  #   None.
  #
  # Postcond:
  #   Returns the resolution of a frame.
  def get_res(self):
    return self.frame_width, self.frame_height

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
  def __connect(self, attempts=5):
    for _ in range(attempts):
      res = self.__send("command")
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
    self.send_channel.sendto(msg.encode('utf-8'), self.tello_addr)
    # Response wait loop
    start = time()
    while self.log[-1][1] is None:
      now = time()
      if (now - start) > self.MAX_TIME_OUT:
        self.log[-1][1] = "TIMED OUT"
        return None
    return self.log[-1][1]

  # Precond:
  #   None.
  #
  # Postcond:
  #   Sends RC messages to the tello based on internal throttle numbers.
  def __send_rc(self):
    while not self.stop:
      cmd = 'rc ' + ' '.join(map(str, self.rc))
      self.rc_log.append(cmd)
      self.__send_nowait(cmd)
      sleep(1/10)


  # Precond:
  #   mess is a string containing the message to send.
  #
  # Postcond:
  #   Sends the given message to the Tello.
  #   Does not wait for a response.
  #   Used (internally) only for sending the emergency signal (which is sent in triplicate.)
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
  #   Receives video messages from the Tello and logs them.
  def __receive_video(self):
    while not self.stop and self.stream_active:
      ret, img = self.video_stream.read()
      # print(ret)
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
