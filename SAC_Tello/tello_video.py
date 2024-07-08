# File: tello_state.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 26 Jun 2023
# Purpose:
#   A class and function for managing getting the state of a Tello in a separate process.
# Notes:
# Update 30 June 2024:
#   Changed to multi-threaded single process.


from threading import Thread
from cv2 import VideoCapture
from cv2 import CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, CAP_ANY
import numpy as np


class TelloVideo:
    """
    Class for handling receiving video frames from a Tello drone.
    """
    def __init__(self):
        """
        Constructor for the TelloVideo class. Does NOT connect to the Tello automatically.
        """
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
    
    def start(self):
        """
        Starts the video frame retrieval thread and sets some properties.
        :return: None
        """
        # Set up the video stream
        self.stream_active = True
        self.video_stream = VideoCapture(self.video_connect_str, CAP_ANY)
        self.frame_width = self.video_stream.get(CAP_PROP_FRAME_WIDTH)
        self.frame_height = self.video_stream.get(CAP_PROP_FRAME_HEIGHT)
        self.video_thread.start()
        self.frame_update = False
    
    def get(self) -> np.ndarray:
        """
        Gets the most recent frame from the Tello Drone.
        :return: A numpy array (openCV format BGR) containing the frame information.
        """
        self.frame_update = False
        return self.last_frame
    
    def has_frame(self):
        """
        Method for detecting if a non-retrieved frame exists.
        :return: Returns true if a frame has been logged, but not retrieval calls have been made since.
        """
        return self.frame_update
    
    def get_dimensions(self) -> tuple[int, int]:
        """
        Returns the size of the frames being retrieved.
        :return: A tuple containing the (width, height) of the frames.
        """
        return self.frame_width, self.frame_height
    
    def close(self):
        """
        Closes the receiving thread.
        :return: None
        """
        self.stream_active = False
        self.video_thread.join()
        self.last_frame = None

    def __receive(self):
        """
        Private method for gathering frames (to be run as the target of a thread.)
        :return: None
        """
        while self.stream_active:
            ret, img = self.video_stream.read()
            if ret:
                self.last_frame = img
                self.frame_update = True
        self.video_stream.release()
        