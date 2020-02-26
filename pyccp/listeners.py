#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2016 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import can
import queue
import pandas as pd
from numpy import NaN
from typing import List

from pyccp import ccp


class CCPMessageSorter(can.Listener):
    def __init__(self, dto_id: int, cro_id: int):
        self.dto_id = dto_id
        self.cro_id = cro_id
        self._crm_queue = queue.Queue()
        self._evm_queue = queue.Queue()
        self._daq_queue = queue.Queue()
        self._cro_queue = queue.Queue()

    def on_message_received(self, msg: can.Message):
        if msg.arbitration_id == self.dto_id:
            pid = msg.data[0]

            if pid == ccp.DTOType.COMMAND_RETURN_MESSAGE:
                msg = ccp.CommandReturnMessage(
                    arbitration_id=msg.arbitration_id,
                    return_code=msg.data[1],
                    ctr=msg.data[2],
                    crm_data=msg.data[3:],
                    timestamp=msg.timestamp,
                    channel=msg.channel,
                    is_extended_id=msg.is_extended_id,
                )
                self._crm_queue.put(msg)
            elif pid == ccp.DTOType.EVENT_MESSAGE:
                msg = ccp.EVM(
                    arbitration_id=msg.arbitration_id,
                    return_code=msg.data[1],
                    timestamp=msg.timestamp,
                    channel=msg.channel,
                    is_extended_id=msg.is_extended_id,
                )
                self._evm_queue.put(msg)
            else:
                # DTO contains a Data Acquisiton Message
                msg = ccp.DataAcquisitionMessage(
                    arbitration_id=msg.arbitration_id,
                    odt_number=msg.data[0],
                    daq_data=msg.data[1:],
                    timestamp=msg.timestamp,
                    channel=msg.channel,
                    is_extended_id=msg.is_extended_id,
                )
            self._daq_queue.put(msg)
        elif msg.arbitration_id == self.cro_id:
            msg = ccp.CommandReceiveObject(
                arbitration_id=msg.arbitration_id,
                command_code=msg.data[0],
                ctr=msg.data[1],
                cro_data=msg.data[2:],
                timestamp=msg.timestamp,
                channel=msg.channel,
                is_extended_id=msg.is_extended_id,
            )
            self._cro_queue.put(msg)
        else:
            pass

    def get_command_return_message(self, timeout: float = 0.5):
        return self._crm_queue.get(timeout=timeout)

    def get_event_message(self, timeout=0.5):
        return self._evm_queue.get(timeout=timeout)

    def get_data_acquisition_message(self, timeout: float = 0.5):
        return self._daq_queue.get(timeout=timeout)

    def get_command_receive_object(self, timeout: float = 0.5):
        return self._cro_queue.get(timeout=timeout)


class DAQParser(can.Listener):
    def __init__(self, dto_id: int,
                 daq_lists: List[List[ccp.ObjectDescriptorTable]] = [],
                 enable_logging: bool = False):
        self.dto_id = dto_id
        self._queue = queue.Queue()
        self.logging = enable_logging
        # Flatten DAQ lists to dict of ODTs
        # self.odt_dict is used for decoding incoming data
        self.odt_dict = {}
        # self.values_dict is used for holding decoded data
        self.values_dict = {}

        for dl in daq_lists:
            for odt in dl:
                self.odt_dict[odt.number] = odt

                for e in odt.elements:
                    self.values_dict[e.name] = None

        if self.logging:
            columns = list(self.values_dict.keys())
            self.log = pd.DataFrame(columns=columns)

    def add_daq_list(self, daq_list: List[ccp.ObjectDescriptorTable]):
        for odt in daq_list:
            self.odt_dict[odt.number]: odt

            for e in odt.elements:
                self.values_dict[e.name] = None

                if self.logging:
                    self.log.loc[:, e.name] = [NaN] * len(self.log.index)

    def on_message_received(self, msg: can.Message):
        if msg.arbitration_id == self.dto_id:
            # The message is a Data Transmission Object
            pid = msg.data[0]

            if pid < 0xFE:
                # The DTO is a Data Acquisition Message
                self._queue.put(msg)
                odt_number = pid
                element_values = self.odt_dict[odt_number].decode(msg.data[1:])

                for k, v in element_values.items():
                    self.values_dict[k] = v

                    if self.logging:
                        fill = [NaN] * len(self.log.columns)
                        self.log.loc[pd.to_datime(msg.timestamp, unit="s")] = fill
                        self.log.loc[pd.to_datime(msg.timestamp, unit="s")][k] = v

    def get(self, element_name: str):
        self._queue.get(timeout=0.5)
        return self.values_dict[element_name]

    def get_log(self):
        if self.logging:
            return self.log
        else:
            return None
