#!/usr/bin/env python
# -*- coding: utf-8 -*-


import can
import enum
from typing import List, Union


class DTOType(enum.IntEnum):
    COMMAND_RETURN_MESSAGE = 0xFF
    EVENT_MESSAGE = 0xFE


class DataTransmissionObject(can.Message):
    """
    Data Transmission Objects (DTO) are sent from the slave to the master, and
    are one of three types:
        Command Return Messages (CRM) are sent in response to CROs.
        Event Messages (EVM) are sent in response to slave internal events.
        Data Acquisition Messages (DAQ) are sent periodically during DAQ
        sessions.
    This class should not be used directly; it is just a superclass for
    CRM, EVM, and DAQ classes.
    """

    def __init__(
        self,
        arbitration_id: int,
        pid: Union[DTOType, int],
        dto_data: Union[List[int], bytearray] = [],
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
    ):
        """
        Parameters
        ----------
        pid : DTOType or int
            0xFF for CRM,
            0xFE for EVM,
            0-0xFD for DAQ.
        dto_data : list of int or bytearray, optional
            Transmitted data. The default is [].

        Returns
        -------
        None.

        """
        self.pid = pid
        data = [pid] + dto_data
        super().__init__(
            arbitration_id=arbitration_id,
            data=data,
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )
