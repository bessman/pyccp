# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:53:01 2020

@author: abemtk
"""

from typing import Union
from pyccp import ccp
from pyccp.messages.data_transmission import DataTransmissionObject


class EventMessage(DataTransmissionObject):
    """
    Event Messages (EVM) are a type of Data Transmission Object which is sent
    from a slave to the master in response to an internal event in the slave.
    """

    def __init__(
        self,
        arbitration_id: int,
        return_code: ccp.ReturnCodes,
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
    ):
        """
        Parameters
        ----------
        return_code : ccp.ReturnCodes
            The command to send to the slave.

        Returns
        -------
        None.

        """
        self.return_code = return_code
        super().__init__(
            arbitration_id=arbitration_id,
            pid=ccp.DTOType.EVENT_MESSAGE,
            dto_data=[return_code] + 6 * [0],
            timestamp=timestamp,
            channel=channel,
            is_extended_id=is_extended_id,
        )

    def __repr__(self) -> str:
        args = [
            "timestamp={}".format(self.timestamp),
            "return_code={:#x}".format(self.return_code),
        ]

        return "ccp.EventMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("EventMessage")
        field_strings.append(ccp.ReturnCodes(self.return_code).name)

        return "  ".join(field_strings).strip()
