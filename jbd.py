
import asyncio
from serial_conn import SerialConnection
from bms import BmsSample
import copy
from typing import List
from util import get_logger


def is_empty_bytearray(result):
    return result == bytearray()


class JbdBms(SerialConnection):

    logger = get_logger(__name__)

    def __init__(self, port='COM9', baudrate = 9600, timeout=1):
        super().__init__(port, baudrate, timeout)
        self._buffer = bytearray()
        self._switches = {'charge': False, 'discharge': False}
        self._last_response = None

    async def connect(self):
        if await super().connect() and self.serial.is_open:
            return self.logger.info(f"Connected to {self.port} successfully")
        self.logger.error("Bad Connection")



    @staticmethod
    def JbdBms_command(command: int ):
        return bytes([0xDD, 0xA5,command, 0x00, 0xFF, 0xFF - (command - 1), 0x77])
    

    async def read_serial_data(self):
        self._buffer += await self.serial.read_async(100)
        self._last_response = copy.copy(self._buffer)
        self._buffer.clear()


    async def _q(self,cmd,):
        await self.serial.write_async(self.JbdBms_command(cmd))
        await self.read_serial_data()
        return self._last_response

        
    async def fetch_basic(self) -> BmsSample:

        buf = await self._q(cmd=0x03)
        if buf:
            buf = buf[4:]
            num_temp = int.from_bytes(buf[22:23], 'big')

            mos_byte = int.from_bytes(buf[20:21], 'big')

            Sample = BmsSample(
                voltage = float(int.from_bytes(buf[0:2], byteorder='big', signed=False)) / 100,
                current = float(int.from_bytes(buf[2:4], byteorder='big', signed=True)) / 100,
                charge=int.from_bytes(buf[4:6], byteorder='big', signed=False) / 100,
                #capacity=int.from_bytes(buf[6:8], byteorder='big', signed=False) / 100,
                soc=int.from_bytes(buf[19:20],byteorder='big', signed=False),

                num_cycles=int.from_bytes(buf[8:10], byteorder='big', signed=False),

                mos_temperature =[(int.from_bytes(buf[23 + i * 2:i * 2 + 25], 'big') - 2731) / 10 for i in range(num_temp)],

                switches = {
                            'discharge': mos_byte & 0x02 > 0,
                            'charge': mos_byte & 0x01 > 0}

            )
            
            return Sample

        else:
            return BmsSample()
        

    async def fetch_voltages(self) -> List[float]:
        buf = await self._q(cmd=0x04)
        num_cell = int(buf[3] // 2)
        voltages = list(map(float, [(int.from_bytes(buf[4 + i * 2: 6 + i * 2], 'big') / 1000) for i in range(num_cell)]))
        
        return voltages


    async def set_switch(self, switch: str, state: bool ):

        assert switch in {"charge", "discharge"}
        
        def JbdBms_checksum(cmd, data):
            crc = 0x10000
            for i in (data + bytes([len(data), cmd])):
                crc = crc - int(i)
            return crc.to_bytes(2, byteorder='big')

        def JbdBms_message(status_bit, cmd, data):
            return bytes([0xDD, status_bit,cmd, len(data)]) + data + JbdBms_checksum(cmd, data) + bytes([0x77])


        new_switches = {**self._switches, switch: state}
        switches_sum = sum(new_switches.values())
        if switches_sum == 2:
            tc = 0x00  # all on
        elif switches_sum == 0:
            tc = 0x03  # all off
        elif (switch == "charge" and not state) or (switch == "discharge" and state):
            tc = 0x01  # charge off
        else:
            tc = 0x02  # charge on, discharge off
        data = JbdBms_message(status_bit=0x5A, cmd=0xE1, data=bytes([0x00, tc])) 
        await self.serial.write_async(data)
        await asyncio.sleep(5)

    @staticmethod
    def modbus_crc(data: bytearray) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                lsb = crc & 1
                crc >>= 1
                if lsb:
                    crc ^= 0xA001
        return crc


    async def control_fan(self,fan_position : int, state:str):
        module_address = 0x01 + (fan_position - 1) // 8  # พัดลม 4 ตัวต่อโมดูล
        relay_number = (fan_position - 1) % 8
        function_code = 0x05

        if state == "ON":
            command = 0xFF00 
        else:
            command = 0x0000  

        frame_without_crc = bytearray([module_address, function_code]) + \
                        bytearray([(relay_number >> 8) & 0xFF, relay_number & 0xFF]) + \
                        bytearray([(command >> 8) & 0xFF, command & 0xFF])

        crc = self.modbus_crc(frame_without_crc)
        modbus_frame = frame_without_crc + crc.to_bytes(2, byteorder='little')
        await self.serial.write_async(modbus_frame)
        if await self.serial.readline_async() == modbus_frame:
            return self.logger.info(f"Fan in slot {fan_position} is {state}")


async def main():
    mock_serial = JbdBms(port = "COM9")
    await mock_serial.connect()
    while True:
        a = await mock_serial.fetch_basic()
        print(a)
        await asyncio.sleep(2)

if __name__ == '__main__':
    asyncio.run(main())
