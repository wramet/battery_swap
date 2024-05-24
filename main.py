import asyncio
import json
import re
import signal
from typing import Dict, List
from math import isnan
from jbd import JbdBms
from bms import BmsSample
from util import get_logger 
from sinks import InfluxDBSink
import aioserial

shutdown = False
logger = get_logger()

class BssStation:

    BATTERY_ID = 1

    def __init__(self, **kwargs):
        self.MAX_BATTERIES = kwargs['battery_config']['max_batteries']
        #self.MAX_SOC = kwargs['battery_config']['max_soc']
        #self.MIN_TEMP = kwargs['fan_control_config']['fan_off_temp_threshold']
        #self.MAX_TEMP = kwargs['fan_control_config']['fan_on_temp_threshold']
        self.batteries_samples: Dict[int, BmsSample] = {}
        self.batteries_voltages: Dict[int, List] = {}
        self.serial_battery = JbdBms(**kwargs['serial_battery_config'])
        #self.serial_control = aioserial.AioSerial(**kwargs['serial_control_config'])
        self.lock = asyncio.Lock()
        self.logger = logger
        self.sink = InfluxDBSink(**kwargs['sink_config'])
        self.charging_battery = {}
        self.update_event = asyncio.Event()
        #self.fan_statuses = {battery_id: "OFF" for battery_id in range(1, 11)}

    async def update_sample(self):
        new_sample: BmsSample = await self.serial_battery.fetch_basic()
        self.batteries_samples[self.BATTERY_ID] = new_sample
        self.logger.info(f"Update Sample for Battery ID {self.BATTERY_ID}")

    async def update_voltages(self):
        new_voltages: List = await self.serial_battery.fetch_voltages()
        self.batteries_voltages[self.BATTERY_ID] = new_voltages
        self.logger.info(f"Update Voltage for Battery ID {self.BATTERY_ID}")

    async def fetch_and_log_battery_loop(self):
        await self.serial_battery.connect()
        while not shutdown:
            async with self.lock:
                self.batteries_samples = {i: BmsSample() for i in range(1, 11)}
                self.batteries_voltages = {i: [] for i in range(1, 11)}
                if self.BATTERY_ID != None:
                    await self.update_sample()
                    await self.update_voltages()
                try:
                    await self.sink.publish_sample(self.batteries_samples)
                    await self.sink.publish_voltage(self.batteries_voltages)
                except Exception as e:
                    self.logger.error(f"Error publishing data to InfluxDB: {e}")
            # Wait for the event to be set or for the timeout
            try:
                await asyncio.wait_for(self.update_event.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass  # Timeout occurred, proceed with the next iteration
            finally:
                self.update_event.clear()  # Reset the event for the next iteration
            if shutdown:  
                break

    """    
    async def listen_controllino(self):
        while not shutdown:
            self.charging_battery = {id: sample for id, sample in self.batteries_samples.items() if not isnan(sample.voltage)}
            data = await self.serial_control.readline_async()
            if data:
                message = data.decode().strip()
                await self.handle_message(message)
            if shutdown: 
                break
            """

    """    
    async def handle_message(self, message: str):
        async with self.lock:
            match = re.search(r'Limit switch (\d+) activated', message)
            if match:
                new_id = int(match.group(1))
                self.logger.info(f"Detect new Battery from slot {new_id}")
                while True:
                    await self.serial_battery.serial.write_async(bytes([0xDD, 0xA5,0x03, 0x00, 0xFF, 0xFD, 0x77]))
                    data = await self.serial_battery.serial.read_async(50)
                    if data:
                        break
                    await asyncio.sleep(1)
                if len(self.charging_battery) == self.MAX_BATTERIES:
                    ready_to_swap = [id for id, sample in self.charging_battery.items() if sample.soc > self.MAX_SOC]
                    if ready_to_swap:
                        await self.remove_battery(ready_to_swap[0])
                        self.BATTERY_ID = new_id

                    else:
                        await self.remove_battery(new_id)
                        self.logger.info("No avaiable batteries")
                else:
                    self.BATTERY_ID = new_id
                
                self.update_event.set()            

    async def remove_battery(self, id: int):
        try:
            message = f"Trigger Relay {id}\n"
            await asyncio.sleep(3)
            await self.serial_control.write_async(message.encode())
            self.logger.info(f"Trying to trigger relay {id}")
            response = await self.serial_control.readline_async()
            message = response.decode().strip()
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Failed to remove battery: {e}")

    async def control_fan(self):
        while not shutdown:
            for battery_id, sample in self.charging_battery.items():
                max_temp = max(sample.mos_temperature) if sample.mos_temperature else None
                current_status = self.fan_statuses[battery_id]

                if max_temp is None:
                    continue

                async with self.lock:
                    if max_temp > self.MAX_TEMP and current_status != "ON":
                        self.logger.info(f"Turning ON fan for battery {battery_id} due to high temperature")
                        await self.serial_battery.control_fan(battery_id, "ON")
                        self.fan_statuses[battery_id] = "ON"

                    elif max_temp < self.MIN_TEMP and current_status != "OFF":
                        self.logger.info(f"Turning OFF fan for battery {battery_id} as temperature is normal")
                        await self.serial_battery.control_fan(battery_id, "OFF")
                        self.fan_statuses[battery_id] = "OFF"

            await asyncio.sleep(30)  # Properly await the sleep coroutine
            if shutdown: 
                break
            """


    async def main(self):
        fetch_log_task = asyncio.create_task(self.fetch_and_log_battery_loop())
        #listen_task = asyncio.create_task(self.listen_controllino())
        #uvicorn_task = asyncio.create_task(start_uvicorn())
        #react_task = asyncio.create_task(start_react_dev_server())
        #fan_task = asyncio.create_task(self.control_fan())
        await asyncio.gather(fetch_log_task)


def signal_handler(signum, frame):
    global shutdown
    if signum == signal.SIGINT:
        logger.warning("Shutting down gracefully...")
        shutdown = True 

uvicorn_process = None

async def start_uvicorn():
    global uvicorn_process
    logger.info("Start API")
    cmd = "uvicorn influxdb_api:app --reload"
    uvicorn_process = await asyncio.create_subprocess_shell(
    cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=r'/home/pi/projects/bss-station'
)

    # Logging stdout and stderr
    async for line in uvicorn_process.stdout:
        logger.info(line.decode().strip())

    await uvicorn_process.wait()  # Wait for the Uvicorn process to exit
    if uvicorn_process.returncode != 0:
        # Log errors if uvicorn didn't exit cleanly
        async for line in uvicorn_process.stderr:
            logger.error(line.decode().strip())

async def shutdown_uvicorn():
    global uvicorn_process
    if uvicorn_process and uvicorn_process.returncode is None:
        logger.info("Shutting down Uvicorn server...")
        uvicorn_process.terminate()
        await uvicorn_process.wait()


react_process = None


async def start_react_dev_server():
    global react_process
    
    # Run 'npm run dev' or similar script to start the React development server
    react_process = await asyncio.create_subprocess_shell(
    'npm run dev',
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=r'/home/pi/projects/bss-React_web'
)

    # Optionally, log stdout and stderr from the React development server
    async for line in react_process.stdout:
        print("REACT STDOUT:", line.decode().strip())
    async for line in react_process.stderr:
        print("REACT STDERR:", line.decode().strip())

    await react_process.wait()

async def shutdown_react_dev_server():
    global react_process
    if react_process and react_process.returncode is None:
        print("Shutting down React dev server...")
        react_process.terminate()
        await react_process.wait()



async def main():
      
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        station = BssStation(**config)
        await station.main()
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
    finally:
        logger.info("Performing cleanup...")
        # Gather shutdown tasks and await them
        shutdown_tasks = [shutdown_uvicorn(), shutdown_react_dev_server()]
        await asyncio.gather(*shutdown_tasks)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler) 

    try:
        asyncio.run(main())
    except KeyboardInterrupt: 
        logger.warning("Exiting due to CTRL+C")