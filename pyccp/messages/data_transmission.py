#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Union

from .ccp_message import CCPMessage
from . import DTOType


class DataTransmissionObject(CCPMessage):
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

    __slots__ = ("pid",)

    def __init__(
        self, arbitration_id: int, pid: Union[DTOType, int], data: bytearray,
    ):
        """
        Parameters
        ----------
        pid : DTOType or int
            0xFF for CRM,
            0xFE for EVM,
            0-0xFD for DAQ.
        data : list of int or bytearray, optional
            Transmitted data. The default is [].

        Returns
        -------
        None.

        """
        self.pid = pid
        data = data
        super().__init__(arbitration_id=arbitration_id, data=data)
