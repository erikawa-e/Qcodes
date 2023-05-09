from functools import partial
from typing import Optional, Union

from qcodes import VisaInstrument, InstrumentChannel
from qcodes.utils.validators import Numbers, Bool, Enum, Ints
import time

def float_round(val):
    """
    Rounds a floating number

    Args:
        val: number to be rounded

    Returns:
        Rounded integer
    """
    return round(float(val))




class yokogawa7651(VisaInstrument):
    """
    This is the qcodes driver for the Yokogawa GS200 voltage and current source

    Args:
      name (str): What this instrument is called locally.
      address (str): The GPIB address of this instrument
      kwargs (dict): kwargs to be passed to VisaInstrument class
      terminator (str): read terminator for reads/writes to the instrument.
    """

    def __init__(self, name: str, address: str, terminator: str="\n",
                 **kwargs) -> None:
        super().__init__(name, address, terminator=terminator, **kwargs)




        self.add_parameter('voltage2',
                           label='Voltage',
                           unit='V',
                           set_cmd=partial(self._set_output_direct, "VOLT"),
                           get_cmd=partial(self._get_set_output, "VOLT")
                           )


        self.output_level = self.voltage2




    def initialize_instrument(self):
        self.write('RC')   
    
    
    def _set_output_direct(self, mode:str,output_level: float) -> None:


        get_value_string=self.ask("OD")
        get_value=get_value_string[4:-4]
        if abs(output_level-float(get_value))<=0.01:
            cmd_str = "S{:.5e}E".format(output_level)
            
            self.write(cmd_str)
        else:
            current_value=float(get_value)
            N=(output_level-current_value)/0.01
            for i in range(int(abs(N))+1):
                input_value=current_value+(output_level-current_value)/abs(N)*i
                cmd_str = "S{:.5e}E".format(input_value)
                self.write(cmd_str)
                time.sleep(0.1)
            cmd_str = "S{:.5e}E".format(output_level)
            self.write(cmd_str)
            
    def _get_set_output(self, mode:str,
                        output_level: float=None) -> Optional[float]:
        """
        Get or set the output level.

        Args:
            mode (str): "CURR" or "VOLT"
            output_level (float), If missing, we assume that we are getting the current level. Else we are setting it
        """

        if output_level is not None:
            self._set_output(output_level)
            return None
        else:
            get_value_string=self.ask("OD")
            get_value=get_value_string[4:-4]
            return float(get_value)    

    def on(self):
        """Turn output on"""
        self.write('O1')


    def off(self):
        """Turn output off"""
        self.write('O0')
