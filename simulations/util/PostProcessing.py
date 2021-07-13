#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 13:11:44 2021

@author: gabrielsoto
"""

from pylab import rc
import matplotlib.pyplot as plt
import pyomo.environ as pe
import numpy as np
import pint
u = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
rc('axes', linewidth=2)
rc('font', weight='bold', size=12)


# BIG difference here is that the Plots class gets initialized
class Plots(object):
    """
    The Plots class is a part of the PostProcessing family of classes. It can 
    output results from SSCmodels. This might be a 
    Sisyphus-ian task as some of the parameters are very unique to whatever 
    plot you are trying to make, but will do my best to provide basic structures
    and templates to work off of. 

    Note that the Plots class must be initialized before using. 
    """

    def __init__(self, module, fsl='x-small', loc='best', legend_offset=False,
                 lp=16, lps=12, fs=12, lw=2, x_shrink=0.85, x_legend=12):
        """ Initializes the Plots module

        The instantiation of this class receives a full module object, the module
        being one of the NE2 modules in the /neup-ies/simulations/modules directory.
        It also contains various inputs relating to cosmetic parameters for
        matplotlib plots. 

        Inputs:
            module (object)     : object representing NE2 module class after simulations
            fsl (str)           : fontsize for legend
            loc (str)           : location of legend
            legend_offset(bool) : are we plotting legends off-axis?
            lp (int)            : labelpad for axis labels
            lps (int)           : labelpad for axis labels - short version
            fs (int)            : fontsize for labels, titles, etc.
            lw (int)            : linewidth for plotting
            x_shrink (float)    : (legend_offset==True) amount to shrink axis to make room for legend
        """
        # full PySAM module
        self.mod = module.Plant

        # define an Output object to extract information from
        Outputs = self.mod.PySAM_Outputs if module.run_loop else self.mod.Outputs

        # saving full time logs
        self.t_full = np.asarray(Outputs.time_hr)*u.hr
        self.full_slice = slice(0, len(self.t_full), 1)

        # setting operating modes, kept it way at the bottom because it's ugly
        self.set_operating_modes_list()

        # user-defined plotting parameters
        self.lp  = lp  # labelpad
        self.lps = lps  # labelpad short
        self.fs  = fs  # fontsize
        self.lw  = lw  # linewidth
        self.fsl = fsl  # fontsize legend
        self.loc = loc  # location of legend
        
        # offsetting legend
        self.legend_offset = legend_offset # boolean - are we plotting legends off-axis?
        self.x_shrink      = x_shrink # amount to shrink x-asis by to make room for legend

        # alternate legend locations
        self.loc_ur = 'upper right'
        self.loc_ul = 'upper left'
        self.loc_lr = 'lower right'  # location of legend
        self.loc_ll = 'lower left'  # location of legend
        self.loc_cr = 'center right'  # location of legend
        self.loc_cl = 'center left'  # location of legend

        # saving some outputs for plotting
        # TODO: make this its own method, that way we can overload it later
        self.p_cycle = np.asarray(Outputs.P_cycle) * u.MW
        self.gen = (np.asarray(Outputs.gen) * u.kW).to('MW')
        self.q_dot_rec_in = np.asarray(Outputs.q_dot_rec_inc) * u.MW
        self.q_pb = np.asarray(Outputs.q_pb) * u.MW
        self.q_dot_pc_su = np.asarray(Outputs.q_dot_pc_startup) * u.MW
        self.m_dot_pc = np.asarray(Outputs.m_dot_pc) * u.kg/u.s
        self.m_dot_rec = np.asarray(Outputs.m_dot_rec) * u.kg/u.s
        self.T_pc_in = np.asarray(Outputs.T_pc_in) * u.degC
        self.T_pc_out = np.asarray(Outputs.T_pc_out) * u.degC
        self.T_tes_cold = np.asarray(Outputs.T_tes_cold) * u.degC
        self.T_tes_hot = np.asarray(Outputs.T_tes_hot) * u.degC
        self.T_cond_out = np.asarray(Outputs.T_cond_out) * u.degC
        self.e_ch_tes = np.asarray(Outputs.e_ch_tes) * u.MWh
        self.op_mode_1 = np.asarray(Outputs.op_mode_1)
        self.defocus = np.asarray(Outputs.defocus)
        self.price = np.asarray(self.mod.TimeOfDeliveryFactors.dispatch_factors_ts)

        # setting static inputs
        self.q_rec_design  = self.mod.SystemDesign.q_dot_nuclear_des * u.MW  # receiver design thermal power
        self.p_pb_design   = self.mod.SystemDesign.P_ref * u.MW              # power block design electrical power
        self.eta_design    = self.mod.SystemDesign.design_eff                # power block design efficiency
        self.q_pb_design  = (self.p_pb_design / self.eta_design).to('MW')    # power block design thermal rating
        self.T_htf_hot    = (self.mod.SystemDesign.T_htf_hot_des*u.celsius).to('degK')   # heat transfer fluid Hot temp
        self.T_htf_cold   = (self.mod.SystemDesign.T_htf_cold_des*u.celsius).to('degK')  # heat transfer fluid Cold temp
        self.e_tes_design = (self.q_pb_design * self.mod.SystemDesign.tshours*u.hr).to('MWh')  # TES storage capacity (kWht)

        # operating modes
        op_mode_result, modes_order = np.unique(self.op_mode_1, return_index=True) # mode orders and re-ordering
        self.op_mode_result = op_mode_result[np.argsort(modes_order)]     # re-order modes by first appearance of each


    def get_array(self, array_str, slicer):
        """ Method to slice through arrays

        The method uses a list of array strings and the default getter method
        from Python to extract attributes from the instantiated NE2 module. 
        It can also return just magnitudes and slice the output array. 

        Inputs:
            array_str (str)  : string name for output array in NE2 module
            slicer (slice)   : slice corresponding to desired simulation times
        Outputs:
            array (ndarray)  : sliced array of data
        """
        # get array from this class object instance
        array = getattr(self, array_str)
        # if the array is in Pint units, grab the magnitude only
        array = array.m if hasattr(array, 'm') else array
        # return the sliced array based on slice input
        return array[slicer]


    def get_slice(self, start_ind, end_ind):
        """ Method to create slice object

        The method creates a slice object for desired simulation times from
        full data. This slice object is used elsewhere to slice through data arrays.

        Inputs:
            start_ind (int)  : starting index for simulation times
            end_ind (int)    : ending index for simulation times
        Outputs:
            slicer (slice)   : slice corresponding to desired simulation times
        """
        # define a slice to use on arrays based on given starting and ending times
        slicer = slice(int(start_ind), int(end_ind), 1)
        return slicer


    def plot_on_axis(self, ax, x_array, y_array, label, color=None):
        """ Method to plot data on given axis as line plot

        The method receives as input an Axis or AxesSubplot object to plot on.
        It then plots the given x and y arrays as a line plot with given label 
        and color. Results plotted as line plot.

        Inputs:
            ax (object)        : axis object to plot on
            x_array (ndarray)  : array of values to plot on x-axis
            y_array (ndarray)  : array of values to plot on y-axis
            label (str)        : label name for specific line
            color(str)         : name of color to use for plot
        """
        # generic plotting given x,y, an axis, label, and optional color for line
        if color is None:
            ax.plot(x_array.m, y_array, linewidth=self.lw, label=label)
        else:
            ax.plot(x_array.m, y_array, color=color, linewidth=self.lw, label=label)


    def bar_plot_on_axis(self, ax, x_array, y_array, dx, label, alpha=0.5, color=None):
        """ Method to plot data on given axis as bar plot

        The method receives as input an Axis or AxesSubplot object to plot on.
        It then plots the given x and y arrays as a line plot with given label 
        and color. Results plotted as a bar plot.

        Inputs:
            ax (object)        : axis object to plot on
            x_array (ndarray)  : array of values to plot on x-axis
            y_array (ndarray)  : array of values to plot on y-axis
            dx (float)         : width of bars 
            label (str)        : label name for specific line
            alpha (float)      : transparency of bar plot (1 is fully opaque)
            color(str)         : name of color to use for plot
        """
        # generic plotting given x,y, an axis, label, and optional color for line
        if color is None:
            ax.bar(x_array.m, y_array, dx, alpha=0.5, label=label)
        else:
            ax.bar(x_array.m, y_array, dx, color=color, alpha=0.5, label=label)


    def plot_SSC_generic(self, ax, array_list, label_list, y_label, title_label=None,
                         plot_all_time=True, start_hr=0, end_hr=48, is_bar_graph=False,
                         return_extra=False, hide_x=False):
        """ Method to plot generic SSC data

        This method is used to plot any type of SSC data. It lives a level above the
        line/bar plotting methods, the ones that are "_on_axis". This would be the 
        middle level, at an even higher level would be specific methods to specify
        a list of arrays to plot. The method just redirects to either the line or 
        bar plot and sets up a loop for all arrays to be plotted. 

        Inputs:
            ax (object)         : axis object to plot on
            array_list (list)   : list of array string names to plot
            label_list (list)   : list of label string names for each array
            y_label (str)       : label name for y-axis
            title_label(str)    : title name for plot
            plot_all_time(bool) : are we plotting all results or just a portion?
            start_hr (int)      : (plot_all_time==False) hour used for starting index 
            end_hr (int)        : (plot_all_time==False) hour used for ending index
            is_bar_graph(bool)  : are we plotting a bar graph instead of line graph?
            return_extra(bool)  : returning extra outputs
            hide_x(bool)        : hiding the x-axis from this particular plot
        Outputs:
            ax (object)         : axis object to plot on
            d_slice (int)       : (return_extra==True) slicer used for arrays
            t_plot (int)        : (return_extra==True) array of times used as x-axis
        """
        # extracting full time array and slice
        t_plot = self.t_full.to('d')
        d_slice = self.full_slice
        time_label = 'Time (days)'

        # if we're not plotting the full results, slice up the arrays for the time portion we want to plot
        if not plot_all_time:
            d_slice = self.get_slice(start_hr, end_hr)
            t_plot = self.t_full[d_slice]
            time_label = 'Time (hrs)'

        # lambda function to plot arrays to a specific axis
        if is_bar_graph:
            # defining width of bars
            dt = np.diff(t_plot)[0].m  
            def plot_data_on_axis(axis, array, d_label, color=None): \
                return self.bar_plot_on_axis(axis, t_plot, array, dt, d_label, color)
        else:
            def plot_data_on_axis(axis, array, d_label, color=None): \
                return self.plot_on_axis(axis, t_plot, array, d_label, color)

        # lambda function to get arrays from self and slice em
        get_array = lambda array_str : self.get_array(array_str, d_slice)

        #========================#
        #--- Creating Figure  ---#
        #========================#
        
        if self.legend_offset:
            # ___Shrinking x-axis to allow room for legends off-plot
            shrink = self.x_shrink
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * shrink, box.height])
        
        # plotting data from list
        for a, l in zip(array_list, label_list):
            plot_data_on_axis(ax, get_array(a), l)

        #========================#
        #---- Setting Labels ----#
        #========================#
        
        # set y label for given axis
        ax.set_ylabel(y_label,  labelpad=self.lp, fontsize=self.fs, fontweight='bold')

        # set x label for given axis
        if hide_x:
            ax.axes.xaxis.set_visible(False) # hiding the label (typically if it's a multiplot axis)
        else:
            ax.set_xlabel(time_label, labelpad=self.lp, fontsize=self.fs, fontweight='bold')
        
        # set title if given
        if title_label is not None:
            ax.set_title(title_label, fontweight='bold')

        # optional to return the slicer and x-inputs (plotting times)
        if return_extra:
            return ax, d_slice, t_plot
        else:
            return ax

    # =============================================================================
    #  Specific SSC plots
    # =============================================================================
    
    def plot_SSC_power_and_energy(self, ax=None, title_label=None, plot_all_time=True, \
                                  start_hr=0, end_hr=48, hide_x=False, x_legend=1.2, \
                                  y_legend_L=1.0, y_legend_R=1.0):
        """ Method to plot power and energy data on single plot

        This method is used specifically to plot power and energy data from SSC simulation
        results. Built-in options to plot legend off-axis. 

        Inputs:
            ax (object)         : axis object to plot on
            plot_all_time(bool) : are we plotting all results or just a portion?
            title_label(str)    : title name for plot
            start_hr (int)      : (plot_all_time==False) hour used for starting index 
            end_hr (int)        : (plot_all_time==False) hour used for ending index
            hide_x(bool)        : hiding the x-axis from this particular plot
            x_legend (float)    : (legend_offset==True) x-offset defining left-most side of legend
            y_legend_L (float)  : (legend_offset==True) y-offset of left y-axis plot
            y_legend_R (float)  : (legend_offset==True) y-offset of right y-axis plot
        """
        #========================#
        #--- Creating Figure  ---#
        #========================#

        # if no axis object specified, create a figure and axis from it
        if ax is None:
            fig = plt.figure(figsize=[10, 5])
            ax = fig.gca()   # this is the power plot

        # twin axis to plot energy on opposite y-axis
        ax2 = ax.twinx()  # this is the energy plot
        
        # custom y limits and ticks to be integers for Power
        #TODO: add these as some sort of input, maybe dict?
        ax.set_ylim(-100, 1100)
        ax.set_yticks([0, 250, 500, 750, 1000])

        # plot Power arrays
        power_array_list = ['p_cycle', 'q_dot_rec_in', 'gen', 'q_dot_pc_su'] # list of array strings
        power_label_list = ['P_cycle (Electric)',
                            'Q_dot to Salt (Thermal)',
                            'Power generated (Electric)',
                            'PC startup thermal power (Thermal)'] # list of labels for each array string to extract from Outputs
        power_ylabel = 'Power \n(MW)'
        ax  = self.plot_SSC_generic(ax, array_list=power_array_list, \
                                    label_list=power_label_list, \
                                    y_label=power_ylabel, \
                                    title_label=title_label, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x)

        # custom y limits and ticks to be integers for Energy
        ax2.set_ylim(-0.05*self.e_tes_design.m, 0.7*self.e_tes_design.m)

        # plot Energy array(s)
        energy_array_list = ['e_ch_tes']
        energy_label_list = ['Salt Charge Energy Level (Thermal)']
        energy_ylabel = 'Energy \n(MWh)'
        ax2 = self.plot_SSC_generic(ax2, array_list=energy_array_list, \
                                    label_list=energy_label_list, \
                                    y_label=energy_ylabel, \
                                    title_label=None, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x)
        
        # set line color to default C4 (purple)
        ax2.get_lines()[0].set_color("C4")
        
        #========================#
        #---- Setting Labels ----#
        #========================#
        
        # customizing legend(s)
        if self.legend_offset:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_L)) # plot legend for Power arrays
            ax2.legend(loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_R)) # plot legend for Energy arrays and also 
        else:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl) # plot legend for Power arrays
            ax2.legend(loc=self.loc_ul, fontsize=self.fsl) # plot legend for Energy arrays and also 


    def plot_SSC_massflow(self, ax=None, title_label=None, plot_all_time=True, \
                          start_hr=0, end_hr=48, hide_x=False,  x_legend=1.2, \
                          y_legend_L=1.0, y_legend_R=1.0):
        """ Method to plot mass flow and defocus data on single plot

        This method is used specifically to plot mass flow and defocus data from SSC simulation
        results. Built-in options to plot legend off-axis. 

        Inputs:
            ax (object)         : axis object to plot on
            plot_all_time(bool) : are we plotting all results or just a portion?
            title_label(str)    : title name for plot
            start_hr (int)      : (plot_all_time==False) hour used for starting index 
            end_hr (int)        : (plot_all_time==False) hour used for ending index
            hide_x(bool)        : hiding the x-axis from this particular plot
            x_legend (float)    : (legend_offset==True) x-offset defining left-most side of legend
            y_legend_L (float)  : (legend_offset==True) y-offset of left y-axis plot
            y_legend_R (float)  : (legend_offset==True) y-offset of right y-axis plot
        """
        #========================#
        #--- Creating Figure  ---#
        #========================#

        # if no axis object specified, create a figure and axis from it
        if ax is None:
            fig = plt.figure(figsize=[10, 5])
            ax = fig.gca()   # this is the power plot

        # twin axis to plot energy on opposite y-axis
        ax2 = ax.twinx()  # this is the energy plot

        # plot mass flow arrays
        mass_array_list = ['m_dot_pc', 'm_dot_rec'] # list of array strings
        mass_label_list = ['PC HTF mass flow rate',
                           'Receiver Mass Flow Rate'] # list of labels for each array string to extract from Outputs
        mass_ylabel = 'Mass Flow \n(kg/s)'
        ax  = self.plot_SSC_generic(ax, array_list=mass_array_list, \
                                    label_list=mass_label_list, \
                                    y_label=mass_ylabel, \
                                    title_label=title_label, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x)
        
        # custom y limits and ticks to be integers for Defocus
        ax2.set_ylim(0, 1.3)
        ax2.set_yticks(np.arange(0, 1.1, 0.5))
        
        # plot defocus array(s)
        energy_array_list = ['defocus']
        energy_label_list = ['Defocus']
        energy_ylabel = 'Defocus'
        ax2 = self.plot_SSC_generic(ax2, array_list=energy_array_list, \
                                    label_list=energy_label_list, \
                                    y_label=energy_ylabel, \
                                    title_label=None, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x)
        
        # set line color to default C3 (reddish)
        ax2.get_lines()[0].set_color("C3")
        
        #========================#
        #---- Setting Labels ----#
        #========================#
        
        # customizing legend(s)
        if self.legend_offset:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_L)) # plot legend for Power arrays
            ax2.legend(loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_R)) # plot legend for Energy arrays and also 
        else:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl) # plot legend for Power arrays
            ax2.legend(loc=self.loc_ul, fontsize=self.fsl) # plot legend for Energy arrays and also 


    def plot_SSC_op_modes(self, ax=None, title_label=None, plot_all_time=True, \
                          start_hr=0, end_hr=48, hide_x=False,  x_legend=1.2, \
                          y_legend_L=1.0, y_legend_R=1.0):
        """ Method to plot operating modes history on single plot

        This method is used specifically to plot operating modes and relative 
        pricing data from SSC simulation results. Built-in options to plot legend off-axis. 

        Inputs:
            ax (object)         : axis object to plot on
            plot_all_time(bool) : are we plotting all results or just a portion?
            title_label(str)    : title name for plot
            start_hr (int)      : (plot_all_time==False) hour used for starting index 
            end_hr (int)        : (plot_all_time==False) hour used for ending index
            hide_x(bool)        : hiding the x-axis from this particular plot
            x_legend (float)    : (legend_offset==True) x-offset defining left-most side of legend
            y_legend_L (float)  : (legend_offset==True) y-offset of left y-axis plot
            y_legend_R (float)  : (legend_offset==True) y-offset of right y-axis plot
        """
        #========================#
        #--- Creating Figure  ---#
        #========================#

        # if no axis object specified, create a figure and axis from it
        if ax is None:
            fig = plt.figure(figsize=[10, 5])
            ax = fig.gca()   # this is the power plot

        # twin axis to plot energy on opposite y-axis
        ax2 = ax.twinx()  # this is the energy plot

        # custom y limits and ticks to be integers
        ax2.set_ylim(0, 2.5)
        ax2.set_yticks(np.arange(0, 2.5, 0.5))
        
        # plot price array(s)
        price_array_list = ['price']
        price_label_list = [None]
        price_ylabel = 'Tariff \n($/kWh)'
        ax2 = self.plot_SSC_generic(ax2, array_list=price_array_list, \
                                    label_list=price_label_list, \
                                    y_label=price_ylabel, \
                                    title_label=None, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x, \
                                    is_bar_graph=True)
            
        # custom y limits and ticks to be integers
        ax.set_ylim(0, 40)
        ax.set_yticks(np.arange(0, 40, 5))

        # plot operating mode arrays
        op_array_list = ['op_mode_1'] # list of array strings
        op_label_list = [None]        # list of labels for each array string to extract from Outputs
        op_ylabel = 'Operating \nMode'
        ax, d_slice, t_plot  = self.plot_SSC_generic(ax, array_list=op_array_list, \
                                    label_list=op_label_list, \
                                    y_label=op_ylabel, \
                                    title_label=title_label, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x, \
                                    return_extra=True)
        
        #==================================================#
        #---- extract operating modes to designated array
        #==================================================#
        op_mode_1 = self.get_array('op_mode_1', d_slice)

        # Plotting data points over the OP mode line with different colors and labels
        for op in self.op_mode_result[d_slice]:
            # getting unique operating modes
            inds = (op_mode_1 == op)
            # individual index getting plotted with unique color and label
            if np.sum(inds):
                ax.plot(t_plot[inds].m, op_mode_1[inds], 'o', label=self.operating_modes[int(op)])

        #========================#
        #---- Setting Labels ----#
        #========================#
        
        # set OP Mode line color to black
        ax.get_lines()[0].set_color("k")
        
        # customizing legend(s)
        if self.legend_offset:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_L)) # plot legend for Power arrays
        else:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl) # plot legend for Power arrays


    def plot_SSC_temperatures(self, ax=None, title_label=None, plot_all_time=True, \
                              start_hr=0, end_hr=48, hide_x=False,  x_legend=1.2, \
                              y_legend_L=1.0, y_legend_R=1.0):
        """ Method to plot temperature data on single plot

        This method is used specifically to plot temperature data from SSC simulation
        results. Built-in options to plot legend off-axis. 

        Inputs:
            ax (object)         : axis object to plot on
            plot_all_time(bool) : are we plotting all results or just a portion?
            title_label(str)    : title name for plot
            start_hr (int)      : (plot_all_time==False) hour used for starting index 
            end_hr (int)        : (plot_all_time==False) hour used for ending index
            hide_x(bool)        : hiding the x-axis from this particular plot
            x_legend (float)    : (legend_offset==True) x-offset defining left-most side of legend
            y_legend_L (float)  : (legend_offset==True) y-offset of left y-axis plot
            y_legend_R (float)  : (legend_offset==True) y-offset of right y-axis plot
        """
        #========================#
        #--- Creating Figure  ---#
        #========================#

        # if no axis object specified, create a figure and axis from it
        if ax is None:
            fig = plt.figure(figsize=[10, 5])
            ax = fig.gca()   # this is the power plot

        # plot temperature arrays
        temp_array_list = ['T_pc_in', 'T_pc_out', 'T_tes_cold', 'T_tes_hot'] # list of array strings
        temp_label_list = ['PC HTF (hot) inlet temperature',
                           'PC HTF (cold) outlet temperature',
                           'TES cold temperature',
                           'TES hot temperature'] # list of labels for each array string to extract from Outputs
        temp_ylabel = 'Temperature (C)'
        ax  = self.plot_SSC_generic(ax, array_list=temp_array_list, \
                                    label_list=temp_label_list, \
                                    y_label=temp_ylabel, \
                                    title_label=title_label, \
                                    plot_all_time=plot_all_time, \
                                    start_hr=start_hr, end_hr=end_hr, hide_x=hide_x)
        
        #========================#
        #---- Setting Labels ----#
        #========================#
        
        # customizing legend(s)
        if self.legend_offset:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl, bbox_to_anchor=(x_legend, y_legend_L)) # plot legend for Temperature arrays
        else:
            ax.legend( loc=self.loc_ul, fontsize=self.fsl) # plot legend for Temperature arrays


    def set_operating_modes_list(self):
        """ Method to define list of operating modes

        This method creates a list of operating modes pertaining to the specific SSC module we are
        using. This particular list was taken from /ssc/tcs/csp_solver_core.h, in the 
        `C_system_operating_modes` class.
        """

        self.operating_modes = [
            'ITER_START',
            'NUC_OFF__PC_OFF__TES_OFF',
            'NUC_SU__PC_OFF__TES_OFF',
            'NUC_ON__PC_SU__TES_OFF',
            'NUC_ON__PC_SB__TES_OFF',
            'NUC_ON__PC_RM_HI__TES_OFF',
            'NUC_ON__PC_RM_LO__TES_OFF',
            'NUC_DF__PC_MAX__TES_OFF',
            'NUC_OFF__PC_SU__TES_DC',
            'NUC_ON__PC_OFF__TES_CH',
            'NUC_ON__PC_TARGET__TES_CH',
            'NUC_ON__PC_TARGET__TES_DC',
            'NUC_ON__PC_RM_LO__TES_EMPTY',
            'NUC_DF__PC_OFF__TES_FULL',
            'NUC_OFF__PC_SB__TES_DC',
            'NUC_OFF__PC_MIN__TES_EMPTY',
            'NUC_OFF__PC_RM_LO__TES_EMPTY',
            'NUC_ON__PC_SB__TES_CH',
            'NUC_SU__PC_MIN__TES_EMPTY',
            'NUC_SU__PC_SB__TES_DC',
            'NUC_ON__PC_SB__TES_DC',
            'NUC_OFF__PC_TARGET__TES_DC',
            'NUC_SU__PC_TARGET__TES_DC',
            'NUC_ON__PC_RM_HI__TES_FULL',
            'NUC_ON__PC_MIN__TES_EMPTY',
            'NUC_SU__PC_RM_LO__TES_EMPTY',
            'NUC_DF__PC_MAX__TES_FULL',
            'NUC_ON__PC_SB__TES_FULL',
            'NUC_SU__PC_SU__TES_DC',
            'NUC_ON__PC_SU__TES_CH',
            'NUC_DF__PC_SU__TES_FULL',
            'NUC_DF__PC_SU__TES_OFF',
            'NUC_TO_COLD__PC_TARGET__TES_DC',
            'NUC_TO_COLD__PC_RM_LO__TES_EMPTY',
            'NUC_TO_COLD__PC_SB__TES_DC',
            'NUC_TO_COLD__PC_MIN__TES_EMPTY',
            'NUC_TO_COLD__PC_OFF__TES_OFF',
            'NUC_TO_COLD__PC_SU__TES_DC',
            'ITER_END']


class DispatchPlots(object):
    """
    The Plots class is a part of the PostProcessing family of classes. It can 
    output results from Pyomo Dispatch models. 

    Note that the DispatchPlots class must be initialized before using. 
    """

    def __init__(self, model, fsl='x-small', loc='best', legend_offset=False,
                 lp=16, lps=12, fs=12, lw=2, x_shrink=0.75, x_legend=12):
        """ Initializes the Plots module

        The instantiation of this class receives a full Dispatch object, the module
        being one of the Pyomo Dispatch model created in the /neup-ies/simulations/dispatch directory.
        It also contains various inputs relating to cosmetic parameters for
        matplotlib plots. 

        Inputs:
            model (object)      : object representing Pyomo Dispatch Model with results
            fsl (str)           : fontsize for legend
            loc (str)           : location of legend
            legend_offset(bool) : are we plotting legends off-axis?
            lp (int)            : labelpad for axis labels
            lps (int)           : labelpad for axis labels - short version
            fs (int)            : fontsize for labels, titles, etc.
            lw (int)            : linewidth for plotting
            x_shrink (float)    : (legend_offset==True) amount to shrink axis to make room for legend
        """
        # full Dispatch Model from Pyomo
        self.dm = model

        # user-defined plotting parameters
        self.lp  = lp  # labelpad
        self.lps = lps  # labelpad short
        self.fs  = fs  # fontsize
        self.lw  = lw  # linewidth
        self.fsl = fsl  # fontsize legend
        self.loc = loc  # location of legend
        
        # offsetting legend
        self.legend_offset = legend_offset # boolean - are we plotting legends off-axis?
        self.x_shrink      = x_shrink # amount to shrink x-asis by to make room for legend

        # alternate legend locations
        self.loc_ur = 'upper right'
        self.loc_ul = 'upper left'
        self.loc_lr = 'lower right'  # location of legend
        self.loc_ll = 'lower left'  # location of legend
        self.loc_cr = 'center right'  # location of legend
        self.loc_cl = 'center left'  # location of legend
        
        # extract outputs from Dispatch model
        self.set_pyomo_outputs()
    
    
    def set_pyomo_outputs(self):
        """ Method to define list of Pyomo output arrays

        This method extracts outputs from the Pyomo Dispatch model, converts them to numpy arrays
        and saves them to `self`. 
        """
        
        # Dispatch Model with results
        dm = self.dm
        
        # lambda functions
        extract_from_model = lambda name: getattr(dm.model, name)
        extract_array      = lambda name: np.array([ pe.value(extract_from_model(name)[t]) for t in dm.model.T ])
        extract_energy     = lambda name: (extract_array(name)*u.kWh).to('MWh') 
        extract_power      = lambda name: (extract_array(name)*u.kW).to('MW') 
        
        # Time and Pricing Arrays
        self.t_array = extract_array('Delta_e') 
        self.p_array = extract_array('P')

        # Energy Arrays
        self.s_array     = extract_energy('s')
        self.ucsu_array  = extract_energy('ucsu')
        self.unsu_array  = extract_energy('unsu')
        
        # Power Arrays
        self.wdot_array             = extract_power('wdot')
        self.wdot_delta_plus_array  = extract_power('wdot_delta_plus')
        self.wdot_delta_minus_array = extract_power('wdot_delta_minus')
        self.wdot_v_plus_array      = extract_power('wdot_v_plus')
        self.wdot_v_minus_array     = extract_power('wdot_v_minus')
        self.wdot_s_array           = extract_power('wdot_s')
        self.wdot_p_array           = extract_power('wdot_p')
        self.x_array                = extract_power('x')
        self.xn_array               = extract_power('xn')
        self.xnsu_array             = extract_power('xnsu')

        # Binary Arrays (Nuclear)
        self.yn_array    = extract_array('yn') 
        self.ynhsp_array = extract_array('ynhsp') 
        self.ynsb_array  = extract_array('ynsb') 
        self.ynsd_array  = extract_array('ynsu') 
        self.ynsu_array  = extract_array('ynsu') 
        self.ynsup_array = extract_array('ynsup') 
        
        # Binary Arrays (Cycle). adding a +2 to show all binaries on the same plot
        self.y_array     = extract_array('y') + 2
        self.ychsp_array = extract_array('ychsp') + 2
        self.ycsb_array  = extract_array('ycsb')  + 2
        self.ycsd_array  = extract_array('ycsd')  + 2
        self.ycsu_array  = extract_array('ycsu')  + 2
        self.ycsup_array = extract_array('ycsup') + 2
        self.ycgb_array  = extract_array('ycgb')  + 2
        self.ycge_array  = extract_array('ycge')  + 2
    
    
    def overwrite_model(self, new_model):
        """ Overwrites current dispatch model saved to self

        This method deletes current model saved to object and overwrites it with new model that
        is used as input to this method.

        Inputs:
            new_model (object)   : object representing Pyomo Dispatch Model with results
        """
        
        # delete current Dispatch mode
        del self.dm
        
        # save new model to self
        self.dm = new_model
        
        # re-set the pyomo outputs from new model
        self.set_pyomo_outputs()
        

    def plot_pyomo(self, dm):

        lw     = self.lw
        lp     = self.lp
        lps    = self.lps
        fs     = self.fs
        fsl    = self.fsl
        loc    = self.loc
        loc_cr = self.loc_cr

       

        # ___Marking 24 hour lines
        time_24hr = np.ones([len(t_array)])*24
        energy_24hr = np.linspace(np.min(s_array.m),
                                  np.max(s_array.m, )*1.1, len(t_array))
        power_24hr = np.linspace(np.min([wdot_array.m, x_array.m]),
                                 np.max([wdot_array.m, x_array.m])*1.3, len(t_array))
        binary_24hr = np.linspace(0, 3.1, len(t_array))
        binary_div = 1.5*np.ones(len(t_array))

        # ======= Plotting ========== #
        fig1 = plt.figure(figsize=[12, 10])
        ax1 = fig1.add_subplot(411)
        ax2 = fig1.add_subplot(412)
        ax3 = fig1.add_subplot(413)
        ax4 = fig1.add_subplot(414)
        ax5 = ax2.twinx()

        # ___Shrinking x-axis to allow room for legends off-plot
        shrink = 0.75
        box = ax1.get_position()
        ax1.set_position([box.x0, box.y0, box.width * shrink, box.height])

        box = ax2.get_position()
        ax2.set_position([box.x0, box.y0, box.width * shrink, box.height])

        box = ax3.get_position()
        ax3.set_position([box.x0, box.y0, box.width * shrink, box.height])

        box = ax4.get_position()
        ax4.set_position([box.x0, box.y0, box.width * shrink, box.height])

        # ___Energy Plots ___________________________________________________________________
        wts = np.linspace(4, 2, 3)
        ax1.plot(t_array, s_array.m,
                 linewidth=wts[0], label='TES Reserve Quantity')
        ax1.plot(t_array, ucsu_array.m,
                 linewidth=wts[1], label='Cycle Startup Energy Inventory')
        ax1.plot(t_array, unsu_array.m,
                 linewidth=wts[2], label='Nuclear Startup Energy Inventory')

        # -Line marking the 24 hour line
        ax1.plot(time_24hr, energy_24hr, 'k--', linewidth=lw)

        # -Labels
        ax1.set_ylabel('Energy (MWh)', labelpad=lp,
                       fontsize=fs, fontweight='bold')
        ax1.legend(loc=loc, fontsize=fsl, bbox_to_anchor=(
            1.4, 1.0))  # bbox stuff places legend off-plot

        # ___Power Plots ___________________________________________________________________
        wts = np.linspace(6, 2, 6)
        ax2.plot(t_array, wdot_array.m,
                 linewidth=wts[0], label='Cycle Out (E)')
        ax2.plot(t_array, x_array.m,    linewidth=wts[1], label='Cycle In (T)')
        ax2.plot(t_array, xn_array.m,
                 linewidth=wts[2], label='Nuclear Out (T)')
        ax2.plot(t_array, xnsu_array.m,
                 linewidth=wts[3], label='Nuclear Startup (T)')
        ax2.plot(t_array, wdot_s_array.m,
                 linewidth=wts[4], label='Energy Sold to Grid (E)')
        ax2.plot(t_array, wdot_p_array.m,
                 linewidth=wts[5], label='Energy Purchased (E)')

        # -Line marking the 24 hour line
        ax2.plot(time_24hr, power_24hr, 'k--', linewidth=lw)

        # -Labels
        ax2.set_ylabel('Power (MW)', labelpad=lp,
                       fontsize=fs, fontweight='bold')
        ax2.legend(loc=loc, fontsize=fsl, bbox_to_anchor=(1.42, 1.0))

        # ___Power Plots x2 ___________________________________________________________________
        wts = np.linspace(6, 2, 6)
        ax3.plot(t_array, wdot_delta_plus_array.m,
                 linewidth=wts[0], label='PC Ramp Up (E)')
        ax3.plot(t_array, wdot_delta_minus_array.m,
                 linewidth=wts[1], label='PC Ramp Down (E)')
        ax3.plot(t_array, wdot_v_plus_array.m,
                 linewidth=wts[2], label='PC Ramp Up Beyond (E')
        ax3.plot(t_array, wdot_v_minus_array.m,
                 linewidth=wts[3], label='PC Ramp Down Beyond(E')

        # -Line marking the 24 hour line
        ax3.plot(time_24hr, power_24hr, 'k--', linewidth=lw)

        # -Labels
        ax3.set_ylabel('Power (MW)', labelpad=lp,
                       fontsize=fs, fontweight='bold')
        ax3.legend(loc=loc, fontsize=fsl, bbox_to_anchor=(1.34, 1.0))

        # ___Price Plot ________________________________________________________________
        ax5.bar(t_array, p_array, np.diff(t_array)
                [0], alpha=0.35, label="Price")

        wts = np.linspace(10, 1, 14)
        # ___Binary Plots ______________________________________________________________
        ax4.plot(t_array, yn_array,    linewidth=wts[0], label='Receiver On?')
        ax4.plot(t_array, ynhsp_array,
                 linewidth=wts[1], label='Receiver HSU Pen?')
        ax4.plot(t_array, ynsb_array,  linewidth=wts[2], label='Receiver SB?')
        ax4.plot(t_array, ynsd_array,  linewidth=wts[3], label='Receiver SD?')
        ax4.plot(t_array, ynsu_array,  linewidth=wts[4], label='Receiver SU?')
        ax4.plot(t_array, ynsup_array,
                 linewidth=wts[5], label='Receiver CSU Pen?')
        ax4.plot(t_array, y_array,
                 linewidth=wts[6], label='Cycle Generating Power?')
        ax4.plot(t_array, ychsp_array,
                 linewidth=wts[7], label='Cycle HSU Pen?')
        ax4.plot(t_array, ycsb_array,  linewidth=wts[8], label='Cycle SB?')
        ax4.plot(t_array, ycsd_array,  linewidth=wts[9], label='Cycle SD?')
        ax4.plot(t_array, ycsu_array,  color='k',
                 linewidth=wts[10], label='Cycle SU?')
        ax4.plot(t_array, ycsup_array,
                 linewidth=wts[11], label='Cycle CSU Pen?')
        ax4.plot(t_array, ycgb_array,
                 linewidth=wts[12], label='Cycle Began Gen?')
        ax4.plot(t_array, ycge_array,
                 linewidth=wts[13], label='Cycle Stopped Gen?')
        ax4.plot(t_array, binary_div, 'k--', linewidth=2)

        # -Line marking the 24 hour line
        ax4.plot(time_24hr, binary_24hr, 'k--', linewidth=lw)

        # -Labels
        ax4.set_xlabel('Time (hrs)', labelpad=lp,
                       fontsize=fs, fontweight='bold')
        ax4.set_ylabel('Binary Vars', labelpad=lp,
                       fontsize=fs, fontweight='bold')
        ax4.legend(loc=loc, fontsize=fsl, bbox_to_anchor=(1.35, 1.3))
        ax5.set_ylabel('Price ($/kWh)', labelpad=lps,
                       fontsize=fs, fontweight='bold')
        ax5.legend(loc=loc_cr, fontsize=fsl)

        # -Axis limits and tickmarks
        ax4.set_ylim(-0.2, 3.4)
        ax4.set_yticks([0, 1, 2, 3])
        ax4.set_yticklabels([0, 1, 0, 1])
        ax5.set_ylim(0.4, 2.5)
        ax5.set_yticks([0.50, 0.75, 1])

        # set full title
        ax1.set_title('Pyomo Results - Normal', fontweight='bold')

        # plt.tight_layout()

        # =============================================================================
        # objective function
        # =============================================================================

        # fig = plt.figure()
        # ax1o = fig.add_subplot(211)
        # # ax1o = fig.add_subplot(111)
        # ax2o = fig.add_subplot(212)

        # #profit
        # Obj_profit      = 0.1 * d_array * p_array * ( wdot_s_array - wdot_p_array )
        # Obj_cycle_susd  = (Ccsu * ycsup_array + 0.1*Cchsp*ychsp_array + ycsd_array)
        # Obj_cycle_ramp  = C_delta_w*(wdot_delta_plus_array + wdot_delta_minus_array) + C_v_w*(wdot_v_plus_array + wdot_v_minus_array)
        # Obj_rec_susd    = Crsu*ynsup_array + Crhsp*ynhsp_array + ynsd_array
        # Obj_ops         = d_array*(Cpc*wdot_array + Ccsb*Qb*ycsb_array + Crec*xn_array)

        # ax1o.plot(t_array, Obj_profit, linewidth=lw, label='Profit Term')
        # ax2o.plot(t_array, -Obj_cycle_susd, linewidth=lw, label='Cycle Startup/Shutdown Term')
        # ax1o.plot(t_array, -Obj_cycle_ramp, linewidth=lw, label='Cycle Ramping Term')
        # ax1o.plot(t_array, -Obj_rec_susd, linewidth=lw, label='Receiver Startup/Shutdown Term')
        # ax1o.plot(t_array, -Obj_ops, linewidth=lw, label='Cycle and Rec Ops Term')

        # ax1o.legend(loc='best')
        # ax2o.legend(loc='best')

        # ax1o.set_title('Pyomo Obj Fun - Normal', fontweight='bold')

        # plt.tight_layout()

