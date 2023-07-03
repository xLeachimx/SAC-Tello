# File: tello_drive.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A program for testing flying a tello drone from a ground station computer.
# Notes:

from .tello_drone import TelloDrone
from .tello_rc import TelloRC
from threading import Thread
from .tello_hud import TelloHud
from time import sleep


def drive_tello():
    drone = TelloRC()
    if not drone.start():
        print("Problem connecting.")
        return False
    hud = TelloHud(drone)
    hud.activate_hud()
    drone.control()
    hud.deactivate_hud()
    drone.close()

    
if __name__ == '__main__':
    drive_tello()
    
    