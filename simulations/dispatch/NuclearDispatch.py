# -*- coding: utf-8 -*-
"""
Pyomo real-time dispatch model


Model authors:
* Mike Wagner - UW-Madison
* Bill Hamilton - NREL 
* John Cox - Colorado School of Mines
* Alex Zolan - NREL

Pyomo code by Alex Zolan
Modified by Gabriel Soto
"""
from dispatch.GeneralDispatch import GeneralDispatch
from dispatch.GeneralDispatch import GeneralDispatchParamWrap
import pyomo.environ as pe
import numpy as np
from util.FileMethods import FileMethods

class NuclearDispatch(GeneralDispatch):
    
    def __init__(self, params, unitRegistry):
        
        # initialize Generic module, csv data arrays should be saved here
        GeneralDispatch.__init__( self, params, unitRegistry )

# =============================================================================
# Dispatch Wrapper
# =============================================================================

class NuclearDispatchParamWrap(GeneralDispatchParamWrap):
    
    def __init__(self, unit_registry, SSC_dict=None, PySAM_dict=None, pyomo_horizon=48, 
                   dispatch_time_step=1):
        
        GeneralDispatchParamWrap.__init__( self, unit_registry, SSC_dict, PySAM_dict, 
                            pyomo_horizon, dispatch_time_step )


    def set_fixed_cost_parameters(self, param_dict):
        
        # grabbing unit registry set up in GeneralDispatch
        u = self.u
    
        # set up costs from parent class
        param_dict = GeneralDispatchParamWrap.set_fixed_cost_parameters( self, param_dict )
        
        # TODO: for now, scaling everything from LORE files
        old_Q_ref = 120 * u.MW / 0.409
        Q_ratio   = (self.q_rec_design / old_Q_ref ).to('')
        
        # TODO: old values from LORE files
        C_rec  = Q_ratio * 0.002  * u.USD/u.kWh        
        C_rsu  = Q_ratio * 950    * u.USD
        C_rhsp = Q_ratio * 950/5. * u.USD

        ### Cost Parameters ###
        param_dict['Crec']   = C_rec.to('USD/kWh')  #C^{rec}: Operating cost of heliostat field and receiver [\$/kWt$\cdot$h]
        param_dict['Crsu']   = C_rsu.to('USD')      #C^{rsu}: Penalty for receiver cold start-up [\$/start]
        param_dict['Crhsp']  = C_rhsp.to('USD')     #C^{rhsp}: Penalty for receiver hot start-up [\$/start]

        return param_dict
        

    def set_nuclear_parameters(self, param_dict):
        
        # grabbing unit registry set up in GeneralDispatch
        u = self.u 
        
        time_fix = 1*u.hr                  # TODO: we're missing a time term to fix units
        dw_rec_pump             = 0*u.MW   # TODO: Pumping parasitic at design point reciever mass flow rate (MWe)
        tower_piping_ht_loss    = 0*u.kW   # TODO: Tower piping heat trace full-load parasitic load (kWe) 
        q_rec_standby_fraction  = 0.       # TODO: Receiver standby energy consumption (fraction of design point thermal power)
        q_rec_shutdown_fraction = 0.       # TODO: Receiver shutdown energy consumption (fraction of design point thermal power)
        
        self.deltal = self.SSC_dict['rec_su_delay']*u.hr
        self.Ehs    = self.SSC_dict['p_start']*u.kWh
        self.Er     = self.SSC_dict['rec_qf_delay'] * self.q_rec_design * time_fix
        self.Eu     = self.SSC_dict['tshours']*u.hr * self.q_pb_design
        self.Lr     = dw_rec_pump / self.q_rec_design
        self.Qrl    = self.SSC_dict['f_rec_min'] * self.q_rec_design * time_fix
        self.Qrsb   = q_rec_standby_fraction  * self.q_rec_design * time_fix
        self.Qrsd   = q_rec_shutdown_fraction * self.q_rec_design * time_fix
        self.Qru    = self.Er / self.deltal  
        self.Wh     = self.SSC_dict['p_track']*u.kW
        self.Wht    = tower_piping_ht_loss
        
        ### CSP Field and Receiver Parameters ###
        param_dict['deltal'] = self.deltal.to('hr')    #\delta^l: Minimum time to start the receiver [hr]
        param_dict['Ehs']    = self.Ehs.to('kWh')      #E^{hs}: Heliostat field startup or shut down parasitic loss [kWe$\cdot$h]
        param_dict['Er']     = self.Er.to('kWh')       #E^r: Required energy expended to start receiver [kWt$\cdot$h]
        param_dict['Eu']     = self.Eu.to('kWh')       #E^u: Thermal energy storage capacity [kWt$\cdot$h]
        param_dict['Lr']     = self.Lr.to('')          #L^r: Receiver pumping power per unit power produced [kWe/kWt]
        param_dict['Qrl']    = self.Qrl.to('kWh')      #Q^{rl}: Minimum operational thermal power delivered by receiver [kWt$\cdot$h]
        param_dict['Qrsb']   = self.Qrsb.to('kWh')     #Q^{rsb}: Required thermal power for receiver standby [kWt$\cdot$h]
        param_dict['Qrsd']   = self.Qrsd.to('kWh')     #Q^{rsd}: Required thermal power for receiver shut down [kWt$\cdot$h] 
        param_dict['Qru']    = self.Qru.to('kW')      #Q^{ru}: Allowable power per period for receiver start-up [kWt$\cdot$h]
        param_dict['Wh']     = self.Wh.to('kW')        #W^h: Heliostat field tracking parasitic loss [kWe]
        param_dict['Wht']    = self.Wht.to('kW')       #W^{ht}: Tower piping heat trace parasitic loss [kWe]
        
        return param_dict
    
    
    def set_time_series_nuclear_parameters(self, param_dict, solar_resource_filepath, df_array, ud_array):
        
        #MAKE SURE TO CALL THIS METHOD AFTER THE NUCLEAR PARAMETERS 
        u = self.u
        
        # self.delta_rs = np.zeros(n)
        # self.delta_cs = np.zeros(n)
        self.Drsu       = 1*u.hr   # Minimum time to start the receiver (hr)
        self.P          = df_array*u.USD/u.kWh
        self.Qin        = np.array([self.q_rec_design.magnitude]*self.T)*self.q_rec_design.units
        self.Qc         = self.Ec / np.ceil(self.SSC_dict['startup_time']*u.hr / np.min(self.Delta)) / np.min(self.Delta) #TODO: make sure Ec is called correctly
        self.Wdotnet    = [1.e10 for j in range(self.T)] *u.kW
        self.W_u_plus   = [(self.Wdotl + self.W_delta_plus*0.5*dt).to('kW').magnitude for dt in self.Delta]*u.kW
        self.W_u_minus  = [(self.Wdotl + self.W_delta_minus*0.5*dt).to('kW').magnitude for dt in self.Delta]*u.kW
        
        n  = len(self.Delta)
        wt = 0.999
        delta_rs = np.zeros(n)
        D        = np.zeros(n)
        
        # grab dry bulb temperature from solar resource file 
        Tdry = FileMethods.read_solar_resource_file(solar_resource_filepath, u) 
        t_start = int(0) # TODO: have currentTime tracker
        t_end   = int(self.pyomo_horizon.to('hr').magnitude)
        time_slice = slice(t_start,t_end,1)
        Tdry = Tdry[time_slice] 
        
        etamult, wmult = self.get_ambient_T_corrections_from_udpc_inputs( Tdry, ud_array ) # TODO:verify this makes sense
        self.etaamb = etamult * self.SSC_dict['design_eff']
        self.etac   = wmult * self.SSC_dict['ud_f_W_dot_cool_des']/100.

        for t in range(n):
            Ein = self.Qin[t]*self.Delta[t]
            E_compare = (self.Er / max(1.*u.kWh, Ein.to('kWh'))).to('')
            delta_rs[t] = min(1., max( E_compare, self.Drsu/self.Delta[t]))
            D[t]        = wt**(self.Delta_e[t]/u.hr)
        
        self.delta_rs   = delta_rs
        self.D          = D
        
        
        ### Time series CSP Parameters ###
        param_dict['delta_rs']  = self.delta_rs   #\delta^{rs}_{t}: Estimated fraction of period $t$ required for receiver start-up [-]
        param_dict['D']         = self.D          #D_{t}: Time-weighted discount factor in period $t$ [-]
        param_dict['etaamb']    = self.etaamb     #\eta^{amb}_{t}: Cycle efficiency ambient temperature adjustment factor in period $t$ [-]
        param_dict['etac']      = self.etac       #\eta^{c}_{t}: Normalized condenser parasitic loss in period $t$ [-] 
        param_dict['P']         = self.P.to('USD/kWh')    #P_{t}: Electricity sales price in period $t$ [\$/kWh]
        param_dict['Qin']       = self.Qin.to('kW')       #Q^{in}_{t}: Available thermal power generated by the CSP heliostat field in period $t$ [kWt]
        param_dict['Qc']        = self.Qc.to('kW')        #Q^{c}_{t}: Allowable power per period for cycle start-up in period $t$ [kWt]
        param_dict['Wdotnet']   = self.Wdotnet.to('kW')   #\dot{W}^{net}_{t}: Net grid transmission upper limit in period $t$ [kWe]
        param_dict['W_u_plus']  = self.W_u_plus.to('kW')  #W^{u+}_{t}: Maximum power production when starting generation in period $t$  [kWe]
        param_dict['W_u_minus'] = self.W_u_minus.to('kW') #W^{u-}_{t}: Maximum power production in period $t$ when stopping generation in period $t+1$  [kWe]
        
        return param_dict


    def set_initial_state(self, param_dict):
        
        u = self.u
        # can re-use this method by choosing self.SSC_dict if t ==0
        #       or some input dict otherwise
        
        # TES masses, temperatures, specific heat
        m_hot  = self.m_tes_design * (self.SSC_dict['csp.pt.tes.init_hot_htf_percent']/100)        # Available active mass in hot tank
        T_tes_hot_init  = (self.SSC_dict['T_tank_hot_init']*u.celsius).to('degK')
        T_tes_init  = 0.5*(T_tes_hot_init + self.T_htf_cold)
        cp_tes_init = self.get_cp_htf(T_tes_init) 
        
        # important parameters
        e_pb_suinitremain  = self.SSC_dict['pc_startup_energy_remain_initial']*u.kWh
        s_current          = m_hot * cp_tes_init * (T_tes_hot_init - self.T_htf_cold) # TES capacity
        s0                 = min(self.Eu.to('kWh'), s_current.to('kWh')  )
        wdot0              = 0*u.MW #TODO: subsequent calls?
        yr0                = (self.SSC_dict['rec_op_mode_initial'] == 2)
        yrsb0              = False   # TODO: try to use Ty's changes to daotk
        yrsu0              = (self.SSC_dict['rec_op_mode_initial'] == 1)
        y0                 = (self.SSC_dict['pc_op_mode_initial'] == 1) 
        ycsb0              = (self.SSC_dict['pc_op_mode_initial'] == 2) 
        ycsu0              = (self.SSC_dict['pc_op_mode_initial'] == 0 or self.SSC_dict['pc_op_mode_initial'] == 4) 
        disp_pc_persist0   = 0
        disp_pc_off0       = 0
        Yu0                = disp_pc_persist0 if y0 else 0.0
        Yd0                = disp_pc_off0 if (not y0) else 0.0
        t_rec_suinitremain = self.SSC_dict['rec_startup_time_remain_init']*u.hr
        e_rec_suinitremain = self.SSC_dict['rec_startup_energy_remain_init']*u.Wh
        rec_accum_time     = max(0.0, self.Drsu - t_rec_suinitremain )
        rec_accum_energy   = max(0.0, self.Er - e_rec_suinitremain )
        # yrsd0             = False 
        # disp_rec_persist0 = 0 
        # drsu0             = disp_rec_persist0 if yrsu0 else 0.0   
        # drsd0             = disp_rec_persist0 if self.SSC_dict['rec_op_mode_initial'] == 0 else 0.0
        
        # defining parameters
        self.s0    = s0              #s_0: Initial TES reserve quantity  [kWt$\cdot$h]
        self.wdot0 = wdot0.to('kW')  #\dot{w}_0: Initial power cycle electricity generation [kWe] 
        self.yr0   = yr0             #y^r_0: 1 if receiver is generating ``usable'' thermal power initially, 0 otherwise 
        self.yrsb0 = yrsb0           #y^{rsb}_0: 1 if receiver is in standby mode initially, 0 otherwise
        self.yrsu0 = yrsu0           #y^{rsu}_0: 1 if receiver is in starting up initially, 0 otherwise
        self.y0    = y0              #y_0: 1 if cycle is generating electric power initially, 0 otherwise   
        self.ycsb0 = ycsb0           #y^{csb}_0: 1 if cycle is in standby mode initially, 0 otherwise
        self.ycsu0 = ycsu0           #y^{csu}_0: 1 if cycle is in starting up initially, 0 otherwise
        self.Yu0   = Yu0*u.hr        #Y^u_0: duration that cycle has been generating electric power [h]
        self.Yd0   = Yd0*u.hr        #Y^d_0: duration that cycle has not been generating power (i.e., shut down or in standby mode) [h]
        # self.yrsd0 = yrsd0  # TODO: do we need this? doesn't exist in current GeneralDispatch
        # self.drsu0 = drsu0  # TODO: need this? Duration that receiver has been starting up before the problem horizon (h)
        # self.drsd0 = drsd0  
        
        # Initial cycle startup energy accumulated
        tol = 1.e-6
        if np.isnan(e_pb_suinitremain): # SSC seems to report NaN when startup is completed
            self.ucsu0 = self.Ec
        else:   
            self.ucsu0 = max(0.0, self.Ec - e_rec_suinitremain ) 
            if self.ucsu0 > (1.0 - tol)*self.Ec:
                self.ucsu0 = self.Ec
        

        # Initial receiver startup energy inventory
        self.ursu0 = min(rec_accum_energy, rec_accum_time * self.Qru)  # Note, SS receiver model in ssc assumes full available power is used for startup (even if, time requirement is binding)
        if self.ursu0 > (1.0 - 1.e-6)*self.Er:
            self.ursu0 = self.Er

        # self.ursd0 = 0.0  
        
        param_dict['s0']     = self.s0.to('kWh')      #s_0: Initial TES reserve quantity  [kWt$\cdot$h]
        param_dict['ucsu0']  = self.ucsu0.to('kWh')   #u^{csu}_0: Initial cycle start-up energy inventory  [kWt$\cdot$h]
        param_dict['ursu0']  = self.ursu0.to('kWh')   #u^{rsu}_0: Initial receiver start-up energy inventory [kWt$\cdot$h]
        param_dict['wdot0']  = self.wdot0.to('kW')    #\dot{w}_0: Initial power cycle electricity generation [kW]e
        param_dict['yr0']    = self.yr0         #y^r_0: 1 if receiver is generating ``usable'' thermal power initially, 0 otherwise
        param_dict['yrsb0']  = self.yrsb0       #y^{rsb}_0: 1 if receiver is in standby mode initially, 0 otherwise
        param_dict['yrsu0']  = self.yrsu0       #y^{rsu}_0: 1 if receiver is in starting up initially, 0 otherwise
        param_dict['y0']     = self.y0          #y_0: 1 if cycle is generating electric power initially, 0 otherwise
        param_dict['ycsb0']  = self.ycsb0       #y^{csb}_0: 1 if cycle is in standby mode initially, 0 otherwise
        param_dict['ycsu0']  = self.ycsu0       #y^{csu}_0: 1 if cycle is in starting up initially, 0 otherwise
        param_dict['Yu0']    = self.Yu0.to('hr')      #Y^u_0: duration that cycle has been generating electric power [h]
        param_dict['Yd0']    = self.Yd0.to('hr')      #Y^d_0: duration that cycle has not been generating power (i.e., shut down or in standby mode) [h]
        param_dict['wdot_s_prev']    = 0*u.hr         #\dot{w}^{s,prev}: previous $\dot{w}^s$, or energy sold to grid [kWe]
        
        return param_dict
