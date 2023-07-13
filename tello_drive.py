# File: tello_drive.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A program for testing flying a tello drone from a ground station computer.
# Notes:

from SAC_Tello import TelloRC
from SAC_Tello import TelloDrone
from SAC_Tello import TelloHud
from SAC_Tello import TelloFaceHud
from SAC_Tello import FaceEncoder
from time import sleep


def drive_tello():
    encoder = FaceEncoder()
    drone = TelloDrone()
    if not drone.start():
        print("Problem connecting.")
        return False
    hud = TelloFaceHud(drone, encoder)
    hud.activate_hud()
    while hud.is_active():
        sleep(1)
    hud.deactivate_hud()
    drone.close()

    
if __name__ == '__main__':
    drive_tello()
    
    