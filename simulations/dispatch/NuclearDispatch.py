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
import pyomo.environ as pe
from dispatch.GeneralDispatch import GeneralDispatch
from dispatch.GeneralDispatch import GeneralDispatchParamWrap
import numpy as np
from util.FileMethods import FileMethods
from util.SSCHelperMethods import SSCHelperMethods
import os, copy

class NuclearDispatch(GeneralDispatch):
    """
    The NuclearDispatch class is meant to set up and run Dispatch
    optimization as a mixed integer linear program problem using Pyomo,
    specifically for the NuclearTES NE2+SSC module.
    """
    
    def __init__(self, params, unitRegistry):
        """ Initializes the NuclearDispatch module
        
        Inputs:
            params (dict)                : dictionary of Pyomo dispatch parameters
            unitRegistry (pint.registry) : unique unit Pint unit registry
        """
        
        # initialize Generic module, csv data arrays should be saved here
        GeneralDispatch.__init__( self, params, unitRegistry )


    def generate_params(self, params):
        
        # generating GeneralDispatch parameters first (PowerCycle, etc.)
        GeneralDispatch.generate_params(self, params)
        
        # lambdas to convert units and data to proper syntax
        gd = self.gd
        gu = self.gu 
        
        ### Cost Parameters ### 
        self.model.Cnuc = pe.Param(mutable=True, initialize=gd("Cnuc"), units=gu("Cnuc"))              #C^{nuc}: Operating cost of nuclear plant [\$/kWt$\cdot$h]
        self.model.Cnsu = pe.Param(mutable=True, initialize=gd("Cnsu"), units=gu("Cnsu"))              #C^{nsu}: Penalty for nuclear cold start-up [\$/start]
        self.model.Cnhsp = pe.Param(mutable=True, initialize=gd("Cnhsp"), units=gu("Cnhsp"))           #C^{nhsp}: Penalty for nuclear hot start-up [\$/start]
        
        ### Nuclear Parameters ###
        self.model.deltanl = pe.Param(mutable=True, initialize=gd("deltanl"), units=gu("deltanl"))    #\delta^{nl}: Minimum time to start the nuclear plant [hr]
        self.model.Ehs = pe.Param(mutable=True, initialize=gd("Ehs"), units=gu("Ehs"))             #E^{hs}: Heliostat field startup or shut down parasitic loss [kWe$\cdot$h]
        self.model.En = pe.Param(mutable=True, initialize=gd("En"), units=gu("En"))                #E^n: Required energy expended to start nuclear plant [kWt$\cdot$h]
        self.model.Eu = pe.Param(mutable=True, initialize=gd("Eu"), units=gu("Eu"))                #E^u: Thermal energy storage capacity [kWt$\cdot$h]
        self.model.Ln = pe.Param(mutable=True, initialize=gd("Ln"), units=gu("Ln"))                #L^n: Nuclear pumping power per unit power produced [kWe/kWt]
        self.model.Qnl = pe.Param(mutable=True, initialize=gd("Qnl"), units=gu("Qnl"))             #Q^{nl}: Minimum operational thermal power delivered by nuclear [kWt$\cdot$h]
        self.model.Qnsb = pe.Param(mutable=True, initialize=gd("Qnsb"), units=gu("Qnsb"))          #Q^{nsb}: Required thermal power for nuclear standby [kWt$\cdot$h]
        self.model.Qnsd = pe.Param(mutable=True, initialize=gd("Qnsd"), units=gu("Qnsd"))          #Q^{nsd}: Required thermal power for nuclear shut down [kWt$\cdot$h] 
        self.model.Qnu = pe.Param(mutable=True, initialize=gd("Qnu"), units=gu("Qnu"))             #Q^{nu}: Allowable power per period for nuclear start-up [kWt$\cdot$h]
        self.model.Wh = pe.Param(mutable=True, initialize=gd("Wh"), units=gu("Wh"))                #W^h: Heliostat field tracking parasitic loss [kWe]
        self.model.Wnht = pe.Param(mutable=True, initialize=gd("Wnht"), units=gu("Wnht"))          #W^{nht}: Nuclear piping heat trace parasitic loss [kWe]

        ### Time series Nuclear Parameters ###
        self.model.delta_ns = pe.Param(self.model.T, mutable=True, initialize=gd("delta_ns"), units=gu("delta_ns"))     #\delta^{ns}_{t}: Estimated fraction of period $t$ required for nuclear start-up [-]
        self.model.D = pe.Param(self.model.T, mutable=True, initialize=gd("D"), units=gu("D"))                          #D_{t}: Time-weighted discount factor in period $t$ [-]
        self.model.etaamb = pe.Param(self.model.T, mutable=True, initialize=gd("etaamb"), units=gu("etaamb"))           #\eta^{amb}_{t}: Cycle efficiency ambient temperature adjustment factor in period $t$ [-]
        self.model.etac = pe.Param(self.model.T, mutable=True, initialize=gd("etac"), units=gu("etac"))                 #\eta^{c}_{t}: Normalized condenser parasitic loss in period $t$ [-] 
        self.model.P = pe.Param(self.model.T, mutable=True, initialize=gd("P"), units=gu("P"))                          #P_{t}: Electricity sales price in period $t$ [\$/kWh]
        self.model.Qin = pe.Param(self.model.T, mutable=True, initialize=gd("Qin"), units=gu("Qin"))                    #Q^{in}_{t}: Available thermal power generated by the CSP heliostat field in period $t$ [kWt]
        self.model.Qc = pe.Param(self.model.T, mutable=True, initialize=gd("Qc"), units=gu("Qc"))                       #Q^{c}_{t}: Allowable power per period for cycle start-up in period $t$ [kWt]
        self.model.Wdotnet = pe.Param(self.model.T, mutable=True, initialize=gd("Wdotnet"), units=gu("Wdotnet"))        #\dot{W}^{net}_{t}: Net grid transmission upper limit in period $t$ [kWe]
        self.model.W_u_plus = pe.Param(self.model.T, mutable=True, initialize=gd("W_u_plus"), units=gu("W_u_plus"))     #W^{u+}_{t}: Maximum power production when starting generation in period $t$  [kWe]
        self.model.W_u_minus = pe.Param(self.model.T, mutable=True, initialize=gd("W_u_minus"), units=gu("W_u_minus"))  #W^{u-}_{t}: Maximum power production in period $t$ when stopping generation in period $t+1$  [kWe]

        ### Initial Condition Parameters ###
        self.model.s0 = pe.Param(mutable=True, initialize=gd("s0"), units=gu("s0"))          #s_0: Initial TES reserve quantity  [kWt$\cdot$h]
        self.model.ucsu0 = pe.Param(mutable=True, initialize=gd("ucsu0"), units=gu("ucsu0")) #u^{csu}_0: Initial cycle start-up energy inventory  [kWt$\cdot$h]
        self.model.ursu0 = pe.Param(mutable=True, initialize=gd("ursu0"), units=gu("ursu0")) #u^{rsu}_0: Initial receiver start-up energy inventory [kWt$\cdot$h]
        self.model.wdot0 = pe.Param(mutable=True, initialize=gd("wdot0"), units=gu("wdot0")) #\dot{w}_0: Initial power cycle electricity generation [kW]e
        self.model.yr0 = pe.Param(mutable=True, initialize=gd("yr0"), units=gu("yr0"))       #y^r_0: 1 if receiver is generating ``usable'' thermal power initially, 0 otherwise  [az] this is new.
        self.model.yrsb0 = pe.Param(mutable=True, initialize=gd("yrsb0"), units=gu("yrsb0")) #y^{rsb}_0: 1 if receiver is in standby mode initially, 0 otherwise [az] this is new.
        self.model.yrsu0 = pe.Param(mutable=True, initialize=gd("yrsu0"), units=gu("yrsu0")) #y^{rsu}_0: 1 if receiver is in starting up initially, 0 otherwise    [az] this is new.
        self.model.y0 = pe.Param(mutable=True, initialize=gd("y0"), units=gu("y0"))          #y_0: 1 if cycle is generating electric power initially, 0 otherwise
        self.model.ycsb0 = pe.Param(mutable=True, initialize=gd("ycsb0"), units=gu("ycsb0")) #y^{csb}_0: 1 if cycle is in standby mode initially, 0 otherwise
        self.model.ycsu0 = pe.Param(mutable=True, initialize=gd("ycsu0"), units=gu("ycsu0")) #y^{csu}_0: 1 if cycle is in starting up initially, 0 otherwise    [az] this is new.
        self.model.Yu0 = pe.Param(mutable=True, initialize=gd("Yu0"), units=gu("Yu0"))       #Y^u_0: duration that cycle has been generating electric power [h]
        self.model.Yd0 = pe.Param(mutable=True, initialize=gd("Yd0"), units=gu("delta_ns"))  #Y^d_0: duration that cycle has not been generating power (i.e., shut down or in standby mode) [h]
        

    def generate_variables(self):
        
        # generating GeneralDispatch variables first (PowerCycle, etc.)
        GeneralDispatch.generate_variables(self)
        
        ### Decision Variables ###
        #------- Variables ---------
        self.model.ursu = pe.Var(self.model.T, domain=pe.NonNegativeReals)                             #u^{rsu}: Receiver start-up energy inventory at period $t$ [kWt$\cdot$h]
        self.model.xr = pe.Var(self.model.T, domain=pe.NonNegativeReals)	                           #x^r: Thermal power delivered by the receiver at period $t$ [kWt]
        self.model.xrsu = pe.Var(self.model.T, domain=pe.NonNegativeReals)                             #x^{rsu}: Receiver start-up power consumption at period $t$ [kWt]
         
        #------- Binary Variables ---------
        self.model.yr = pe.Var(self.model.T, domain=pe.Binary)        #y^r: 1 if receiver is generating ``usable'' thermal power at period $t$; 0 otherwise
        self.model.yrhsp = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rhsp}: 1 if receiver hot start-up penalty is incurred at period $t$ (from standby); 0 otherwise
        self.model.yrsb = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rsb}: 1 if receiver is in standby mode at period $t$; 0 otherwise
        self.model.yrsd = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rsd}: 1 if receiver is shut down at period $t$; 0 otherwise
        self.model.yrsu = pe.Var(self.model.T, domain=pe.Binary)      #y^{rsu}: 1 if receiver is starting up at period $t$; 0 otherwise
        self.model.yrsup = pe.Var(self.model.T, domain=pe.Binary)     #y^{rsup}: 1 if receiver cold start-up penalty is incurred at period $t$ (from off); 0 otherwise


    def add_objective(self):
        def objectiveRule(model):
            return (
                    sum( model.D[t] * 
                    #obj_profit
                    model.Delta[t]*model.P[t]*0.1*(model.wdot_s[t] - model.wdot_p[t])
                    #obj_cost_cycle_su_hs_sd
                    - (model.Ccsu*model.ycsup[t] + 0.1*model.Cchsp*model.ychsp[t] + model.alpha*model.ycsd[t])
                    #obj_cost_cycle_ramping
                    - (model.C_delta_w*(model.wdot_delta_plus[t]+model.wdot_delta_minus[t])+model.C_v_w*(model.wdot_v_plus[t] + model.wdot_v_minus[t]))
                    #obj_cost_rec_su_hs_sd
                    - (model.Cnuc*model.yrsup[t] + model.Cnhsp*model.yrhsp[t] + model.alpha*model.yrsd[t])
                    #obj_cost_ops
                    - model.Delta[t]*(model.Cpc*model.wdot[t] + model.Ccsb*model.Qb*model.ycsb[t] + model.Cnuc*model.xr[t] )
                    for t in model.T) 
                    )
        
        self.model.OBJ = pe.Objective(rule=objectiveRule, sense = pe.maximize)


    def addReceiverStartupConstraints(self):
        def rec_inventory_rule(model,t):
            if t == 1:
                return model.ursu[t] <= model.ursu0 + model.Delta[t]*model.xrsu[t]
            return model.ursu[t] <= model.ursu[t-1] + model.Delta[t]*model.xrsu[t]
        def rec_inv_nonzero_rule(model,t):
            return model.ursu[t] <= model.En * model.yrsu[t]
        def rec_startup_rule(model,t):
            if t == 1:
                return model.yr[t] <= model.ursu[t]/model.En + model.yr0 + model.yrsb0
            return model.yr[t] <= model.ursu[t]/model.En + model.yr[t-1] + model.yrsb[t-1]
        def rec_su_persist_rule(model,t):
            if t == 1: 
                return model.yrsu[t] + model.yr0 <= 1
            return model.yrsu[t] +  model.yr[t-1] <= 1
        def ramp_limit_rule(model,t):
            return model.xrsu[t] <= model.Qnu*model.yrsu[t]
        def nontrivial_solar_rule(model,t):
            return model.yrsu[t] <= model.Qin[t]
        self.model.rec_inventory_con = pe.Constraint(self.model.T,rule=rec_inventory_rule)
        self.model.rec_inv_nonzero_con = pe.Constraint(self.model.T,rule=rec_inv_nonzero_rule)
        self.model.rec_startup_con = pe.Constraint(self.model.T,rule=rec_startup_rule)
        self.model.rec_su_persist_con = pe.Constraint(self.model.T,rule=rec_su_persist_rule)
        self.model.ramp_limit_con = pe.Constraint(self.model.T,rule=ramp_limit_rule)
        self.model.nontrivial_solar_con = pe.Constraint(self.model.T,rule=nontrivial_solar_rule)
        
        
    def addReceiverSupplyAndDemandConstraints(self):
        def rec_production_rule(model,t):
            return model.xr[t] + model.xrsu[t] + model.Qnsd*model.yrsd[t] <= model.Qin[t]
        def rec_generation_rule(model,t):
            return model.xr[t] <= model.Qin[t] * model.yr[t]
        def min_generation_rule(model,t):
            return model.xr[t] >= model.Qnl * model.yr[t]
        def rec_gen_persist_rule(model,t):
            return model.yr[t] <= model.Qin[t]/model.Qnl
        self.model.rec_production_con = pe.Constraint(self.model.T,rule=rec_production_rule)
        self.model.rec_generation_con = pe.Constraint(self.model.T,rule=rec_generation_rule)
        self.model.min_generation_con = pe.Constraint(self.model.T,rule=min_generation_rule)
        self.model.rec_gen_persist_con = pe.Constraint(self.model.T,rule=rec_gen_persist_rule)
        
        
    def addReceiverNodeLogicConstraints(self):
        def rec_su_sb_persist_rule(model,t):
            return model.yrsu[t] + model.yrsb[t] <= 1
        def rec_sb_persist_rule(model,t):
            return model.yr[t] + model.yrsb[t] <= 1
        def rsb_persist_rule(model,t):
            if t == 1:
                return model.yrsb[t] <= (model.yr0 + model.yrsb0) 
            return model.yrsb[t] <= model.yr[t-1] + model.yrsb[t-1]
        def rec_su_pen_rule(model,t):
            if t == 1:
                return model.yrsup[t] >= model.yrsu[t] - model.yrsu0 
            return model.yrsup[t] >= model.yrsu[t] - model.yrsu[t-1]
        def rec_hs_pen_rule(model,t):
            if t == 1:
                return model.yrhsp[t] >= model.yr[t] - (1 - model.yrsb0)
            return model.yrhsp[t] >= model.yr[t] - (1 - model.yrsb[t-1])
        def rec_shutdown_rule(model,t):
            current_Delta = model.Delta[t]
            # structure of inequality is lb <= model.param <= ub with strict=False by default
            if self.eval_ineq(1,current_Delta) and t == 1: #not strict
                return 0 >= model.yr0 - model.yr[t] +  model.yrsb0 - model.yrsb[t]
            elif self.eval_ineq(1,current_Delta) and t > 1: # not strict
                return model.yrsd[t-1] >= model.yr[t-1] - model.yr[t] + model.yrsb[t-1] - model.yrsb[t]
            elif self.eval_ineq(current_Delta,1,strict=True) and t == 1:
                return model.yrsd[t] >= model.yr0  - model.yr[t] + model.yrsb0 - model.yrsb[t]
            # only case remaining: Delta[t]<1, t>1
            return model.yrsd[t] >= model.yr[t-1] - model.yr[t] + model.yrsb[t-1] - model.yrsb[t]
        
        self.model.rec_su_sb_persist_con = pe.Constraint(self.model.T,rule=rec_su_sb_persist_rule)
        self.model.rec_sb_persist_con = pe.Constraint(self.model.T,rule=rec_sb_persist_rule)
        self.model.rsb_persist_con = pe.Constraint(self.model.T,rule=rsb_persist_rule)
        self.model.rec_su_pen_con = pe.Constraint(self.model.T,rule=rec_su_pen_rule)
        self.model.rec_hs_pen_con = pe.Constraint(self.model.T,rule=rec_hs_pen_rule)
        self.model.rec_shutdown_con = pe.Constraint(self.model.T,rule=rec_shutdown_rule)
        

    def addTESEnergyBalanceConstraints(self):
        def tes_balance_rule(model, t):
            if t == 1:
                return model.s[t] - model.s0 == model.Delta[t] * (model.xr[t] - (model.Qc[t]*model.ycsu[t] + model.Qb*model.ycsb[t] + model.x[t] + model.Qnsb*model.yrsb[t]))
            return model.s[t] - model.s[t-1] == model.Delta[t] * (model.xr[t] - (model.Qc[t]*model.ycsu[t] + model.Qb*model.ycsb[t] + model.x[t] + model.Qnsb*model.yrsb[t]))
        def tes_upper_rule(model, t):
            return model.s[t] <= model.Eu
        def tes_start_up_rule(model, t):
            if t == 1:
                return model.s0 >= model.Delta[t]*model.delta_ns[t]*( (model.Qu + model.Qb)*( -3 + model.yrsu[t] + model.y0 + model.y[t] + model.ycsb0 + model.ycsb[t] ) + model.x[t] + model.Qb*model.ycsb[t] )
            return model.s[t-1] >= model.Delta[t]*model.delta_ns[t]*( (model.Qu + model.Qb)*( -3 + model.yrsu[t] + model.y[t-1] + model.y[t] + model.ycsb[t-1] + model.ycsb[t] ) + model.x[t] + model.Qb*model.ycsb[t] )
        def maintain_tes_rule(model):
            return model.s[model.num_periods] <= model.s0
        
        self.model.tes_balance_con = pe.Constraint(self.model.T,rule=tes_balance_rule)
        self.model.tes_upper_con = pe.Constraint(self.model.T,rule=tes_upper_rule)
        self.model.tes_start_up_con = pe.Constraint(self.model.T,rule=tes_start_up_rule)
        self.model.maintain_tes_con = pe.Constraint(rule=maintain_tes_rule)


    def addPiecewiseLinearEfficiencyConstraints(self):
        def grid_sun_rule(model, t):
            return (
                    model.wdot_s[t] - model.wdot_p[t] == (1-model.etac[t])*model.wdot[t]
                		- model.Ln*(model.xr[t] + model.xrsu[t] + model.Qnl*model.yrsb[t])
                		- model.Lc*model.x[t] 
                        - model.Wh*model.yr[t] - model.Wb*model.ycsb[t] - model.Wnht*(model.yrsb[t]+model.yrsu[t])		#Is Wrsb energy [kWh] or power [kW]?  [az] Wrsb = Wht in the math?
                		- (model.Ehs/model.Delta[t])*(model.yrsu[t] + model.yrsb[t] + model.yrsd[t])
            )
        
        # call the parent version of this method
        GeneralDispatch.addPiecewiseLinearEfficiencyConstraints(self)
        
        # additional constraints
        self.model.grid_sun_con = pe.Constraint(self.model.T,rule=grid_sun_rule)


    def generate_constraints(self):
        
        # generating GeneralDispatch constraints first (PowerCycle, etc.)
        GeneralDispatch.generate_constraints(self)
        
        self.addReceiverStartupConstraints()
        self.addReceiverSupplyAndDemandConstraints()
        self.addReceiverNodeLogicConstraints()
        self.addTESEnergyBalanceConstraints()

    
# =============================================================================
# Dispatch Wrapper
# =============================================================================

class NuclearDispatchParamWrap(GeneralDispatchParamWrap):
    """
    The NuclearDispatchParamWrap class is meant to be the staging area for the 
    creation of Parameters ONLY for the NuclearDispatch class. It communicates 
    with the NE2 modules, receiving SSC and PySAM input dictionaries to calculate 
    both static parameters used for every simulation segment AND initial conditions 
    that can be updated.
    """
    
    def __init__(self, unit_registry, SSC_dict=None, PySAM_dict=None, pyomo_horizon=48, 
                   dispatch_time_step=1):
        """ Initializes the NuclearDispatchParamWrap module
        
        Inputs:
            unitRegistry (pint.registry)   : unique unit Pint unit registry
            SSC_dict (dict)                : dictionary of SSC inputs needed to run modules
            PySAM_dict (dict)              : dictionary of PySAM inputs + file names
            pyomo_horizon (int Quant)      : length of Pyomo simulation segment (hours)
            dispatch_time_step (int Quant) : length of each Pyomo time step (hours)
        """
        
        GeneralDispatchParamWrap.__init__( self, unit_registry, SSC_dict, PySAM_dict, 
                            pyomo_horizon, dispatch_time_step )


    def set_fixed_cost_parameters(self, param_dict):
        """ Method to set fixed costs of the Plant
        
        This method calculates some fixed costs for the Plant operations, startup,
        standby, etc. 
        
        Inputs:
            param_dict (dict) : dictionary of Pyomo dispatch parameters
        Outputs:
            param_dict (dict) : updated dictionary of Pyomo dispatch parameters
        """
        
        # grabbing unit registry set up in GeneralDispatch
        u = self.u
    
        # set up costs from parent class
        param_dict = GeneralDispatchParamWrap.set_fixed_cost_parameters( self, param_dict )
        
        # TODO: old values from LORE files
        C_nuc  = self.PySAM_dict['nuc_op_cost'] * u.USD / u.MWh #Q_ratio * 0.002  * u.USD/u.kWh        
        C_nsu  = self.PySAM_dict['nuc_cold_su'] * u.USD
        C_nhsp = self.PySAM_dict['nuc_hot_su'] * u.USD

        ### Cost Parameters ###
        param_dict['Cnuc']   = C_nuc.to('USD/kWh')  #C^{rec}: Operating cost of nuclear plant [\$/kWt$\cdot$h]
        param_dict['Cnsu']   = C_nsu.to('USD')      #C^{rsu}: Penalty for nuclear cold start-up [\$/start]
        param_dict['Cnhsp']  = C_nhsp.to('USD')     #C^{rhsp}: Penalty for nuclear hot start-up [\$/start]

        return param_dict
        

    def set_nuclear_parameters(self, param_dict):
        """ Method to set parameters specific to the Nuclear Plant for Dispatch optimization
        
        This method calculates some parameters specific to the NuclearTES plant
        which are meant to be fixed throughout the simulation. 
        
        Inputs:
            param_dict (dict) : dictionary of Pyomo dispatch parameters
        Outputs:
            param_dict (dict) : updated dictionary of Pyomo dispatch parameters
        """
        
        # grabbing unit registry set up in GeneralDispatch
        u = self.u 
        
        time_fix = 1*u.hr                  # TODO: we're missing a time term to fix units
        dw_rec_pump             = self.PySAM_dict['dw_nuc_pump']*u.MW   # TODO: Pumping parasitic at design point reciever mass flow rate (MWe)
        tower_piping_ht_loss    = self.PySAM_dict['nuc_piping_ht_loss']*u.kW   # TODO: Tower piping heat trace full-load parasitic load (kWe) 
        q_rec_standby_fraction  = self.PySAM_dict['q_nuc_standby_frac']        # TODO: Receiver standby energy consumption (fraction of design point thermal power)
        q_rec_shutdown_fraction = self.PySAM_dict['q_nuc_shutdown_frac']        # TODO: Receiver shutdown energy consumption (fraction of design point thermal power)
        
        self.deltanl = self.SSC_dict['rec_su_delay']*u.hr
        self.Ehs    = self.SSC_dict['p_start']*u.kWh
        self.En     = self.SSC_dict['rec_qf_delay'] * self.q_rec_design * time_fix
        self.Eu     = self.SSC_dict['tshours']*u.hr * self.q_pb_design
        self.Ln     = dw_rec_pump / self.q_rec_design
        self.Qnl    = self.SSC_dict['f_rec_min'] * self.q_rec_design * time_fix
        self.Qnsb   = q_rec_standby_fraction  * self.q_rec_design * time_fix
        self.Qnsd   = q_rec_shutdown_fraction * self.q_rec_design * time_fix
        self.Qnu    = self.En / self.deltanl  
        self.Wh     = self.SSC_dict['p_track']*u.kW
        self.Wnht    = tower_piping_ht_loss
        
        ### CSP Field and Receiver Parameters ###
        param_dict['deltanl'] = self.deltanl.to('hr')    #\delta^l: Minimum time to start the nuclear plant [hr]
        param_dict['Ehs']    = self.Ehs.to('kWh')      #E^{hs}: Heliostat field startup or shut down parasitic loss [kWe$\cdot$h]
        param_dict['En']     = self.En.to('kWh')       #E^n: Required energy expended to start nuclear plant [kWt$\cdot$h]
        param_dict['Eu']     = self.Eu.to('kWh')       #E^u: Thermal energy storage capacity [kWt$\cdot$h]
        param_dict['Ln']     = self.Ln.to('')          #L^n: Nuclear pumping power per unit power produced [kWe/kWt]
        param_dict['Qnl']    = self.Qnl.to('kWh')      #Q^{nl}: Minimum operational thermal power delivered by nuclear [kWt$\cdot$h]
        param_dict['Qnsb']   = self.Qnsb.to('kWh')     #Q^{nsb}: Required thermal power for nuclear standby [kWt$\cdot$h]
        param_dict['Qnsd']   = self.Qnsd.to('kWh')     #Q^{nsd}: Required thermal power for nuclear shut down [kWt$\cdot$h] 
        param_dict['Qnu']    = self.Qnu.to('kW')       #Q^{nu}: Allowable power per period for nuclear start-up [kWt$\cdot$h]
        param_dict['Wh']     = self.Wh.to('kW')        #W^h: Heliostat field tracking parasitic loss [kWe]
        param_dict['Wnht']    = self.Wnht.to('kW')       #W^{nht}: Nuclear piping heat trace parasitic loss [kWe]
        
        return param_dict
    
    
    def set_time_series_nuclear_parameters(self, param_dict, df_array, ud_array, current_pyomo_slice):
        """ Method to set fixed costs of the Plant for Dispatch optimization
        
        This method calculates some time series parameters for the Plant operations, startup,
        standby, etc. These are NOT meant to be fixed, but updated at the beginning
        of every segment using the latest SSC outputs or to extract the next relevant
        segment of pricing arrays, efficiencies, etc. 
        
        Inputs:
            param_dict (dict)             : dictionary of Pyomo dispatch parameters
            df_array (array)              : array of user defined dispatch factors over simulation time
            ud_array (list of list)       : table of user defined data as nested lists
            current_pyomo_slice (slice)   : range of current pyomo horizon (ints representing hours)
        Outputs:
            param_dict (dict) : updated dictionary of Pyomo dispatch parameters
        """
        
        #MAKE SURE TO CALL THIS METHOD AFTER THE NUCLEAR PARAMETERS 
        u = self.u
        
        self.Drsu       = self.PySAM_dict['Dnsu']*u.hr   # Minimum time to start the receiver (hr)
        self.Qin        = np.array([self.q_rec_design.magnitude]*self.T)*self.q_rec_design.units #TODO: update at each segment
        self.Qc         = self.Ec / np.ceil(self.SSC_dict['startup_time']*u.hr / np.min(self.Delta)) / np.min(self.Delta) #TODO: make sure Ec is called correctly
        self.Wdotnet    = [1.e10 for j in range(self.T)] *u.kW
        self.W_u_plus   = [(self.Wdotl + self.W_delta_plus*0.5*dt).to('kW').magnitude for dt in self.Delta]*u.kW
        self.W_u_minus  = [(self.Wdotl + self.W_delta_minus*0.5*dt).to('kW').magnitude for dt in self.Delta]*u.kW
        
        n  = len(self.Delta)
        wt = self.PySAM_dict['nuc_wt']
        delta_ns = np.zeros(n)
        D        = np.zeros(n)
        
        # grab time series data that we have to index
        Tdry  = self.Tdry # dry bulb temperature from solar resource file 
        Price = df_array  # pricing multipliers
        # if we're at the last segment, we won't have 48 hour data for the sim. here is a quick fix
        if current_pyomo_slice.stop > len(Tdry):
            Tdry  = np.hstack([Tdry,  Tdry])
            Price = np.hstack([Price, Price])
        # grabbing relevant dry temperatures
        Tdry   = Tdry[current_pyomo_slice]
        self.P = Price[current_pyomo_slice]*u.USD/u.kWh
        
        etamult, wmult = SSCHelperMethods.get_ambient_T_corrections_from_udpc_inputs( self.u, Tdry, ud_array ) # TODO:verify this makes sense
        self.etaamb = etamult * self.SSC_dict['design_eff']
        self.etac   = wmult * self.SSC_dict['ud_f_W_dot_cool_des']/100.

        for t in range(n):
            Ein = self.Qin[t]*self.Delta[t]
            E_compare = (self.En / max(1.*u.kWh, Ein.to('kWh'))).to('')
            delta_ns[t] = min(1., max( E_compare, self.Drsu/self.Delta[t]))
            D[t]        = wt**(self.Delta_e[t]/u.hr)
        
        self.delta_ns   = delta_ns
        self.D          = D
        
        ### Time series CSP Parameters ###
        param_dict['delta_ns']  = self.delta_ns   #\delta^{rs}_{t}: Estimated fraction of period $t$ required for receiver start-up [-]
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


    def set_initial_state(self, param_dict, updated_dict=None, plant=None, npts=None ):
        """ Method to set the initial state of the Plant before Dispatch optimization
        
        This method uses SSC data to set the initial state of the Plant before Dispatch
        optimization in Pyomo. This method is called in two ways: once before starting 
        the simulation loop, in which case it only uses values from the SSC_dict portion
        of the given JSON script. The method is also called within the simulation loop
        to update the initial state parameters based on the ending conditions of the 
        previous simulation segment (provided by SSC). 
        
        TODO: can we just input another dictionary instead of passing the full Plant?
        
        Inputs:
            param_dict (dict)    : dictionary of Pyomo dispatch parameters
            updated_dict (dict)  : dictionary with updated SSC initial conditions from previous run
            plant (obj)          : the full PySAM Plant object. 
            npts (int)           : length of the SSC horizon
        Outputs:
            param_dict (dict) : updated dictionary of Pyomo dispatch parameters
        """
        u = self.u
        
        if updated_dict is None:
            self.current_Plant = copy.deepcopy(self.SSC_dict)
            self.first_run = True
        else:
            self.current_Plant = updated_dict
            self.first_run = False
            
        # TES masses, temperatures, specific heat
        m_hot  = self.m_tes_design * (self.current_Plant['csp.pt.tes.init_hot_htf_percent']/100)        # Available active mass in hot tank
        T_tes_hot_init  = (self.current_Plant['T_tank_hot_init']*u.celsius).to('degK')
        T_tes_init  = 0.5*(T_tes_hot_init + self.T_htf_cold)
        cp_tes_init = SSCHelperMethods.get_cp_htf(self.u, T_tes_init, self.SSC_dict['rec_htf'] )
        
        # important parameters
        e_pb_suinitremain  = self.current_Plant['pc_startup_energy_remain_initial']*u.kWh
        s_current          = m_hot * cp_tes_init * (T_tes_hot_init - self.T_htf_cold) # TES capacity
        s0                 = min(self.Eu.to('kWh'), s_current.to('kWh')  )
        wdot0              = (0 if self.first_run else self.current_Plant['wdot0'])*u.MW 
        yr0                = (self.current_Plant['rec_op_mode_initial'] == 2)
        yrsb0              = False   # We don't have standby mode for either Nuclear or CSP
        yrsu0              = (self.current_Plant['rec_op_mode_initial'] == 1)
        y0                 = (self.current_Plant['pc_op_mode_initial'] == 1) 
        ycsb0              = (self.current_Plant['pc_op_mode_initial'] == 2) 
        ycsu0              = (self.current_Plant['pc_op_mode_initial'] == 0 or self.current_Plant['pc_op_mode_initial'] == 4) 
        pc_persist, pc_off = self.get_pc_persist_and_off_logs( param_dict, plant, npts ) if plant is not None else [48,48]
        Yu0                = pc_persist if y0       else 0.0
        Yd0                = pc_off     if (not y0) else 0.0
        t_rec              = self.current_Plant['rec_startup_time_remain_init']
        t_rec_suinitremain = t_rec if not np.isnan( t_rec ) else 0.0
        e_rec              = self.current_Plant['rec_startup_energy_remain_init']
        e_rec_suinitremain = e_rec if not np.isnan( e_rec ) else 0.0
        rec_accum_time     = max(0.0*u.hr, self.Drsu - t_rec_suinitremain*u.hr )
        rec_accum_energy   = max(0.0*u.Wh, self.En   - e_rec_suinitremain*u.Wh )
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
            self.ucsu0 = max(0.0, self.Ec - e_pb_suinitremain ) 
            if self.ucsu0 > (1.0 - tol)*self.Ec:
                self.ucsu0 = self.Ec
        

        # Initial receiver startup energy inventory
        self.ursu0 = min(rec_accum_energy, rec_accum_time * self.Qnu)  # Note, SS receiver model in ssc assumes full available power is used for startup (even if, time requirement is binding)
        if self.ursu0 > (1.0 - 1.e-6)*self.En:
            self.ursu0 = self.En

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
        # param_dict['wdot_s_prev']    = 0*u.hr         #\dot{w}^{s,prev}: previous $\dot{w}^s$, or energy sold to grid [kWe]
        # ^ this should be gen[-1] from previous SSC run, 0 if first_run == True
        
        # print('      y_r     - Receiver On?            ', self.yr0)
        # print('      yrsb0   - Receiver Standby?       ', self.yrsb0)
        # print('      yrsu0   - Receiver Startup?       ', self.yrsu0)
        # print('      ursu_0  - Receiver Startup Energy ', self.ursu0.to('kWh') )
        # print(' ')
        # print('      y       - Cycle On?               ', self.y0)
        # print('      ycsb0   - Cycle Standby?          ', self.ycsb0)
        # print('      ycsu0   - Cycle Startup?          ', self.ycsu0)
        # print('      ucsu_0  - Cycle Startup Energy    ', self.ucsu0.to('kWh') )
        # print(' ')
        return param_dict
    
    
    def get_pc_persist_and_off_logs( self, param_dict, plant, npts ):
        """ Method to log the amount of time Power Cycle has been ON and OFF
        
        This method uses SSC output data from the previous run to log how long
        the Power Cycle has been both ON and OFF. One of the two outputs will be
        populated in this method, and there are a bunch of logic statements to
        correctly log the respective length of time. Method adapted from LORE Team. 
        
        TODO: can we just input another dictionary instead of passing the full Plant?
        
        Inputs:
            param_dict (dict)    : dictionary of Pyomo dispatch parameters
            plant (obj)          : the full PySAM Plant object. 
            npts (int)           : length of the SSC horizon
        Outputs:
            disp_pc_persist0 (int) : length of time PC has been ON in the past segment
            disp_pc_off0 (int)     : length of time PC has been OFF in the past segment
        """
        
        # cycle state before start of most recent set of simulation calls
        previous_pc_state = plant.SystemControl.pc_op_mode_initial
        # cycle state after most recent set of simulation calls
        current_pc_state  = plant.Outputs.pc_op_mode_final
        # times when cycle is not generating power
        is_pc_not_on = np.array( plant.Outputs.P_cycle[0:npts-1] ) <= 1.e-3
        
        ###=== Persist Log ===### 
        # if PC is ON
        if current_pc_state == 1:
            # array of times (PC was generating power == True)
            is_pc_current = np.array( plant.Outputs.P_cycle[0:npts-1] ) > 1.e-3 
            
        # if PC is STANDBY
        elif current_pc_state == 2:
            # array of times (PC was generating power == False) + (PC getting input energy == True) + (PC using startup power == False)
            is_pc_current = np.logical_and( \
                                np.logical_and( \
                                    np.array( plant.Outputs.P_cycle[0:npts-1] ) <= 1.e-3, np.array( plant.Outputs.q_pb[0:npts-1] ) >= 1.e-3 ), \
                                    np.array( plant.Outputs.q_dot_pc_startup[0:npts-1] ) <= 1.e-3 )
        
        # if PC is STARTUP
        elif current_pc_state == 0:
            # array of times (PC using startup power == True)
            is_pc_current = np.array( plant.Outputs.q_dot_pc_startup[0:npts-1] ) > 1.e-3
        
        # if PC is OFF
        elif current_pc_state == 3:
            # array of times (PC getting input energy + PC using startup power == False)
            is_pc_current = (np.array( plant.Outputs.q_dot_pc_startup[0:npts-1] ) + np.array( plant.Outputs.q_pb[0:npts-1] ) ) <= 1.e-3
        
        ###=== Indexing ===###
        ssc_time_step = 1   # 1 hour per time step
        n = npts            # length of ssc horizon
        
        ###=== OFF Log ===###
        # if PC is ON
        if current_pc_state == 1: 
            # returning 0 for OFF log
            disp_pc_off0 = 0.0
        
        # if PC is OFF for full simulation
        elif is_pc_not_on.min() == 1:  
            # add all OFF positions in this current horizon to existing OFF log
            disp_pc_off0 = param_dict['Yd0'].to('hr').m + n*ssc_time_step  
        
        # if PC is OFF for some portion of current horizon
        else:
            # find indeces of changed OFF state
            i = np.where(np.abs(np.diff(is_pc_not_on)) == 1)[0][-1]
            # use index to find length of times PC was oFF
            disp_pc_off0 = int(n-1-i)*ssc_time_step          
        
        ###=== Final Indexing and Logging ===###
        # Plant has not changed state over this simulation window:
        if n == 1 or np.abs(np.diff(is_pc_current)).max() == 0:  
            # adding to existing persist array from Dispatch Params dictionary if state continued
            disp_pc_persist0 = n*ssc_time_step if previous_pc_state != current_pc_state else param_dict['Yu0'].to('hr').m + n*ssc_time_step
        # Plant *has* changed state over this simulation window:
        else:
            # find indeces of changed state
            i = np.where(np.abs(np.diff(is_pc_current)) == 1)[0][-1]
            # use index to find length of times PC was ON
            disp_pc_persist0 = int(n-1-i)*ssc_time_step
        
        return disp_pc_persist0, disp_pc_off0
    

