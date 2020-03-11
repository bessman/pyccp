#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A Command Return Message (CRM)."""

import enum

from .ccp_message import DTOType, MAX_DLC, MessageByte
from .data_transmission import DataTransmissionObject


class ReturnCodes(enum.IntEnum):
    ACKNOWLEDGE = 0x00
    DAQ_PROCESSOR_OVERLOAD = 0x01  # C0
    COMMAND_PROCESSOR_BUSY = 0x10  # C1 NONE (wait until ACK or timeout)
    DAQ_PROCESSOR_BUSY = 0x11  # C1 NONE (wait until ACK or timeout)
    INTERNAL_TIMEOUT = 0x12  # C1 NONE (wait until ACK or timeout)
    KEY_REQUEST = 0x18  # C1 NONE (embedded seed&key)
    SESSION_STATUS_REQUEST = 0x19  # C1 NONE (embedded SET_S_STATUS)
    COLD_START_REQUEST = 0x20  # C2 COLD START
    CAL_DATA_INIT_REQUEST = 0x21  # C2 cal. data initialization
    DAQ_LIST_INIT_REQUEST = 0x22  # C2 DAQ list initialization
    CODE_UPDATE_REQUEST = 0x23  # C2 (COLD START)
    UNKNOWN_COMMAND = 0x30  # C3 (FAULT)
    COMMAND_SYNTAX = 0x31  # C3 FAULT
    PARAMETER_OUT_OF_RANGE = 0x32  # C3 FAULT
    ACCESS_DENIED = 0x33  # C3 FAULT
    OVERLOAD = 0x34  # C3 FAULT
    ACCESS_LOCKED = 0x35  # C3 FAULT
    RESOURCE_FUNCTION_NOT_AVAILABLE = 0x36  # C3 FAULT


class CommandReturnMessage(DataTransmissionObject):
    """CRMs are sent by the slave in response to a CRO."""

    def __init__(
        self,
        arbitration_id: int = 0,
        return_code: ReturnCodes = ReturnCodes.RESOURCE_FUNCTION_NOT_AVAILABLE,
        ctr: int = 0,
        data: bytearray = bytearray(MAX_DLC),
    ):
        """Create a CRM.

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
        """Get the CRM's return_code."""
        return ReturnCodes(self.data[MessageByte.DTO_ERR])

    @return_code.setter
    def return_code(self, value: ReturnCodes):
        self.data[MessageByte.DTO_ERR] = value

    @property
    def ctr(self) -> int:
        """Get the CRM's counter."""
        return self.data[MessageByte.CRM_CTR]

    @ctr.setter
    def ctr(self, value: int):
        self.data[MessageByte.CRM_CTR] = value
