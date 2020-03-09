#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base class for CCP messages plus some utility functions."""

import can
from copy import deepcopy

from . import DTOType


def is_cro(msg: can.Message, cro_id: int,) -> bool:
    """Check if the message is a CommandReceiveObject.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.
    cro_id : int
        Expected arbitration ID.

    Returns
    -------
    bool
        True if the message is a CommandReceiveObject, False otherwise.
    """
    return msg.arbitration_id == cro_id


def is_dto(msg: can.Message, dto_id: int,) -> bool:
    """Check if the message is a DataTransmissionObject.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.
    dto_id : int
        Expected arbitration ID.

    Returns
    -------
    bool
        True if the message is a DataTransmissionObject, False otherwise.
    """
    return msg.arbitration_id == dto_id


def is_crm(msg: can.Message, dto_id: int,) -> bool:
    """Check if the message is a CommandReturnMessage.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.
    dto_id : int
        Expected arbitration ID.

    Returns
    -------
    bool
        True if the message is a CommandReturnMessage, False otherwise.
    """
    pid = msg.data[0]

    return is_dto(dto_id=dto_id, msg=msg) and (pid == DTOType.COMMAND_RETURN_MESSAGE)


def is_evm(msg: can.Message, dto_id: int,) -> bool:
    """Check if the message is an EventMessage.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.
    dto_id : int
        Expected arbitration ID.

    Returns
    -------
    bool
        True if the message is a EventMessage, False otherwise.
    """
    pid = msg.data[0]

    return is_dto(dto_id=dto_id, msg=msg) and (pid == DTOType.EVENT_MESSAGE)


def is_daq(msg: can.Message, dto_id: int,) -> bool:
    """Check if the message is a DataAcquisitionMessage.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.
    dto_id : int
        Expected arbitration ID.

    Returns
    -------
    bool
        True if the message is a DataAcquisitionMessage, False otherwise.
    """
    pid = msg.data[0]

    return is_dto(dto_id=dto_id, msg=msg) and (pid < DTOType.EVENT_MESSAGE)


def check_msg_type(msg: can.Message):
    """Check that the message is a normal CAN message.

    Parameters
    ----------
    msg : can.Message
        CAN message to be checked.

    Raises
    ------
    ValueError
        If the message is of a type which cannot be converted to a CCP message.
    """
    if msg.is_remote_frame:
        raise ValueError("Cannot create CRO from remote frame")
    elif msg.is_error_frame:
        raise ValueError("Cannot create CRO from error frame")
    elif msg.error_state_indicator:
        raise ValueError("Cannot create CRO from error state indicator")
    elif msg.bitrate_switch:
        raise ValueError("Cannot create CRO from bitrate switch")


class CCPMessage(can.Message):
    """Base class for CCP messages."""

    @classmethod
    def from_can_message(cls, msg: can.Message):
        """Copy constructor for creating CCP messages from CAN messages."""
        check_msg_type(msg)
        ccpmsg = cls()

        for s in can.Message.__slots__:
            if not s[:2] == "__":
                ccpmsg.__setattr__(s, deepcopy(msg.__getattribute__(s)))

        return ccpmsg
