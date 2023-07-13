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
#       conf_q: Used by the child to send the next frame gathered from the Tello.
#
#   Commands (case insensitive) accepted:
#       halt: Stops the process and closes the management object.


from threading import Thread
from multiprocessing import Queue
from queue import Empty
from cv2 import VideoCapture
from cv2 import CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, CAP_ANY
from math import ceil


def tello_video_loop(halt_q: Queue, frame_q: Queue):
    # Create a management object.
    manager = TelloVideo()
    manager.start()
    running = True
    while running:
        try:
            if not halt_q.empty():
                halt = str(halt_q.get(False))
                if halt.lower() == 'halt':
                    break
        except Empty:
            pass
        if frame_q.empty():
            frame_q.put( manager.get())
    try:
        while not frame_q.empty():
            frame_q.get_nowait()
    except Empty:
        pass
    frame_q.close()
    manager.close()


# Class for handling receiving video frames from a Tello.
class TelloVideo:
    def __init__(self):
        # Running info
        self.last_frame = None
        self.frame_update = False

        # Connecting the video
        self.video_connect_str = 'udp://192.168.10.1:11111'
        self.video_stream = None
        self.video_thread = Thread(target=self.__receive)
        self.video_thread.daemon = True
        self.last_frame = None
        self.stream_active = True
        self.frame_width = 0
        self.frame_height = 0
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Starts the state receiving thread.
    def start(self):
        # Set up the video stream
        self.stream_active = True
        self.video_stream = VideoCapture(self.video_connect_str, CAP_ANY)
        self.frame_width = self.video_stream.get(CAP_PROP_FRAME_WIDTH)
        self.frame_height = self.video_stream.get(CAP_PROP_FRAME_HEIGHT)
        self.video_thread.start()
        self.frame_update = False
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Non-blocking function.
    #   Returns the most recent frame.
    #   If no new frame has been received then None is returned.
    def get(self):
        return self.last_frame
    
    # Precond:
    #   None.
    #
    # Postcond:
    #   Closes the threads and various channels.
    def close(self):
        self.stream_active = False
        self.video_thread.join()
        self.last_frame = None

    # Precond:
    #   None.
    #
    # Postcond:
    #   Receives video messages from the Tello.
    def __receive(self):
        while self.stream_active:
            ret, img = self.video_stream.read()
            if ret:
                self.last_frame = img
        self.video_stream.release()