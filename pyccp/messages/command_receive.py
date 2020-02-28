# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:39:03 2020

@author: abemtk
"""

import can
from pyccp import ccp
from pyccp import commands


class CommandReceiveObject(can.Message):
    """
    Command Receive Objects (CRO) are sent from the master to the slave and
    contain commands and associated data which the slave must handle.
    """

    def __init__(
        self,
        arbitration_id: int = 0,
        command_code: ccp.CommandCodes = None,
        ctr: int = 0,
        **kwargs,
    ):
        """
        Parameters
        ----------
        command_code : ccp.CommandCodes
            The command to send to the slave.
        ctr : int
            Command counter, 0-0xFF. Used to associate CROs with CRMs.
        cro_data : list of int or bytearray
            Command data.

        Returns
        -------
        None.

        """
        self.command_code = command_code
        self.ctr = ctr
        self.parameters = kwargs

        if command_code is not None:
            data = commands.to_bytes(command_code=command_code, **self.parameters)
            data = bytearray([command_code, ctr]) + data
        else:
            data = bytearray()

        super().__init__(arbitration_id=arbitration_id, data=data)

    def from_can_message(
        self, msg: can.Message
    ) -> "CommandReceiveObject":  # FIXME python4
        if msg.is_remote_frame:
            raise ValueError("Cannot create CRO from remote frame")
        elif msg.is_error_frame:
            raise ValueError("Cannot create CRO from error frame")
        elif msg.error_state_indicator:
            raise ValueError("Cannot create CRO from error state indicator")
        elif msg.bitrate_switch:
            raise ValueError("Cannot create CRO from bitrate switch")

        self.timestamp = msg.timestamp
        self.arbitration_id = msg.arbitration_id
        self.is_extended_id = msg.is_extended_id
        self.channel = msg.channel
        self.is_fd = msg.is_fd

        self.command_code = msg.data[0]
        self.parameters = commands.from_bytes(data=msg.data)

        return self

    def _from_bytes(self, start: int, length: int, byteorder: str = "big") -> int:
        """
        Convert the CRO's command data, or part of the command data, to an
        integer value.

        Parameters
        ----------
        start : int
            Start byte.
        length : int
            Number of bytes to convert.
        byteorder : str, optional
            Endianess. The default is "big".

        Returns
        -------
        int
            Converted bytes.

        """
        return hex(
            int.from_bytes(self.cro_data[start : start + length], byteorder=byteorder)
        )

    def parse(self) -> str:
        """
        Show the CRO's command code and data in a easily readable format.

        Returns
        -------
        str
            The command code's name followed by its associated data as
            integers.

        """
        field_strings = [ccp.CommandCodes(self.command_code).name]

        if self.command_code == ccp.CommandCodes.ACTION_SERVICE:
            action_service_number = self._from_bytes(0, 2)
            field_strings.append(action_service_number)
            parameters = self._from_bytes(2, 4)

            if parameters != "0x0":
                field_strings.append(parameters)

        elif self.command_code == ccp.CommandCodes.BUILD_CHKSUM:
            block_size = self._from_bytes(0, 4)
            field_strings.append(block_size)
        elif self.command_code == ccp.CommandCodes.CLEAR_MEMORY:
            memory_size = self._from_bytes(0, 4)
            field_strings.append(memory_size)
        elif self.command_code == ccp.CommandCodes.CONNECT:
            station_address = self._from_bytes(0, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == ccp.CommandCodes.DIAG_SERVICE:
            diagnostic_service_number = self._from_bytes(0, 2)
            field_strings.append(diagnostic_service_number)
            parameters = self._from_bytes(2, 4)

            if parameters != "0x0":
                field_strings.append(parameters)

        elif self.command_code == ccp.CommandCodes.DISCONNECT:
            permanence = self._from_bytes(0, 1)
            field_strings.append(permanence)
            station_address = self._from_bytes(2, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == ccp.CommandCodes.DNLOAD:
            data_size = self._from_bytes(0, 1)
            field_strings.append(data_size)
            data = self._from_bytes(1, 5)
            field_strings.append(data)
        elif self.command_code == ccp.CommandCodes.DNLOAD_6:
            data = self._from_bytes(0, 6)
            field_strings.append(data)
        elif self.command_code == ccp.CommandCodes.EXCHANGE_ID:
            device_info = self._from_bytes(0, 6)

            if device_info != "0x0":
                field_strings.append(device_info)

        elif self.command_code == ccp.CommandCodes.GET_ACTIVE_CAL_PAGE:
            pass
        elif self.command_code == ccp.CommandCodes.GET_CCP_VERSION:
            main = self._from_bytes(0, 1)
            field_strings.append(main)
            release = self._from_bytes(1, 1)
            field_strings.append(release)
        elif self.command_code == ccp.CommandCodes.GET_DAQ_SIZE:
            daq_no = self._from_bytes(0, 1)
            field_strings.append(daq_no)
            dto_id = self._from_bytes(2, 4)
            field_strings.append(dto_id)
        elif self.command_code == ccp.CommandCodes.GET_SEED:
            resource_mask = self._from_bytes(0, 1)
            field_strings.append(resource_mask)
        elif self.command_code == ccp.CommandCodes.GET_S_STATUS:
            pass
        elif self.command_code == ccp.CommandCodes.MOVE:
            data_size = self._from_bytes(0, 4)
            field_strings.append(data_size)
        elif self.command_code == ccp.CommandCodes.PROGRAM:
            data_size = self._from_bytes(0, 1)
            field_strings.append(data_size)
            data = self._from_bytes(1, 5)
            field_strings.append(data)
        elif self.command_code == ccp.CommandCodes.PROGRAM_6:
            data = self._from_bytes(0, 6)
            field_strings.append(data)
        elif self.command_code == ccp.CommandCodes.SELECT_CAL_PAGE:
            pass
        elif self.command_code == ccp.CommandCodes.SET_DAQ_PTR:
            daq_list_no = self._from_bytes(0, 1)
            field_strings.append(daq_list_no)
            odt_no = self._from_bytes(1, 1)
            field_strings.append(odt_no)
            element_no = self._from_bytes(2, 1)
            field_strings.append(element_no)
        elif self.command_code == ccp.CommandCodes.SET_MTA:
            mta_number = self._from_bytes(0, 1)
            field_strings.append(mta_number)
            address_extension = self._from_bytes(1, 1)
            field_strings.append(address_extension)
            address = self._from_bytes(2, 4)
            field_strings.append(address)
        elif self.command_code == ccp.CommandCodes.SET_S_STATUS:
            status_bits = self._from_bytes(0, 1)
            field_strings.append(status_bits)
        elif self.command_code == ccp.CommandCodes.SHORT_UP:
            data_size = self._from_bytes(0, 1)
            field_strings.append(data_size)
            address_extension = self._from_bytes(1, 1)
            field_strings.append(address_extension)
            address = self._from_bytes(2, 4)
            field_strings.append(address)
        elif self.command_code == ccp.CommandCodes.START_STOP:
            mode = self._from_bytes(0, 1)
            field_strings.append(mode)
            daq_list_number = self._from_bytes(1, 1)
            field_strings.append(daq_list_number)
            last_odt_number = self._from_bytes(2, 1)
            field_strings.append(last_odt_number)
            event_channel_number = self._from_bytes(3, 1)
            field_strings.append(event_channel_number)
            transmission_rate_prescaler = self._from_bytes(4, 2)
            field_strings.append(transmission_rate_prescaler)
        elif self.command_code == ccp.CommandCodes.START_STOP_ALL:
            mode = self._from_bytes(0, 1)
            field_strings.append(mode)
        elif self.command_code == ccp.CommandCodes.TEST:
            station_address = self._from_bytes(0, 2, "little")
            field_strings.append(station_address)
        elif self.command_code == ccp.CommandCodes.UNLOCK:
            key = self._from_bytes(0, 6)
            field_strings.append(key)
        elif self.command_code == ccp.CommandCodes.UPLOAD:
            data_size = self._from_bytes(0, 1)
            field_strings.append(data_size)
        elif self.command_code == ccp.CommandCodes.WRITE_DAQ:
            daq_element_size = self._from_bytes(0, 1)
            field_strings.append(daq_element_size)
            address_extension = self._from_bytes(1, 1)
            field_strings.append(address_extension)
            address = self._from_bytes(2, 4)
            field_strings.append(address)
        else:
            pass

        return "  ".join(field_strings).strip()

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRO")
        field_strings.append(str(self.ctr))
        field_strings.append(commands.to_str(self.command_code, **self.parameters))

        return "  ".join(field_strings).strip()
