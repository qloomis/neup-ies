#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 13 09:35:14 2021

@author: gabrielsoto
"""

import modules.NuclearTES as NuclearTES
import os, time
import pint
import numpy as np
u = pint.UnitRegistry()
import pickle
from util.FileMethods import FileMethods

pid = os.getpid()
print("PID = ", pid)

# =============================================================================
#     Run Simulation
# =============================================================================

# setting up arrays to cycle through
dispatch  = np.array([ True, True, False ])
tshours   = np.array([ 10, 12, 14, 16, 18])
p_mult    = np.array([ 1.05, 1.15, 1.25, 1.35, 1.45])

# SSC and dispatch horizons for each dispatch element above ^
sscH = np.array([12, 24, 24])
pyoH = np.array([24, 48, 48])

# baseline cycle power output
P_ref = 465

# formally defining the iterator arrays
iterator1 = tshours 
iterator2 = p_mult

# initializing an empty array
empty = np.zeros([  len(dispatch) , len(iterator1), len(iterator2) ])

# initializing output arrays
annual_energy_array = empty.copy()
ppa_array           = empty.copy()
lcoe_nom_array      = empty.copy()
npv_aftertax        = empty.copy()
flip_actual_irr     = empty.copy()
flip_actual_year    = empty.copy()
irr_aftertax        = empty.copy()
cost_installed      = empty.copy()
size_of_equity      = empty.copy()
size_of_debt        = empty.copy()


# starting the time counter
tic = time.perf_counter()

# TRIPLE LOOP
for d,dp in enumerate(dispatch): #over dispatch type
    for i,th in enumerate(iterator1): #over TES size
        for j,fm in enumerate(iterator2): #over Cycle output power
            
            # print current position in loop
            print("dispatch :      ", dp)
            print("tshours :       ", th)
            print("output mult :   ", fm)
            
            # defining directories
            nuctes = NuclearTES.NuclearTES(is_dispatch=dp)
            
            # horizons
            nuctes.PySAM_dict['ssc_horizon']   = sscH[d]
            nuctes.ssc_horizon   = sscH[d] * nuctes.u.hr
            nuctes.PySAM_dict['pyomo_horizon'] = pyoH[d]
            nuctes.pyomo_horizon = pyoH[d] * nuctes.u.hr

            # have to redo this step from the init
            nuctes.dispatch_wrap = nuctes.create_dispatch_wrapper( nuctes.PySAM_dict )
            
            # update SSC dictionary parameters
            nuctes.SSC_dict['P_ref'] = fm*P_ref
            nuctes.SSC_dict['tshours'] = th
            
            # run simulation
            nuctes.run_sim( run_loop=True )
            nt = nuctes.Plant
            so = nuctes.SO
            
            # log outputs
            annual_energy_array[d,i,j] = (nt.Outputs.annual_energy*u.kWh).to('TWh').m
            ppa_array[d,i,j]         = so.Outputs.ppa           # in cents/kWh
            lcoe_nom_array[d,i,j]    = so.Outputs.lcoe_nom      # in cents/kWh
            npv_aftertax[d,i,j]      = so.Outputs.project_return_aftertax_npv/1e6 #in million $
            flip_actual_irr[d,i,j]   = so.Outputs.flip_actual_irr   # in %
            flip_actual_year[d,i,j]  = so.Outputs.flip_actual_year  # in yr
            irr_aftertax[d,i,j]      = so.Outputs.project_return_aftertax_irr  # in %
            cost_installed [d,i,j]   = so.Outputs.cost_installed/1e6  #in million $
            size_of_equity[d,i,j]    = so.Outputs.size_of_equity/1e6  #in million $
            size_of_debt[d,i,j]      = so.Outputs.size_of_debt/1e6    #in million $

            # reset the Plant and Grid, prevents memory leak
            del nuctes
            del nt
            del so

# end time counter
toc = time.perf_counter()        

# print out time elapsed and store it (current record is 5.6 hours)
time_elapsed = ((toc-tic)*u.s).to('hr')
print('Made it past the triple loop. Time %.2f hrs' % time_elapsed.m)

# =============================================================================
# Storing Data
# =============================================================================

# storage dictionary
Storage = {}
Storage['time_elapsed'] = time_elapsed
Storage['dispatch'] = dispatch
Storage['tshours']  = tshours
Storage['p_mult'] = p_mult
Storage['P_ref']  = P_ref
Storage['iterator1']  = iterator1
Storage['iterator2']  = iterator2
Storage['sscH']   = sscH
Storage['pyoH']   = pyoH
Storage['annual_energy_array'] = annual_energy_array
Storage['ppa_array']           = ppa_array
Storage['lcoe_nom_array']      = lcoe_nom_array
Storage['npv_aftertax']        = npv_aftertax
Storage['flip_actual_irr']     = flip_actual_irr
Storage['flip_actual_year']    = flip_actual_year
Storage['irr_aftertax']        = irr_aftertax
Storage['cost_installed']      = cost_installed
Storage['size_of_equity']      = size_of_equity
Storage['size_of_debt']        = size_of_debt

# locating output directory
output_dir = FileMethods.output_dir
filename   = 'pricePerfvsDispatch_sizingTESandCycle_irr11pct.nuctes' 
NTPath = os.path.join(output_dir, filename)

# pickling
with open(NTPath, 'wb') as f:
    pickle.dump(Storage, f)
    

