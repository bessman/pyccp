#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import DTOType, MAX_DLC, MessageByte, ReturnCodes
from .data_transmission import DataTransmissionObject


class EventMessage(DataTransmissionObject):
    """
    Event Messages (EVM) are a type of Data Transmission Object which is sent
    from a slave to the master in response to an internal event in the slave.
    """

    def __init__(
        self,
        arbitration_id: int = 0,
        return_code: ReturnCodes = ReturnCodes.RESOURCE_FUNCTION_NOT_AVAILABLE,
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
        self.data = bytearray(MAX_DLC)
        self.return_code = return_code
        super().__init__(
            arbitration_id=arbitration_id, pid=DTOType.EVENT_MESSAGE, data=self.data,
        )

    @property
    def return_code(self) -> ReturnCodes:
        return ReturnCodes(self.data[MessageByte.DTO_ERR])

    @return_code.setter
    def return_code(self, value: ReturnCodes):
        self.data[MessageByte.DTO_ERR] = value
