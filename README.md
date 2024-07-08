# SAC-Tello
A simple library for controlling a DJI Tello Drone. Built for educational use.

# Dependencies

> numpy>=1.23.4
> 
> opencv-python>=4.6.0.66
> 
> pygame>=2.5.0

# Disclaimer

This is not official software of DJI or Ryze. All code is
given as-is. Please seek official DJI Tello resources for
additional information about the DJI Tello's technical information
and SDK.

### Install
SAC-Tello can be installed by running the following command:
```commandline
python3 -m pip install SAC-Tello
```
for MacOS/Linux

Or
```commandline
python -m pip install SAC-Tello
```
for Windows

Note: Some users may have problems installing dependencies such as `opencv-python` 
or dependencies of `SAC-Tello` dependencies. We find that
often this due to external non-python build tools being needed, for example
`opencv-python` needs C++ build tools from Visual Studio to properly install on
Windows.

# How To Use (Older version <= 0.1.1)

Since this package spawns multiple child processes any use of the package must originate from
a protected starting point (i.e. `if __name__ == __main__:`) or else a Runtime Error **will**
occur.

## Tello Drone

The primary interface for the drone is the TelloDrone class.

Creating a TelloDrone object is a simple as the following:
```python
from SAC_Tello import TelloDrone
if __name__ == '__main__':
    drone = TelloDrone()
``` 

A created drone object does **not** connect to the tello drone. This merely
sets up everything that needs to be in place **before** a connection is made.

To connect to the Tello, the TelloDrone class has a method called `start()`
once the Tello is connected **remember** to call the `close()` method when
done. The `start()` method returns `True` if the connection worked and `False`
if not.

For example a simple takeoff and land program looks like this:
```python
from SAC_Tello import TelloDrone
if __name__ == '__main__':
    drone = TelloDrone()
    drone.start()
    drone.takeoff()
    drone.land()
    drone.close()
```

The following are all commands that can be sent to the Tello:

| Command       | Method        | Arguments                                                       |
|---------------|---------------|-----------------------------------------------------------------| 
| takeoff       | takeoff       | None                                                            |
| land          | land          | None                                                            |
| up            | up            | distance: int                                                   |
| down          | down          | distance: int                                                   |
| left          | left          | distance: int                                                   |
| right         | right         | distance: int                                                   |
| forward       | forward       | distance: int                                                   |
| backward      | backward      | distance: int                                                   |
| rotate cw     | rotate_cw     | degrees: int                                                    |
| rotate ccw    | rotate_ccw    | degrees: int                                                    |
| flip left     | flip_left     | None                                                            |
| flip right    | flip_right    | None                                                            |
| flip forward  | flip_forward  | None                                                            |
| flip backward | flip_backward | None                                                            |
| go            | move          | x: int, y: int, z: int, spd: int                                |
| curve         | curve         | x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, spd: int  |
| emergency     | emergency     | None                                                            |

Commands are run in parallel to their display in the video feed. This is required to not
disturb the continuity of the video feed.

## Tello Heads-up Display

As an additional feature SAC-Tello gives access to a near-real time video
stream while the Tello is connected. To make this stream more useful a
HUD was added. This HUD shows the following:
- Current Battery life
- Current Time-of-Flight sensor reading
- Artificial Horizon indicating changes in pitch and roll

To use the HUD simply import and create a `TelloDrone` object and link it
with a `TelloHud` object:
```python
from SAC_Tello import TelloDrone, TelloHud
if __name__ == '__main__':
    drone = TelloDrone()
    hud = TelloHud(drone)
    drone.start()
    hud.activate_hud()
    hud.deactivate_hud()
    drone.close()
```

The HUD will launch a separate window when activated. This window can be
closed at anytime by pressing the `X` in the upper right-hand corner.

Pressing the `P` key while the hud is active and streaming from the Tello will
save the current frame from the Tello (this will remove all HUD elements.) The
file will be saved, as a jpeg, in the current working directory using a
UUID as its name.

Note: Before the HUD is activated nothing will happen. Once the HUD is
active you will need to deactivate before your program ends.

## Tello Face Detection

Another feature provided by SAC-Tello is access to face recognition via the
tello's camera. In order to access the face recognition we must first make
a `FaceRecognizer` object. `FaceRecognizer` objects take images and names and log
a person's facial characteristics for later comparison. To register a face
with the encoder we need to call the `encode_face` method and give it a name
and the filename of a image containing that person's face. For example:

```python
from SAC_Tello import FaceRecognizer

if __name__ == '__main__':
    face_encoder = FaceRecognizer()
    face_encoder.encode_face("Jim", "jim_selfie.jpg")
```

Once we have given all the faces we want to recognize to the `FaceRecognizer`
object we can pass in the current camera frame from the tello drone. The
example below simply lists out the names of all people detected by the drone.

```python
from SAC_Tello import FaceRecognizer
from SAC_Tello import TelloDrone

if __name__ == '__main__':
    face_encoder = FaceRecognizer()
    face_encoder.encode_face("Jim", "jim_selfie.jpg")
    drone = TelloDrone()
    drone.start()
    while drone.get_frame() is None:
        pass
    faces = face_encoder.detect_faces(drone.get_frame())
    for name, frame_location in faces:
        print(name, "is in the frame.")
    drone.close()
```

Of course this only looks at the first frame from the camera. To make it easier
to see the face recognition in action SAC-Tello provides a face recognition
version of the heads-up display. This is contained in the `TelloFaceHud` class
and works similarly to the `TelloHud` class. For example the following code
will allow for commands based control of the Tello while streaming video that
recognizes faces and displays names:

```python
from SAC_Tello import FaceRecognizer
from SAC_Tello import TelloDrone
from SAC_Tello import TelloFaceHud

if __name__ == '__main__':
    face_encoder = FaceRecognizer()
    face_encoder.encode_face("Jim", "jim_selfie.jpg")
    drone = TelloDrone()
    hud = TelloFaceHud(drone, face_encoder)
    hud.activate_hud()
    drone.takeoff()
    # insert drone flight commands here
    drone.land()
    hud.deactivate_hud()
    drone.close()
```

Since encoding faces can take a long time the `FaceRecognizer` class gives the
ability to save and load a set of encodings. Consider the following block of
code:

```python
from SAC_Tello import FaceRecognizer

if __name__ == '__main__':
    face_encoder = FaceRecognizer()
    face_encoder.encode_face("Jim", "jim_selfie.jpg")
    # Saves the encodings.
    face_encoder.save("my_encodings.enc")
    another_encoder = FaceRecognizer()
    another_encoder.load("my_encodings.enc")
```

This code saves the encodings computed in the first `FaceEndocer` object to the
file `my_encodings.enc` and then loads them into another `FaceRecognizer` object.

If you are going to encode many faces for use with the Tello we suggest you write
a separate program which encodes all the faces you desire and saves that
information to a file, then when using the Tello you load that file. This ensures
the Tello will not automatically shutdown while face encoding is happening.

Notes:
- It is best to use photos taken by the Tello itself. This helps to reduce the
potential difference in distortion, resolution, and aspect ratio from affecting
the accuracy of face recognition.
- It is possible to assign multiple images to a single name. This will increase
the accuracy of face recognition.
- It may take a long time to encode all faces and so you should encode
faces first, then use them.
- As encoding faces takes a long time, it is recommended to encode first, then
connect to the drone as encoding time may exceed the drone's auto-shutoff limit.
- If a `FaceRecognizer` object detects a face it does not recognize it will
attribute the name `unknown` to it.
- With recent update (>= version 0.1.1) detection is capable of realtime performance
30fps, with reasonable hardware.
- Face Recognition (which occurs after detection) uses a model (S-Face) which is
designed for speed of recognition, however performance degrades with number of faces
in frame and number of faces registered.
- Face recognition in this package not entirely reliable and results may vary.

## Tello Remote Control

SAC-Tello also comes with a class for using a ground station computer as
a remote control for the tello. This remote control can be combined with
the `TelloHud` class just like the `TelloDrone` class, but we will skip that
here.

To create and use the remote control simply include the following in your
program:
```python
from SAC_Tello import TelloRC
if __name__ == '__main__':
    drone = TelloRC()
    drone.start()
    drone.control()
    drone.close()
```

The `TelloRC` class has its own integrated hud system and does **not** require
creation and activation of a separate hud.

The `control()` method begins polling loop for keyboard input. The controls
are as follows:

| Key Press   | Effect                  |
|-------------|-------------------------|
| T           | Takeoff                 |
| L           | Land                    |
| ESCAPE      | Emergency Kill Switch   | 
| BACKSPACE   | End Remote Control      |
| DELETE      | Zero Velocity           |
| LEFT ARROW  | Flip Drone to the Left  |
| RIGHT ARROW | Flip Drone to the Right |
| UP ARROW    | Flip Drone Forward      |
| DOWN ARROW  | Flip Drone Backeard     |

| Key Held | Effect                      |
|----------|-----------------------------|
| W        | Increase Forward Velocity   |
| A        | Increase Leftward Velocity  |
| S        | Increase Backward Velocity  |
| D        | Increase Rightward Velocity |
| Q        | Rotate Counterclockwise     |
| E        | Rotate Clockwise            |
| R        | Increase Hover Height       |
| F        | Decrease Hover Height       |