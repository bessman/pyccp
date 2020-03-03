#!/usr/bin/env python
# -*- coding: utf-8 -*-


from typing import Union

from pyccp.messages.data_transmission import DataTransmissionObject, DTOType
from pyccp.messages.command_return import ReturnCodes


class EventMessage(DataTransmissionObject):
    """
    Event Messages (EVM) are a type of Data Transmission Object which is sent
    from a slave to the master in response to an internal event in the slave.
    """

    def __init__(
        self,
        arbitration_id: int,
        return_code: ReturnCodes,
        timestamp: float = 0,
        channel: Union[int, str] = None,
        is_extended_id: bool = True,
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
        self.return_code = return_code
        super().__init__(
            arbitration_id=arbitration_id,
            pid=DTOType.EVENT_MESSAGE,
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

        return "EventMessage({})".format(", ".join(args))

    def __str__(self) -> str:
        field_strings = ["Timestamp: {0:>8.6f}".format(self.timestamp)]
        field_strings.append("EventMessage")
        field_strings.append(ReturnCodes(self.return_code).name)

        return "  ".join(field_strings).strip()
