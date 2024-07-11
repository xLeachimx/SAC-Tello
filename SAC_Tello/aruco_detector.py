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

    _TELLO_RES = (960, 720)

    def __init__(self):
        """
        ArucoDetector class constructor
        """
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
        self.aruco_params = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
    
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
        corners, ids, rejected_points = self.detector.detectMarkers(img)
        detected_markers = []
        if len(corners) == 0:
            return detected_markers
        for location, num in zip(corners, ids):
            _, R, _ = ArucoDetector.my_estimatePoseSingleMarkers(location, self._MARKER_SIZE_CM,
                                                     self._CAMERA_PARAMETERS,
                                                     self._DISTORTION_PARAMETERS)
            distance = int(R[0][0][2])
            detected_markers.append((num[0], ArucoDetector.__convert_corners_to_rect(location), distance))
        return detected_markers

    @staticmethod
    def my_estimatePoseSingleMarkers(corners, marker_size, mtx, distortion):
        """
        This will estimate the rvec and tvec for each of the marker corners detected by:
           corners, ids, rejectedImgPoints = detector.detectMarkers(image)
        corners - is an array of detected corners for each detected marker in the image
        marker_size - is the size of the detected markers
        mtx - is the camera matrix
        distortion - is the camera distortion matrix
        RETURN list of rvecs, tvecs, and trash (so that it corresponds to the old estimatePoseSingleMarkers())
        """
        marker_points = np.array([[-marker_size / 2, marker_size / 2, 0],
                                  [marker_size / 2, marker_size / 2, 0],
                                  [marker_size / 2, -marker_size / 2, 0],
                                  [-marker_size / 2, -marker_size / 2, 0]], dtype=np.float32)
        trash = []
        rvecs = []
        tvecs = []

        for c in corners:
            nada, R, t = cv.solvePnP(marker_points, c, mtx, distortion, False, cv.SOLVEPNP_IPPE_SQUARE)
            rvecs.append(R)
            tvecs.append(t)
            trash.append(nada)
        # return rvecs, tvecs, trash
        return np.array([rvecs]), np.array([tvecs]), trash

    @staticmethod
    def __convert_corners_to_rect(location: list):
        """
        Converts a set of 4 corners to a rectangle in configuration (top, left, height, width)
        :param location: A list containing 4 coordinate pairs.
        :return: Returns the (top, left, height, width) of the given corner defined rectangle.
        """
        location = location[0]
        left = int(min(map(lambda x: x[0], location)))
        right = int(max(map(lambda x: x[0], location)))
        top = int(min(map(lambda x: x[1], location)))
        bottom = int(max(map(lambda x: x[1], location)))
        return top, left, bottom-top, right-left
        
