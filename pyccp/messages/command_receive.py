# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:39:03 2020

@author: abemtk
"""

import can
import cantools
from typing import Dict

from pyccp import ccp


commands = cantools.database.load_file('commands.dbc')


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

        if command_code is not None:
            data = self.encode(**kwargs)
        else:
            data = bytearray()

        super().__init__(arbitration_id=arbitration_id, data=data)

    def encode(self, **kwargs) -> bytes:
        parameters = kwargs
        parameters["command_code"] = self.command_code
        parameters["ctr"] = self.ctr
        return dispatcher[self.command_code].encode(parameters)
    
    def decode(self) -> Dict[str, int]:
        return dispatcher[self.command_code].decode(self.data)

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

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRO")
        field_strings.append(str(self.ctr))
        field_strings.append(ccp.CommandCodes(self.command_code).name)
        field_strings.append(commands.to_str(self.command_code, **self.parameters))

        return "  ".join(field_strings).strip()

    def __str__(self) -> str:
        strings = []

        for k, (s, l, v) in self.parameters.items():
            strings.extend([k, hex(v)])

        return "  ".join(strings)


dispatcher = {
    # Mandatory Commands.
    ccp.CONNECT: commands.get_message_by_name("connect"),
    ccp.GET_CCP_VERSION: commands.get_message_by_name("get_ccp_version"),
    ccp.EXCHANGE_ID: commands.get_message_by_name("exchange_id"),
    ccp.SET_MTA: commands.get_message_by_name("set_mta"),
    ccp.DNLOAD: commands.get_message_by_name("dnload"),
    ccp.UPLOAD: commands.get_message_by_name("upload"),
    ccp.GET_DAQ_SIZE: commands.get_message_by_name("get_daq_size"),
    ccp.SET_DAQ_PTR: commands.get_message_by_name("set_daq_ptr"),
    ccp.WRITE_DAQ: commands.get_message_by_name("write_daq"),
    ccp.START_STOP: commands.get_message_by_name("start_stop"),
    ccp.DISCONNECT: commands.get_message_by_name("disconnect"),
    # Optional Commands.
    # ccp.GET_SEED: getSeed,
    # ccp.UNLOCK: unlock,
    # ccp.DNLOAD_6: dnload6,
    # ccp.SHORT_UP: shortUp,
    # ccp.SELECT_CAL_PAGE: selectCalPage,
    ccp.SET_S_STATUS: commands.get_message_by_name("set_s_status"),
    # ccp.GET_S_STATUS: getSStatus,
    # ccp.BUILD_CHKSUM: buildChksum,
    # ccp.CLEAR_MEMORY: clearMemory,
    # ccp.PROGRAM: program,
    # ccp.PROGRAM_6: program6,
    # ccp.MOVE: move,
    # ccp.TEST: test,
    # ccp.GET_ACTIVE_CAL_PAGE: getActiveCalPage,
    # ccp.START_STOP_ALL: startStopAll,
}