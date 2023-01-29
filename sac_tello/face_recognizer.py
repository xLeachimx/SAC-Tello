# File: face_recognizer.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 29 Jan 2023
# Purpose:
#   A simple face recognition suite.
# Notes:

import os

import face_recognition

import pickle

import numpy as np


class FaceRecognizer:
  # Precond:
  #   encode is a string of the directory where the program can find the faces to encode.
  #     if encode is a file, not a directory, an attempt will be made to de-serialize encoding data from the file.\
  #     if encode is None then no loading takes place.
  #
  # Postcond:
  #   Creates a new face recognizer trained off images in a given folder.
  def __init__(self, encode=None):
    self.encodings = {}
    if encode is not None:
      try:
        if os.path.isdir(encode):
          self.encode_directory(encode)
        elif os.path.isfile(encode):
          self.load_serialized(encode)

      except Exception as exc:
        print("Problem Loading Encodings:")
        print(exc)
        print("No encodings loaded.")
  
  # Precond:
  #   img is a valid ndarray representing an image.
  #   min_dist is a floating point number indicating the minimal face distance (default: 0.6) for recognition.
  #
  # Postcond:
  #   Returns the most likely name of the faces in the image, paired with their locations.
  #   If no face matches within the specified distance, then it is labeled Unknown.
  #   Returned tuples are (name, location)
  def recognize_faces(self, img, min_dist=0.6):
    locations = face_recognition.face_locations(img)
    encodings = face_recognition.face_encodings(img, locations)
    names = self.encodings.keys()
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
  #   face_dir is a directory with the following:
  #     1) Contains subdirectories for each individual you wish to encode.
  #     2) Each subdirectory holds JPEG files of pictures with those individuals and no others.
  #     3) Each subdirectory is named the same as the name of the person in the images.
  #
  # Postcond:
  #   Updates the recognizers encodings based on those taken from the directory.
  # Note:
  #   No exceptions handled by this method.
  def encode_directory(self, face_dir):
    contents = os.listdir(face_dir)
    dirs = []
    # Separate the image directories from files, etc.
    for filename in contents:
      if not filename.startswith(".") and os.path.isdir(filename) and not os.path.islink(filename):
        dirs.append(filename)
    # Ge to each directory and encode faces based on the images within.
    for person in dirs:
      dir_name = os.path.join(face_dir, person)
      if person not in self.encodings:
        self.encodings[person] = []
      for filename in os.listdir(dir_name):
        # Make sure not to process non-image files.
        if os.path.splitext(filename)[1] not in ['.jpg', '.JPG', '.jpeg', '.JPEG']:
          continue
        # Process a single file, assume the first detected face is the face to encode.
        filename = os.path.join(dir_name, filename)
        img = face_recognition.load_image_file(filename)
        location = face_recognition.face_locations(img)
        if len(location) > 0:
          location = location[0]
          self.encodings[person].append(face_recognition.face_encodings(img, location))
  
  # Precond:
  #   filename is the path to a file which contains serialized face encodings.
  #
  # Postcond:
  #   Updates the recognizers encodings using the provided file.
  # Note:
  #   No exceptions handled by this method.
  def load_serialized(self, filename):
    loaded = {}
    with open(filename, 'rb') as fin:
      loaded = pickle.load(fin)
    for person in loaded:
      if person not in self.encodings:
        self.encodings[person] = []
      self.encodings[person].extend(loaded[person])
        
        