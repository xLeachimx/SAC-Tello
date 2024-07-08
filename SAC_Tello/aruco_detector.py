# File: aruco_detector.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2024
# License: GNU GPLv3
# Created On: 05 Jul 2024
# Purpose:
#   A class for handling detecting aruco markers in an image.
# Notes:
#   Aligns as closely as possible with the FaceRecognizer class for simplicity of use.
#   Code adapted from that provided by Dr. Adam R. Albina

import numpy as np
import cv2 as cv
from cv2 import aruco


class ArucoDetector:
    """
    Class for detecting and recognizing Aruco markers as well as distance from the Tello Drone to them.
    """
    # Face recognition setup
    # Dim: Width, Height
    _CAMERA_PARAMETERS = np.array([[921.170702, 0.000000, 459.904354],
                                  [0.000000, 919.018377, 351.238301],
                                  [0.000000, 0.000000, 1.000000]])

    _DISTORTION_PARAMETERS = np.array([-0.033458,
                                      0.105152,
                                      0.001256,
                                      -0.006647,
                                      0.000000])
    _MARKER_SIZE_CM = 8.89

    _TELLO_RES = (1280, 720)

    def __init__(self):
        """
        ArucoDetector class constructor
        """
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_ARUCO_ORIGINAL)
        self.aruco_params = aruco.DetectorParameters_create()
    
    def detect_markers(self, img: np.ndarray) -> list:
        """
        Converts the image into a list of names and associated face locations.
        :param img:
            A valid ndarray representing an image.
        :return:
            Returns a list containing (id, location, dist) triples. Each location represents a
            rectangle (top, left, height, width.) Distance given in cm.
        """
        # convert image to gray scale for ease of use/speed.
        img = cv.cvtColor(cv.resize(img, self._TELLO_RES), cv.COLOR_BGR2GRAY)
        corners, ids, rejected_points = aruco.detectMarkers(img, self.aruco_dict, parameters=self.aruco_params)
        detected_markers = []
        for location, num in zip(corners, ids):
            pose = aruco.estimatePoseSingleMarkers(location, self._MARKER_SIZE_CM, self._CAMERA_PARAMETERS,
                                                   self._DISTORTION_PARAMETERS)
            translation = pose[1]
            distance = int(np.linalg.norm(translation))
            detected_markers.append((num, ArucoDetector.__convert_corners_to_rect(location), distance))
        return detected_markers

    @staticmethod
    def __convert_corners_to_rect(location: list[int]):
        """
        Converts a set of 4 corners to a rectangle in configuration (top, left, height, width)
        :param location: A list containing 4 coordinate pairs.
        :return: Returns the (top, left, height, width) of the given corner defined rectangle.
        """
        left = min(map(lambda x: x[0], location))
        right = max(map(lambda x: x[0], location))
        top = min(map(lambda x: x[1], location))
        bottom = max(map(lambda x: x[1], location))
        return top, left, bottom-top, right-left
        
