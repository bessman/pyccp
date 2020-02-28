# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:48:04 2020

@author: abemtk
"""

from typing import List, Union
from pyccp import ccp
from pyccp.messages.data_transmission import DataTransmissionObject


class CommandReturnMessage(DataTransmissionObject):
    """
    Command Return Messages (CRM) are a type of Data Transmission Object which
    is sent from a slave to the master in response to a Command Receive Object.
    """

    def __init__(
        self,
        arbitration_id: int,
        return_code: ccp.ReturnCodes,
        ctr: int,
        crm_data: Union[List[int], bytearray],
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
    ):
        """
        Parameters
        ----------
        return_code : ccp.ReturnCodes
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
            pid=ccp.DTOType.COMMAND_RETURN_MESSAGE,
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
        field_strings.append(ccp.ReturnCodes(self.return_code).name)
        field_strings.append(str(self.ctr))
        field_strings.append(str(list(self.crm_data)))

        return "  ".join(field_strings).strip()
