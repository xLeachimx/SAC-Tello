
from tello_drone import TelloDrone
from face_recognizer import FaceRecognizer
import pygame as pg
from time import perf_counter
def main():
  # setup drone and face recognition
  drone = TelloDrone()
  recog = FaceRecognizer('images')
  input("Press Enter to connect to drone.")
  # Connect to drone
  drone.connect(5)
  if not drone.connected:
    print("Trouble connecting to drone.")
    return
  print("Remaining Battery:", drone.last_state['bat'])
  # Startup pygame display
  pg.init()
  font = pg.font.SysFont(None, 24)
  display = pg.display.set_mode(drone.get_res())
  running = True
  frame_delta = 1 / 25
  frame_start = perf_counter()
  # Main loop
  while running:
    # Frame accounting
    delta = (perf_counter() - frame_start)
    if delta >= frame_delta:
      frame_start = perf_counter()
      for event in pg.event.get():
        if event.type == pg.QUIT:
          running = False
        elif event.type == pg.KEYDOWN:
          if event.key == pg.K_ESCAPE:
            running = False
      img = drone.get_frame()
      if img is not None:
        # Recognize faces from video stream
        faces = recog.recognize_faces(img)
        img = pg.image.frombuffer(img.tobytes(), img.shape[1::-1], "BGR")
        display.blit(img, (0, 0))
        # Draw boxes around each face with names
        for name, face_box in faces:
          pg_rect = pg.Rect(face_box[3], face_box[0], face_box[1]-face_box[3], face_box[2]-face_box[0])
          pg.draw.rect(display, (0,255,0), pg_rect, width=5)
          pg_text = font.render(name, True, (0,0,255))
          display.blit(pg_text, pg_rect.topleft)
        pg.display.flip()
  drone.land()
  drone.close()
  pg.quit()

if __name__ == '__main__':
  main()