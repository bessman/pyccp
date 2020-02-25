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

import can
from collections import namedtuple
import enum
from pprint import pprint
import struct


MAX_CTO = 0x0008
MAX_DTO = 0x0008

CCP_VERSION = (2, 1)


class CommandCodes(enum.IntEnum):

    # Mandatory Commands.
    CONNECT = 0x01
    GET_CCP_VERSION = 0x1B
    EXCHANGE_ID = 0x17
    SET_MTA = 0x02
    DNLOAD = 0x03
    UPLOAD = 0x04
    GET_DAQ_SIZE = 0x14
    SET_DAQ_PTR = 0x15
    WRITE_DAQ = 0x16
    START_STOP = 0x06
    DISCONNECT = 0x07
    # Optional Commands.
    GET_SEED = 0x12
    UNLOCK = 0x13
    DNLOAD_6 = 0x23
    SHORT_UP = 0x0F
    SELECT_CAL_PAGE = 0x11
    SET_S_STATUS = 0x0C
    GET_S_STATUS = 0x0D
    BUILD_CHKSUM = 0x0E
    CLEAR_MEMORY = 0x10
    PROGRAM = 0x18
    PROGRAM_6 = 0x22
    MOVE = 0x19
    TEST = 0x05
    GET_ACTIVE_CAL_PAGE = 0x09
    START_STOP_ALL = 0x08
    DIAG_SERVICE = 0x20
    ACTION_SERVICE = 0x21


class ReturnCodes(enum.IntEnum):
    ACKNOWLEDGE = 0x00
    DAQ_PROCESSOR_OVERLOAD = 0x01  # C0
    COMMAND_PROCESSOR_BUSY = 0x10  # C1 NONE (wait until ACK or timeout)
    DAQ_PROCESSOR_BUSY = 0x11  # C1 NONE (wait until ACK or timeout)
    INTERNAL_TIMEOUT = 0x12  # C1 NONE (wait until ACK or timeout)
    KEY_REQUEST = 0x18  # C1 NONE (embedded seed&key)
    SESSION_STATUS_REQUEST = 0x19  # C1 NONE (embedded SET_S_STATUS)
    COLD_START_REQUEST = 0x20  # C2 COLD START
    CAL_DATA_INIT_REQUEST = 0x21  # C2 cal. data initialization
    DAQ_LIST_INIT_REQUEST = 0x22  # C2 DAQ list initialization
    CODE_UPDATE_REQUEST = 0x23  # C2 (COLD START)
    UNKNOWN_COMMAND = 0x30  # C3 (FAULT)
    COMMAND_SYNTAX = 0x31  # C3 FAULT
    PARAMETER_OUT_OF_RANGE = 0x32  # C3 FAULT
    ACCESS_DENIED = 0x33  # C3 FAULT
    OVERLOAD = 0x34  # C3 FAULT
    ACCESS_LOCKED = 0x35  # C3 FAULT
    RESOURCE_FUNCTION_NOT_AVAILABLE = 0x36  # C3 FAULT


class MemoryTransferAddressNumber(enum.IntEnum):
    """
    The MTA number (handle) is used to identify different transfer address
    locations (pointers). MTA0 is used by the commands DNLOAD, UPLOAD, DNLOAD_6,
    SELECT_CAL_PAGE, CLEAR_MEMORY, PROGRAM and PROGRAM_6. MTA1 is used by the
    MOVE command. See also command ‘MOVE’.
    """

    MTA0_NUMBER = 0
    MTA1_NUMBER = 1


class DTOType(enum.IntEnum):
    COMMAND_RETURN_MESSAGE = 0xFF
    EVENT_MESSAGE = 0xFE


class State(enum.IntEnum):
    pass


class CommandReceiveObject(can.Message):
    """Command Receive Object.
    """

    def __init__(
        self,
        arbitration_id,
        command_code,
        ctr,
        cro_data,
        timestamp=0,
        channel=None,
        is_extended_id=True,
    ):
        self.command_code = command_code
        self.ctr = ctr
        self.cro_data = cro_data
        data = [command_code, ctr] + list(cro_data)
        # Pad data array to eight bytes
        data = data + [0] * (8 - len(data))
        if len(data) > 8:
            raise ValueError("CRO data must be six bytes or fewer")

        super().__init__(
            arbitration_id=arbitration_id,
            data=data,
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __get_bytes(self, start, length, byteorder="big"):
        return hex(
            int.from_bytes(self.cro_data[start : start + length], byteorder=byteorder)
        )

    def parse(self):
        field_strings = [CommandCodes(self.command_code).name]

        if self.command_code == CommandCodes.ACTION_SERVICE:
            action_service_number = self.__get_bytes(0, 2)
            field_strings.append(action_service_number)
            parameters = self.__get_bytes(2, 4)

            if parameters != "0x0":
                field_strings.append(parameters)

        elif self.command_code == CommandCodes.BUILD_CHKSUM:
            block_size = self.__get_bytes(0, 4)
            field_strings.append(block_size)
        elif self.command_code == CommandCodes.CLEAR_MEMORY:
            memory_size = self.__get_bytes(0, 4)
            field_strings.append(memory_size)
        elif self.command_code == CommandCodes.CONNECT:
            station_address = self.__get_bytes(0, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == CommandCodes.DIAG_SERVICE:
            diagnostic_service_number = self.__get_bytes(0, 2)
            field_strings.append(diagnostic_service_number)
            parameters = self.__get_bytes(2, 4)

            if parameters != "0x0":
                field_strings.append(parameters)

        elif self.command_code == CommandCodes.DISCONNECT:
            permanence = self.__get_bytes(0, 1)
            field_strings.append(permanence)
            station_address = self.__get_bytes(2, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == CommandCodes.DNLOAD:
            data_size = self.__get_bytes(0, 1)
            field_strings.append(data_size)
            data = self.__get_bytes(1, 5)
            field_strings.append(data)
        elif self.command_code == CommandCodes.DNLOAD_6:
            data = self.__get_bytes(0, 6)
            field_strings.append(data)
        elif self.command_code == CommandCodes.EXCHANGE_ID:
            device_info = self.__get_bytes(0, 6)

            if device_info != "0x0":
                field_strings.append(device_info)

        elif self.command_code == CommandCodes.GET_ACTIVE_CAL_PAGE:
            pass
        elif self.command_code == CommandCodes.GET_CCP_VERSION:
            main = self.__get_bytes(0, 1)
            field_strings.append(main)
            release = self.__get_bytes(1, 1)
            field_strings.append(release)
        elif self.command_code == CommandCodes.GET_DAQ_SIZE:
            daq_no = self.__get_bytes(0, 1)
            field_strings.append(daq_no)
            dto_id = self.__get_bytes(2, 4)
            field_strings.append(dto_id)
        elif self.command_code == CommandCodes.GET_SEED:
            resource_mask = self.__get_bytes(0, 1)
            field_strings.append(resource_mask)
        elif self.command_code == CommandCodes.GET_S_STATUS:
            pass
        elif self.command_code == CommandCodes.MOVE:
            data_size = self.__get_bytes(0, 4)
            field_strings.append(data_size)
        elif self.command_code == CommandCodes.PROGRAM:
            data_size = self.__get_bytes(0, 1)
            field_strings.append(data_size)
            data = self.__get_bytes(1, 5)
            field_strings.append(data)
        elif self.command_code == CommandCodes.PROGRAM_6:
            data = self.__get_bytes(0, 6)
            field_strings.append(data)
        elif self.command_code == CommandCodes.SELECT_CAL_PAGE:
            pass
        elif self.command_code == CommandCodes.SET_DAQ_PTR:
            daq_list_no = self.__get_bytes(0, 1)
            field_strings.append(daq_list_no)
            odt_no = self.__get_bytes(1, 1)
            field_strings.append(odt_no)
            element_no = self.__get_bytes(2, 1)
            field_strings.append(element_no)
        elif self.command_code == CommandCodes.SET_MTA:
            mta_number = self.__get_bytes(0, 1)
            field_strings.append(mta_number)
            address_extension = self.__get_bytes(1, 1)
            field_strings.append(address_extension)
            address = self.__get_bytes(2, 4)
            field_strings.append(address)
        elif self.command_code == CommandCodes.SET_S_STATUS:
            status_bits = self.__get_bytes(0, 1)
            field_strings.append(status_bits)
        elif self.command_code == CommandCodes.SHORT_UP:
            data_size = self.__get_bytes(0, 1)
            field_strings.append(data_size)
            address_extension = self.__get_bytes(1, 1)
            field_strings.append(address_extension)
            address = self.__get_bytes(2, 4)
            field_strings.append(address)
        elif self.command_code == CommandCodes.START_STOP:
            mode = self.__get_bytes(0, 1)
            field_strings.append(mode)
            daq_list_number = self.__get_bytes(1, 1)
            field_strings.append(daq_list_number)
            last_odt_number = self.__get_bytes(2, 1)
            field_strings.append(last_odt_number)
            event_channel_number = self.__get_bytes(3, 1)
            field_strings.append(event_channel_number)
            transmission_rate_prescaler = self.__get_bytes(4, 2)
            field_strings.append(transmission_rate_prescaler)
        elif self.command_code == CommandCodes.START_STOP_ALL:
            mode = self.__get_bytes(0, 1)
            field_strings.append(mode)
        elif self.command_code == CommandCodes.TEST:
            station_address = self.__get_bytes(0, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == CommandCodes.UNLOCK:
            key = self.__get_bytes(0, 6)
            field_strings.append(key)
        elif self.command_code == CommandCodes.UPLOAD:
            data_size = self.__get_bytes(0, 1)
            field_strings.append(data_size)
        elif self.command_code == CommandCodes.WRITE_DAQ:
            daq_element_size = self.__get_bytes(0, 1)
            field_strings.append(daq_element_size)
            address_extension = self.__get_bytes(1, 1)
            field_strings.append(address_extension)
            address = self.__get_bytes(2, 4)
            field_strings.append(address)
        else:
            pass

        return "  ".join(field_strings).strip()

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "command_code={:#x}".format(self.command_code),
            "counter={:#x}".format(self.ctr),
        ]

        crm_data = ["{:#02x}".format(byte) for byte in self.cro_data]
        args += ["cro_data=[{}]".format(", ".join(crm_data))]

        return "ccp.CommandReceiveObject({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRO")
        field_strings.append(str(self.ctr))
        field_strings.append(self.parse())

        return "  ".join(field_strings).strip()


class DataTransmissionObject(can.Message):
    """Data Transmission Object.
    """

    def __init__(
        self,
        arbitration_id,
        pid,
        dto_data=[],
        timestamp=0,
        channel=None,
        is_extended_id=True,
    ):
        self.pid = pid
        data = [pid] + dto_data
        super().__init__(
            arbitration_id=arbitration_id,
            data=data,
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )


class CommandReturnMessage(DataTransmissionObject):
    """Command Return Message.
    """

    def __init__(
        self,
        arbitration_id,
        return_code,
        ctr,
        crm_data,
        timestamp=0,
        channel=None,
        is_extended_id=True,
    ):
        self.return_code = return_code
        self.ctr = ctr
        self.crm_data = crm_data
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.COMMAND_RETURN_MESSAGE,
            dto_data=[return_code, ctr] + list(crm_data),
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "return_code={:#x}".format(self.return_code),
            "counter={:#x}".format(self.ctr),
        ]

        crm_data = ["{:#02x}".format(byte) for byte in self.crm_data]
        args += ["crm_data=[{}]".format(", ".join(crm_data))]

        return "ccp.CommandReturnMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRM")
        field_strings.append(ReturnCodes(self.return_code).name)
        field_strings.append(str(self.ctr))
        field_strings.append(str(list(self.crm_data)))

        return "  ".join(field_strings).strip()


class EventMessage(DataTransmissionObject):
    """Event Message.
    """

    def __init__(
        self,
        arbitration_id,
        return_code,
        timestamp=0,
        channel=None,
        is_extended_id=True,
    ):
        self.return_code = return_code
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.EVENT_MESSAGE,
            dto_data=[return_code] + 6 * [0],
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "return_code={:#x}".format(self.return_code),
        ]

        return "ccp.EventMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("EventMessage")
        field_strings.append(ReturnCodes(self.return_code).name)

        return "  ".join(field_strings).strip()


class DataAcquisitionMessage(DataTransmissionObject):
    """Data Acquisition Message.
    """

    def __init__(
        self,
        arbitration_id,
        odt_number,
        daq_data,
        timestamp=0,
        channel=None,
        is_extended_id=True,
    ):
        self.odt_number = odt_number
        self.daq_data = daq_data
        super().__init__(
            arbitration_id=arbitration_id,
            pid=odt_number,
            dto_data=list(daq_data),
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "odt_number={:#x}".format(self.odt_number),
        ]

        daq_data = ["{:#02x}".format(byte) for byte in self.daq_data]
        args += ["daq_data=[{}]".format(", ".join(daq_data))]

        return "ccp.DataAcquisitionMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("DAQ")
        field_strings.append(str(self.odt_number))
        field_strings.append(str(list(self.daq_data)))

        return "  ".join(field_strings).strip()


class ODT(object):
    """Object Descriptor Table.
    """


class DAQList(object):
    """Data Acquisition List.
    """

    """
    2401
    360a
    360b
    360c
    360d
    """


class Memory(object):
    def __init__(self):
        pass


class CcpError(can.CanError):
    """Indicates an error with the CCP communication.
    """
