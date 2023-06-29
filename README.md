# SAC-Tello
A simple library for controlling a DJI Tello Drone. Built for educational use.

# Dependencies

> numpy>=1.23.4
> 
> opencv-python>=4.6.0.66
> 
> face_recognition>=1.3.0
> 
> pygame>=2.2.0

### Install
SAC-Tello can be install by running the following command:
```commandline
python3 -m pip install SAC-Tell0
```
for MacOS/Linux

Or
```commandline
python -m pip install SAC-Tello
```
for Windows

# How To Use

## Tello Drone

The primary interface for the drone is the TelloDrone class.

Creating a TelloDrone object is a simple as the following:
```python
from SAC_Tello import TelloDrone
drone = TelloDrone()
``` 

A created drone object does **not** connect to the tello drone. This merely
sets up everything that needs to be in place **before** a connection is made.

To connect to the Tello, the TelloDrone class has a method called `start()`
once the Tello is connected **remember** to call the `close()` method when
done.

For example a simple takeoff and land program looks like this:
```python
from SAC_Tello import TelloDrone
drone = TelloDrone()
drone.start()
drone.takeoff()
drone.land()
drone.close()
```

The following are all commands that can be sent to the Tello:

| Command       | Method        | Arguments                        |
|---------------|---------------|----------------------------------| 
| takeoff       | takeoff       | None                             |
| land          | land          | None                             |
| up            | up            | distance: int                    |
| down          | down          | distance: int                    |
| left          | left          | distance: int                    |
| right         | right         | distance: int                    |
| forward       | forward       | distance: int                    |
| backward      | backward      | distance: int                    |
| rotate cw     | rotate_cw     | degrees: int                     |
| rotate ccw    | rotate_ccw    | degrees: int                     |
| flip left     | flip_left     | None                             |
| flip right    | flip_right    | None                             |
| flip forward  | flip_forward  | None                             |
| flip backward | flip_backward | None                             |
| move          | move          | x: int, y: int, z: int, spd: int |
| emergency     | emergency     | None                             |

## Tello Heads-up Display

As an additional feature SAC-Tello gives access to a near-real time video
stream while the Tello is connected. To make this stream more useful a
HUD was added. This HUD shows the following:
- Current Battery life
- Current Time-of-Flight sensor reading
- Artificial Horizon indicating changes in pitch rnd roll

To use the HUD simply import and create a `TelloDrone` object and link it
with a `TelloHud` object:
```python
from SAC_Tello import TelloDrone, TelloHud
drone = TelloDrone()
hud = TelloHud(drone)
drone.start()
hud.activate_hud()
hud.deactivate_hud()
drone.close()
```

The HUD will launch a separate window when activated. This window can be
closed at anytime by pressing the `X` in the upper right-hand corner.

Note: Before the HUD is activated nothing will happen. Once the HUD is
active you will need to deactivate before your program ends.