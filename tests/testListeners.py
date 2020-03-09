#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from pyccp.listeners import MessageSorter
from pyccp.messages import CommandCodes, ReturnCodes
from pyccp.messages.command_return import CommandReturnMessage
from pyccp.messages.data_acquisition import (
    DataAcquisitionMessage,
    Element,
    ObjectDescriptorTable,
)
from pyccp.messages.event import EventMessage
from pyccp.messages.command_receive import CommandReceiveObject


class TestListeners(unittest.TestCase):
    def setUp(self):
        self.cro_id = 0x7E1
        self.dto_id = 0x321
        self.master_bus = can.Bus("test", bustype="virtual", receive_own_messages=True)
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.sorter = MessageSorter(self.dto_id, self.cro_id)
        test_signal = Element(name="testSignal", size=4, address=0xDEADBEEF,)
        self.test_odt = ObjectDescriptorTable(elements=[test_signal], number=2)
        self.test_odt.register()
        self.notifier = can.Notifier(self.master_bus, [self.sorter])

    def tearDown(self):
        self.notifier.stop()
        self.test_odt.deregister()

    def testReceiveCRM(self):
        crm = CommandReturnMessage(
            arbitration_id=self.dto_id, ctr=0x27, return_code=ReturnCodes.ACKNOWLEDGE,
        )
        self.slave_bus.send(crm)
        msg = self.sorter.get_command_return_message()
        msg.channel = None
        self.assertTrue(crm.equals(msg, timestamp_delta=None))

    def testReceiveEVM(self):
        evm = EventMessage(
            arbitration_id=self.dto_id, return_code=ReturnCodes.DAQ_PROCESSOR_OVERLOAD,
        )
        self.slave_bus.send(evm)
        msg = self.sorter.get_event_message()
        msg.channel = None
        self.assertTrue(evm.equals(msg, timestamp_delta=None))

    def testReceiveDAQ(self):
        daq = DataAcquisitionMessage(arbitration_id=self.dto_id, odt_number=2,)
        daq.data[1:] = bytearray(range(7))
        self.slave_bus.send(daq)
        msg = self.sorter.get_data_acquisition_message()
        msg.channel = None
        self.assertTrue(daq.equals(msg, timestamp_delta=None))

    def testReceiveCRO(self):
        cro = CommandReceiveObject(
            arbitration_id=self.cro_id,
            ctr=0x27,
            command_code=CommandCodes.CONNECT,
            station_address=0x39,
        )
        self.master_bus.send(cro)
        msg = self.sorter.get_command_receive_object()
        msg.channel = None
        self.assertTrue(cro.equals(msg, timestamp_delta=None))

    def testParseDAQ(self):
        daq = DataAcquisitionMessage(arbitration_id=self.dto_id, odt_number=2,)
        daq.data[1:] = bytearray(range(7))
        self.slave_bus.send(daq)
        msg = self.sorter.get_data_acquisition_message()
        value = msg.decode()["testSignal"]
        self.assertEqual(value, 0x10203)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
