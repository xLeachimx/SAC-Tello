# File: tello_drone.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Purpose:
# Notes:
# Code inspired/borrowed from: github.com/dji-sdk/Tello-Python/

from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import sleep, time
from datetime import datetime

class TelloDrone:
  # Precond:
  #   The computer creating the TelloDrone instance is connected to the Tello's wifi.
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
    
    # Connection/Drone Accounting
    self.pos = [0, 0, 0]  # Measured in cm
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
  
  # ======================================
  # VIDEO METHODS
  # ======================================
  
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
  #   Sends the emergency command. Does not wait for response.
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
    self.send_channel.close()
    self.receive_thread.join()
    t = datetime.now()
    log_fname = t.strftime("%Y-%m-%d-%X") + '.log'
    with open(log_fname, 'w') as fout:
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
  