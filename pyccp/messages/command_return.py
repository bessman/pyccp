#!/usr/bin/env python
# -*- coding: utf-8 -*-


import enum
from typing import List, Union
from pyccp.messages.data_transmission import DataTransmissionObject, DTOType


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
    """
    Command Return Messages (CRM) are a type of Data Transmission Object which
    is sent from a slave to the master in response to a Command Receive Object.
    """

    def __init__(
        self,
        arbitration_id: int,
        return_code: ReturnCodes,
        ctr: int,
        crm_data: Union[List[int], bytearray],
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
    ):
        """
        Parameters
        ----------
        return_code : ReturnCodes
            The command to send to the slave.
        ctr : int
            Command counter, 0-255. Used to associate CROs with CRMs.
        crm_data : list of int or bytearray
            Command data.

        Returns
        -------
        None.

        """
        self.return_code = return_code
        self.ctr = ctr
        self.crm_data = crm_data
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.COMMAND_RETURN_MESSAGE,
            dto_data=[return_code, ctr] + list(crm_data),
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "return_code={:#x}".format(self.return_code),
            "counter={:#x}".format(self.ctr),
        ]

        crm_data = ["{:#02x}".format(byte) for byte in self.crm_data]
        args += ["crm_data=[{}]".format(", ".join(crm_data))]

        return "ccp.CommandReturnMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("CRM")
        field_strings.append(ReturnCodes(self.return_code).name)
        field_strings.append(str(self.ctr))
        field_strings.append(str(list(self.crm_data)))

        return "  ".join(field_strings).strip()
