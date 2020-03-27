#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from pya2l.model import EcuAddress, Measurement

from pyccp import Master, DAQSession
from pyccp.error import CCPError
from pyccp.messages import (
    ReturnCodes,
    CommandReturnMessage,
    Element,
    ObjectDescriptorTable,
)

CRO_ID = 0x7E1
DTO_ID = 0x321

test_measurements = [
    Measurement(name="0", datatype="ULONG", ecu_address=EcuAddress(address=0)),
    Measurement(name="1", datatype="ULONG", ecu_address=EcuAddress(address=1)),
    Measurement(name="2", datatype="UBYTE", ecu_address=EcuAddress(address=2)),
    Measurement(name="3", datatype="UWORD", ecu_address=EcuAddress(address=3)),
    Measurement(name="4", datatype="UWORD", ecu_address=EcuAddress(address=4)),
    Measurement(name="5", datatype="ULONG", ecu_address=EcuAddress(address=5)),
]
test_elements = [
    Element(name=m.name, datatype=m.datatype, address=m.ecu_address.address) for m in test_measurements
]


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.master_bus = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.master = Master(transport=self.master_bus, cro_id=CRO_ID, dto_id=DTO_ID)
        self.daq_session = DAQSession(master=self.master, station_address=0x39)
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
        packed = self.daq_session._pack_elements(test_elements)
        expected = [
            [test_elements[0], test_elements[3], test_elements[2]],
            [test_elements[1], test_elements[4]],
            [test_elements[5]],
        ]
        self.assertEqual(packed, expected)

    def test_get_daq_lists(self):
        self.get_daq_lists_replies()
        self.daq_session._get_daq_lists()
        expected = [(0, 10)]
        self.assertEqual(self.daq_session.daq_lists, expected)

    def make_odts(self):
        self.daq_session.odts = [
            ObjectDescriptorTable(elements=[test_elements[i]], number=i)
            for i in range(len(test_elements))
        ]

    def test_ensure_odts_fit(self):
        self.make_odts()
        self.daq_session.daq_lists = [(0, 3)]
        self.assertRaises(CCPError, self.daq_session._ensure_odts_fit)

    def test_send_daq_lists(self):
        self.set_daq_lists_replies()
        self.make_odts()
        self.daq_session.daq_lists = [(0, 3), (3, 4)]
        self.daq_session._set_daq_lists()

    def get_daq_lists_replies(self, start=0):
        # get daq lists
        reply = CommandReturnMessage.from_can_message(self.acknowledge)
        reply.data[3:5] = [10, 0]
        reply.ctr = start
        self.master._queue.on_message_received(reply)
        reply = CommandReturnMessage.from_can_message(self.acknowledge)
        reply.data[3:5] = [0, 0]
        reply.ctr = start + 1
        self.master._queue.on_message_received(reply)

    def set_daq_lists_replies(self, start=0):
        # send daq lists
        for e in range(start, 2 * len(test_elements) + 2 + start):
            reply = CommandReturnMessage.from_can_message(self.acknowledge)
            reply.ctr = e
            self.master._queue.on_message_received(reply)

    def test_initialize(self):
        self.master._queue.on_message_received(self.acknowledge)
        self.get_daq_lists_replies(start=1)
        self.set_daq_lists_replies(start=3)
        self.daq_session.initialize(test_measurements)
        self.assertTrue(self.daq_session._initialized)
        self.daq_session._initialized = False


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
