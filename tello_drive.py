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


def drive_tello():
    drone = TelloRC()
    if not drone.start():
        print("Problem connecting.")
        return False
    drone.control()
    drone.close()

    
if __name__ == '__main__':
    drive_tello()
    
    