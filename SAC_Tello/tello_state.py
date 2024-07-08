# File: tello_state.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 26 Jun 2023
# Purpose:
#   A class and function for managing getting the state of a Tello.
# Notes:
# Update 27 June 2024:
#   Changed to multi-threaded single process.

from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter
from datetime import datetime
import os
    

class TelloState:
    """
    Class for handling receiving and logging state information from a Tello Drone.
    """
    def __init__(self):
        """
        TelloState class constructor. Sets up connection to the Tello to listen for state information.
        """
        # Running info
        self.active = False
        self.mission_start = perf_counter()
        self.new_state = False

        # Connecting to current state information
        self.state_addr = ('192.168.10.1', 8890)
        self.local_state_addr = ('', 8890)
        self.state_channel = socket(AF_INET, SOCK_DGRAM)
        self.state_channel.bind(self.local_state_addr)
        self.state_log = []
    
        self.receive_state_thread = Thread(target=self.__receive)

    def start(self):
        """
        Starts the process of receiving state packets from the Tello drone.
        :return: None.
        """
        if not self.active:
            self.active = True
            self.mission_start = perf_counter()
            self.receive_state_thread.start()

    def get(self) -> dict | None:
        """
        Retrieves the last received states.
        :return: Returns a dictionary (str -> str) of the state values. Returns None if no state has been logged or the
        object is not actively receiving state updates.
        """
        if not self.active or len(self.state_log) == 0:
            return None
        self.new_state = False
        return self.state_log[-1][0]
    
    def has_state(self):
        """
        Method for detecting if a non-retrieved state exists.
        :return: Returns true if a state has been logged, but not retrieval calls have been made since.
        """
        return self.new_state
    
    def close(self, fldr: str = "logs"):
        """
        Closes the receiving stream and logs the data to the provided directory.
        :param fldr:
            fldr is a string containing the path to the directory where the log is to be written.
        :return:
            None.
        """
        self.active = False
        self.state_channel.close()
        self.receive_state_thread.join()
        t = datetime.now()
        log_name = os.path.join(fldr, t.strftime("%Y-%m-%d_%H-%M-%S") + '-state.log')
        if not os.path.exists(fldr):
            os.mkdir(fldr)
        with open(log_name, 'w') as fout:
            for entry in self.state_log:
                if entry[0] is None:
                    continue
                print("Mission Time(s):", round(entry[1], 3), file=fout)
                print("State:", entry[0], file=fout)

    def __receive(self):
        """
        Private method for handling (in a separate thread) receiving state information from the Tello Drone.
        :return:
            None
        """
        while self.active:
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
                state_time = perf_counter() - self.mission_start
                self.state_log.append((state, state_time))
                self.new_state = True
            except OSError as exc:
                if not self.stop:
                    print("Caught exception socket.error : %s" % exc)
                    