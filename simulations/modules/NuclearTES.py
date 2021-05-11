#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 13:44:30 2021

@author: gabrielsoto
"""

import sys
sys.path.append('..')
import PySAM.NuclearTes as NuclearTes
from modules.GenericSSCModule import GenericSSCModule
from util.SSCHelperMethods import SSCHelperMethods
from dispatch.NuclearDispatch import NuclearDispatch as ND
from dispatch.NuclearDispatch import NuclearDispatchParamWrap as NDP
import PySAM.PySSC as pssc
from util.FileMethods import FileMethods

class NuclearTES(GenericSSCModule):
    
    def __init__(self, plant_name="nuclear_tes", json_name="model1"):
        
        # initialize Generic module, csv data arrays should be saved here
        GenericSSCModule.__init__( self, plant_name, json_name )

        
    def store_csv_arrays(self, input_dict):
        """ Method to get data from specified csv files and store in class
        
        Inputs:
            input_dict (dict) : dictionary with csv file names
        """
        
        # saving location of solar resource file for SSC input using parent class def
        GenericSSCModule.store_csv_arrays(self, input_dict)
        
        # read csv and save data to arrays
        samsim_dir = FileMethods.samsim_dir + '/'
        self.df_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['dispatch_factors_file'])
        self.ud_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['ud_file'])
        self.wl_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['wlim_file'])
        self.hp_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['helio_file'])
        self.gc_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['grid_file'])
        self.em_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['eta_file'])
        self.fm_array = FileMethods.read_csv_through_pandas(samsim_dir + input_dict['flux_file'])
        
        
    def create_Plant(self):
        """ Method to create Plant object for the first time
        """
        
        # create plant data encoding for generic system
        plant_dat = pssc.dict_to_ssc_table( self.SSC_dict, self.plant_name )
        
        # create new Plant object
        self.Plant = NuclearTes.wrap(plant_dat)
        
        # manually setting data arrays from csv files
        self.Plant.SolarResource.solar_resource_file         = self.solar_resource_file
        self.Plant.TimeOfDeliveryFactors.dispatch_factors_ts = self.df_array
        self.Plant.UserDefinedPowerCycle.ud_ind_od           = self.ud_array
        self.Plant.SystemControl.wlim_series                 = self.wl_array
        self.Plant.HeliostatField.helio_positions            = self.hp_array
        self.Plant.HeliostatField.eta_map                    = self.em_array
        self.Plant.HeliostatField.flux_maps                  = self.fm_array
        self.Plant.SystemControl.dispatch_series = [1.2]*8760


    def create_Grid(self):
        """ Method to create Grid object for the first time
        
        Inputs:
            plant (obj) : object representing Plant
        """
        
        # create grid data using parent class
        GenericSSCModule.create_Grid(self)
        
        #set curtailment to be really high
        self.Grid.GridLimits.grid_curtailment = self.gc_array  
        
    def run_pyomo(self, params):
        
        dispatch_model = ND(params, self.u)
        rt_results = dispatch_model.solve_model()
        
        self.rt_results = rt_results
        return rt_results


    def create_dispatch_wrapper(self, PySAM_dict):
        
        DispatchParameterClass = NDP
        
        dispatch_wrap = DispatchParameterClass( self.u, self.SSC_dict, PySAM_dict,
                    self.pyomo_horizon, self.dispatch_time_step)
        
        return dispatch_wrap

    
    def create_dispatch_params(self):
        
        DW = self.dispatch_wrap
        
        params = GenericSSCModule.create_dispatch_params(self)
        params = DW.set_nuclear_parameters( params )
        params = DW.set_time_series_nuclear_parameters( params, self.solar_resource_file, 
                                                       self.df_array, self.ud_array )
        params = DW.set_initial_state( params )
        
        
        return params