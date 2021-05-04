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
#import pyomo
import pyomo.environ as pe
import numpy as np
import pint
u = pint.UnitRegistry()

class GeneralDispatch(object):
    def __init__(self, params, include={"pv":False,"battery":False,"persistence":False}):
        self.model = pe.ConcreteModel()
        self.include = include
        self.generate_params(params)
        self.generate_variables()
        self.add_objective()
        self.generate_constraints()

    def generate_params(self,params):
        ### Sets and Indices ###
        self.model.T = pe.Set(initialize = range(1,params["T"]+1))  #T: time periods
        self.model.num_periods = pe.Param(initialize=params["T"]) #N_T: number of time periods
        
        #------- Time indexed parameters ---------
        self.model.Delta = pe.Param(self.model.T, mutable=False, initialize=params["Delta"])          #\Delta_{t}: duration of period t
        self.model.Delta_e = pe.Param(self.model.T, mutable=False, initialize=params["Delta_e"])       #\Delta_{e,t}: cumulative time elapsed at end of period t
        
        ### Time series CSP Parameters ###
        self.model.delta_rs = pe.Param(self.model.T, mutable=True, initialize=params["delta_rs"]) #\delta^{rs}_{t}: Estimated fraction of period $t$ required for receiver start-up [-]
        self.model.D = pe.Param(self.model.T, mutable=True, initialize=params["D"]) #D_{t}: Time-weighted discount factor in period $t$ [-]
        self.model.etaamb = pe.Param(self.model.T, mutable=True, initialize=params["etaamb"])  #\eta^{amb}_{t}: Cycle efficiency ambient temperature adjustment factor in period $t$ [-]
        self.model.etac = pe.Param(self.model.T, mutable=True, initialize=params["etac"])   #\eta^{c}_{t}: Normalized condenser parasitic loss in period $t$ [-] 
        self.model.P = pe.Param(self.model.T, mutable=True, initialize=params["P"])       #P_{t}: Electricity sales price in period $t$ [\$/kWh]
        self.model.Qin = pe.Param(self.model.T, mutable=True, initialize=params["Qin"])    #Q^{in}_{t}: Available thermal power generated by the CSP heliostat field in period $t$ [kWt]
        self.model.Qc = pe.Param(self.model.T, mutable=True, initialize=params["Qc"])     #Q^{c}_{t}: Allowable power per period for cycle start-up in period $t$ [kWt]
        self.model.Wdotnet = pe.Param(self.model.T, mutable=True, initialize=params["Wdotnet"])  #\dot{W}^{net}_{t}: Net grid transmission upper limit in period $t$ [kWe]
        self.model.W_u_plus = pe.Param(self.model.T, mutable=True, initialize=params["W_u_plus"])  #W^{u+}_{t}: Maximum power production when starting generation in period $t$  [kWe]
        self.model.W_u_minus = pe.Param(self.model.T, mutable=True, initialize=params["W_u_minus"])  #W^{u-}_{t}: Maximum power production in period $t$ when stopping generation in period $t+1$  [kWe]

        ### Cost Parameters ###
        self.model.alpha = pe.Param(mutable=True, initialize=params["alpha"])        #\alpha: Conversion factor between unitless and monetary values [\$]
        self.model.Crec = pe.Param(mutable=True, initialize=params["Crec"])         #C^{rec}: Operating cost of heliostat field and receiver [\$/kWt$\cdot$h]
        self.model.Crsu = pe.Param(mutable=True, initialize=params["Crsu"])         #C^{rsu}: Penalty for receiver cold start-up [\$/start]
        self.model.Crhsp = pe.Param(mutable=True, initialize=params["Crhsp"])        #C^{rhsp}: Penalty for receiver hot start-up [\$/start]
        self.model.Cpc = pe.Param(mutable=True, initialize=params["Cpc"])          #C^{pc}: Operating cost of power cycle [\$/kWe$\cdot$h]
        self.model.Ccsu = pe.Param(mutable=True, initialize=params["Ccsu"])        #C^{csu}: Penalty for power cycle cold start-up [\$/start]
        self.model.Cchsp = pe.Param(mutable=True, initialize=params["Cchsp"])       #C^{chsp}: Penalty for power cycle hot start-up [\$/start]
        self.model.C_delta_w = pe.Param(mutable=True, initialize=params["C_delta_w"])    #C^{\delta_w}: Penalty for change in power cycle  production [\$/$\Delta\text{kWe}$]
        self.model.C_v_w = pe.Param(mutable=True, initialize=params["C_v_w"])        #C^{v_w}: Penalty for change in power cycle  production tcb{beyond designed limits} [\$/$\Delta\text{kWe}$]
        self.model.Ccsb = pe.Param(mutable=True, initialize=params["Ccsb"])         #C^{csb}: Operating cost of power cycle standby operation [\$/kWt$\cdot$h]
        
        ### CSP Field and Receiver Parameters ###
        self.model.deltal = pe.Param(mutable=True, initialize=params["deltal"])    #\delta^l: Minimum time to start the receiver [hr]
        self.model.Ehs = pe.Param(mutable=True, initialize=params["Ehs"])       #E^{hs}: Heliostat field startup or shut down parasitic loss [kWe$\cdot$h]
        self.model.Er = pe.Param(mutable=True, initialize=params["Er"])        #E^r: Required energy expended to start receiver [kWt$\cdot$h]
        self.model.Eu = pe.Param(mutable=True, initialize=params["Eu"])        #E^u: Thermal energy storage capacity [kWt$\cdot$h]
        self.model.Lr = pe.Param(mutable=True, initialize=params["Lr"])        #L^r: Receiver pumping power per unit power produced [kWe/kWt]
        self.model.Qrl = pe.Param(mutable=True, initialize=params["Qrl"])       #Q^{rl}: Minimum operational thermal power delivered by receiver [kWt$\cdot$h]
        self.model.Qrsb = pe.Param(mutable=True, initialize=params["Qrsb"])      #Q^{rsb}: Required thermal power for receiver standby [kWt$\cdot$h]
        self.model.Qrsd = pe.Param(mutable=True, initialize=params["Qrsd"])      #Q^{rsd}: Required thermal power for receiver shut down [kWt$\cdot$h] 
        self.model.Qru = pe.Param(mutable=True, initialize=params["Qru"])       #Q^{ru}: Allowable power per period for receiver start-up [kWt$\cdot$h]
        self.model.Wh = pe.Param(mutable=True, initialize=params["Wh"])        #W^h: Heliostat field tracking parasitic loss [kWe]
        self.model.Wht = pe.Param(mutable=True, initialize=params["Wht"])       #W^{ht}: Tower piping heat trace parasitic loss [kWe]
        
        ### Power Cycle Parameters ###
        self.model.Ec = pe.Param(mutable=True, initialize=params["Ec"])           #E^c: Required energy expended to start cycle [kWt$\cdot$h]
        self.model.eta_des = pe.Param(mutable=True, initialize=params["eta_des"])      #\eta^{des}: Cycle nominal efficiency [-] 
        self.model.etap = pe.Param(mutable=True, initialize=params["etap"])         #\eta^p: Slope of linear approximation of power cycle performance curve [kWe/kWt]
        self.model.Lc = pe.Param(mutable=True, initialize=params["Lc"])           #L^c: Cycle heat transfer fluid pumping power per unit energy expended [kWe/kWt]
        self.model.Qb = pe.Param(mutable=True, initialize=params["Qb"])           #Q^b: Cycle standby thermal power consumption per period [kWt]
        self.model.Ql = pe.Param(mutable=True, initialize=params["Ql"])           #Q^l: Minimum operational thermal power input to cycle [kWt]
        self.model.Qu = pe.Param(mutable=True, initialize=params["Qu"])           #Q^u: Cycle thermal power capacity [kWt]
        self.model.Wb = pe.Param(mutable=True, initialize=params["Wb"])           #W^b: Power cycle standby operation parasitic load [kWe]
        self.model.Wdotl = pe.Param(mutable=True, initialize=params["Wdotl"])        #\dot{W}^l: Minimum cycle electric power output [kWe]
        self.model.Wdotu = pe.Param(mutable=True, initialize=params["Wdotu"])        #\dot{W}^u: Cycle electric power rated capacity [kWe]
        self.model.W_delta_plus = pe.Param(mutable=True, initialize=params["W_delta_plus"]) #W^{\Delta+}: Power cycle ramp-up designed limit [kWe/h]
        self.model.W_delta_minus = pe.Param(mutable=True, initialize=params["W_delta_minus"]) #W^{\Delta-}: Power cycle ramp-down designed limit [kWe/h]
        self.model.W_v_plus = pe.Param(mutable=True, initialize=params["W_v_plus"])     #W^{v+}: Power cycle ramp-up violation limit [kWe/h]
        self.model.W_v_minus = pe.Param(mutable=True, initialize=params["W_v_minus"])    #W^{v-}: Power cycle ramp-down violation limit [kWe/h]
        self.model.Yu = pe.Param(mutable=True, initialize=params["Yu"])           #Y^u: Minimum required power cycle uptime [h]
        self.model.Yd = pe.Param(mutable=True, initialize=params["Yd"])           #Y^d: Minimum required power cycle downtime [h]
        
        ### Initial Condition Parameters ###
        self.model.s0 = pe.Param(mutable=True, initialize=params["s0"])  #s_0: Initial TES reserve quantity  [kWt$\cdot$h]
        self.model.ucsu0 = pe.Param(mutable=True, initialize=params["ucsu0"]) #u^{csu}_0: Initial cycle start-up energy inventory  [kWt$\cdot$h]
        self.model.ursu0 = pe.Param(mutable=True, initialize=params["ursu0"]) #u^{rsu}_0: Initial receiver start-up energy inventory [kWt$\cdot$h]
        self.model.wdot0 = pe.Param(mutable=True, initialize=params["wdot0"]) #\dot{w}_0: Initial power cycle electricity generation [kW]e
        self.model.yr0 = pe.Param(mutable=True, initialize=params["yr0"])  #y^r_0: 1 if receiver is generating ``usable'' thermal power initially, 0 otherwise  [az] this is new.
        self.model.yrsb0 = pe.Param(mutable=True, initialize=params["yrsb0"])  #y^{rsb}_0: 1 if receiver is in standby mode initially, 0 otherwise [az] this is new.
        self.model.yrsu0 = pe.Param(mutable=True, initialize=params["yrsu0"])  #y^{rsu}_0: 1 if receiver is in starting up initially, 0 otherwise    [az] this is new.
        self.model.y0 = pe.Param(mutable=True, initialize=params["y0"])  #y_0: 1 if cycle is generating electric power initially, 0 otherwise
        self.model.ycsb0 = pe.Param(mutable=True, initialize=params["ycsb0"])  #y^{csb}_0: 1 if cycle is in standby mode initially, 0 otherwise
        self.model.ycsu0 = pe.Param(mutable=True, initialize=params["ycsu0"])  #y^{csu}_0: 1 if cycle is in starting up initially, 0 otherwise    [az] this is new.
        self.model.Yu0 = pe.Param(mutable=True, initialize=params["Yu0"])  #Y^u_0: duration that cycle has been generating electric power [h]
        self.model.Yd0 = pe.Param(mutable=True, initialize=params["Yd0"])  #Y^d_0: duration that cycle has not been generating power (i.e., shut down or in standby mode) [h]
        
        #------- Persistence Parameters ---------
        self.model.wdot_s_prev  = pe.Param(self.model.T, mutable=True, initialize=params["wdot_s_prev"]) #\dot{w}^{s,prev}: previous $\dot{w}$ 
        self.model.wdot_s_pen  = pe.Param(self.model.T, mutable=True, initialize=params["wdot_s_pen"]) #\dot{w}_{s,pen}: previous $\dot{w}$ 

        

    def generate_variables(self):
        ### Decision Variables ###
        #------- Variables ---------
        self.model.s = pe.Var(self.model.T, domain=pe.NonNegativeReals, bounds = (0,self.model.Eu))    #s: TES reserve quantity at period $t$  [kWt$\cdot$h]
        self.model.ucsu = pe.Var(self.model.T, domain=pe.NonNegativeReals)                         #u^{csu}: Cycle start-up energy inventory at period $t$ [kWt$\cdot$h]
        self.model.ursu = pe.Var(self.model.T, domain=pe.NonNegativeReals)                         #u^{rsu}: Receiver start-up energy inventory at period $t$ [kWt$\cdot$h]
        self.model.wdot = pe.Var(self.model.T, domain=pe.NonNegativeReals)                         #\dot{w}: Power cycle electricity generation at period $t$ [kWe]
        self.model.wdot_delta_plus = pe.Var(self.model.T, domain=pe.NonNegativeReals)	             #\dot{w}^{\Delta+}: Power cycle ramp-up in period $t$ [kWe]
        self.model.wdot_delta_minus = pe.Var(self.model.T, domain=pe.NonNegativeReals)	         #\dot{w}^{\Delta-}: Power cycle ramp-down in period $t$ [kWe]
        self.model.wdot_v_plus = pe.Var(self.model.T, domain=pe.NonNegativeReals, bounds = (0,self.model.W_v_plus))      #\dot{w}^{v+}: Power cycle ramp-up beyond designed limit in period $t$ [kWe]
        self.model.wdot_v_minus = pe.Var(self.model.T, domain=pe.NonNegativeReals, bounds = (0,self.model.W_v_minus)) 	 #\dot{w}^{v-}: Power cycle ramp-down beyond designed limit in period $t$ [kWe]
        self.model.wdot_s = pe.Var(self.model.T, domain=pe.NonNegativeReals)	                     #\dot{w}^s: Energy sold to grid in time t
        self.model.wdot_p = pe.Var(self.model.T, domain=pe.NonNegativeReals)	                     #\dot{w}^p: Energy purchased from the grid in time t
        self.model.x = pe.Var(self.model.T, domain=pe.NonNegativeReals)                            #x: Cycle thermal power utilization at period $t$ [kWt]
        self.model.xr = pe.Var(self.model.T, domain=pe.NonNegativeReals)	                         #x^r: Thermal power delivered by the receiver at period $t$ [kWt]
        self.model.xrsu = pe.Var(self.model.T, domain=pe.NonNegativeReals)                         #x^{rsu}: Receiver start-up power consumption at period $t$ [kWt]
        
        #------- Binary Variables ---------
        self.model.yr = pe.Var(self.model.T, domain=pe.Binary)        #y^r: 1 if receiver is generating ``usable'' thermal power at period $t$; 0 otherwise
        self.model.yrhsp = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rhsp}: 1 if receiver hot start-up penalty is incurred at period $t$ (from standby); 0 otherwise
        self.model.yrsb = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rsb}: 1 if receiver is in standby mode at period $t$; 0 otherwise
        self.model.yrsd = pe.Var(self.model.T, domain=pe.Binary)	    #y^{rsd}: 1 if receiver is shut down at period $t$; 0 otherwise
        self.model.yrsu = pe.Var(self.model.T, domain=pe.Binary)      #y^{rsu}: 1 if receiver is starting up at period $t$; 0 otherwise
        self.model.yrsup = pe.Var(self.model.T, domain=pe.Binary)     #y^{rsup}: 1 if receiver cold start-up penalty is incurred at period $t$ (from off); 0 otherwise
        self.model.y = pe.Var(self.model.T, domain=pe.Binary)         #y: 1 if cycle is generating electric power at period $t$; 0 otherwise
        self.model.ychsp = pe.Var(self.model.T, domain=pe.Binary)     #y^{chsp}: 1 if cycle hot start-up penalty is incurred at period $t$ (from standby); 0 otherwise
        self.model.ycsb = pe.Var(self.model.T, domain=pe.Binary)      #y^{csb}: 1 if cycle is in standby mode at period $t$; 0 otherwise
        self.model.ycsd = pe.Var(self.model.T, domain=pe.Binary)	    #y^{csd}: 1 if cycle is shutting down at period $t$; 0 otherwise
        self.model.ycsu = pe.Var(self.model.T, domain=pe.Binary)      #y^{csu}: 1 if cycle is starting up at period $t$; 0 otherwise
        self.model.ycsup = pe.Var(self.model.T, domain=pe.Binary)     #y^{csup}: 1 if cycle cold start-up penalty is incurred at period $t$ (from off); 0 otherwise
        self.model.ycgb = pe.Var(self.model.T, domain=pe.NonNegativeReals, bounds=(0,1))      #y^{cgb}: 1 if cycle begins electric power generation at period $t$; 0 otherwise
        self.model.ycge = pe.Var(self.model.T, domain=pe.NonNegativeReals, bounds=(0,1))      #y^{cge}: 1 if cycle stops electric power generation at period $t$; 0 otherwise
        
        #------- Persistence Variables ---------
        self.model.wdot_s_prev_delta_plus = pe.Var(self.model.T, domain=pe.NonNegativeReals) #\dot{w}^{\Delta+}_{s,prev}: previous delta+ w
        self.model.wdot_s_prev_delta_minus = pe.Var(self.model.T, domain=pe.NonNegativeReals) #\dot{w}^{\Delta-}_{s,prev}: previous delta- w           
        self.model.ycoff = pe.Var(self.model.T, domain=pe.Binary)     #y^{c,off}: 1 if power cycle is off at period $t$; 0 otherwise
        

                
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
                    - (model.Crsu*model.yrsup[t] + model.Crhsp*model.yrhsp[t] + model.alpha*model.yrsd[t])
                    #obj_cost_ops
                    - model.Delta[t]*(model.Cpc*model.wdot[t] + model.Ccsb*model.Qb*model.ycsb[t] + model.Crec*model.xr[t] )
                    for t in model.T) 
                    )
        
        self.model.OBJ = pe.Objective(rule=objectiveRule, sense = pe.maximize)


    def addPersistenceConstraints(self):
        def wdot_s_persist_pos_rule(model,t):
            return model.wdot_s_prev_delta_plus[t] >= model.wdot_s[t] - model.wdot_s_prev[t]
        def wdot_s_persist_neg_rule(model,t):
            return model.wdot_s_prev_delta_minus[t] >= model.wdot_s_prev[t] - model.wdot_s[t]
        self.model.persist_pos_con = pe.Constraint(self.model.T,rule=wdot_s_persist_pos_rule)
        self.model.persist_neg_con = pe.Constraint(self.model.T,rule=wdot_s_persist_neg_rule)


    def addReceiverStartupConstraints(self):
        def rec_inventory_rule(model,t):
            if t == 1:
                return model.ursu[t] <= model.ursu0 + model.Delta[t]*model.xrsu[t]
            return model.ursu[t] <= model.ursu[t-1] + model.Delta[t]*model.xrsu[t]
        def rec_inv_nonzero_rule(model,t):
            return model.ursu[t] <= model.Er * model.yrsu[t]
        def rec_startup_rule(model,t):
            if t == 1:
                return model.yr[t] <= model.ursu[t]/model.Er + model.yr0 + model.yrsb0
            return model.yr[t] <= model.ursu[t]/model.Er + model.yr[t-1] + model.yrsb[t-1]
        def rec_su_persist_rule(model,t):
            if t == 1: 
                return model.yrsu[t] + model.yr0 <= 1
            return model.yrsu[t] +  model.yr[t-1] <= 1
        def ramp_limit_rule(model,t):
            return model.xrsu[t] <= model.Qru*model.yrsu[t]
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
            return model.xr[t] + model.xrsu[t] + model.Qrsd*model.yrsd[t] <= model.Qin[t]
        def rec_generation_rule(model,t):
            return model.xr[t] <= model.Qin[t] * model.yr[t]
        def min_generation_rule(model,t):
            return model.xr[t] >= model.Qrl * model.yr[t]
        def rec_gen_persist_rule(model,t):
            return model.yr[t] <= model.Qin[t]/model.Qrl
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
            if model.Delta[t] >= 1 and t == 1:
                return 0 >= model.yr0 - model.yr[t] +  model.yrsb0 - model.yrsb[t]
            elif model.Delta[t] >= 1 and t > 1:
                return model.yrsd[t-1] >= model.yr[t-1] - model.yr[t] + model.yrsb[t-1] - model.yrsb[t]
            elif model.Delta[t] < 1 and t == 1:
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
                return model.s[t] - model.s0 == model.Delta[t] * (model.xr[t] - (model.Qc[t]*model.ycsu[t] + model.Qb*model.ycsb[t] + model.x[t] + model.Qrsb*model.yrsb[t]))
            return model.s[t] - model.s[t-1] == model.Delta[t] * (model.xr[t] - (model.Qc[t]*model.ycsu[t] + model.Qb*model.ycsb[t] + model.x[t] + model.Qrsb*model.yrsb[t]))
        def tes_upper_rule(model, t):
            return model.s[t] <= model.Eu
        def tes_start_up_rule(model, t):
            if t == 1:
                return model.s0 >= model.Delta[t]*model.delta_rs[t]*( (model.Qu + model.Qb)*( -3 + model.yrsu[t] + model.y0 + model.y[t] + model.ycsb0 + model.ycsb[t] ) + model.x[t] + model.Qb*model.ycsb[t] )
            return model.s[t-1] >= model.Delta[t]*model.delta_rs[t]*( (model.Qu + model.Qb)*( -3 + model.yrsu[t] + model.y[t-1] + model.y[t] + model.ycsb[t-1] + model.ycsb[t] ) + model.x[t] + model.Qb*model.ycsb[t] )
        def maintain_tes_rule(model):
            return model.s[model.num_periods] <= model.s0
        
        self.model.tes_balance_con = pe.Constraint(self.model.T,rule=tes_balance_rule)
        self.model.tes_upper_con = pe.Constraint(self.model.T,rule=tes_upper_rule)
        self.model.tes_start_up_con = pe.Constraint(self.model.T,rule=tes_start_up_rule)
        self.model.maintain_tes_con = pe.Constraint(rule=maintain_tes_rule)
        
        
    def addCycleStartupConstraints(self):
        def pc_inventory_rule(model, t):
            if t == 1:
                return model.ucsu[t] <= model.ucsu0 + model.Delta[t] * model.Qc[t] * model.ycsu[t]
            return model.ucsu[t] <= model.ucsu[t-1] + model.Delta[t] * model.Qc[t] * model.ycsu[t]
        def pc_inv_nonzero_rule(model, t):
            return model.ucsu[t] <= model.Ec * model.ycsu[t]
        def pc_startup_rule(model, t):
            if model.Delta[t] >= 1 and t == 1:
                return model.y[t] <= model.ucsu[t]/model.Ec + model.y0 + model.ycsb0
            elif model.Delta[t] >= 1 and t > 1:
                return model.y[t] <= model.ucsu[t]/model.Ec + model.y[t-1] + model.ycsb[t-1]
            elif model.Delta[t] < 1 and t == 1:
                return model.y[t] <= model.ucsu0/model.Ec + model.y0 + model.ycsb0
            # only case remaining: Delta[t]<1, t>1
            return model.y[t] <= model.ucsu[t-1]/model.Ec + model.y[t-1] + model.ycsb[t-1]
        def pc_production_rule(model, t):
            return model.x[t] + model.Qc[t]*model.ycsu[t] <= model.Qu
        def pc_generation_rule(model, t):
            return model.x[t] <= model.Qu * model.y[t]
        def pc_min_gen_rule(model, t):
            return model.x[t] >= model.Ql * model.y[t]
        
        self.model.pc_inventory_con = pe.Constraint(self.model.T,rule=pc_inventory_rule)
        self.model.pc_inv_nonzero_con = pe.Constraint(self.model.T,rule=pc_inv_nonzero_rule)
        self.model.pc_startup_con = pe.Constraint(self.model.T,rule=pc_startup_rule)
        self.model.pc_production_con = pe.Constraint(self.model.T,rule=pc_production_rule)
        self.model.pc_generation_con = pe.Constraint(self.model.T,rule=pc_generation_rule)
        self.model.pc_min_gen_con = pe.Constraint(self.model.T,rule=pc_min_gen_rule)
        
        
    def addPiecewiseLinearEfficiencyConstraints(self):
        def power_rule(model, t):
            return model.wdot[t] == (model.etaamb[t]/model.eta_des)*(model.etap*model.x[t] + model.y[t]*(model.Wdotu - model.etap*model.Qu))
        def power_ub_rule(model, t):
            return model.wdot[t] <= model.Wdotu*(model.etaamb[t]/model.eta_des)*model.y[t]
        def power_lb_rule(model, t):
            return model.wdot[t] >= model.Wdotl*(model.etaamb[t]/model.eta_des)*model.y[t]
        def change_in_w_pos_rule(model, t):
            if t == 1:
                return model.wdot_delta_plus[t] >= model.wdot[t] - model.wdot0
            return model.wdot_delta_plus[t] >= model.wdot[t] - model.wdot[t-1]
        def change_in_w_neg_rule(model, t):
            if t == 1:
                return model.wdot_delta_minus[t] >= model.wdot0 - model.wdot[t]
            return model.wdot_delta_minus[t] >= model.wdot[t-1] - model.wdot[t]
        def cycle_ramp_rate_pos_rule(model, t):
            return (
                    model.wdot_delta_plus[t] - model.wdot_v_plus[t] <= model.W_delta_plus*model.Delta[t] 
                    + ((model.etaamb[t]/model.eta_des)*model.W_u_plus[t] - model.W_delta_plus*model.Delta[t])
            )
        def cycle_ramp_rate_neg_rule(model, t):
            return (
                    model.wdot_delta_minus[t] - model.wdot_v_minus[t] <= model.W_delta_minus*model.Delta[t] 
                    + ((model.etaamb[t]/model.eta_des)*model.W_u_minus[t] - model.W_delta_minus*model.Delta[t])
            )
        def grid_max_rule(model, t):
            return model.wdot_s[t] <= model.Wdotnet[t]
        def grid_sun_rule(model, t):
            return (
                    model.wdot_s[t] - model.wdot_p[t] == (1-model.etac[t])*model.wdot[t]
                		- model.Lr*(model.xr[t] + model.xrsu[t] + model.Qrl*model.yrsb[t])
                		- model.Lc*model.x[t] 
                        - model.Wh*model.yr[t] - model.Wb*model.ycsb[t] - model.Wht*(model.yrsb[t]+model.yrsu[t])		#Is Wrsb energy [kWh] or power [kW]?  [az] Wrsb = Wht in the math?
                		- (model.Ehs/model.Delta[t])*(model.yrsu[t] + model.yrsb[t] + model.yrsd[t])
            )
        
        self.model.power_con = pe.Constraint(self.model.T,rule=power_rule)
        self.model.power_ub_con = pe.Constraint(self.model.T,rule=power_ub_rule)
        self.model.power_lb_con = pe.Constraint(self.model.T,rule=power_lb_rule)
        self.model.change_in_w_pos_con = pe.Constraint(self.model.T,rule=change_in_w_pos_rule)
        self.model.change_in_w_neg_con = pe.Constraint(self.model.T,rule=change_in_w_neg_rule)
        self.model.cycle_ramp_rate_pos_con = pe.Constraint(self.model.T,rule=cycle_ramp_rate_pos_rule)
        self.model.cycle_ramp_rate_neg_con = pe.Constraint(self.model.T,rule=cycle_ramp_rate_neg_rule)
        self.model.grid_max_con = pe.Constraint(self.model.T,rule=grid_max_rule)
        self.model.grid_sun_con = pe.Constraint(self.model.T,rule=grid_sun_rule)
        
    def addMinUpAndDowntimeConstraints(self):
        def min_cycle_uptime_rule(model,t):
            if pe.value(model.Delta_e[t] > (model.Yu - model.Yu0) * model.y0):
                return sum(model.ycgb[tp] for tp in model.T if pe.value(model.Delta_e[t]-model.Delta_e[tp] < model.Yu) and pe.value(model.Delta_e[t] - model.Delta_e[tp] >= 0)) <= model.y[t]
            return pe.Constraint.Feasible
        def min_cycle_downtime_rule(model,t):
            if pe.value(model.Delta_e[t] > ((model.Yd - model.Yd0)*(1-model.y0))):
                return sum( model.ycge[tp] for tp in model.T if pe.value(model.Delta_e[t]-model.Delta_e[tp] < model.Yd) and pe.value(model.Delta_e[t] - model.Delta_e[tp] >= 0))  <= (1 - model.y[t])
            return pe.Constraint.Feasible
        def cycle_start_end_gen_rule(model,t):
            if t == 1:
                return model.ycgb[t] - model.ycge[t] == model.y[t] - model.y0
            return model.ycgb[t] - model.ycge[t] == model.y[t] - model.y[t-1]
        def cycle_min_updown_init_rule(model,t):
            if model.Delta_e[t] <= max(pe.value(model.y0*(model.Yu-model.Yu0)), pe.value((1-model.y0)*(model.Yd-model.Yd0))):
                return model.y[t] == model.y0
            return pe.Constraint.Feasible
        
        self.model.min_cycle_uptime_con = pe.Constraint(self.model.T,rule=min_cycle_uptime_rule)
        self.model.min_cycle_downtime_con = pe.Constraint(self.model.T,rule=min_cycle_downtime_rule)
        self.model.cycle_start_end_gen_con = pe.Constraint(self.model.T,rule=cycle_start_end_gen_rule)
        self.model.cycle_min_updown_init_con = pe.Constraint(self.model.T,rule=cycle_min_updown_init_rule)
        
    def addCycleLogicConstraints(self):
        def pc_su_persist_rule(model, t):
            if t == 1:
                return model.ycsu[t] + model.y0 <= 1
            return model.ycsu[t] + model.y[t-1] <= 1
        def pc_su_subhourly_rule(model, t):
            if model.Delta[t] < 1:
                return model.y[t] + model.ycsu[t] <= 1
            return pe.Constraint.Feasible  #no analogous constraint for hourly or longer time steps
        def pc_sb_start_rule(model, t):
            if t == 1:
                return model.ycsb[t] <= model.y0 + model.ycsb0
            return model.ycsb[t] <= model.y[t-1] + model.ycsb[t-1]
        def pc_sb_part1_rule(model, t):
            return model.ycsu[t] + model.ycsb[t] <= 1
        def pc_sb_part2_rule(model, t):
            return model.y[t] + model.ycsb[t] <= 1
        def cycle_sb_pen_rule(model, t):
            if t == 1:
                 return model.ychsp[t] >= model.y[t] - (1 - model.ycsb0)
            return model.ychsp[t] >= model.y[t] - (1 - model.ycsb[t-1])
        def cycle_shutdown_rule(model, t):
            if t == 1:
                return model.ycsd[t] >= model.y0 - model.y[t] + model.ycsb0 - model.ycsb[t]
            return model.ycsd[t] >= model.y[t-1] - model.y[t] + model.ycsb[t-1] - model.ycsb[t]
        def cycle_start_pen_rule(model, t):
            if t == 1: 
                return model.ycsup[t] >= model.ycsu[t] - model.ycsu0 
            return model.ycsup[t] >= model.ycsu[t] - model.ycsu[t-1]
         
        self.model.pc_su_persist_con = pe.Constraint(self.model.T,rule=pc_su_persist_rule)
        self.model.pc_su_subhourly_con = pe.Constraint(self.model.T,rule=pc_su_subhourly_rule)
        self.model.pc_sb_start_con = pe.Constraint(self.model.T,rule=pc_sb_start_rule)
        self.model.pc_sb_part1_con = pe.Constraint(self.model.T,rule=pc_sb_part1_rule)
        self.model.pc_sb_part2_con = pe.Constraint(self.model.T,rule=pc_sb_part2_rule)
        self.model.cycle_sb_pen_con = pe.Constraint(self.model.T,rule=cycle_sb_pen_rule)
        self.model.cycle_shutdown_con = pe.Constraint(self.model.T,rule=cycle_shutdown_rule)
        self.model.cycle_start_pen_con = pe.Constraint(self.model.T,rule=cycle_start_pen_rule)


    def generate_constraints(self):
        self.addPersistenceConstraints()
        self.addReceiverStartupConstraints()
        self.addReceiverSupplyAndDemandConstraints()
        self.addReceiverNodeLogicConstraints()
        self.addTESEnergyBalanceConstraints()
        self.addCycleStartupConstraints()
        self.addPiecewiseLinearEfficiencyConstraints()
        self.addMinUpAndDowntimeConstraints()
        self.addCycleLogicConstraints()
        
            
    def solve_model(self, mipgap=0.005):
        opt = pe.SolverFactory('cbc')
        opt.options["ratioGap"] = mipgap
        results = opt.solve(self.model, tee=False, keepfiles=False)
        return results
    
    
# =============================================================================
# Dispatch Wrapper
# =============================================================================

class GeneralDispatchParamWrap(object):
    
    def __init__(self, SSC_dict=None, PySAM_dict=None, pyomo_horizon=48, 
                       dispatch_time_step=1):
        
        self.SSC_dict           = SSC_dict
        self.PySAM_dict         = PySAM_dict
        self.pyomo_horizon      = pyomo_horizon * u.hr
        self.dispatch_time_step = dispatch_time_step * u.hr
        
        
    def set_time_indexed_parameters(self, param_dict):
        
        self.T     = int( self.pyomo_horizon.to('hr').magnitude )
        self.Delta = np.array([self.dispatch_time_step.to('hr').magnitude]*params['T'])
        
        #------- Time indexed parameters ---------
        param_dict['T']        = self.T                  #T: time periods
        param_dict['Delta']    = self.Delta              #\Delta_{t}: duration of period t
        param_dict['Delta_e']  = np.cumsum(self.Delta)   #\Delta_{e,t}: cumulative time elapsed at end of period t
        
        return param_dict

    
    def set_power_cycle_parameters(self, param_dict):
        
        # design parameters
        self.q_rec_design = self.SSC_dict['q_dot_nuclear_des'] * u.MW  # receiver design thermal power
        self.p_pb_design  = self.SSC_dict['P_ref'] * u.MW              # power block design electrical power
        self.eta_design   = self.SSC_dict['design_eff']                # power block efficiency
        self.q_pb_design  = self.p_pb_design / self.eta_design         # power block design thermal rating
        self.dm_pb_design = 0*u.kg/u.s                                 # TODO: get_cycle_design_mass_flow
        
        # fixed parameter calculations
        self.Ec    = self.SSC_dict['startup_frac'] * self.q_pb_design
        self.etap  = 0  # TODO: function needed for this slope
        self.Lc    = (self.SSC_dict['pb_pump_coef']*u.kW/u.kg) * self.dm_pb_design.to('kg') / self.q_pb_design.to('kW')
        self.Qb    = (self.SSC_dict['q_sby_frac'] * self.q_pb_design)
        self.Ql    = (self.SSC_dict['cycle_cutoff_frac'] * self.q_pb_design)
        self.Qu    = (self.SSC_dict['cycle_max_frac'] * self.q_pb_design)
        self.Wb    = (self.SSC_dict['Wb_fract']* self.p_pb_design)
        self.Wdotl = 0*u.kW  # TODO: same function as etap
        self.Wdotu = 0*u.kW  # TODO: same function as etap
        self.W_delta_plus  = self.SSC_dict['disp_pc_rampup']      * param_dict['Wdotu'] # rampup -> frac/min
        self.W_delta_minus = self.SSC_dict['disp_pc_rampdown']    * param_dict['Wdotu']
        self.W_v_plus      = self.SSC_dict['disp_pc_rampup_vl']   * param_dict['Wdotu']
        self.W_v_minus     = self.SSC_dict['disp_pc_rampdown_vl'] * param_dict['Wdotu']
        self.Yu    = 0*u.hr  # TODO: minimum required power cycle uptime 
        self.Yd    = 0*u.hr  # TODO: minimum required power cycle downtime 
        
        ### Power Cycle Parameters ###
        param_dict['Ec']      = self.Ec.to('kW')   #E^c: Required energy expended to start cycle [kWt$\cdot$h]
        param_dict['eta_des'] = self.eta_design    #\eta^{des}: Cycle nominal efficiency [-]
        param_dict['etap']    = self.etap          #\eta^p: Slope of linear approximation of power cycle performance curve [kWe/kWt]
        param_dict['Lc']      = self.Lc.to('')     #L^c: Cycle heat transfer fluid pumping power per unit energy expended [kWe/kWt]
        param_dict['Qb']      = self.Qb.to('kW')   #Q^b: Cycle standby thermal power consumption per period [kWt]
        param_dict['Ql']      = self.Ql.to('kW')   #Q^l: Minimum operational thermal power input to cycle [kWt]
        param_dict['Qu']      = self.Qu.to('kW')   #Q^u: Cycle thermal power capacity [kWt]
        param_dict['Wb']      = self.Wb.to('kW')   #W^b: Power cycle standby operation parasitic load [kWe]
        param_dict['Wdotl']   = self.Wdotl         #\dot{W}^l: Minimum cycle electric power output [kWe]
        param_dict['Wdotu']   = self.Wdotu         #\dot{W}^u: Cycle electric power rated capacity [kWe]
        param_dict['W_delta_plus']  = self.W_delta_plus  #W^{\Delta+}: Power cycle ramp-up designed limit [kWe/h]
        param_dict['W_delta_minus'] = self.W_delta_minus #W^{\Delta-}: Power cycle ramp-down designed limit [kWe/h]
        param_dict['W_v_plus']      = self.W_v_plus      #W^{v+}: Power cycle ramp-up violation limit [kWe/h]
        param_dict['W_v_minus']     = self.W_v_minus     #W^{v-}: Power cycle ramp-down violation limit [kWe/h]
        param_dict['Yu']      = self.Yu            #Y^u: Minimum required power cycle uptime [h]
        param_dict['Yd']      = self.Yd            #Y^d: Minimum required power cycle downtime [h]
        
        return param_dict

    
    def set_fixed_cost_parameters(self, param_dict):
        pass

    
    
if __name__ == "__main__": 
    import dispatch_params
    # import dispatch_outputs
    params = dispatch_params.buildParamsFromAMPLFile("./input_files/data_energy.dat")
    include = {"pv":False,"battery":False,"persistence":False,"force_cycle":True}
    rt = GeneralDispatch(params,include)
    rt_results = rt.solve_model()
    # outputs = dispatch_outputs.RTDispatchOutputs(rt.model)
    # outputs.print_outputs()
    