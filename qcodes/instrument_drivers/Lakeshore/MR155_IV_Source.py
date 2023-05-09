# -*- coding: utf-8 -*-
"""
Created on Tue Apr 25 16:36:31 2023

@author: asher.jennings@riken.jp
simple qcodes driver for the MeasurementReady 155 I/V Source
currently only commands related to voltage is set


"""

#import logging
#from enum import IntEnum
from typing import Any

from qcodes.instrument.visa import VisaInstrument
from qcodes.utils.validators import Ints, Numbers, Enum
#from qcodes.instrument.parameter import Parameter, ArrayParameter, \
#    ParameterWithSetpoints
    

class MR155(VisaInstrument):
    def __init__(self,
                 name: str,
                 address: str,
                 terminator: str = '\r\n',
                 **kwargs: Any):
        """
        Args:
            name: Name of the instrument.
            **kwargs:
        """
        super().__init__(name, address, terminator=terminator, **kwargs)
        
        self.add_parameter('output',
                           label='Output',
                           get_cmd="OUTP:STAT?",
                           set_cmd="OUTP:STAT {}",
                           vals=Ints(0, 1),
                           docstring='Turns on the output of the generator')
        
        self.add_parameter('shape',
                           label='Shape',
                           get_cmd="SOUR:FUNC?",
                           set_cmd="SOUR:FUNC {}",
                           vals=Enum("DC", "SIN", "SINUSOID"),
                           docstring='DC for DC mod, SINusoid for sine AC mode')
        
        self.add_parameter('frequency',
                           label='Frequency',
                           unit="Hz",
                           get_cmd="SOUR:FREQ?",
                           set_cmd="SOUR:FREQ {}",
                           get_parser=float,
                           vals=Numbers(100e-3, 100e3),
                           docstring='Turns on the output of the generator')
        
        self.add_parameter('mode',
                           label='Mode',
                           get_cmd="SOUR:FUNC:MODE?",
                           set_cmd="SOUR:FUNC:MODE {}",
                           vals=Enum("VOLT", "CURR", "VOLTAGE", "CURRENT"),
                           docstring='VOLTage for voltage mode, CURRent for current mode.')
        
        self.add_parameter('voltage',
                           label='Voltage',
                           unit="V",
                           get_cmd="SOUR:VOLT?",
                           set_cmd="SOUR:VOLT {}",
                           get_parser=float,
                           vals=Numbers(-100, 100),
                           docstring="Sets the output voltage amplitude in AC mode,"
                                      "or the whole voltage in DC move."
                                      "-100 V to +100 V.")
        
        self.add_parameter('offset',
                           label='Offset',
                           unit="V"
                           get_cmd="SOUR:VOLT:OFFS?",
                           set_cmd="SOUR:VOLT:OFFS {}",
                           get_parser=float,
                           vals=Numbers(-100, 100),
                           docstring='The DC offset when in AC mode. Does nothing in DC mode.'
                                     "-100 V to +100 V")
        
        self.add_parameter('voltage_limit',
                           label='Voltage Limit',
                           unit="V",
                           get_cmd="SOUR:VOLT:LIM?",
                           set_cmd="SOUR:VOLT:LIM {}",
                           get_parser=float,
                           vals=Numbers(0, 100),
                           docstring='Sets a maximum bound for the voltage output.')
        
        self.add_parameter('voltage_range',
                           label='Voltage Range',
                           unit="V",
                           get_cmd="SOUR:VOLT:RANG?",
                           set_cmd="SOUR:VOLT:RANG {}",
                           get_parser=float,
                           vals=Numbers(),
                           docstring='Sets voltage range from 0.01, 0.1, 1, 10, 100 V.'
                                     "Auto rounds up.")
        
        self.add_parameter('autorange',
                           label='Autorange',
                           get_cmd="SOUR:VOLT:RANG:AUTO?",
                           set_cmd="SOUR:VOLT:RANG:AUTO {}",
                           vals=Ints(0, 1),
                           docstring='Turns on the voltage autorange of the generator')        
        
        self.add_parameter('voltage_protection',
                           label='Voltage Protection',
                           unit="A",
                           get_cmd="SOUR:VOLT:PROT?",
                           set_cmd="SOUR:VOLT:PROT {}",
                           get_parser=float,
                           vals=Numbers(100e-9, 100e-3),
                           docstring='Sets DC current limit.')
        
