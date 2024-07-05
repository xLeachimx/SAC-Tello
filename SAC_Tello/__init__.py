# File: __init__.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Purpose:
# Notes:
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame as __pg
if not __pg.get_init():
    __pg.init()
from .tello_drone import TelloDrone
from .tello_hud import TelloHud
from .tello_rc import TelloRC
from .face_recognition import FaceRecognizer
from .tello_face_hud import TelloFaceHud
