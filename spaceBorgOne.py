#!/usr/bin/env python
# coding: Latin-1

###################################################################################
# SpaceBorgOne: An example of a remote commanded robot using programmed sequences #
###################################################################################

# Import library functions we need
import PicoBorgRev
import time
import math
import sys
import threading
import SocketServer
import picamera
import picamera.array
import cv2

print 'Initialising motors'

# Global values
global PBR
global lastFrame
global lockFrame
global camera
global processor
global sequencer
global running
global sequenceAbort
global speed
global timePerUnit
running = True
sequenceAbort = False
speed = 1.0
timePerUnit = 0.2

# Setup the PicoBorg Reverse
PBR = PicoBorgRev.PicoBorgRev()
#PBR.i2cAddress = 0x44                  # Uncomment and change the value if you have changed the board address
PBR.Init()
if not PBR.foundChip:
    boards = PicoBorgRev.ScanForPicoBorgReverse()
    if len(boards) == 0:
        print 'No PicoBorg Reverse found, check you are attached :)'
    else:
        print 'No PicoBorg Reverse at address %02X, but we did find boards:' % (PBR.i2cAddress)
        for board in boards:
            print '    %02X (%d)' % (board, board)
        print 'If you need to change the I²C address change the setup line so it is correct, e.g.'
        print 'PBR.i2cAddress = 0x%02X' % (boards[0])
    sys.exit()
#PBR.SetEpoIgnore(True)                 # Uncomment to disable EPO latch, needed if you do not have a switch / jumper
PBR.SetCommsFailsafe(False)             # Disable the communications failsafe
PBR.ResetEpo()
PBR.MotorsOff()

# Camera settings
tcpPort = 8080                          # Port number for the web-page
imageWidth = 240                        # Width of the captured image in pixels
imageHeight = 180                       # Height of the captured image in pixels
frameRate = 10                          # Number of images to capture per second

# Power settings
voltageIn = 12.0                        # Total battery voltage to the PicoBorg Reverse
voltageOut = 6.0                        # Maximum motor voltage

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.start()

    def run(self):
        global lastFrame
        global lockFrame
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and save globally
                    self.stream.seek(0)
                    flippedArray = cv2.flip(self.stream.array, -1) # Flips X and Y
                    retval, thisFrame = cv2.imencode('.jpg', flippedArray)
                    del flippedArray
                    lockFrame.acquire()
                    lastFrame = thisFrame
                    lockFrame.release()
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print 'Start the stream using the video port'
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print 'Terminating camera processing...'
        processor.terminated = True
        processor.join()
        print 'Processing terminated.'

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Movement sequence thread
class SequencedMove(threading.Thread):
    def __init__(self):
        super(SequencedMove, self).__init__()
        self.pc = 0
        self.counter = 0
        self.sequence = ['EMPTY']
        self.terminated = False
        self.armed = False
        self.start()

    # Function to perform a general movement
    def PerformMove(self, driveLeft, driveRight, units):
        global PBR
        global sequenceAbort
        # Set the motors running
        PBR.SetMotor1(driveRight * maxPower)
        PBR.SetMotor2(-driveLeft * maxPower)
        # Wait for the time
        numSeconds = timePerUnit * units
        startTime = time.time()
        timeLeft = numSeconds
        while (timeLeft > 0) and (not sequenceAbort):
            if timeLeft > 1.0:
                time.sleep(1.0)
            else:
                time.sleep(timeLeft)
                break
            timeLeft = numSeconds - (time.time() - startTime)
        # Turn the motors off
        PBR.MotorsOff()

    # Function to spin for a number of units
    def PerformSpin(self, units):
        global PBR
        global speed
        if units < 0.0:
            # Left turn
            driveLeft  = -speed
            driveRight = +speed
            units *= -1
        else:
            # Right turn
            driveLeft  = +speed
            driveRight = -speed
        # Perform the motion
        self.PerformMove(driveLeft, driveRight, units * 0.6)

    # Function to drive for a number of units
    def PerformDrive(self, units):
        global PBR
        global speed
        if units < 0.0:
            # Reverse drive
            driveLeft  = -speed
            driveRight = -speed
            units *= -1
        else:
            # Forward drive
            driveLeft  = +speed
            driveRight = +speed
        # Perform the motion
        self.PerformMove(driveLeft, driveRight, units)

    # Command functions
    def Remark(self, data):
        print '### %s ###' % (data)
    def MoveForward(self, data):
        print 'Forward %s' % (data)
        self.PerformDrive(float(data))
    def MoveBackward(self, data):
        print 'Backward %s' % (data)
        self.PerformDrive(-float(data))
    def MoveLeft(self, data):
        print 'Spin left %s' % (data)
        self.PerformSpin(-float(data))
    def MoveRight(self, data):
        print 'Spin right %s' % (data)
        self.PerformSpin(float(data))
    def Delay(self, data):
        print 'Wait for %s s' % (data)
        time.sleep(float(data))
    def Goto(self, data):
        print 'Jump to instruction %s' % (data)
        self.pc = int(data) - 1
    def Quit(self, data):
        print 'End sequence'
        self.pc = self.PC_EXIT - 1
    def SetCounter(self, data):
        print 'Set counter to %s' % (data)
        self.counter = int(data)
    def DecrementCounter(self, data):
        print 'Decrement counter,',
        self.counter -= 1
        print 'now at %d' % (self.counter)
    def IncrementCounter(self, data):
        print 'Increment counter,',
        self.counter += 1
        print 'now at %d' % (self.counter)
    def DecrementJumpNotZero(self, data):
        print 'Decrement counter and jump,',
        self.counter -= 1
        print 'counter now %d' % (self.counter)
        if self.counter > 0:
            print '   Jump to instruction %s' % (data)
            self.pc = int(data) -1
    def SetSpeed(self, data):
        global speed
        speed = float(data)
        print 'Set the speed to %d %%' % (round(speed * 100, 0))

    # Decoder for assembly to command functions
    dCommands = {
            'RM':Remark,
            'FD':MoveForward,
            'BK':MoveBackward,
            'LT':MoveLeft,
            'RT':MoveRight,
            'DL':Delay,
            'GO':Goto,
            'QT':Quit,
            'SC':SetCounter,
            'DC':DecrementCounter,
            'IC':IncrementCounter,
            'DJ':DecrementJumpNotZero,
            'SP':SetSpeed,
    }
    PC_EXIT = -9
    PC_ABORT = -99

    # Main sequence running loop
    def runSequence(self, sequence):
        self.pc = 1
        self.armed = False
        while (0 < self.pc) and (self.pc < len(self.sequence)):
            # See if we need to abort
            if sequenceAbort:
                self.pc = self.PC_ABORT
                break
            else:
                command = self.sequence[self.pc]
                print '<%02d>' % (self.pc),
            # Split the command into function and data
            func = command[:2].upper()
            data = command[2:]
            # Lookup the command and run it
            if self.dCommands.has_key(func):
                func = self.dCommands[func]
                try:
                    func(self, data)
                except Exception, e:
                    print 'Failed running "%s"' % (command)
                    print '    [%s]' % (e)
                time.sleep(0.1)
            else:
                print 'Unknown command "%s"' % (command)
                time.sleep(1.0)
            # Move on to the next instruction
            self.pc += 1
        # Determine the reason execution terminated
        if self.pc > 0:
            print '[OUT OF INSTRUCTIONS]'
        elif self.pc == self.PC_EXIT:
            print '[SEQUENCE COMPLETE]'
        elif self.pc == self.PC_ABORT:
            print '[SEQUENCE ABORTED]'
        else:
            print '[EXIT DUE TO ERROR %d]' % (-self.pc)


    # Main thread idle loop
    def run(self):
        global PBR
        global sequenceAbort
        while not self.terminated:
            if sequenceAbort:
                # Abort signaled out-of-sequence, clear
                sequenceAbort = False
            elif self.armed:
                # New sequence loaded, start running
                self.runSequence(self.sequence)
                self.pc = 0
            else:
                # Nothing to do, idle
                time.sleep(1)

# Class used to implement the TCP server
class TcpServer(SocketServer.BaseRequestHandler):
    def handle(self):
        global running
        global PBR
        global lastFrame
        global sequenceAbort
        global sequencer
        # Get the request data
        reqData = self.request.recv(1024).strip()
        reqParts = reqData.split('\n')
        command = reqParts[0].upper()
        # Handle incoming TCP command
        if command == 'CAM':
            # Camera frame
            lockFrame.acquire()
            sendFrame = lastFrame
            lockFrame.release()
            if sendFrame != None:
                self.send(command, sendFrame.tostring())
        elif command == 'ABORT':
            # Abort all movements right now
            print 'Aborting all movement'
            sequenceAbort = True
            PBR.MotorsOff()
            self.send(command, '')
        elif command == 'SIGNAL-LOST':
            # Emulate a lost signal, wait a bit then cancel movement
            print 'Signal update slow...'
            time.sleep(1.0)
            print 'Signal lost...'
            sequenceAbort = True
            PBR.MotorsOff()
            self.send(command, '')
        elif command == 'SEQ':
            # Signal any current sequence to finish and wait
            print 'Waiting for sequencer to terminate...'
            sequenceAbort = True
            while sequenceAbort:
                time.sleep(0.1)
            print '    Sequencer reports finished'
            print 'Loading sequence...'
            sequencer.sequence = reqParts[:]
            sequencer.armed = True
            print '    Sequence loaded, waiting for start...'
            while sequencer.armed:
                time.sleep(0.1)
            print '    Sequence running'
            self.send(command, 'RUNNING')
        elif command == 'STATUS':
            # Status query
            powerLeft = -round((PBR.GetMotor2() / maxPower), 2)
            powerRight = round(PBR.GetMotor1() / maxPower, 2)
            status = ''
            status += 'PC:%d\n' % (sequencer.pc)
            status += 'CNT:%d\n' % (sequencer.counter)
            status += 'ABORT:%s\n' % (sequenceAbort)
            status += 'ARMED:%s\n' % (sequencer.armed)
            status += 'MOTOR-L:%d\n' % (powerLeft * 100)
            status += 'MOTOR-R:%d\n' % (powerRight * 100)
            self.send(command, status)
        elif command == 'QUIT':
            # Request to terminate operations
            print 'Terminating all operations...'
            running = False
            self.send(command, '')
        else:
            # Unexpected command
            print 'Bad command "%s"!' % (command)
            self.send('ERROR', 'Bad command "%s"' % (command))

    def send(self, datum, content):
        self.request.sendall('%s\n%s' % (datum, content))


# Create the image buffer frame
lastFrame = None
lockFrame = threading.Lock()

# Startup sequence
print 'Setup camera'
camera = picamera.PiCamera()
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate

print 'Setup the stream processing thread'
processor = StreamProcessor()

print 'Wait ...'
time.sleep(2)
captureThread = ImageCapture()

print 'Setup the movement sequencer'
sequencer = SequencedMove()

# Run the TCP server until we are told to close
try:
    tcpServer = SocketServer.TCPServer(("0.0.0.0", tcpPort), TcpServer)
except Exception, e:
    print 'Error opening socket!'
    print '    "%s"' % (e)
    running = False
PBR.SetLed(True)
try:
    print 'Press CTRL+C to terminate the TCP-server'
    while running:
        tcpServer.handle_request()
except KeyboardInterrupt:
    # CTRL+C exit
    print '\nUser shutdown'
finally:
    # Turn the motors off under all scenarios
    sequenceAbort = True
    PBR.MotorsOff()
    print 'Motors off'
# Tell each thread to stop, and wait for them to end
running = False
captureThread.join()
processor.terminated = True
sequencer.terminated = True
processor.join()
sequencer.join()
del camera
PBR.SetLed(False)
print 'TCP-server terminated.'
