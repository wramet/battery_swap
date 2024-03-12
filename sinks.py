import asyncio
from influxdb_client_3 import InfluxDBClient3, Point, flight_client_options
from typing import List, Dict
from bms import BmsSample 
from util import get_logger
import certifi
import concurrent.futures
from functools import partial
import time
import pandas as pd
import random

class InfluxDBSink:

    logger = get_logger(__name__)

    def __init__(self, url: str, token: str, org: str, bucket: str):
        with open(certifi.where(), "r") as fh:
            cert = fh.read()


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



async def main():


    sink = InfluxDBSink(
        url="https://us-east-1-1.aws.cloud2.influxdata.com",
        token="8KcwFmBCTahxXRbq9gsjHTfHmHfSUgw2f8Ym78zXidI3hk9VShc97zL81Hu36_DBVy5q35heEBzt_-CAO3pNZA==",
        org="Benz",
        bucket="test_mark2"
    )

    batteries_samples = {
    1: BmsSample(voltage=60.3, current=0, charge=5.3, num_cycles=5, soc=30, mos_temperature=[25.5, 28.3]),
    2: BmsSample(voltage=50.3, current=3.6, charge=18.9, num_cycles=5, soc=36, mos_temperature=[22.4, 26.2]),
    3: BmsSample(voltage=48.1, current=-4.2, charge=12.5, num_cycles=10, soc=99, mos_temperature=[24.1, 27.5]),
    4: BmsSample(),
    5: BmsSample(voltage=55.2, current=4.5, charge=10.2, num_cycles=7, soc=47, mos_temperature=[21.9, 24.6]),
    6: BmsSample(voltage=52.7, current=0, charge=15.3, num_cycles=8, soc=95, mos_temperature=[23.3, 25.8]),
    7: BmsSample(voltage=58.6, current=0, charge=8.4, num_cycles=6, soc=86, mos_temperature=[26.2, 29.4]),
    8: BmsSample(voltage=47.3, current=3.2, charge=17.6, num_cycles=11, soc=77, mos_temperature=[23.8, 27.1]),
    9: BmsSample(voltage=56.9, current=4.7, charge=9.8, num_cycles=4, soc=27, mos_temperature=[24.4, 28.0]),
    10: BmsSample(voltage=53.4, current=4.0, charge=14.2, num_cycles=12, soc=82, mos_temperature=[25.1, 27.8]),
}
    
    await sink.publish_sample(batteries_samples)

if __name__ == '__main__':
    asyncio.run(main())