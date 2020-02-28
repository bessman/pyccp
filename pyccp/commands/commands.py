# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 16:13:29 2020

@author: abemtk
"""

from typing import List

from pyccp import ccp


# #
# Mandatory Commands.
# #
class Connect:
    def __init__(self, station_address: int = 0):
        self.station_address = station_address

    def to_bytes(self) -> bytearray:
        return self.station_address.to_bytes(length=2, byteorder="little")

    def from_bytes(self, data: bytearray) -> List[int]:
        station_address = int.from_bytes(data[2:4], byteorder="little")
        return station_address

    def to_str(self) -> str:
        strings = [ccp.CommandCodes.CONNECT.name, hex(self.station_address)]
        return "  ".join(strings)


def connect(self, station_address: int):
    """
    Connect to slave specified by :param station_address. All subsequent
    commands refer to this specific slave. If a different slave is already
    connected, it will be disconnected. A connect command to an already
    connected slave is acknowledged without further action.

    Parameters
    ----------
    station_address : int
        Station address of slave ecu (little endian).

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.CONNECT,
        self.ctr,
        station_address.to_bytes(2, "little"),
    )
    self._transport.send(cro)
    self._receive()

def getCCPVersion(
    self, major: int = ccp.CCP_VERSION[0], minor: int = ccp.CCP_VERSION[1]
) -> tuple:
    """
    Send desired CCP version to slave.

    Parameters
    ----------
    major : int, optional
        Major version number. The default is ccp.CCP_VERSION[0].
    minor : int, optional
         Minor version number. The default is ccp.CCP_VERSION[1].

    Returns
    -------
    tuple
        (major, minor)

    """

    cro = CommandReceiveObject(
        self.cro_id, ccp.CommandCodes.GET_CCP_VERSION, self.ctr, [major, minor]
    )
    self._transport.send(cro)
    data = self._receive()
    return (data[0], data[1])

def exchangeId(self, device_info: int = 0) -> tuple:
    """
    Exchange ID with slave.

    Parameters
    ----------
    device_info : TYPE, optional
       Implementation specific. The default is 0.

    Returns
    -------
    tuple
        (size:         Length of slave device ID in bytes,
         dtype:        Data type qualifier of slave device ID,
         availability: Resource availability mask,
         protection:   Resource protection mask)

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.EXCHANGE_ID,
        self.ctr,
        device_info.to_bytes(6, self.endianess),
    )
    self._transport.send(cro)
    size, dtype, availability, protection, _ = self._receive()
    return (size, dtype, availability, protection)

def setMta(
    self,
    address: int,
    addressExtension: int = 0x00,
    mta: int = ccp.MemoryTransferAddressNumber.MTA0_NUMBER,
):
    """
    Set memory transfer address for subsequent data transfer.

    Parameters
    ----------
    address : int
        Memory address in slave.
    addressExtension : int, optional
        The address extension depends on the slave controller's
        organization and may identify a switchable memory bank
        or a memory segment. The default is 0x00.
    mta : int, optional
        See ccp.MemoryTransferAddressNumber. The default is
        ccp.MTA0_NUMBER.

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.SET_MTA,
        self.ctr,
        [mta, addressExtension, *address.to_bytes(4, self.endianess)],
    )
    self._transport.send(cro)
    self._receive()

def dnload(self, size: int, data: int) -> tuple:
    """
    Transfer data from master to slave. Up to five (5) bytes can be
    transferred per message. The data will be written to MTA0, after which
    MTA0 is incremented to point at the address immediately following the
    written data.

    Parameters
    ----------
    size : int
        Number of bytes to be transferred (0 - 5).
    data : int
        Data to be written to MTA0 in the slave.

    Returns
    -------
    tuple
        (mta0_ext:  Current MTA0 extension,
         mta0_addr: Current MTA0 address)

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.DNLOAD,
        self.ctr,
        [size, *data.to_bytes(size, self.endianess)],
    )
    self._transport.send(cro)
    data = self._receive()
    return (data[0], data[1:])

def upload(self, size: int) -> bytearray:
    """
    Transfer data from slave to master. Up to five (5) bytes can be
    transferred per message. The data is read starting from memory address
    MTA0, after which MTA0 is incremented to point to the address after the
    uploaded data.

    Parameters
    ----------
    size : int
        Number of bytes to be transferred (0 - 5).

    Returns
    -------
    bytearray
        <size> number of data bytes.

    """

    cro = CommandReceiveObject(
        self.cro_id, ccp.CommandCodes.UPLOAD, self.ctr, [size]
    )
    self._transport.send(cro)
    data = self._receive()
    return data[:size]

def getDaqSize(self, daqListNumber: int, dto_id: int = None) -> tuple:
    """
    Returns the size of the specified DAQ list as the number of available
    Object DescriptorTables (ODTs) and clears the current list. If the
    specified list number is not available, size = 0 should be returned.
    The DAQ list is initialized and data acquisition by this list is
    stopped.

    An individual CAN Identifier may be assigned to a DAQ list to configure
    multi ECU data acquisition. This feature is optional. If the given
    identifier isn’t possible, an error code is returned. 29 bit CAN
    identifiers are marked by the most significant bit set.

    Parameters
    ----------
    daqListNumber : int
        DESCRIPTION.
    dto_id : int
        CAN ID of the Data Transfer Object dedicated to this daqListNumber.

    Returns
    -------
    tuple
        (size: Number of Object Descriptor Tables in DAQ list,
         pid0: First PID of DAQ list)

    """

    dto_id = self.dto_id if dto_id is None else dto_id

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.GET_DAQ_SIZE,
        self.ctr,
        [daqListNumber, 0, *dto_id.to_bytes(4, self.endianess)],
    )
    self._transport.send(cro)
    data = self._receive()
    return (data[0], data[1])

def setDaqPtr(self, daqListNumber: int, odtNumber: int, elementNumber: int):
    """
    Initializes the DAQ list pointer for a subsequent write to a DAQ list.

    Parameters
    ----------
    daqListNumber : int
        DESCRIPTION.
    odtNumber : int
        DESCRIPTION.
    elementNumber : int
        DESCRIPTION.

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.SET_DAQ_PTR,
        self.ctr,
        [daqListNumber, odtNumber, elementNumber],
    )
    self._transport.send(cro)
    self._receive()

def writeDaq(self, elementSize: int, addressExtension: int, address: int):
    """
    Writes one entry (description of single DAQ element) to a DAQ list
    defined by the DAQ list pointer (see SET_DAQ_PTR). The following DAQ
    element sizes are defined: 1 byte , 2 bytes, 4 bytes.

    An ECU may not support individual address extensions for each element
    and 2 or 4 byte element sizes. It is the responsibility of the master
    device to care for the ECU limitations. The limitations may be defined
    in the slave device description file (e.g. ASAP2). It is the
    responsibility of the slave device, that all bytes of a DAQ element are
    consistent upon transmission.

    Parameters
    ----------
    elementSize : int
        Size of DAQ element in bytes (1, 2, 4).
    addressExtension : int
        Address extension of DAQ element.
    address : int
        Memory address of DAQ element in slave.

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.WRITE_DAQ,
        self.ctr,
        [elementSize, addressExtension, *address.to_bytes(4, self.endianess)],
    )
    self._transport.send(cro)
    self._receive()

def startStop(
    self,
    mode: int,
    daqListNumber: int,
    lastOdtNumber: int,
    eventChannel: int,
    ratePrescaler: int,
):
    """
    This command is used to start or to stop the data acquisition or to
    prepare a synchronized start of the specified DAQ list.

    Parameters
    ----------
    mode : int
        Must be 0, 1, or 2.
        0 stops specified DAQ list, 1 starts specified DAQ list,
        2 prepares DAQ list for synchronised start. If the slave device is
        not capable of performing the synchronized start of the data
        acquisition, the slave device may start data acquisition
        immediately.
    daqListNumber : int
        DESCRIPTION.
    lastOdtNumber : int
        Specifies which ODTs (From 0 to Last ODT number) of this DAQ list
        should be transmitted.
    eventChannel : int
        Specifies the generic signal source that effectively determines the
        data transmission timing.
    ratePrescaler : int
        To allow reduction of the desired transmission rate, a prescaler
        may be applied to the Event Channel. The prescaler value factor
        must be greater than or equal to 1.

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.START_STOP,
        self.ctr,
        [
            mode,
            daqListNumber,
            lastOdtNumber,
            eventChannel,
            *ratePrescaler.to_bytes(2, "big"),
        ],
    )
    self._transport.send(cro)
    self._receive()

def disconnect(self, permanent: int, station_address: int):
    """
    Disconnects the slave device. The disconnect can be temporary or
    permanent. Terminating the session invalidates all state information
    and resets the slave protection status.

    A temporary disconnect doesn’t stop the transmission of DAQ messages.
    The MTA values, the DAQ setup, the session status and the protection
    status are unaffected by the temporary disconnect and remain unchanged.

    Parameters
    ----------
    permanent : int
        0: temporary, 1: permanent.
    station_address : int
        Station address of slave ecu (little endian).

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id,
        ccp.CommandCodes.DISCONNECT,
        self.ctr,
        [permanent, 0, *station_address.to_bytes(2, "little")],
    )
    self._transport.send(cro)
    self._receive()

# #
# Optional Commands
# #

def test(self):
    raise NotImplementedError

def dnload6(self):
    raise NotImplementedError

def shortUp(self, size, address, addressExtension):
    raise NotImplementedError

def startStopAll(self):
    raise NotImplementedError

def setSStatus(self, status_bits: int):
    """
    Keeps the slave node informed about the current state of the
    calibration session.

    Parameters
    ----------
    status_bits : int
        0x01 CAL:     Calibration data initialized
        0x02 DAQ:     DAQ list(s) initialized
        0x04 RESUME:  Resume session after temporary disconnect
        0x08 reserved
        0x10 reserved
        0x20 reserved
        0x40 STORE:   Save calibration during device shut-down
        0x80 RUN:     Session in progress

    Returns
    -------
    None.

    """

    cro = CommandReceiveObject(
        self.cro_id, ccp.CommandCodes.SET_S_STATUS, self.ctr, [status_bits]
    )
    self._transport.send(cro)
    self._receive()

def getSStatus(self):
    raise NotImplementedError

def buildChksum(self):
    raise NotImplementedError

def clearMemory(self):
    raise NotImplementedError

def program(self):
    raise NotImplementedError

def program6(self):
    raise NotImplementedError

def move(self):
    raise NotImplementedError

def getActiveCalPage(self):
    raise NotImplementedError

def selectCalPage(self):
    raise NotImplementedError

def unlock(self):
    raise NotImplementedError

def getSeed(self):
    raise NotImplementedError


dispatcher = {
    # Mandatory Commands.
    ccp.CONNECT: connect,
    ccp.GET_CCP_VERSION: getCCPVersion,
    ccp.EXCHANGE_ID: exchangeId,
    ccp.SET_MTA: setMta,
    ccp.DNLOAD: dnload,
    ccp.UPLOAD: upload,
    ccp.GET_DAQ_SIZE: getDaqSize,
    ccp.SET_DAQ_PTR: setDaqPtr,
    ccp.WRITE_DAQ: writeDaq,
    ccp.START_STOP: startStop,
    ccp.DISCONNECT: disconnect,
    # Optional Commands.
    ccp.GET_SEED: getSeed,
    ccp.UNLOCK: unlock,
    ccp.DNLOAD_6: dnload6,
    ccp.SHORT_UP: shortUp,
    ccp.SELECT_CAL_PAGE: selectCalPage,
    ccp.SET_S_STATUS: setSStatus,
    ccp.GET_S_STATUS: getSStatus,
    ccp.BUILD_CHKSUM: buildChksum,
    ccp.CLEAR_MEMORY: clearMemory,
    ccp.PROGRAM: program,
    ccp.PROGRAM_6: program6,
    ccp.MOVE: move,
    ccp.TEST: test,
    ccp.GET_ACTIVE_CAL_PAGE: getActiveCalPage,
    ccp.START_STOP_ALL: startStopAll,
    }


def to_bytes(command_code: ccp.CommandCodes, **kwargs) -> bytearray:
    return dispatcher[command_code](**kwargs).to_bytes()


def from_bytes(data: bytearray) -> List[int]:
    command_code = data[0]
    return dispatcher[command_code]().from_bytes(data)


def to_str(command_code: ccp.CommandCodes, **kwargs) -> str:
    return dispatcher[command_code](**kwargs).to_str()
