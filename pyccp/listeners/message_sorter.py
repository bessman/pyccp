#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import queue
from typing import List, Union

from ..messages.command_receive import CommandReceiveObject
from ..messages.command_return import CommandReturnMessage
from ..messages.event import EventMessage
from ..messages.data_acquisition import DataAcquisitionMessage
from ..messages.ccp_message import is_crm, is_cro, is_daq, is_evm


class MessageSorter(can.Listener):
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
        if is_crm(msg=msg, dto_id=self.dto_id):
            msg = CommandReturnMessage.from_can_message(msg)
            self._crm_queue.put(msg)

        elif is_evm(msg=msg, dto_id=self.dto_id):
            msg = EventMessage.from_can_message(msg)
            self._evm_queue.put(msg)

        elif is_daq(msg=msg, dto_id=self.dto_id):
            msg = DataAcquisitionMessage().from_can_message(msg)
            self._daq_queue.put(msg)

        elif is_cro(msg=msg, cro_id=self.cro_id):
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
