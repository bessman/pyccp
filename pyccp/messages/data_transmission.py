# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:43:48 2020

@author: abemtk
"""

import can
from typing import List, Union
from pyccp import ccp


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
        pid: Union[ccp.DTOType, int],
        dto_data: Union[List[int], bytearray] = [],
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
    ):
        """
        Parameters
        ----------
        pid : ccp.DTOType or int
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
