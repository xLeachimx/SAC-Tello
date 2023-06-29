# File: face_encoder.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A simple face recognition suite.
# Notes:

import pickle
import numpy as np
import face_recognition
import cv2


class FaceEncoder:
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
        img = cv2.imread(img_file)
        if name not in self.encodings:
            self.encodings[name] = []
        location = face_recognition.face_locations(img)
        if len(location) > 0:
            location = location[0]
            encoding = face_recognition.face_encodings(img, location)[0]
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
    def detect_faces(self, img, min_dist=0.6):
        locations = face_recognition.face_locations(img)
        encodings = face_recognition.face_encodings(img, locations)
        names = list(self.encodings.keys())
        distances = np.ones(len(names))
        idents = []
        for encoding in encodings:
            for idx, name in enumerate(names):
                distances[idx] = face_recognition.face_distance(self.encodings[name], encoding).min()
            if distances.min() > min_dist:
                idents.append("unknown")
            else:
                idents.append(names[distances.argmax()])
        return zip(idents, locations)

    # Precond:
    #   filename is the path to a file which contains serialized face encodings.
    #
    # Postcond:
    #   Updates the recognizers encodings using the provided file.
    # Note:
    #   No exceptions handled by this method.
    def load(self, filename):
        loaded = {}
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
        