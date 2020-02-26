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
