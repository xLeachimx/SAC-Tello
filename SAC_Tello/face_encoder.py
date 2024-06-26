# File: face_encoder.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A simple face recognition suite.
# Notes:
# Update 26 June 2024:
#   Change from face_recognition package to using only open-cv and two models.
#   Speed improvement allows for real-time (30fps) face recognition on even moderate hardware.
#   Still not real time with minimal (R-Pi) type hardware.
#   All images are automatically resized to the Tello image size (

import pickle
from typing import Sequence

import numpy as np
import cv2 as cv
import os


class FaceEncoder:
    # Face recognition setup
    # Dim: Width, Height
    _TELLO_RES = (960, 720)
    
    _file_location = os.path.dirname(os.path.abspath(__file__))
    
    _face_detector = cv.FaceDetectorYN_create(os.path.join(_file_location,
                                                           "models",
                                                           "face_detection_yunet_2023mar.onnx"), "", _TELLO_RES)
    _face_detector.setScoreThreshold(0.87)
    _face_recognizer = cv.FaceRecognizerSF_create(os.path.join(_file_location,
                                                               "models",
                                                               "face_recognition_sface_2021dec.onnx"),"")
    _COSINE_THRESHOLD = 0.6

    # Precond:
    #   encode is a string containing a file name to load a set of encodings from.
    #
    # Postcond:
    #   Creates a new FaceEncoder object loaded with encodings from a given file.
    def __init__(self, load_file=None):
        self.encodings = {}
        if load_file is not None:
            self.load(load_file)

    # Precond:
    #   name is a string containing the name of the person whose face is being encoded.
    #   img_file is a string containing the name of a file containing an image of a single
    #       person's face.
    #
    # Postcond:
    #   Updates the encodings based on the image file.
    #   Returns False if no face was found.
    def encode_face(self, name, img_file):
        img = cv.resize(cv.imread(img_file), self._TELLO_RES)
        if name not in self.encodings:
            self.encodings[name] = []
        face_locations = self.__find_faces(img)
        if len(face_locations) > 0:
            location = face_locations[0]
            encoding = self.__encode_face(img, location)
            self.encodings[name].append(encoding)
            return True
        return False
    
    # Precond:
    #   img is a valid ndarray representing an image.
    #   min_dist is a floating point number indicating the minimal face distance (default: 0.6) for recognition.
    #
    # Postcond:
    #   Returns the most likely name of the faces in the image, paired with their locations.
    #   If no face matches within the specified distance, then it is labeled Unknown.
    #   Returned tuples are (name, location)
    def detect_faces(self, img: np.ndarray) -> list:
        img = cv.resize(img, self._TELLO_RES)
        face_locations = self.__find_faces(img)
        if len(face_locations) == 0:
            return []
        if len(self.encodings.keys()) == 0:
            idents = ['Unknown' for i in range(len(face_locations))]
            face_boxes = list(map(FaceEncoder.__extract_face_boxes, face_locations))
            return list(zip(idents, face_boxes))
        encodings = []
        for location in face_locations:
            encodings.append(self.__encode_face(img, location))
        idents = list(map(self.__match_face, encodings))
        return list(zip(idents, face_locations))

    # Precond:
    #   filename is the path to a file which contains serialized face encodings.
    #
    # Postcond:
    #   Updates the recognizers encodings using the provided file.
    # Note:
    #   No exceptions handled by this method.
    def load(self, filename):
        with open(filename, 'rb') as fin:
            loaded = pickle.load(fin)
        for person in loaded:
            if person not in self.encodings:
                self.encodings[person] = []
            self.encodings[person].extend(loaded[person])

    # Precond:
    #   filename is the path to a file to save the serialized face encodings to.
    #
    # Postcond:
    #   Saves the known face encodings to the provided file.
    # Note:
    #   No exceptions handled by this method.
    def save(self, filename):
        with open(filename, 'wb') as fout:
            pickle.dump(self.encodings, fout)
    
    def __find_faces(self, img: np.ndarray) -> list[np.ndarray]:
        """
        :param img:
            An openCV image (numpy array) in RGB format
        :return:
            Returns a list of face locations.
        """
        result = []
        height, width, _ = img.shape
        self._face_detector.setInputSize((width, height))
        try:
            _, faces = self._face_detector.detect(img)
            if len(faces) == 0:
                return result
            return faces
        except Exception as _:
            return []

    def __encode_face(self, img: np.ndarray, face_location) -> np.ndarray | None:
        """
        Encodes the face in the image at the provided location for later recognition.
        :param img:
            An openCV image (numpy array) in RGB format.
        :param face_location:
            A raw face location including the bounding box and 5-point face landmarks
        :return:
            A 128 dimensional vector representing the face.
        """
        try:
            aligned_face = self._face_recognizer.alignCrop(img, face_location)
            return self._face_recognizer.feature(aligned_face)
        except Exception as _:
            return None
    
    def __match_face(self, unknown_encoding: np.ndarray) -> str:
        best_sim = 0.0
        best_match = None
        for name, encoding in self.encodings.items():
            sim = self._face_recognizer.match(unknown_encoding, encoding, cv.FACE_RECOGNIZER_SF_FR_COSINE)
            if best_match is None or sim > best_sim:
                best_match = name
                best_sim = sim
        if best_match is None or best_sim < self._COSINE_THRESHOLD:
            return "Unknown"
        return best_match
    
    @staticmethod
    def __extract_face_boxes(raw_face_location: Sequence) -> list[int]:
        """
        Takes a raw face location (as given by the face_detector and returns the bounding box of the face.
        :param raw_face_location:
            The bounding box and 5 landmark points are returned by the face_detector.
        :return:
            The bounding box converted to integers in the order (top, left, height, width)
        """
        return list(map(int, raw_face_location))[:4]