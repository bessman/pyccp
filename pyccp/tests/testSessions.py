#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from ..messages import CommandCodes, ReturnCodes
from ..messages.command_return import CommandReturnMessage
from ..messages.data_acquisition import (
    DataAcquisitionMessage,
    Element,
    ObjectDescriptorTable,
)
from ..messages.command_receive import CommandReceiveObject
from ..master import Master
from ..session import DAQSession
from .. import CCPError

CRO_ID = 0x7E1
DTO_ID = 0x321


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.master_bus = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.test_elements = [
            Element(name="0", size=4, address=0),
            Element(name="1", size=4, address=1),
            Element(name="2", size=1, address=2),
            Element(name="3", size=2, address=3),
            Element(name="4", size=2, address=4),
            Element(name="5", size=4, address=5),
        ]
        self.master = Master(transport=self.master_bus, cro_id=CRO_ID, dto_id=DTO_ID)
        self.daq_session = DAQSession(
            master=self.master, station_address=0x39, elements=self.test_elements
        )
        self.acknowledge = CommandReturnMessage(
            arbitration_id=DTO_ID,
            return_code=ReturnCodes.ACKNOWLEDGE,
            ctr=self.master.ctr,
        )

    def tearDown(self):
        self.daq_session.stop()
        self.master.stop()
        self.slave_bus.shutdown()

    def test_pack_elements(self):
        packed = self.daq_session._pack_elements()
        expected = [
            [self.test_elements[0], self.test_elements[3], self.test_elements[2]],
            [self.test_elements[1], self.test_elements[4]],
            [self.test_elements[5]],
        ]
        self.assertEqual(packed, expected)

    def test_get_daq_lists(self):
        reply = CommandReturnMessage.from_can_message(self.acknowledge)
        reply.data[3:5] = [10, 0]
        self.master._queue.on_message_received(reply)
        reply = CommandReturnMessage.from_can_message(self.acknowledge)
        reply.data[3:5] = [0, 0]
        reply.ctr = 1
        self.master._queue.on_message_received(reply)
        self.daq_session._get_daq_lists()
        expected = [(0, 10)]
        self.assertEqual(self.daq_session.daq_lists, expected)

    def test_ensure_odts_fit(self):
        self.daq_session.odts = [
            ObjectDescriptorTable(elements=[self.test_elements[i]], number=i)
            for i in range(len(self.test_elements))
        ]
        self.daq_session.daq_lists = [(0, 3)]
        self.assertRaises(CCPError, self.daq_session._ensure_odts_fit)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
