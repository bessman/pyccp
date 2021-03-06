#!/usr/bin/env python
# -*- coding: utf-8 -*-

import can
import unittest

from pyccp import Master
from pyccp.error import CCPError
from pyccp.messages import ReturnCodes, CommandReturnMessage


class TestMaster(unittest.TestCase):
    def setUp(self):
        transport = can.Bus("test", bustype="virtual")
        self.slave_bus = can.Bus("test", bustype="virtual")
        self.master = Master(transport, cro_id=0x7E1, dto_id=0x321)
        self.master.ctr = 0x27
        self.acknowledge = CommandReturnMessage(
            arbitration_id=0x321,
            return_code=ReturnCodes.ACKNOWLEDGE,
            ctr=self.master.ctr,
        )

    def tearDown(self):
        self.master.stop()
        self.slave_bus.shutdown()
        del self.master

    def runTest(
        self, command, expected_result, reply, **kwargs,
    ):
        self.master._queue.on_message_received(reply)
        command(**kwargs)
        message = self.slave_bus.recv(timeout=1)
        addr_fmt = "08X" if message.is_extended_id else "04X"
        result = (
            f"{message.arbitration_id:{addr_fmt}}"
            + "  "
            + " ".join([f"{i:02X}" for i in message.data])
        )
        self.assertEqual(result, expected_result)

    def testConnect(self):
        self.runTest(
            self.master.connect,
            "000007E1  01 27 39 00 00 00 00 00",
            self.acknowledge,
            station_address=0x39,
        )

    def testGetCCPVersion(self):
        self.runTest(
            self.master.get_ccp_version,
            "000007E1  1B 27 02 01 00 00 00 00",
            self.acknowledge,
            major=2,
            minor=1,
        )

    def testExchangeID(self):
        self.runTest(
            self.master.exchange_id,
            "000007E1  17 27 00 00 00 00 00 00",
            self.acknowledge,
            device_info=0,
        )

    def testSetMta(self):
        self.runTest(
            self.master.set_mta,
            "000007E1  02 27 00 02 34 00 20 00",
            self.acknowledge,
            address=0x34002000,
            extension=0x02,
            mta=0,
        )

    def testDnload(self):
        self.runTest(
            self.master.dnload,
            "000007E1  03 27 05 10 11 12 13 14",
            self.acknowledge,
            size=5,
            data=0x1011121314,
        )

    def testUpload(self):
        self.runTest(
            self.master.upload,
            "000007E1  04 27 04 00 00 00 00 00",
            self.acknowledge,
            size=4,
        )

    def testGetDaqSize(self):
        self.runTest(
            self.master.get_daq_size,
            "000007E1  14 27 03 00 01 02 03 04",
            self.acknowledge,
            daq_list_number=3,
            dto_id=0x01020304,
        )

    def testSetDaqPtr(self):
        self.runTest(
            self.master.set_daq_ptr,
            "000007E1  15 27 03 05 02 00 00 00",
            self.acknowledge,
            daq_list_number=3,
            odt_number=5,
            element_number=2,
        )

    def testWriteDaqPtr(self):
        self.runTest(
            self.master.write_daq,
            "000007E1  16 27 02 01 02 00 42 00",
            self.acknowledge,
            size=2,
            extension=0x01,
            address=0x02004200,
        )

    def testStartStopPtr(self):
        self.runTest(
            self.master.start_stop,
            "000007E1  06 27 01 03 07 02 00 01",
            self.acknowledge,
            mode=0x01,
            daq_list_number=0x03,
            last_odt_number=0x07,
            event_channel=0x02,
            rate_prescaler=0x01,
        )

    def testDisconnect(self):
        self.runTest(
            self.master.disconnect,
            "000007E1  07 27 00 00 08 02 00 00",
            self.acknowledge,
            permanent=0x00,
            station_address=0x0208,
        )

    def testSetSStatus(self):
        self.runTest(
            self.master.set_s_status,
            "000007E1  0C 27 01 00 00 00 00 00",
            self.acknowledge,
            status_bits=0x01,
        )

    def testNoReply(self):
        self.assertRaises(CCPError, self.master._receive)

    def testWrongCtr(self):
        msg = CommandReturnMessage(
            arbitration_id=0x321,
            return_code=ReturnCodes.ACKNOWLEDGE,
            ctr=self.master.ctr + 1,
        )
        self.master._queue.on_message_received(msg)
        self.assertRaises(CCPError, self.master._receive)

    def testSlaveError(self):
        msg = CommandReturnMessage(
            arbitration_id=0x321,
            return_code=ReturnCodes.ACCESS_DENIED,
            ctr=self.master.ctr,
        )
        self.master._queue.on_message_received(msg)
        self.assertRaises(CCPError, self.master._receive)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
