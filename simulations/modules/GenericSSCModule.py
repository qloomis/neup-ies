#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 13:40:22 2021

@author: gabrielsoto
"""

import PySAM.GenericSystem as GenericSystem
import PySAM.Grid as Grid
import PySAM.Singleowner as Singleowner
import PySAM.PySSC as pssc
from util.FileMethods import FileMethods

class GenericSSCModule(object):
    
    def __init__(self, plant_name="generic_system", json_name="100mW_Generic"):
        
        # grab names, either default here or from child class
        self.json_name  = json_name
        self.plant_name = plant_name
        
        # read in dictionaries from json script
        PySAM_dict, SSC_dict = FileMethods.read_json( self.json_name )
        
        # save SSC_dict for usage later
        self.SSC_dict = SSC_dict
        
        # save csv arrays to class 
        self.get_csv_arrays( PySAM_dict )


    def run_single_sim(self):
        """ Method to run single simulation for Generic System
        """
        
        plant = self.create_plant_object( )
        plant.execute( )
        
        grid  = self.create_grid_object( plant )
        grid.execute( )
        
        so    = self.create_so_object( plant )
        so.execute( )
        
        return plant, grid, so
        
    def get_csv_arrays(self, input_dict):
        """ Method to get data from specified csv files
        
        Inputs:
            input_dict (dict) : dictionary with csv file names
        """
        
        # saving location of solar resource file for SSC input
        parent_dir = FileMethods.parent_dir
        self.solar_resource_file = parent_dir + input_dict['solar_resource_rel_parent']
        
        
    def create_plant_object(self):
        """ Method to create Plant object
        """
        
        # create plant data encoding for generic system
        plant_dat = pssc.dict_to_ssc_table( self.SSC_dict, self.plant_name )
        
        # create new Plant object
        plant = GenericSystem.wrap(plant_dat)
        
        return plant
    
    
    def create_grid_object(self, plant):
        """ Method to create Grid object
        
        Inputs:
            plant (obj) : object representing Plant
        """
        
        # create grid data encoding for grid
        grid_dat = pssc.dict_to_ssc_table( self.SSC_dict, "grid" )
        
        # create new Grid object from existing Plant object
        grid = Grid.from_existing( plant )
        
        # import Grid-specific data to Grid object
        grid.assign(Grid.wrap(grid_dat).export())
        
        return grid


    def create_so_object(self, plant):
        """ Method to create SingleOwner object
        
        Inputs:
            plant (obj) : object representing Plant
        """
        
        # create singleowner data encoding for singleowner object
        so_dat   = pssc.dict_to_ssc_table( self.SSC_dict, "singleowner" )
        
        # create new Singleowner object from existing Plant object
        so = Singleowner.from_existing( plant )
        
        # import Singleowner-specific data to Singleowner object
        so.assign(Singleowner.wrap(so_dat).export())
        
        return so
    
    
