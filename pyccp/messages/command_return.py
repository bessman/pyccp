#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can

from . import DTOType, MAX_DLC, MessageByte, ReturnCodes
from .data_transmission import DataTransmissionObject


class CommandReturnMessage(DataTransmissionObject):
    """
    Command Return Messages (CRM) are a type of Data Transmission Object which
    is sent from a slave to the master in response to a Command Receive Object.
    """

    __slots__ = (
        "return_code",
        "ctr",
    )

    def __init__(
        self,
        arbitration_id: int = 0,
        return_code: ReturnCodes = ReturnCodes.ACKNOWLEDGE,
        ctr: int = 0,
    ):
        """
        Parameters
        ----------
        return_code : ReturnCodes
            The command to send to the slave.
        ctr : int
            Command counter, 0-255. Used to associate CROs with CRMs.

        Returns
        -------
        None.

        """
        self.return_code = return_code
        self.ctr = ctr
        data = bytearray(MAX_DLC)
        data[MessageByte.DTO_PID] = DTOType.COMMAND_RETURN_MESSAGE
        data[MessageByte.DTO_ERR] = return_code
        data[MessageByte.CRM_CTR] = ctr
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.COMMAND_RETURN_MESSAGE,
            data=data,
        )

    @classmethod
    def from_can_message(cls, msg: can.Message):
        crm = super().from_can_message(msg)
        crm.pid = DTOType.COMMAND_RETURN_MESSAGE
        crm.ctr = msg.data[MessageByte.CRM_CTR]
        crm.return_code = msg.data[MessageByte.DTO_ERR]

        return crm
