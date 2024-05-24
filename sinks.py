import asyncio
from influxdb_client_3 import InfluxDBClient3, Point, flight_client_options
from typing import List, Dict
from bms import BmsSample 
from util import get_logger
import certifi
import concurrent.futures
from functools import partial
import time
import json

with open('config.json', 'r') as config_file:
        config = json.load(config_file)

class InfluxDBSink:

    logger = get_logger(__name__)

    def __init__(self):
        with open(certifi.where(), "r") as fh:
            cert = fh.read()
            
        sink_config = config['sink_config']
        url = sink_config['url']
        token = sink_config['token'] 
        org = sink_config['org']
        bucket = sink_config['bucket']

        self.client = InfluxDBClient3(
            host=url, 
            token=token, 
            org=org, 
            database=bucket,
            flight_client_options=flight_client_options(tls_root_certs=cert)
        )
        self.executor = concurrent.futures.ThreadPoolExecutor()

    def create_sample_point(self, id: int, sample: BmsSample):
        sample_dict = sample.to_dict()
        point = Point("sample").tag("battery_id", id)

        for field_key, field_value in sample_dict.items():
            point = point.field(field_key, field_value)
        if len(sample_dict) > 1:
            self.logger.info(f"Create data point for Battery ID {id}")
        return point
    
    def create_voltage_point(self, id: int, voltages: List[float]):
        voltage_cells = {f"cell{i+1}": float(v) for i, v in enumerate(voltages)}
        point = Point("voltage").tag("battery_id", id).field("timestamp", int(time.time()))

        for field_key, field_value in voltage_cells.items():
            point = point.field(field_key, field_value)
        return point

    async def publish_sample(self, samples_dict: Dict[int, BmsSample]):
        data_points = [self.create_sample_point(id, sample) for id, sample in samples_dict.items()]
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, partial(self.client.write, record=data_points))
            self.logger.info("Sample data points written successfully.")
        except Exception as e:
            self.logger.error(f"Failed to write sample data points: {e}")

    async def publish_voltage(self, voltages_dict: Dict[int, List[float]]):
        voltage_points = [self.create_voltage_point(id, voltages) for id, voltages in voltages_dict.items()]
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, partial(self.client.write, record=voltage_points))
            self.logger.info("Voltage data points written successfully.")
        except Exception as e:
            self.logger.error(f"Failed to write voltage data points: {e}")


