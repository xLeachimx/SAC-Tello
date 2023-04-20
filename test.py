from sac_tello.tello_drone import TelloDrone
from time import sleep

def traverse(drone: TelloDrone, sides, length):
  ang = 180 - (180*(sides-2))
  for i in range(sides):
    drone.forward(length)
    drone.rotate_cw(ang)

def traverse_star(drone: TelloDrone, sides, length):
  ang = 180 - (180 * (sides - 2))
  ang = 2*ang
  for i in range(sides):
    drone.forward(length)
    drone.rotate_cw(ang)

def main():
  sides = int(input("Sides:"))
  while sides < 3:
    print("Need at leadt 3 sides.")
    sides = int(input("Sides:"))
  length = int(input("Side length:"))
  while length not in range(20, 501):
    print("Length must be between 20 and 500 (inclusive).")
    length = int(input("Side length:"))
  drone = TelloDrone()
  drone.connect()
  print("Connected.")
  drone.takeoff()
  traverse(drone, sides, length)
  drone.land()
  drone.close()


if __name__ == '__main__':
  main()