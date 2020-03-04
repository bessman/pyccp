#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can

from .. import MAX_DLC, DTO_ERR_BYTE, DTO_PID_BYTE
from . import DTOType, ReturnCodes
from .data_transmission import DataTransmissionObject


class EventMessage(DataTransmissionObject):
    """
    Event Messages (EVM) are a type of Data Transmission Object which is sent
    from a slave to the master in response to an internal event in the slave.
    """

    __slot__ = ("return_code",)

    def __init__(
        self, arbitration_id: int = 0, return_code: ReturnCodes = 0,
    ):
        """
        Parameters
        ----------
        return_code : ReturnCodes
            The command to send to the slave.

        Returns
        -------
        None.

        """
        self.return_code = return_code
        data = bytearray(MAX_DLC)
        data[DTO_PID_BYTE] = DTOType.EVENT_MESSAGE
        data[DTO_ERR_BYTE] = return_code
        super().__init__(
            arbitration_id=arbitration_id, pid=DTOType.EVENT_MESSAGE, data=data,
        )

    @classmethod
    def from_can_message(cls, msg: can.Message):
        evm = super().from_can_message(msg)
        evm.pid = DTOType.EVENT_MESSAGE
        evm.return_code = msg.data[DTO_ERR_BYTE]

        return evm

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "return_code={:#x}".format(self.return_code),
        ]

        return "EventMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("EventMessage")
        field_strings.append(ReturnCodes(self.return_code).name)

        return "  ".join(field_strings).strip()
