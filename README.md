# SpaceBorgOne
Our code for controlling a DiddyBorg on Mars via a Raspberry Pi touchscreen.

For those who did not see us at the Raspberry Pi 4th Birthday Bash this was our challenge for controlling a Mars rover.
It consists of three scripts:
1. The Touchscreen UI, commandCentre.py:
![](screenshot.png?raw=true)
2. The robot motion script, spaceBorgOne.py:
![](we-come-in-peace.jpg?raw=true)
3. An additional set of optional controls, piborgSpaceAgency.py:
![](screenshot2.png?raw=true)

# What you need
## The robot
For the script to work as-is you will want a [DiddyBorg](https://www.piborg.org/diddyborg) with a Raspberry Pi camera attached.
It will also work with any PicoBorg Reverse based robot by changing the `spaceBorgOne.py` script slightly as explained later.
For other robots the `spaceBorgOne.py` script will need to be changed to drive the motors correctly.

You will also need:
* A Raspberry Pi camera module
* A WiFi dongle (or Raspberry Pi 3)
* The Raspberry Pi attached to a WiFi network
* The IP address of the Raspberry Pi
You can find out what your IP address is using the `ifconfig` command
It should be 4 numbers separated by dots, e.g. `192.168.0.198`
We will need this number to change the `commandCentre.py` script later, so make a note of it

## The touchscreen
You will want a Raspberry Pi with a touchscreen already setup and running.
The only other thing you will need is a connection to the same network as the robot via Ethernet or WiFi.
We recommend using Ethernet for the best results.

## Downloading the code
You will need the code on both the touchscreen Raspberry Pi and the robot.
To get the code we will clone this repository to the Raspberry Pi.
In a terminal run the following commands
```bash
cd ~
git clone https://github.com/piborg/SpaceBorgOne.git
```

# Running the scripts

## On the robot - spaceBorgOne.py
This script moves the robot around in the programmed sequence.

Before running the script we need to change `voltageIn` and `voltageOut` for the robot:
* With DiddyBorg no changes are needed
* With DiddyBorg Red Edition change to
`voltageOut = 12.0 * 0.95`
* With DiddyBorg Metal Edition change to
```voltageIn = 1.2 * 12
voltageOut = 12.0
```
* With 4Borg change to
`voltageIn = 8.4`
* For other PicoBorg Reverse robots make `voltageIn` the total battery voltage and `voltageOut` the voltage used for the motors
* Any other robots will need to replace the `PBR` lines with the correct code for controlling the motors on the robot

Additionally for 4Borg you need to swap the `PBR.SetMotor` lines so they read:
```PBR.SetMotor1(-driveLeft)
PBR.SetMotor2(driveRight)
```

You can run the script once using SSH or a keyboard by using this command:
```~/SpaceBorgOne/spaceBorgOne.py
```

To run the script when the Raspberry Pi starts add this line to `rc.local`:
```/home/pi/SpaceBorgOne/spaceBorgOne.py &
```
See [this guide](https://www.raspberrypi.org/documentation/linux/usage/rc-local.md) more more detail on how.

## On the touchscreen - commandCentre.py
This script provides the touchscreen interface for controlling your SpaceBorg robot.

Before you can use it you need to change the `REMOTE_IP` line so it matches the IP address of the robot from earlier.
For example if your robot has address `192.168.0.1` the line should be:
```REMOTE_IP = "192.168.0.1"
```

You can run the script once by using this command:
```~/SpaceBorgOne/commandCentre.py
```

To use the GUI:

1. Type a number (up-to 50) for how far you want to go
2. Press a direction (forward, backward, spin left, spin right)
3. Repeat 1 and 2 to build a sequence
4. Press the `transmit` button to send the sequence (3 second delay)

Pressing the `abort / clear` button will cancel the move and clear any commands.

By default there is a 7 minute time limit, this can be changed by altering the `TIME_LIMIT` line.

## Optional, additional controls on another machine - piborgSpaceAgency.py
This script provides an emergency off and the ability to reset the timer to start a new mission.
It is entirely optional and can be run on any machine (Windows, Mac, Linux, Raspberry Pi) with Python and Tkinter available.

For this GUI to work it needs to have `REMOTE_IP` changed to the IP address of the Raspberry Pi attached to the touchscreen.
It also needs to be on a machine connected to the same network as the robot.

Simply run the script to get a set of mission buttons and an end turn button.

Pressing the end turn button will stop the robot and show a mission failure on the touchscreen.
Pressing a mission button will send a new mission to the touchscreen and reset the timer.
The text box and the button below allow for sending custom missions.
