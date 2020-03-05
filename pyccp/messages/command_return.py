#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import DTOType, MAX_DLC, MessageByte, ReturnCodes
from .data_transmission import DataTransmissionObject


class CommandReturnMessage(DataTransmissionObject):
    """
    Command Return Messages (CRM) are a type of Data Transmission Object which
    is sent from a slave to the master in response to a Command Receive Object.
    """

    def __init__(
        self,
        arbitration_id: int = 0,
        return_code: ReturnCodes = ReturnCodes.RESOURCE_FUNCTION_NOT_AVAILABLE,
        ctr: int = 0,
        data: bytearray = bytearray(MAX_DLC),
    ):
        """
        Parameters
        ----------
        return_code : ReturnCodes
            Status information about command execution.
        ctr : int
            Command counter, 0-255. Used to associate CROs with CRMs.

        Returns
        -------
        None.

        """
        self.data = data
        self.return_code = return_code
        self.ctr = ctr
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.COMMAND_RETURN_MESSAGE,
            data=self.data,
        )

    @property
    def return_code(self) -> ReturnCodes:
        return ReturnCodes(self.data[MessageByte.DTO_ERR])

    @return_code.setter
    def return_code(self, value: ReturnCodes):
        self.data[MessageByte.DTO_ERR] = value

    @property
    def ctr(self) -> int:
        return self.data[MessageByte.CRM_CTR]

    @ctr.setter
    def ctr(self, value: int):
        self.data[MessageByte.CRM_CTR] = value
