# File: tello_drive.py
# Author: Michael Huelsman
# Copyright: Dr. Michael Andrew Huelsman 2023
# License: GNU GPLv3
# Created On: 27 Jun 2023
# Purpose:
#   A program for flying a tello drone from a ground station computer.
# Notes:

from tello_drone import TelloDrone
from threading import Thread
from tello_hud import TelloHud
from time import sleep


def drive_tello():
    drone = TelloDrone()
    if not drone.start():
        print("Problem connecting.")
        return False
    hud = TelloHud(drone)
    hud.activate_hud()
    while hud.is_active():
        pass
    hud.deactivate_hud()
    drone.close()

    
if __name__ == '__main__':
    drive_tello()
    
    