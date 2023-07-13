# File: face_encoder.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jun 2023
# Purpose:
#   A simple face recognition suite.
# Notes:

import pickle
from numpy import ones
from face_recognition import face_encodings, face_locations, face_distance
import cv2


class FaceEncoder:
    # Precond:
    #   encode is a string containing a file name to load a set of encodings from.
    #
    # Postcond:
    #   Creates a new FaceEncoder object loaded with encodings from a given file.
    def __init__(self, load_file=None):
        self.encodings = {}
        # Speed upgrades
        self.encode_scale = 4
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
        img = self.__scale_image(cv2.imread(img_file))
        if name not in self.encodings:
            self.encodings[name] = []
        locations = face_locations(img)
        if len(locations) > 0:
            location = locations[0]
            encoding = face_encodings(img, [location], model='large')[0]
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
        img = self.__scale_image(img)
        locations = face_locations(img)
        if len(locations) == 0:
            return []
        if len(self.encodings.keys()) == 0:
            idents = ['unknown' for i in range(len(locations))]
            locations = list(map(self.__unscale_rect, locations))
            return list(zip(idents, locations))
        encodings = face_encodings(img, locations)
        names = list(self.encodings.keys())
        distances = ones(len(names))
        idents = []
        for encoding in encodings:
            for idx, name in enumerate(names):
                distances[idx] = face_distance(self.encodings[name], encoding).mean()
            if distances.min(initial=1.0) > min_dist:
                idents.append("unknown")
            else:
                idents.append(names[distances.argmin()])
        locations = list(map(self.__unscale_rect, locations))
        return list(zip(idents, locations))

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
        
    # Precond:
    #   location is a rectangle on the resized image.
    #
    # Postcond:
    #   Returns a rectangle on the non-scaled image.
    def __unscale_rect(self, location):
        return tuple(map(lambda x: int(x * self.encode_scale), location))
    
    # Precond:
    #   img is a numpy array representing an image.
    #
    # Postcond:
    #   Returns a resized image by the encoder's scale factor.
    def __scale_image(self, img):
        height = 720 // self.encode_scale
        width = 960 // self.encode_scale
        return cv2.resize(img, (width, height))
    