#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 14:03:51 2021

@author: gabrielsoto
"""

import sys, copy
sys.path.append('..')
import numpy as np
import PySAM.NuclearMsptTes as NuclearMsptTes
from modules.GenericSSCModule import GenericSSCModule
from modules.NuclearTES import NuclearTES
from modules.SolarTES import SolarTES

class DualPlantTES(SolarTES): 
    """
    The DualPlantTES class intializes, updates, and runs SSC simulations through PySAM,
    specifically for the SSC nuclear_mspt_tes module. 
    
    This is meant to simulate the intermediate cycle where the Nuclear and Solar 
    plants are both directly connected to the storage tank - power cycle loop. 
    That is, the Nuclear and Solar Power Tower heat parallel mass flows
    of molten salt via respective heat exchangers. Each molten salt mass flow
    then routes directly to the hot storage tank where it can be dispatched
    out to the power cycle. 
    """

    def __init__(self, plant_name="nuclear_mspt_tes", json_name="model2", is_dispatch=False):
        """ Initializes the DualPlantTES module
        
        Inputs:
            plant_name (str)         : name of SSC module to run 
            json_name (str)          : name of JSON script with input data for module
            is_dispatch (bool)       : boolean, if True runs Pyomo dispatch optimization
        """
        
        # initialize Solar+Nuclear+Generic module, csv data arrays should be saved here
        SolarTES.__init__( self, plant_name, json_name, is_dispatch )
        
        # define specific PySAM module to be called later
        self.PySAM_Module = NuclearMsptTes


    def update_Plant_after_SSC(self):
        """ Update SSC Plant inputs with SSC outputs from previous segment simulation
        
        ** self.run_loop == True
        
        This method uses the SSC end results from the previous simulation segment
        and sets them as the initial conditions for the next SSC segment. As a 
        small note: some outputs are arrays that span the full year, however the
        only relevant parts are the first indeces corresponding to the SSC Horizon.
        All other values are typically 0. 
        """
        
        ssc_slice = self.slice_ssc_firstH
        
        # field and receiver initial conditions
        self.Plant.SystemControl.rec_op_mode_initial              = self.Plant.Outputs.rec_op_mode_final
        self.Plant.SystemControl.rec_startup_time_remain_init     = self.Plant.Outputs.rec_startup_time_remain_final
        self.Plant.SystemControl.rec_startup_energy_remain_init   = self.Plant.Outputs.rec_startup_energy_remain_final
        self.Plant.SystemControl.is_field_tracking_init           = self.Plant.Outputs.is_field_tracking_final
        
        # nuclear initial conditions
        self.Plant.SystemControl.nuc_op_mode_initial              = self.Plant.Outputs.nuc_op_mode_final
        self.Plant.SystemControl.nuc_startup_time_remain_init     = self.Plant.Outputs.nuc_startup_time_remain_final
        self.Plant.SystemControl.nuc_startup_energy_remain_init   = self.Plant.Outputs.nuc_startup_energy_remain_final
        
        # TES initial conditions
        self.Plant.SystemControl.T_tank_cold_init                 = self.Plant.Outputs.T_tes_cold[ssc_slice][-1]
        self.Plant.SystemControl.T_tank_hot_init                  = self.Plant.Outputs.T_tes_hot[ssc_slice][-1]
        self.Plant.ThermalStorage.csp_pt_tes_init_hot_htf_percent = self.Plant.Outputs.hot_tank_htf_percent_final
        
        # PC initial conditions
        self.Plant.SystemControl.pc_op_mode_initial               = self.Plant.Outputs.pc_op_mode_final
        self.Plant.SystemControl.pc_startup_energy_remain_initial = self.Plant.Outputs.pc_startup_time_remain_final
        self.Plant.SystemControl.pc_startup_time_remain_init      = self.Plant.Outputs.pc_startup_energy_remain_final
        
        
    def initialize_arrays(self):
        """ Initializing empty arrays to log SSC outputs after segment simulations
        
        This method creates empty arrays where SSC outputs will be written to.
        Also creates a list of str names for logged simulation outputs.
        
        """
        
        u = self.u
        
        # start and end times for full simulation
        i_start = (self.SSC_dict['time_start'] * u.s).to('hr').m
        i_end   = (self.SSC_dict['time_stop'] * u.s).to('hr').m
        
        # size of simulation arrays
        N_sim = int( i_end - i_start )
        
        # dictionary of output variable names to log after each segment simulation
        self.Log_Arrays = {
        #    name of NE2 variable || name of SSC module variable
                'time_log':          'time_hr',          # logging time
                'gen_log':           'gen',              # electricity generation log
                'q_nuc_thermal_log': 'Q_nuc_thermal',    # thermal power from nuclear to HTF 
                'q_rec_thermal_log': 'Q_thermal',        # thermal power from receiver to HTF 
                'p_cycle_log' :      'P_cycle',          # PC electrical power output (gross)
                'q_dot_nuc_inc_log': 'q_dot_nuc_inc',    # Nuclear incident thermal power
                'q_dot_rec_inc_log': 'q_dot_rec_inc',    # Receiver incident thermal power
                'q_pb_log':          'q_pb',             # PC input energy
                'q_dot_pc_su_log' :  'q_dot_pc_startup', # PC startup thermal power
                'm_dot_pc_log' :     'm_dot_pc',         # PC HTF mass flow rate
                'm_dot_nuc_log'  :   'm_dot_nuc',        # Nuc mass flow rate
                'm_dot_rec_log'  :   'm_dot_rec',        # Rec mass flow rate
                'T_pc_in_log' :      'T_pc_in',          # PC HTF inlet temperature 
                'T_pc_out_log'   :   'T_pc_out',         # PC HTF outlet temperature
                'T_tes_cold_log':    'T_tes_cold',       # TES cold temperature
                'T_tes_hot_log'  :   'T_tes_hot',        # TES hot temperature
                'T_nuc_in_log':      'T_nuc_in',         # Nuclear HTF inlet temperature
                'T_nuc_out_log'  :   'T_nuc_out',        # Nuclear HTF outlet temperature
                'T_rec_in_log':      'T_rec_in',         # Receiver HTF inlet temperature
                'T_rec_out_log'  :   'T_rec_out',        # Receiver HTF outlet temperature
                'T_cond_out_log':    'T_cond_out',       # PC condenser water outlet temperature
                'e_ch_tes_log'  :    'e_ch_tes',         # TES charge state
                'op_mode_1_log' :    'op_mode_1',        # Operating Mode
                'defocus_log'   :    'defocus',          # Receiver Defocus fraction
                'eta_log'       :    'eta'               # PC efficiency, gross
            } if self.run_loop \
                 else {'gen_log':    'gen'  # electricity generation log
                      }
        
        # empty array to initalize log arrays
        empty_array = np.zeros(N_sim)
        
        # loop through keys in ^ dictionary, save the KEY name to NE2 module as empty array
        for key in self.Log_Arrays.keys():
            # meta: if we don't grab the copy of empty_array, it'll assign a pointer to the array!!
            setattr( self, key, empty_array.copy() ) 
            
        if self.log_dispatch_targets:
            self.Log_Target_Arrays = {
                   'is_rec_su_allowed_in' : empty_array.copy(),
                   'is_rec_sb_allowed_in' : empty_array.copy(),
                   'is_pc_su_allowed_in'  : empty_array.copy(),
                   'is_pc_sb_allowed_in'  : empty_array.copy(),
                   'q_pc_target_su_in'    : empty_array.copy(),
                   'q_pc_target_on_in'    : empty_array.copy(),
                   'q_pc_max_in'          : empty_array.copy()
                   }