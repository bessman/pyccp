#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
from typing import Dict

from .. import MAX_DLC, CRO_CMD_BYTE, CRO_CTR_BYTE
from .ccp_message import CCPMessage
from . import CommandCodes, COMMAND_DISPATCH


class CommandReceiveObject(CCPMessage):
    """
    Command Receive Objects (CRO) are sent from the master to the slave and
    contain commands and associated data which the slave must handle.
    """
    __slots__ = ("command_code", "ctr",)

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
            data[CRO_CMD_BYTE] = 0
            data[CRO_CTR_BYTE] = ctr

        super().__init__(arbitration_id=arbitration_id, data=data)

    @classmethod
    def from_can_message(cls, msg: can.Message):
        cro = super().from_can_message(msg)
        cro.command_code = msg.data[CRO_CMD_BYTE]
        cro.ctr = msg.data[CRO_CTR_BYTE]

        return cro

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
