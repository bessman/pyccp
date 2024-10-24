import enum
import queue
import logging
from typing import Dict, Iterator, List

import can
import cantools


_logger = logging.getLogger(__name__)


class MessageByte(enum.IntEnum):
    CRO_CMD = 0
    CRO_CTR = 1
    DTO_PID = 0
    DTO_ERR = 1
    CRM_CTR = 2
    DAQ_DATA_START = 1


class DTOType(enum.IntEnum):
    COMMAND_RETURN_MESSAGE = 0xFF
    EVENT_MESSAGE = 0xFE


class IterQueue(queue.Queue):
    def __iter__(self) -> Iterator:
        while True:
            try:
                yield self.get(timeout=1)
            except queue.Empty:
                pass


class CRMDecoder(can.Listener):
    """A can.Listener which sorts incoming CCP messages by type."""

    def __init__(self, dto_id: int, decoders: Dict[int, cantools.database.can.Message]):
        self.dto_id = dto_id
        self.decoders = decoders
        self.queue = queue.Queue()

    def _hexlist(self, data: bytearray) -> str:
        return " ".join([format(b, "x") for b in data])

    def on_message_received(self, msg: can.Message):
        """Sort an incoming message.

        Parameters
        ----------
        msg : can.Message

        Returns
        -------
        None.
        """
        if (
            msg.arbitration_id == self.dto_id
            and msg.data[MessageByte.DTO_PID] == DTOType.COMMAND_RETURN_MESSAGE
        ):
            ctr = msg.data[MessageByte.CRM_CTR]
            decoded = self.decoders[ctr].decode(msg.data)
            self.queue.put(decoded)
            _logger.debug(f"Received CRM: {msg}")
            _logger.debug(decoded)


class DAQDecoder(can.Listener):
    """Decode incoming messages."""

    def __init__(self, dto_id: int, decoders: List[cantools.database.can.Message]):
        self.dto_id = dto_id
        self.decoders = decoders
        self.queue = IterQueue()

    def on_message_received(self, msg: can.Message) -> None:
        """Decode an incoming message.

        Parameters
        ----------
        msg : can.Message
        """
        if (msg.arbitration_id == self.dto_id) and (
            msg.data[MessageByte.DTO_PID] in (odt.number for odt in self.decoders)
        ):
            pid = msg.data[MessageByte.DTO_PID]
            decoder = self.decoders[pid]
            decoded = decoder.decode(msg.data[MessageByte.DAQ_DATA_START :])
            for element_name, value in decoded.items():
                element = decoder.elements[element_name]
                if element.on_receive:
                    element.on_receive(element, value)
            self.queue.put(decoded)
            _logger.debug(f"Received DAQ#{pid}: {decoded}")
