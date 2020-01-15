#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2016 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from can import Bus

from pyccp import ccp
from pyccp.logger import Logger


"""
The MTA number (handle) is used to identify different transfer address
locations (pointers). MTA0 is used by the commands DNLOAD, UPLOAD, DNLOAD_6,
SELECT_CAL_PAGE, CLEAR_MEMORY, PROGRAM and PROGRAM_6. MTA1 is used by the
MOVE command. See also command ‘MOVE’.
"""
MTA0_NUMBER = 0
MTA1_NUMBER = 1


class Master:
    def __init__(self, transport: Bus):
        self.slaveConnections = {}
        self._transport = transport
        self.ctr = 0x00
        self.mta0_extension = 0
        self.mta0_address = 0
        self.endianess = "big"
        self.logger = Logger("pyccp.master")

    def send(self, message):
        self._transport.send(message)
        self.ctr = (self.ctr + 1) % 0x100

    # #
    # Mandatory Commands.
    # #

    def connect(self, canID, station_address):
        # Station address is always little endian per the CCP standard
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.CONNECT,
            self.ctr,
            station_address.to_bytes(2, "little"),
        )
        self.send(cro)

    def getCCPVersion(self, canID, major=ccp.CCP_VERSION[0], minor=ccp.CCP_VERSION[1]):
        cro = ccp.CommandReceiveObject(
            canID, ccp.CommandCodes.GET_CCP_VERSION, self.ctr, [major, minor]
        )
        self.send(cro)

    def exchangeId(self, canID, device_info=0):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.EXCHANGE_ID,
            self.ctr,
            device_info.to_bytes(6, self.endianess),
        )
        self.send(cro)

    def setMta(self, canID, address, addressExtension=0x00, mta=MTA0_NUMBER):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.SET_MTA,
            self.ctr,
            [mta, addressExtension, *address.to_bytes(4, self.endianess)],
        )
        self.send(cro)

    def dnload(self, canID, size, data):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.DNLOAD,
            self.ctr,
            [size, *data.to_bytes(size, self.endianess)],
        )
        self.send(cro)

    def upload(self, canID, size):
        cro = ccp.CommandReceiveObject(canID, ccp.CommandCodes.UPLOAD, self.ctr, [size])
        self.send(cro)

    def getDaqSize(self, canID, daqListNumber, address):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.GET_DAQ_SIZE,
            self.ctr,
            [daqListNumber, 0, *address.to_bytes(4, self.endianess)],
        )
        self.send(cro)

    def setDaqPtr(self, canID, daqListNumber, odtNumber, elementNumber):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.SET_DAQ_PTR,
            self.ctr,
            [daqListNumber, odtNumber, elementNumber],
        )
        self.send(cro)

    def writeDaq(self, canID, elementSize, addressExtension, address):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.WRITE_DAQ,
            self.ctr,
            [elementSize, addressExtension, *address.to_bytes(4, self.endianess)],
        )
        self.send(cro)

    def startStop(
        self, canID, mode, daqListNumber, lastOdtNumber, eventChannel, ratePrescaler
    ):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.START_STOP,
            self.ctr,
            [
                mode,
                daqListNumber,
                lastOdtNumber,
                eventChannel,
                *ratePrescaler.to_bytes(2, self.endianess),
            ],
        )
        self.send(cro)

    def disconnect(self, canID, permanent, station_address):
        cro = ccp.CommandReceiveObject(
            canID,
            ccp.CommandCodes.DISCONNECT,
            self.ctr,
            [permanent, 0, *station_address.to_bytes(2, "little")],
        )
        self.send(cro)

    # #
    # Optional Commands
    # #

    def test(self, canID):
        raise NotImplementedError

    def dnload6(self, canID):
        raise NotImplementedError

    def shortUp(self, canID, size, address, addressExtension):
        raise NotImplementedError

    def startStopAll(self, canID):
        raise NotImplementedError

    def setSStatus(self, canID):
        raise NotImplementedError

    def getSStatus(self, canID):
        raise NotImplementedError

    def buildChksum(self, canID):
        raise NotImplementedError

    def clearMemory(self, canID):
        raise NotImplementedError

    def program(self, canID):
        raise NotImplementedError

    def program6(self, canID):
        raise NotImplementedError

    def move(self, canID):
        raise NotImplementedError

    def getActiveCalPage(self, canID):
        raise NotImplementedError

    def selectCalPage(self, canID):
        raise NotImplementedError

    def unlock(self, canID):
        raise NotImplementedError

    def getSeed(self, canID):
        raise NotImplementedError
