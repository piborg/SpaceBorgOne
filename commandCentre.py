#!/usr/bin/env python
# coding: utf-8

# Import library functions we need 
import Tkinter
import time
import socket
import SocketServer
import threading
from cStringIO import StringIO
from PIL import Image, ImageTk
# If ImageTk fails to import run:
# sudo apt-get install python-imaging-tk

### Configuration ###
IP_TYPE = socket.AF_INET        # Base protocol type (e.g. IP4)
REMOTE_IP = "192.168.1.79"      # IP of the other system
REMOTE_PORT = 8080              # Port of the other system
LOCAL_IP = "0.0.0.0"            # IP of this system to send from (use 0.0.0.0 for all interfaces allowed)
LOCAL_PORT = REMOTE_PORT        # Local port to reserve (use 0 for auto-allocation)
TIMEOUT = 1                     # Time in seconds to block attempting network comms (0 is for non-blocking operation)
WOULD_BLOCK_HOLDOFF = 0.1       # Time in seconds to hold off if a non-blocking operation would have blocked otherwise
BUFFER_LIMIT = 2048             # Maximum buffer for receiving a single packet into
POLL_DELAY_MS = 300             # Time between updates from SpaceBorg One
MAXIMUM_MOVE = 50               # Largest allowed movement (1 unit is defined by the spaceBorgOne.py)
TRANSMISSION_LAG_MS = 3000      # Simulated lag time transmitting to Mars
TIME_LIMIT = 7 * 60             # Time that the robot remains in contact

FRAME_LAG = int(round(TRANSMISSION_LAG_MS / POLL_DELAY_MS, 0))

### Remote status ###
STATUS_WAITNG       = 0
STATUS_READY        = 1
STATUS_SENT         = 2
STATUS_RUNNING      = 3
STATUS_COMPLETE     = 4
STATUS_ABORTING     = 5
STATUS_ABORTED      = 6
STATUS_OUT_OF_RANGE = 7
global status
global waitStart
global statusText
global startTime
global running
global mainGui
status = STATUS_OUT_OF_RANGE
waitStart = False
statusText = ''
startTime = time.time() + (TRANSMISSION_LAG_MS / 1000.0)
running = True

def InstantClear():
    global status
    if status == STATUS_WAITNG:
        return True
    elif status == STATUS_READY:
        return True
    elif status == STATUS_SENT:
        return False
    elif status == STATUS_RUNNING:
        return False
    elif status == STATUS_COMPLETE:
        return True
    elif status == STATUS_ABORTING:
        return False
    elif status == STATUS_ABORTED:
        return True
    elif status == STATUS_OUT_OF_RANGE:
        return True
    else:
        return False

def SetStatus(gui, newStatus):
    global status
    global waitStart
    global statusText
    if status != newStatus:
        if newStatus == STATUS_WAITNG:
            gui.SequenceButtonsEnabled(False)
            statusText = 'Waiting for connection...'
        elif newStatus == STATUS_READY:
            gui.SequenceButtonsEnabled(True)
            statusText = 'Connected'
        elif newStatus == STATUS_SENT:
            waitStart = True
            gui.SequenceButtonsEnabled(False)
            statusText = 'Sending sequence, waiting for response...'
        elif newStatus == STATUS_RUNNING:
            waitStart = False
            gui.SequenceButtonsEnabled(False)
            statusText = 'Sequence running...'
        elif newStatus == STATUS_COMPLETE:
            waitStart = False
            gui.SequenceButtonsEnabled(True)
            gui.lstCommands.delete(0, Tkinter.END)
            statusText = 'Sequence completed'
        elif newStatus == STATUS_ABORTING:
            gui.SequenceButtonsEnabled(False)
            statusText = 'Aborting...'
        elif newStatus == STATUS_ABORTED:
            gui.SequenceButtonsEnabled(True)
            statusText = 'Sequence aborted!'
            gui.lstCommands.delete(0, Tkinter.END)
        elif newStatus == STATUS_OUT_OF_RANGE:
            SendOnly('SIGNAL-LOST')
            gui.SequenceButtonsEnabled(False)
            statusText = 'Signal to Mars lost'
        else:
            gui.SequenceButtonsEnabled(False)
            statusText += 'UNKNOWN STATE!'
        status = newStatus
        gui.title('SpaceBorg One Command Centre - ' + statusText)
        statusText = statusText.replace(', ', '\n')

def UpdateStatusFromData(gui, pc):
    global status
    global waitStart
    if status == STATUS_WAITNG:
        # We now have status, change to ready
        SetStatus(gui, STATUS_READY)
    elif status == STATUS_READY:
        # There should be nothing to do here
        pass
    elif status == STATUS_SENT:
        # Waiting for a running state
        if pc != 0:
            SetStatus(gui, STATUS_RUNNING)
    elif status == STATUS_RUNNING:
        # Waiting for a finished state
        if pc == 0:
            SetStatus(gui, STATUS_COMPLETE)
    elif status == STATUS_COMPLETE:
        # There should be nothing to do here
        pass
    elif status == STATUS_ABORTING:
        # Waiting for an aborted state
        if waitStart:
            if pc != 0:
                waitStart = False
        else:
            if pc == 0:
                SetStatus(gui, STATUS_ABORTED)
    elif status == STATUS_ABORTED:
        # There should be nothing to do here
        pass
    elif status == STATUS_OUT_OF_RANGE:
        # We are waiting for a go signal, nothing to do yet
        pass
    else:
        # Nothing we can sensibly do here!
        pass

def RemainingTime():
    global startTime
    timeTaken = time.time() - startTime
    timeLeft = TIME_LIMIT - timeTaken
    if timeLeft <= 0.0:
        return None
    else:
        timeLeft = round(timeLeft)
        minutes = int(timeLeft / 60)
        seconds = int(timeLeft % 60)
        return '%02d:%02d' % (minutes, seconds)

### Socket transmission ###
def SendAndGetReply(command):
    try:
        spaceBorgOne = socket.socket(IP_TYPE, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        spaceBorgOne.settimeout(TIMEOUT)
        spaceBorgOne.connect((REMOTE_IP, REMOTE_PORT))
        spaceBorgOne.sendto(command, (REMOTE_IP, REMOTE_PORT))
        reply = ''
        part = spaceBorgOne.recv(BUFFER_LIMIT)
        while part:
            reply += part
            part = spaceBorgOne.recv(BUFFER_LIMIT)
    except Exception, e:
        print e
        reply = 'ERROR\nCommunication failed'
    return reply

def SendOnly(command):
    try:
        spaceBorgOne = socket.socket(IP_TYPE, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        spaceBorgOne.settimeout(TIMEOUT)
        spaceBorgOne.connect((REMOTE_IP, REMOTE_PORT))
        spaceBorgOne.sendto(command, (REMOTE_IP, REMOTE_PORT))
    except Exception, e:
        print e
        reply = 'ERROR\nCommunication failed'

### Helper functions ###
def GetSize(widget):
    return (int(widget.winfo_width()), int(widget.winfo_height()))

def GetWithDefaultInt(dictionary, key, default):
    if dictionary.has_key(key):
        return int(dictionary[key])
    else:
        return int(default)

def MarsFilter(image):
    rgb2xyz = (
        #   Rin     Gin     Bin
            1.00,   0.00,   0.00,   0.00,   # Rout
            0.00,   0.50,   0.00,   0.00,   # Gout
            0.00,   0.00,   0.40,   0.00)   # Bout
    return image.convert("RGB", rgb2xyz)


# Class used to implement the TCP server
class TcpServer(SocketServer.BaseRequestHandler):
    def handle(self):
        global mainGui
        global startTime
        # Get the request data
        reqData = self.request.recv(1024).strip()
        reqParts = reqData.split('\n')
        command = reqParts[0].upper()
        print '> %s' % (reqData)
        # Handle incoming TCP command
        if command == 'MISSION':
            # New mission
            if len(reqParts) > 1:
                mainGui.mission = reqParts[1]
                
            else:
                mainGui.mission = 'Explorer the area'
            self.send(command, mainGui.mission)
            mainGui.runCommand = command
        elif command == 'ABORT':
            # Send an immediate abort from here
            SendOnly('ABORT')
            self.send(command, '')
        elif command == 'QUIT':
            # Request to terminate the GUI
            self.send(command, 'Terminating...')
            mainGui.OnExit()
        elif command == 'END TURN':
            SendOnly('ABORT')
            startTime = time.time() - TIME_LIMIT
            mainGui.mission = 'SpaceBorg One damaged!'
            mainGui.runCommand = command
        else:
            # Unexpected command
            self.send(command, '???')

    def send(self, datum, content):
        print '< %s\n%s' % (datum, content)
        self.request.sendall('%s\n%s' % (datum, content))

# Networking thread
class NetworkHandler(threading.Thread):
    def __init__(self):
        super(NetworkHandler, self).__init__()
        self.tcpServer = SocketServer.TCPServer((LOCAL_IP, LOCAL_PORT), TcpServer)
        self.tcpServer.timeout = 1.0
        self.start()

    def run(self):
        global running
        # This method runs in a separate thread
        while running:
            self.tcpServer.handle_request()

# Class representing the GUI dialog
class CommandCentre_tk(Tkinter.Tk):
    # Constructor (called when the object is first created)
    def __init__(self, parent):
        global mainGui
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.frames = []
        self.mission = 'Search for alien life'
        mainGui = self
        self.runCommand = None
        self.networkHandler = NetworkHandler()
        self.protocol("WM_DELETE_WINDOW", self.OnExit) # Call the OnExit function when user closes the dialog
        self.Initialise()

    # Initialise the dialog
    def Initialise(self):
        self.title('SpaceBorg One Command Centre')

        # Extract the animated GIF frames
        self.imgTransmit = Image.open('./Transmit.gif')
        self.gifFrames = []
        try:
            while True:
                nextFrame = Image.new('RGBA', self.imgTransmit.size)
                nextFrame.paste(self.imgTransmit, (0,0), self.imgTransmit.convert('RGBA'))
                self.gifFrames.append(nextFrame)
                self.imgTransmit.seek(self.imgTransmit.tell() + 1)
        except EOFError:
            pass

        # Set the size of the dialog
        self.resizable(False, False)
        self.geometry('800x480')
        self.attributes("-fullscreen", True)

        self.imgBlank = Image.new("RGB", (240, 180), "black")
        self.picCam = Tkinter.Canvas(self, bd = 0, highlightthickness = 0, bg = '#000')
        self.picCam.place(relx = 0.5, rely = 0.0, relwidth = 0.5, relheight = 0.625)

        self.lblStatus = Tkinter.Label(self, text = 'Waiting for signal...', justify = Tkinter.LEFT, bg = '#444', fg = '#000')
        self.lblStatus['font'] = ('Trebuchet', 12, 'bold')
        self.lblStatus.place(relx = 0.25, rely = 0.625, relwidth = 0.25, relheight = 0.375)

        self.cnvStatusLeftDrive = Tkinter.Canvas(self, bd = 2, highlightthickness = 0, bg = '#222', relief = Tkinter.SUNKEN)
        self.cnvStatusLeftDrive.place(relx = 0.8, rely = 0.625, relwidth = 0.1, relheight = 0.375)

        self.cnvStatusRightDrive = Tkinter.Canvas(self, bd = 2, highlightthickness = 0, bg = '#222', relief = Tkinter.SUNKEN)
        self.cnvStatusRightDrive.place(relx = 0.9, rely = 0.625, relwidth = 0.1, relheight = 0.375)

        self.lblRemainingTime = Tkinter.Label(self, text = 'Not in contact...', justify = Tkinter.CENTER, bg = '#666', fg = '#000')
        self.lblRemainingTime['font'] = ('Trebuchet', 12, 'bold')
        self.lblRemainingTime.place(relx = 0.5, rely = 0.625, relwidth = 0.3, relheight = 0.375)

        self.lstCommands = Tkinter.Listbox(self)
        self.lstCommands['font'] = ('Trebuchet', 12, 'bold')
        self.lstCommands.place(relx = 0.25, rely = 0.0, relwidth = 0.25, relheight = 0.625)

        sizeThird = 0.25 / 3.0
        posThird = 0.25 / 3.0
        posTwoThird = 2.0 * posThird

        self.controlButtons = []

        self.but1 = Tkinter.Button(self, text = '1', command = lambda: self.AddNumber(1))
        self.but1['font'] = ('Trebuchet', 12, 'bold')
        self.but1.place(relx = 0.0, rely = 0.0, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but1)

        self.but2 = Tkinter.Button(self, text = '2', command = lambda: self.AddNumber(2))
        self.but2['font'] = ('Trebuchet', 12, 'bold')
        self.but2.place(relx = posThird, rely = 0.0, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but2)

        self.but3 = Tkinter.Button(self, text = '3', command = lambda: self.AddNumber(3))
        self.but3['font'] = ('Trebuchet', 12, 'bold')
        self.but3.place(relx = posTwoThird, rely = 0.0, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but3)

        self.but4 = Tkinter.Button(self, text = '4', command = lambda: self.AddNumber(4))
        self.but4['font'] = ('Trebuchet', 12, 'bold')
        self.but4.place(relx = 0.0, rely = 0.1, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but4)

        self.but5 = Tkinter.Button(self, text = '5', command = lambda: self.AddNumber(5))
        self.but5['font'] = ('Trebuchet', 12, 'bold')
        self.but5.place(relx = posThird, rely = 0.1, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but5)

        self.but6 = Tkinter.Button(self, text = '6', command = lambda: self.AddNumber(6))
        self.but6['font'] = ('Trebuchet', 12, 'bold')
        self.but6.place(relx = posTwoThird, rely = 0.1, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but6)

        self.but7 = Tkinter.Button(self, text = '7', command = lambda: self.AddNumber(7))
        self.but7['font'] = ('Trebuchet', 12, 'bold')
        self.but7.place(relx = 0.0, rely = 0.2, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but7)

        self.but8 = Tkinter.Button(self, text = '8', command = lambda: self.AddNumber(8))
        self.but8['font'] = ('Trebuchet', 12, 'bold')
        self.but8.place(relx = posThird, rely = 0.2, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but8)

        self.but9 = Tkinter.Button(self, text = '9', command = lambda: self.AddNumber(9))
        self.but9['font'] = ('Trebuchet', 12, 'bold')
        self.but9.place(relx = posTwoThird, rely = 0.2, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but9)

        self.but0 = Tkinter.Button(self, text = '0', command = lambda: self.AddNumber(0))
        self.but0['font'] = ('Trebuchet', 12, 'bold')
        self.but0.place(relx = posThird, rely = 0.3, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.but0)

        self.butForward = Tkinter.Button(self, text = '↑', command = lambda: self.AddMove('FD'))
        self.butForward['font'] = ('Trebuchet', 12, 'bold')
        self.butForward.place(relx = posThird, rely = 0.45, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.butForward)

        self.butLeft = Tkinter.Button(self, text = '←', command = lambda: self.AddMove('LT'))
        self.butLeft['font'] = ('Trebuchet', 12, 'bold')
        self.butLeft.place(relx = 0.0, rely = 0.5, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.butLeft)

        self.butRight = Tkinter.Button(self, text = '→', command = lambda: self.AddMove('RT'))
        self.butRight['font'] = ('Trebuchet', 12, 'bold')
        self.butRight.place(relx = posTwoThird, rely = 0.5, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.butRight)

        self.butReverse = Tkinter.Button(self, text = '↓', command = lambda: self.AddMove('BK'))
        self.butReverse['font'] = ('Trebuchet', 12, 'bold')
        self.butReverse.place(relx = posThird, rely = 0.55, relwidth = sizeThird, relheight = 0.1)
        self.controlButtons.append(self.butReverse)

        self.butAbort = Tkinter.Button(self, text = 'Abort / clear all', command = self.butAbort_click)
        self.butAbort['font'] = ('Trebuchet', 12, 'bold')
        self.butAbort.place(relx = 0.0, rely = 0.7, relwidth = 0.25, relheight = 0.1)

        self.butSend = Tkinter.Button(self, text = 'Transmit sequence to\nSpaceBorg One', command = self.butSend_click)
        self.butSend['font'] = ('Trebuchet', 12, 'bold')
        self.butSend.place(relx = 0.0, rely = 0.85, relwidth = 0.25, relheight = 0.15)

        self.picSend = Tkinter.Canvas(self, bd = 0, highlightthickness = 0, bg='#000')

        # Set the initial state
        self.butSend['state'] = Tkinter.DISABLED
        self.butAbort['state'] = Tkinter.DISABLED
        SetStatus(self, STATUS_WAITNG)

        # Start polling
        self.after(POLL_DELAY_MS, self.Poll)

    # Polling function
    def Poll(self):
        global statusText
        startTime_ms = time.time() * 1000

        # Check for any internal signals
        if self.runCommand:
            if self.runCommand == 'END TURN':
                SetStatus(self, STATUS_ABORTED)
            elif self.runCommand == 'MISSION':
                self.MissionReceived()
            else:
                print '? %s' % (command)
            self.runCommand = None

        # Update the countdown timer
        remainingTime = RemainingTime()
        if remainingTime:
            self.lblRemainingTime['text'] = 'Mission:\n' + self.mission + '\n\n' + remainingTime + '\nuntil contact is lost'
            # Get the camera shot
            image = SendAndGetReply('CAM')
            if image[:4] == 'CAM\n':
                image = image[4:]
            else:
                image = None

            # Get the status
            status = SendAndGetReply('STATUS')
            if status[:7] == 'STATUS\n':
                status = status[7:]
            else:
                status = ''

            # Queue the data frames to represent the lag time
            self.frames.insert(0, [image, status])
            if len(self.frames) >= FRAME_LAG:
                # show the oldest frame
                frame = self.frames.pop()
            else:
                frame = None
        else:
            # Out-of-contact, do not allow further control or updates
            self.lblRemainingTime['text'] = 'Mission:\n' + self.mission + '\n\nContact has been lost!'
            SetStatus(self, STATUS_OUT_OF_RANGE)
            if len(self.frames) > 0:
                # show the oldest frame
                frame = self.frames.pop()
            else:
                frame = None

        # See if we have a frame to show
        size = GetSize(self.picCam)
        if frame:
            image = frame[0]
            status = frame[1]
            # Show the image or blank
            if image == None:
                self.imgCam = self.imgBlank.resize(size, Image.ANTIALIAS)
            else:
                file_jpgdata = StringIO(image)
                image = Image.open(file_jpgdata)
                image = image.resize(size, Image.ANTIALIAS)
                self.imgCam = MarsFilter(image)
            # Set the status displays
            dStatus = {}
            for stateLine in status.split('\n'):
                parts = stateLine.split(':')
                if len(parts) == 2:
                    dStatus[parts[0].upper()] = parts[1]
            driveLeft = GetWithDefaultInt(dStatus, 'MOTOR-L', 0)
            driveRight = GetWithDefaultInt(dStatus, 'MOTOR-R', 0)
            pc = GetWithDefaultInt(dStatus, 'PC', 0)
            counter = GetWithDefaultInt(dStatus, 'CNT', 0)
            # Draw the left motor speed
            size = GetSize(self.cnvStatusLeftDrive)
            lower = size[1] / 2
            upper = int(lower * (1.0 - (driveLeft / 100.0)))
            self.cnvStatusLeftDrive.delete('BAR')
            self.cnvStatusLeftDrive.create_rectangle(0, upper, size[0], lower, fill = '#800', width = 0, tags = 'BAR')
            # Draw the right motor speed
            size = GetSize(self.cnvStatusRightDrive)
            lower = size[1] / 2
            upper = int(lower * (1.0 - (driveRight / 100.0)))
            self.cnvStatusRightDrive.delete('BAR')
            self.cnvStatusRightDrive.create_rectangle(0, upper, size[0], lower, fill = '#800', width = 0, tags = 'BAR')
            # Highlight the program command
            self.lstCommands.select_clear(0, Tkinter.END)   
            if pc > 0:
                if pc <= self.lstCommands.size():
                    self.lstCommands.select_set(pc - 1)
                else:
                    self.lstCommands.select_set(-1)
            else:
                self.lstCommands.select_set(-1)
            # Update the system status
            UpdateStatusFromData(self, pc)
            # Set the status text
            self.lblStatus['text'] = statusText + '\n\n' + status.strip()
        else:
            self.imgCam = self.imgBlank.resize(size, Image.ANTIALIAS)
        self.itkCam = ImageTk.PhotoImage(self.imgCam)
        self.picCam.delete('IMG')
        self.picCam.create_image(0, 0, image = self.itkCam, anchor = Tkinter.NW, tags = 'IMG')
        
        # Prime the next poll
        endTime_ms = time.time() * 1000
        delay = int(POLL_DELAY_MS - (endTime_ms - startTime_ms))
        if delay < 0:
            delay = 0
        self.after(delay, self.Poll)

    # Called when the user closes the dialog
    def OnExit(self):
        global running
        running = False
        SendOnly('SIGNAL-LOST')
        self.quit()
    
    # Enables or disables the movement controls
    def SequenceButtonsEnabled(self, enabled):
        if enabled:
            newState = Tkinter.NORMAL
            self.butAbort['state'] = newState
            self.butSend['state'] = newState
        else:
            newState = Tkinter.DISABLED
        for button in self.controlButtons:
            button['state'] = newState
    
    # Transmission animation
    def AnimatedSend(self):
        waited = (time.time() - self.animStartTime) * 1000
        if waited < TRANSMISSION_LAG_MS:
            # Load the next frame
            if self.frame >= len(self.gifFrames):
                self.frame = 0
            self.imgSend = self.gifFrames[self.frame].resize(self.animSize, Image.ANTIALIAS)
            self.itkSend = ImageTk.PhotoImage(self.imgSend)
            self.picSend.delete('IMG')
            self.picSend.create_image(0, 0, image = self.itkSend, anchor = Tkinter.NW, tags = 'IMG')
            self.frame += 1
            # Wait for animation step
            delay = int(100 - ((time.time() - self.animLastFrame) * 1000))
            if delay < 0:
                delay = 0
            self.animLastFrame = time.time()
            self.after(delay, self.AnimatedSend)
        else:
            # End the animation. transmit the command
            self.picSend.place_forget()
            SendOnly(self.animCommand)

    # Start the transmission animation
    def StartAnimatedSend(self):
        # Perform animation (represents transmission lag)
        self.picSend.place(relx = 0.0, rely = 0.0, relwidth = 0.25, relheight = 1.0)
        self.animSize = (200, 480) # GetSize(self.picSend)
        self.animStartTime = time.time()
        self.animLastFrame = self.animStartTime
        self.frame = 0
        self.AnimatedSend()

    # Called when butSend is clicked
    def butSend_click(self):
        if self.lstCommands.size() == 0:
            # Nothing to send...
            self.title('SpaceBorg One Command Centre - ERROR: No movement programmed!')
        else:
            # Set the status to sending
            self.butSend['state'] = Tkinter.DISABLED
            SetStatus(self, STATUS_SENT)
            # Build the sequence to send and animate sending it
            self.animCommand = 'SEQ'
            for line in self.lstCommands.get(0, Tkinter.END):
                self.animCommand += '\n%s' % (line)
            self.animCommand += '\nqt'
            self.animSetStatus = None
            self.StartAnimatedSend()

    # Next digit for the sequence
    def AddNumber(self, number):
        # Add value here
        if self.lstCommands.size() == 0:
            # No commands added, build a new one
            cursor = str(number)
        else:
            cursor = self.lstCommands.get(Tkinter.END)
            if cursor.isdigit():
                # Only numbers, append the new one
                self.lstCommands.delete(Tkinter.END)
                cursor = cursor + str(number)
            else:
                # Has a command, build a new one
                cursor = str(number)
        self.lstCommands.insert(Tkinter.END, cursor)

    # Next movement for the sequence
    def AddMove(self, move):
        # Add command here
        if self.lstCommands.size() == 0:
            # No commands added, build a new one
            cursor = move + ' 1'
        else:
            cursor = self.lstCommands.get(Tkinter.END)
            if cursor.isdigit():
                # Only numbers, build the command from them
                value = int(cursor)
                if value > MAXIMUM_MOVE:
                    cursor = str(MAXIMUM_MOVE)
                self.lstCommands.delete(Tkinter.END)
                cursor = move + ' ' + cursor
            else:
                # Has a command, build a new one
                cursor = move + ' 1'
        self.lstCommands.insert(Tkinter.END, cursor)

    # New mission received
    def MissionReceived(self):
        global startTime
        self.lstCommands.delete(0, Tkinter.END)
        self.lblRemainingTime['text'] = self.mission + '\n\nMars is now in alignment'
        SetStatus(self, STATUS_WAITNG)
        startTime = time.time() + (TRANSMISSION_LAG_MS / 1000.0)
    
    # Called when butAbort is clicked
    def butAbort_click(self):
        if InstantClear():
            # Clear the movement sequence
            self.lstCommands.delete(0, Tkinter.END)
        else:
            # Disable the control
            self.butAbort['state'] = Tkinter.DISABLED
            # Build the command to send and animate sending it
            self.animCommand = 'ABORT'
            SetStatus(self, STATUS_ABORTING)
            self.StartAnimatedSend()

# if we are the main program (python was passed a script) load the dialog automatically
if __name__ == "__main__":
    app = CommandCentre_tk(None)
    app.mainloop()

