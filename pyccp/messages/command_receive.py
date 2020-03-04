#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
from typing import Dict

from .ccp_message import CCPMessage
from . import CommandCodes, COMMAND_DISPATCH, MAX_DLC, MessageByte


class CommandReceiveObject(CCPMessage):
    """
    Command Receive Objects (CRO) are sent from the master to the slave and
    contain commands and associated data which the slave must handle.
    """

    __slots__ = (
        "command_code",
        "ctr",
    )

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
            data = bytearray(MAX_DLC)
            data[MessageByte.CRO_CMD] = 0
            data[MessageByte.CRO_CTR] = ctr

        super().__init__(arbitration_id=arbitration_id, data=data)

    @classmethod
    def from_can_message(cls, msg: can.Message):
        cro = super().from_can_message(msg)
        cro.command_code = msg.data[MessageByte.CRO_CMD]
        cro.ctr = msg.data[MessageByte.CRO_CTR]

        return cro

    def encode(self, **kwargs: int) -> bytes:
        parameters = kwargs
        parameters["command_code"] = self.command_code
        parameters["ctr"] = self.ctr

        return COMMAND_DISPATCH[self.command_code].encode(parameters)

    def decode(self) -> Dict[str, int]:
        return COMMAND_DISPATCH[self.command_code].decode(self.data)
