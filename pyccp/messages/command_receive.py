#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import cantools
import enum
from typing import Dict


class CommandCodes(enum.IntEnum):
    # Mandatory commands
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
    # Optional commands
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


class CommandReceiveObject(can.Message):
    """
    Command Receive Objects (CRO) are sent from the master to the slave and
    contain commands and associated data which the slave must handle.
    """

    def __init__(
        self,
        arbitration_id: int = 0,
        command_code: CommandCodes = None,
        ctr: int = 0,
        **kwargs: int,
    ):
        """
        Parameters
        ----------
        command_code : CommandCodes
            The command to send to the slave.
        ctr : int
            Command counter, 0-0xFF. Used to associate CROs with CRMs.
        **kwargs : int
            Keyword arguments for the command specified by command_code.

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

    def from_can_message(self, msg: can.Message):
        self._check_msg_type(msg)
        self.timestamp = msg.timestamp
        self.arbitration_id = msg.arbitration_id
        self.is_extended_id = msg.is_extended_id
        self.channel = msg.channel
        self.is_fd = msg.is_fd
        self.command_code = msg.data[0]
        self.data = msg.data

        return self

    def _check_msg_type(self, msg: can.Message):
        if msg.is_remote_frame:
            raise ValueError("Cannot create CRO from remote frame")
        elif msg.is_error_frame:
            raise ValueError("Cannot create CRO from error frame")
        elif msg.error_state_indicator:
            raise ValueError("Cannot create CRO from error state indicator")
        elif msg.bitrate_switch:
            raise ValueError("Cannot create CRO from bitrate switch")

    def encode(self, **kwargs: int) -> bytes:
        parameters = kwargs
        parameters["command_code"] = self.command_code
        parameters["ctr"] = self.ctr

        return COMMAND_DISPATCH[self.command_code].encode(parameters)

    def decode(self) -> Dict[str, int]:
        return COMMAND_DISPATCH[self.command_code].decode(self.data)

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRO")
        field_strings.append(str(self.ctr))
        field_strings.append(CommandCodes(self.command_code).name)

        for k, v in self.decode().items():
            if not (k == "command_code"):
                field_strings.extend([k, hex(v)])

        return "  ".join(field_strings).strip()


COMMANDS_DB = cantools.database.load_file("pyccp/messages/commands.dbc")


COMMAND_DISPATCH = {
    # Mandatory commands
    CommandCodes.CONNECT: COMMANDS_DB.get_message_by_name("connect"),
    CommandCodes.GET_CCP_VERSION: COMMANDS_DB.get_message_by_name("get_ccp_version"),
    CommandCodes.EXCHANGE_ID: COMMANDS_DB.get_message_by_name("exchange_id"),
    CommandCodes.SET_MTA: COMMANDS_DB.get_message_by_name("set_mta"),
    CommandCodes.DNLOAD: COMMANDS_DB.get_message_by_name("dnload"),
    CommandCodes.UPLOAD: COMMANDS_DB.get_message_by_name("upload"),
    CommandCodes.GET_DAQ_SIZE: COMMANDS_DB.get_message_by_name("get_daq_size"),
    CommandCodes.SET_DAQ_PTR: COMMANDS_DB.get_message_by_name("set_daq_ptr"),
    CommandCodes.WRITE_DAQ: COMMANDS_DB.get_message_by_name("write_daq"),
    CommandCodes.START_STOP: COMMANDS_DB.get_message_by_name("start_stop"),
    CommandCodes.DISCONNECT: COMMANDS_DB.get_message_by_name("disconnect"),
    # Optional commands
    # CommandCodes.GET_SEED: getSeed,
    # CommandCodes.UNLOCK: unlock,
    # CommandCodes.DNLOAD_6: dnload6,
    # CommandCodes.SHORT_UP: shortUp,
    # CommandCodes.SELECT_CAL_PAGE: selectCalPage,
    CommandCodes.SET_S_STATUS: COMMANDS_DB.get_message_by_name("set_s_status"),
    # CommandCodes.GET_S_STATUS: getSStatus,
    # CommandCodes.BUILD_CHKSUM: buildChksum,
    # CommandCodes.CLEAR_MEMORY: clearMemory,
    # CommandCodes.PROGRAM: program,
    # CommandCodes.PROGRAM_6: program6,
    # CommandCodes.MOVE: move,
    # CommandCodes.TEST: test,
    # CommandCodes.GET_ACTIVE_CAL_PAGE: getActiveCalPage,
    # CommandCodes.START_STOP_ALL: startStopAll,
}
