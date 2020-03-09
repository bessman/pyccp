#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A Command Receive Object (CRO)."""

from typing import Dict

from .ccp_message import CCPMessage
from . import CommandCodes, COMMAND_DISPATCH, MAX_DLC, MessageByte


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
