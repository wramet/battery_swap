import math
from typing import List, Dict, Optional
import time


class BmsSample:
    def __init__(self, voltage=math.nan, current=math.nan, charge=math.nan, 
                 num_cycles=None, soc=None, mos_temperature: Optional[List[float]] = None , 
                 switches: Optional[Dict[str, bool]] = None):
        self.voltage = float(voltage)
        self.current = float(current)
        self.charge = float(charge)
        self.num_cycles = int(num_cycles) if num_cycles is not None else None
        self.soc = int(soc) if num_cycles is not None else None
        self.mos_temperature = mos_temperature if mos_temperature is not None else []
        self.switches = switches
        self.timestamp = time.time()

    def __str__(self):
        return str(vars(self))
        
    def to_dict(self):
        result = {}
        for key, value in vars(self).items():
            if key == 'switches':
                continue
            if value is not None and not (isinstance(value, float) and math.isnan(value)):
                result[key] = value
        
        if 'mos_temperature' in result:
            mos_temps = result.pop('mos_temperature')
            for i, temp in enumerate(mos_temps, start=1):
                result[f'mos_temperature_{i}'] = temp

        return result
    


    
