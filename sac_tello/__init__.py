# File: __init__.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 09 Jan 2023
# Purpose:
# Notes:

import os
from .tello_drone import TelloDrone
from .tello_hud import TelloHud
from .tello_rc import TelloRC
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
