#!/usr/bin/env python
# coding: utf-8

# Import library functions we need 
import Tkinter
import socket

### Configuration ###
IP_TYPE = socket.AF_INET        # Base protocol type (e.g. IP4)
REMOTE_IP = "192.168.1.86"      # IP of the other system
REMOTE_PORT = 8080              # Port of the other system
LOCAL_IP = "0.0.0.0"            # IP of this system to send from (use 0.0.0.0 for all interfaces allowed)
LOCAL_PORT = 0                  # Local port to reserve (use 0 for auto-allocation)
TIMEOUT = 10                    # Time in seconds to block attempting network comms (0 is for non-blocking operation)
WOULD_BLOCK_HOLDOFF = 0.1       # Time in seconds to hold off if a non-blocking operation would have blocked otherwise
BUFFER_LIMIT = 2048             # Maximum buffer for receiving a single packet into

### Socket transmission ###
def SendAndGetReply(command):
    try:
        commandCenter = socket.socket(IP_TYPE, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        commandCenter.settimeout(TIMEOUT)
        commandCenter.connect((REMOTE_IP, REMOTE_PORT))
        commandCenter.sendto(command, (REMOTE_IP, REMOTE_PORT))
        reply = ''
        part = commandCenter.recv(BUFFER_LIMIT)
        while part:
            reply += part
            part = commandCenter.recv(BUFFER_LIMIT)
    except Exception, e:
        print e
        reply = 'ERROR\nCommunication failed'
    return reply

def SendOnly(command):
    try:
        commandCenter = socket.socket(IP_TYPE, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        commandCenter.settimeout(TIMEOUT)
        commandCenter.connect((REMOTE_IP, REMOTE_PORT))
        commandCenter.sendto(command, (REMOTE_IP, REMOTE_PORT))
    except Exception, e:
        print e
        reply = 'ERROR\nCommunication failed'

# Class representing the GUI dialog
class PiborgSpaceAgency_tk(Tkinter.Tk):
    # Constructor (called when the object is first created)
    def __init__(self, parent):
        global mainGui
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.OnExit) # Call the OnExit function when user closes the dialog
        self.Initialise()

    # Initialise the dialog
    def Initialise(self):
        self.title('PiBorg Space Agency')

        # Set the size of the dialog
        self.resizable(True, True)
        self.geometry('300x800')

        buttonHeight = 1.0 / 6.0

        self.butSpaceSuit = Tkinter.Button(self, text = 'Return to the launchpad', command = self.butSpaceSuit_click)
        self.butSpaceSuit['font'] = ('Trebuchet', 12, 'bold')
        self.butSpaceSuit.place(relx = 0.0, rely = 0 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)

        self.butAlien = Tkinter.Button(self, text = 'Search for alien life', command = self.butAlien_click)
        self.butAlien['font'] = ('Trebuchet', 12, 'bold')
        self.butAlien.place(relx = 0.0, rely = 1 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)

        self.butCrater = Tkinter.Button(self, text = 'Investigate the crater', command = self.butCrater_click)
        self.butCrater['font'] = ('Trebuchet', 12, 'bold')
        self.butCrater.place(relx = 0.0, rely = 2 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)

        self.txtMission = Tkinter.Entry(self)
        self.txtMission['font'] = ('Trebuchet', 12, 'bold')
        self.txtMission.insert(0, 'Boldly go ...')
        self.txtMission.place(relx = 0.0, rely = 3 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)

        self.butMission = Tkinter.Button(self, text = 'Custom Mission ↑', command = self.butMission_click)
        self.butMission['font'] = ('Trebuchet', 12, 'bold')
        self.butMission.place(relx = 0.0, rely = 4 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)

        self.butEndTurn = Tkinter.Button(self, text = 'End turn (crashed)', command = self.butEndTurn_click)
        self.butEndTurn['font'] = ('Trebuchet', 12, 'bold')
        self.butEndTurn.place(relx = 0.0, rely = 5 * buttonHeight, relwidth = 1.0, relheight = buttonHeight)
    
    # Called when butSpaceSuit is clicked
    def butSpaceSuit_click(self):
        command = 'MISSION\n%s' % (self.butSpaceSuit['text'])
        SendOnly(command)

    # Called when butAlien is clicked
    def butAlien_click(self):
        command = 'MISSION\n%s' % (self.butAlien['text'])
        SendOnly(command)
    
    # Called when butCrater is clicked
    def butCrater_click(self):
        command = 'MISSION\n%s' % (self.butCrater['text'])
        SendOnly(command)
    # Called when the user closes the dialog
    def OnExit(self):
        self.quit()

    # Called when butMission is clicked
    def butMission_click(self):
        command = 'MISSION\n%s' % (self.txtMission.get())
        SendOnly(command)

    # Called when butEndTurn is clicked
    def butEndTurn_click(self):
        SendOnly('END TURN')

# if we are the main program (python was passed a script) load the dialog automatically
if __name__ == "__main__":
    app = PiborgSpaceAgency_tk(None)
    app.mainloop()

