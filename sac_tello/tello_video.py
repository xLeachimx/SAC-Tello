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
import multiprocessing as mp
import cv2
import queue


def tello_video_loop(halt_q: mp.Queue, frame_q: mp.Queue):
    # Create a management object.
    manager = TelloVideo()
    manager.start()
    running = True
    while running:
        try:
            halt = str(halt_q.get(False))
            if halt.lower() == 'halt':
                break
        except queue.Empty:
            pass
        if frame_q.empty():
            frame = manager.get()
            if frame is not None:
                frame_q.put(frame)
    try:
        while not frame_q.empty():
            frame_q.get_nowait()
    except queue.Empty:
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
        self.video_stream = cv2.VideoCapture(self.video_connect_str)
        self.video_stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.frame_width = self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.frame_height = self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
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
        if self.frame_update:
            self.frame_update = False
            return self.last_frame
        return None
    
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
                self.last_frame = (img, self.frame_width, self.frame_height)
                self.frame_update = True
        self.video_stream.release()
        cv2.destroyAllWindows()