#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import queue
from typing import List

from ..messages.data_acquisition import ObjectDescriptorTable
from ..messages.ccp_message import is_daq


class DAQParser(can.Listener):
    def __init__(
        self,
        dto_id: int,
        odts: List[ObjectDescriptorTable] = [],
        verbose: bool = False,
    ):
        self.dto_id = dto_id
        self._verbose = verbose
        # Flatten DAQ lists to dict of ODTs
        # self.odt_dict is used for decoding incoming data
        self.odt_dict = {}
        # self.values_dict is a dictionary of queues for holding decoded data
        self.values_dict = {}

        for odt in odts:
            self.odt_dict[odt.number] = odt

            for e in odt.elements:
                self.values_dict[e.name] = queue.Queue()

    def add_odt(self, odt: ObjectDescriptorTable):
        self.odt_dict[odt.number]: odt

        for e in odt.elements:
            self.values_dict[e.name] = queue.Queue()

    def on_message_received(self, msg: can.Message):
        if is_daq(msg=msg, dto_id=self.dto_id):
            odt_number = msg.data[0]
            element_values = self.odt_dict[odt_number].decode(msg.data[1:])
            output = []

            for k, v in element_values.items():
                self.values_dict[k].put((msg.timestamp, v))
                output.append(k + ": " + str(v))

            if self._verbose:
                print("\n".join(output))

    def get(self, element_name: str):
        return self.values_dict[element_name].get(timeout=0.5)
