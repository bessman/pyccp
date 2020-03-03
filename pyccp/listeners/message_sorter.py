#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import queue
from typing import List, Union

from pyccp.messages.command_receive import CommandReceiveObject
from pyccp.messages.data_transmission import DTOType
from pyccp.messages.command_return import CommandReturnMessage
from pyccp.messages.event import EventMessage
from pyccp.messages.data_acquisition import DataAcquisitionMessage


class MessageTypeChecker:
    def is_cro(self, msg: can.Message) -> bool:
        return msg.arbitration_id == self.cro_id

    def is_dto(self, msg: can.Message) -> bool:
        return msg.arbitration_id == self.dto_id

    def is_crm(self, msg: can.Message) -> bool:
        pid = msg.data[0]

        return self.is_dto(msg) and (pid == DTOType.COMMAND_RETURN_MESSAGE)

    def is_evm(self, msg: can.Message) -> bool:
        pid = msg.data[0]

        return self.is_dto(msg) and (pid == DTOType.EVENT_MESSAGE)

    def is_daq(self, msg: can.Message) -> bool:
        pid = msg.data[0]

        return self.is_dto(msg) and (pid < DTOType.EVENT_MESSAGE)


class MessageSorter(can.Listener, MessageTypeChecker):
    def __init__(
        self, dto_id: int, cro_id: int, verbose: Union[bool, List[str]] = False
    ):
        self.dto_id = dto_id
        self.cro_id = cro_id
        self.types = {
            "CRM": CommandReturnMessage,
            "EVM": EventMessage,
            "DAQ": DataAcquisitionMessage,
            "CRO": CommandReceiveObject,
        }

        if verbose is True:
            self._verbose = list(self.types.values())
        elif verbose is False:
            self._verbose = []
        elif isinstance(verbose, list):
            self._verbose = [self.types[v] for v in verbose]
        else:
            raise TypeError("Argument 'verbose' must be bool or list")

        self._crm_queue = queue.Queue()
        self._evm_queue = queue.Queue()
        self._daq_queue = queue.Queue()
        self._cro_queue = queue.Queue()

    def output(self, msg):
        if any([isinstance(msg, t) for t in self._verbose]):
            print(msg)

    def on_message_received(self, msg: can.Message):
        if self.is_crm(msg):
            msg = CommandReturnMessage(
                arbitration_id=msg.arbitration_id,
                return_code=msg.data[1],
                ctr=msg.data[2],
                crm_data=msg.data[3:],
                timestamp=msg.timestamp,
                channel=msg.channel,
                is_extended_id=msg.is_extended_id,
            )
            self._crm_queue.put(msg)

        elif self.is_evm(msg):
            msg = EventMessage(
                arbitration_id=msg.arbitration_id,
                return_code=msg.data[1],
                timestamp=msg.timestamp,
                channel=msg.channel,
                is_extended_id=msg.is_extended_id,
            )
            self._evm_queue.put(msg)

        elif self.is_daq(msg):
            msg = DataAcquisitionMessage(
                arbitration_id=msg.arbitration_id,
                odt_number=msg.data[0],
                daq_data=msg.data[1:],
                timestamp=msg.timestamp,
                channel=msg.channel,
                is_extended_id=msg.is_extended_id,
            )
            self._daq_queue.put(msg)

        elif self.is_cro(msg):
            msg = CommandReceiveObject().from_can_message(msg)
            self._cro_queue.put(msg)

        self.output(msg)

    def get_command_return_message(self, timeout: float = 0.5):
        return self._crm_queue.get(timeout=timeout)

    def get_event_message(self, timeout=0.5):
        return self._evm_queue.get(timeout=timeout)

    def get_data_acquisition_message(self, timeout: float = 0.5):
        return self._daq_queue.get(timeout=timeout)

    def get_command_receive_object(self, timeout: float = 0.5):
        return self._cro_queue.get(timeout=timeout)
