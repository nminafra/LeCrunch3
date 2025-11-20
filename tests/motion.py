from __future__ import print_function 
import serial
from time import sleep
import numpy as np
import logging

class motion:
    """
        Class to control the motion of the chuck at KU
        authors:    nicola.minafra@cern.ch
                    crogan@ku.edu
    """
    def __init__(self, port='COM3', timeout=0.5, emulate=False):
        self.commandIndex = 0
        self.softHome = [0,0,0]
        self.emulate = emulate
        if not self.emulate:
            self.ser = serial.Serial(port=port, baudrate=115200, timeout=timeout)
            self.ser.readline()
        self.motors = ['X', 'Y']
        self.scale = {'X': 1, 'Y' : 1, 'Z': 1}
        self.timeout = timeout

        self.maxLimit = {'X': None, 'Y' : None, 'Z': None}
        self.minLimit = {'X': None, 'Y' : None, 'Z': None}

    def sendCommand(self, command, returnImmediately=False):
        self.commandIndex = (self.commandIndex+1)%10
        command = f'{self.commandIndex}{command}\r\n'
        # print(command)

        if returnImmediately:
            return None
        if self.emulate:
            return "Emulation mode ON"

        counterOfAttempt = 0

        while (True):
            self.ser.reset_input_buffer()
            self.ser.write(command.encode())
            sleep(2*self.timeout)
            readStr = self.ser.readline().decode()
            if len(readStr)>1 and int(readStr[0]) == self.commandIndex:
                logging.debug(f'Reply: {readStr[3:-2]}')
                return readStr[3:-2]
            else:
                # print(f'Waiting for index {self.commandIndex}, received: {readStr}')
                counterOfAttempt += 1
            if counterOfAttempt > 50:
                logging.debug('No answer after {counterOfAttempt*2*self.timeout} seconds!')
            sleep(2*self.timeout)



    def moveTo(self, x=0, y=0, z=0, returnImmediately=False):
        """
			Sends to chick to the wanted position
			Returns the final position
        """
        self.commandIndex = (self.commandIndex+1)%10;
        command = f'g {x + self.softHome[0]} {y + self.softHome[1]}'
        self.sendCommand(command, returnImmediately=returnImmediately)
        if returnImmediately:   
            return None
        else:
            return self.getPosition()

    def moveFor(self, x=0, y=0, z=0, returnImmediately=False):
        """
                Moves the chuck for the wanted distance (positive or negative)
                Returns the distance traveled
        """
        positionBefore = self.getPosition()
        logging.debug(f'positionBefore: {positionBefore}')
        command = f'r {x} {y}'
        logging.debug(f'Command: {command}')
        self.sendCommand(command, returnImmediately=returnImmediately)
        if returnImmediately:
            return None
        else:
            positionNow = self.getPosition()
            logging.debug(f'positionNow: {positionNow}')
            return [positionNow[i] - positionBefore[i] for i in range(len(positionBefore))]

    def goHome(self, returnImmediately=False):
        """
                Sends to chuck to home position
        """
        self.moveTo(0,0,0,returnImmediately=returnImmediately)
        if returnImmediately:
            return None
        else:
            return self.getPosition()
    
    def setHome(self):
        """
                Sets current position as coordinate origin (home)
        """
        self.softHome = self.getPosition(absolute=True)
        return
        
    def getPosition(self, absolute=False):
        """
                Returns current position of the chuck for a given motor (if specified) or for all
        """
        
        if not self.emulate:
            readStr = self.sendCommand('p', returnImmediately=False)
            xposStr = readStr[readStr.find("X")+2:]
            xposStr = xposStr[:xposStr.find(" ")]
            xpos = float(xposStr)
            yposStr = readStr[readStr.find("Y")+2:]
            yposStr = yposStr[:yposStr.find(" ")]
            ypos = float(yposStr)
            logging.debug(f'Abs Position: {xpos} {ypos}\t Relative position: {xpos - self.softHome[0]} {ypos - self.softHome[1]}')
            if not absolute:
                xpos -= self.softHome[0]
                ypos -= self.softHome[1]
            return [xpos,ypos,0.0]
        else:
            logging.debug("Emulation mode ON")
            return [-1,-1,-1]

     
        
    # def setSafetyLimit(self, motor, min=None, max=None):
    #     motor = motor.upper()
    #     if motor not in self.motors:
    #         self.logger.error(f'Unknown motor: {motor}')
    #         return
    #     if min is not None:
    #         self.minLimit[motor] = min
    #         print(f'min set to {min} for {motor}')
    #     if max is not None:
    #         self.maxLimit[motor] = max
    #         print(f'max set to {max} for {motor}')

if __name__ == '__main__':
    m = motion()
    print(m.setHome())
    
       
    
        





