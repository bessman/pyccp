#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A Command Receive Object (CRO)."""

from typing import Dict
import os
import enum
import cantools

from .ccp_message import CCPMessage, MAX_DLC, MessageByte


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


_dir_path = os.path.dirname(os.path.realpath(__file__))
COMMANDS_DB = cantools.database.load_file(os.path.join(_dir_path, "commands.dbc"))

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


class CommandReceiveObject(CCPMessage):
    """CROs hold commands from the master to the slave."""

    def __init__(
        self,
        arbitration_id: int = 0,
        command_code: CommandCodes = None,
        ctr: int = 0,
        **kwargs: int,
    ):
        """Create a CommandReceiveObject.

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
        self.data = bytearray(MAX_DLC)
        self.command_code = command_code
        self.ctr = ctr

        if command_code is not None:
            self.data = self.encode(**kwargs)

        super().__init__(arbitration_id=arbitration_id, data=self.data)

    def encode(self, **kwargs: int) -> bytes:
        """Encode keyword arguments to bytes.

        Parameters
        ----------
        **kwargs : int
            Keyword arguments for the command specified by command_code.

        Returns
        -------
        bytes
            Encoded data ready to be transmitted on the CAN bus.
        """
        parameters = kwargs
        parameters["command_code"] = self.command_code
        parameters["ctr"] = self.ctr

        return COMMAND_DISPATCH[self.command_code].encode(parameters)

    def decode(self) -> Dict[str, int]:
        """Decode data bytes to find the keyword arguments used to generate them.

        Returns
        -------
        Dict[str, int]
            Dictionary of {keyword: value}-pairs.
        """
        return COMMAND_DISPATCH[self.command_code].decode(self.data)

    @property
    def command_code(self) -> CommandCodes:
        """Get the CRO's command_code."""
        return CommandCodes(self.data[MessageByte.CRO_CMD])

    @command_code.setter
    def command_code(self, value: CommandCodes):
        if value is not None:
            self.data[MessageByte.CRO_CMD] = value
        else:
            self.data[MessageByte.CRO_CMD] = 0

    @property
    def ctr(self) -> int:
        """Get the CRO's counter."""
        return self.data[MessageByte.CRO_CTR]

    @ctr.setter
    def ctr(self, value: int):
        self.data[MessageByte.CRO_CTR] = value
