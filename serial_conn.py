import asyncio
import aioserial
from bms import BmsSample
from typing import List
from util import get_logger

class SerialConnection:

    logger = get_logger(__name__)

    def __init__(self, port: str = 'COM9', baudrate: int = 9600 , timeout = 0.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    async def connect(self):
        self.logger.info('Serial Port Connection Attempt :')
        try:
            self.serial = aioserial.AioSerial(port= self.port, 
                                        baudrate = self.baudrate,
                                        timeout = self.timeout)
            return True
        except aioserial.SerialException as e:
            self.logger.info(f" - failed to connect to {self.port} - {str(e)}")
            return False
        
        
    def disconnect(self):
        if self.serial:
            self.serial.close()
            self.logger.info(f"Disconnected from {self.port}")
    

    async def fetch_basic(self) -> BmsSample:

        raise NotImplementedError()

    async def fetch_voltages(self) -> List[int]:

        raise NotImplementedError()


    async def set_switch(self, switch: str, state: bool):

        raise NotImplementedError()
    


async def main():
    serial = SerialConnection(port = "COM8")
    await serial.connect()
    command = bytes([0xDD, 0xA5,0x03, 0x00, 0xFF, 0xFD, 0x77])
    while True:
        await serial.serial.write_async(command)
        res = await serial.serial.read_async(50)
        print(res)
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())

