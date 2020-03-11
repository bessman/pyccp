#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""An Event Message (EVM)."""

from .ccp_message import DTOType, MAX_DLC, MessageByte
from .data_transmission import DataTransmissionObject
from .command_return import ReturnCodes


class EventMessage(DataTransmissionObject):
    """EVMs are sent by the slave in response to an internal event."""

    def __init__(
        self,
        arbitration_id: int = 0,
        return_code: ReturnCodes = ReturnCodes.RESOURCE_FUNCTION_NOT_AVAILABLE,
    ):
        """Create an EVM.

        Parameters
        ----------
        return_code : ReturnCodes
            Information about the event which triggered the EVM.

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
        """Get the EVM's return_code."""
        return ReturnCodes(self.data[MessageByte.DTO_ERR])

    @return_code.setter
    def return_code(self, value: ReturnCodes):
        self.data[MessageByte.DTO_ERR] = value
