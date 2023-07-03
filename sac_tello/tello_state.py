# File: tello_state.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 26 Jun 2023
# Purpose:
#   A class and function for managing getting the state of a Tello in a separate process.
# Notes:
#   This is intended for use in a multiprocessing capacity.
#   Start by running tello_state_loop as the target of a Process object.
#
#   Two multiprocessing queues are used:
#       halt_q: Used by the parent to send commands to the state gatherer.
#               Commands should be sent as a single string.
#       conf_q: Used by the child to send the next state gathered from the Tello.
#
#   Commands (case insensitive) accepted:
#       halt: Stops the process and closes the management object.

from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from time import perf_counter
from datetime import datetime
import multiprocessing as mp
import queue
import os


def tello_state_loop(halt_q: mp.Queue, state_q: mp.Queue):
    # Create a management object.
    manager = TelloState()
    manager.start()
    running = True
    while running:
        try:
            halt = str(halt_q.get(False))
            if halt.lower() == 'halt':
                break
        except queue.Empty:
            pass
        if state_q.empty():
            state = manager.get()
            if state is not None:
                state_q.put(state)
    try:
        while not state_q.empty():
            state_q.get_nowait()
    except queue.Empty:
        pass
    state_q.close()
    manager.close()
    

# Class for handling receiving the state information from a Tello.
class TelloState:
    def __init__(self):
        # Running info
        self.stop = False
        self.last_grab = -1
        self.mission_start = perf_counter()

        # Connecting to current state information
        self.state_addr = ('192.168.10.1', 8890)
        self.local_state_addr = ('', 8890)
        self.state_channel = socket(AF_INET, SOCK_DGRAM)
        self.state_channel.bind(self.local_state_addr)
        self.state_log = []
    
        self.receive_state_thread = Thread(target=self.__receive)
        self.receive_state_thread.daemon = True

    # Precond:
    #   None.
    #
    # Postcond:
    #   Starts the state receiving thread.
    def start(self):
        self.mission_start = perf_counter()
        self.receive_state_thread.start()

    # Precond:
    #   None.
    #
    # Postcond:
    #   Non-blocking function.
    #   Returns the next state
    #   If no new state has been received then None is returned.
    def get(self):
        if self.last_grab + 1 < len(self.state_log):
            self.last_grab += 1
            return self.state_log[self.last_grab]
        return None
    
    # Precond:
    #   fldr is a string containing the path to the folder to place the log file..
    #
    # Postcond:
    #   Closes the threads and various channel.
    #   Writes out log data.
    def close(self, fldr: str = "logs"):
        self.stop = True
        self.state_channel.close()
        self.receive_state_thread.join()
        t = datetime.now()
        log_name = os.path.join(fldr, t.strftime("%Y-%m-%d_%H-%M-%S") + '-state.log')
        if not os.path.exists(fldr):
            os.mkdir(fldr)
        with open(log_name, 'w') as fout:
            for entry in self.state_log:
                print("Mission Time(s):", round(entry[1], 3), file=fout)
                print("State:", entry[0], file=fout)

    # Precond:
    #   None.
    #
    # Postcond:
    #   Receives states messages from the Tello and logs them.
    def __receive(self):
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
                state_time = perf_counter() - self.mission_start
                self.state_log.append((state, state_time))
            except OSError as exc:
                if not self.stop:
                    print("Caught exception socket.error : %s" % exc)
                    
                    
if __name__ == '__main__':
    mp.freeze_support()
    