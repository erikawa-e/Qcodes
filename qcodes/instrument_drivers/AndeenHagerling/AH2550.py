# -*- coding: utf-8 -*-
"""
Created on Mon Apr  3 16:18:01 2023

@author: riken FEBQI asher.jennings@riken.jp


Simple qcodes driver for the Andeen Hagerling 2550 Capacitance Bridge.
Maybe works with 2700 model as well.

Functions to add maybe:
    - continuous mode with polling?
    - 
"""

from functools import partial
from typing import Optional, Union

from qcodes import VisaInstrument, InstrumentChannel, MultiParameter
from qcodes.utils.validators import Numbers, Bool, Enum, Ints
import time


class Single(MultiParameter):
    
    def __init__(self, name: str, instrument: str, loss_unit: str):
    # only name, names, and shapes are required
    # this version returns two scalars (shape = `()`)
        super().__init__(name=name, instrument=instrument, names=('C', 'Loss', "V"),
                         shapes=((), (), ()),
                         labels=('Capacitance', 'Loss', "Voltage"),
                         units=('pF', loss_unit, "V"),
                         docstring='param that returns capacitance, loss and test voltage as the original single command does')

    def get_raw(self) -> tuple:
        res = self.instrument._get_single()
        try:
            c = float(res[0].split("=")[1].split(" ")[0])
        except ValueError:
            c = float(res[0].split("=")[1].split(" ")[1])            
        try:
            l = float(res[1].split("=")[1].split(" ")[0])
        except ValueError:
            l = float(res[1].split("=")[1].split(" ")[1])

        v = float(res[2].split("=")[1].split(" ")[0])        
        return (c, l, v)

class AH2550(VisaInstrument):
    
    def __init__(self, name: str, address: str, terminator: str="\n",
             **kwargs) -> None:
        super().__init__(name, address, terminator=terminator, **kwargs)
    
        self._loss_unit = "nS"
        
        self.add_parameter("capacitance",
                           label='Capacitance',
                           unit='pF',
                           get_cmd=self._get_capacitance,
                           get_parser=float,
                           docstring="capacitance in pico Farads")
        
        self.add_parameter("loss",
                           label='Loss',
                           unit=self._loss_unit,
                           get_cmd=self._get_loss,
                           get_parser=float,
                           docstring="Loss, with the unit set by the loss unit parameter")
    
        self.add_parameter("single",
                           parameter_class=Single,
                           loss_unit=self._loss_unit)    
     
        self.add_parameter("averaging",
                           get_cmd=self._get_average,
                           set_cmd="AVERAGE {}",
                           vals=Ints(min_value=0, max_value=15),
                           get_parser=int,
                           docstring="Sets the average time of the experiment. Recommended to not leave higher than 7 for extended time as this will force a cold start measurement, which is longer and uses mechanical relay switches.")
            
        self.add_parameter("voltage",
                           get_cmd=self._get_voltage,
                           set_cmd="VOLTAGE {}",
                           vals=Numbers(min_value=0, max_value=15),
                           get_parser=float,
                           docstring="Limits the maximum voltage applied to the DUT. Lower voltage is better for higher capacitance or loss.")
    
    
    def _get_single(self) -> str:
        return self.ask("SINGLE").split(",")[:-1]
    
    def _get_capacitance(self)-> float:
        
        a = self._get_single()[0]
        try:
            return float(a.split("=")[1].split(" ")[0])
        except ValueError:
            return float(a.split("=")[1].split(" ")[1])
    
    def _get_loss(self)-> float:
        a = self._get_single()[1]
        try:
            return float(a.split("=")[1].split(" ")[0])
        except ValueError:
            return float(a.split("=")[1].split(" ")[1])
    
    def _show(self, param: str) -> str: #maybe I will make it so it can be used with partial instead of individual commands for each param later
        return self.ask(f"SHOW {param}")
    
    def _get_average(self) -> int:
        avg = self._show("AVERAGE")
        return int(avg.split(" ")[-1])
    
    def _get_voltage(self) -> float:
        v = self._show("VOLTAGE")
        return float(v.split(" ")[-1])
    
    def averages_converter(self, avgs: int, cold_start = False) -> float:
        
        """
        simple function that converts the averaging time integer to seconds,
        which depends on warm or cold start. By default the bridge tries
        a warm start, but can be forced into cold start with averaging > 7
        """
        
        _avg_cold = {0: 0.36, 1: 0.4, 2: 0.45, 3: 0.53, 4: 0.63,
                     5: 0.79, 6: 1.10, 7: 1.64, 8: 2.5, 9: 4.0, 10: 6.9,
                     11: 12, 12: 23, 13: 44, 14: 85, 15: 184}
        _avg_warm = {0: 0.038, 1: 0.056, 2: 0.084, 3: 0.133, 4: 0.215,
                     5: 0.35, 6: 0.58}   
        
        if avgs > 6:
            cold_start == True
        else:
            pass
        
        if cold_start == True:
            return _avg_cold[avgs]
        else:
            return _avg_warm[avgs]
    
