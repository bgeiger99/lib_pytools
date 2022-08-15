# -*- coding: utf-8 -*-
"""
Created on Thu Jan 28 15:22:34 2021

@author: geiger_br

Basic Example for Shared Memory and Simple PyGame Display

 The master version of this code is tracked separately. The latest version
(which may not be compatible) is available at:
    http://gitlab/gitlab/reference/lib_pytools
    -- or --
    https://github.com/bgeiger99/lib_pytools
"""

# This is just required for the example directory
import os, sys
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))


import pygame
import simple_pygame_display
from shared_mem_dict import SharedMemDict
import yaml


cfg_file = 'sim_config_example.yaml'

# Read Configuration Settings ---------------------------------------------------------------------
with open(cfg_file,'r') as f:
    cfg_dict = yaml.safe_load(f)


# Init Shared Memory ------------------------------------------------------------------------------
# This is the position, attitude, and control settings of the vehicle sent to XPlane and
#  terrain height and normal vector reported below the vehicle from XPlane
reset_shm = True # if True, always reset the shared_memory
xplane_shm_io = cfg_dict['shr_mem']['sim_io']
sim_shm = SharedMemDict(**cfg_dict['shr_mem']['sim_io'], reset_shm=reset_shm)

#%%
simdsp = simple_pygame_display.BaseSimpleDisplay(app_title="App2-Downcount",
                           app_size = (300,700),  # (width, height)
                           fps_desired = 100,
                           app_icon_filename = r"piac_icon.png",
                           fontname="Consolas",
                           fontsize=11,
                          )

#%%
app1_names = 'time u_mps v_mps w_mps p_dps q_dps r_dps roll_deg pitch_deg yaw_deg x_earth_m y_earth_m z_earth_m accx_mps2 accy_mps2 accz_mps2 lat_deg lon_deg alt_m v_north_mps v_east_mps v_down_mps TAS_mps alpha_deg beta_deg oat_degC'.split()
app2_names = 'elevon_port_deg elevon_stbd_deg elevon_sym_deg elevon_dif_deg alt_agl_ref terr_ht_m terr_nrml_east terr_nrml_north terr_nrml_up over_water'.split()


pressed_w=False
pause_data=False
x1=0.
x2=0.
x3=0.
while simdsp.loop_controller():
    # this loop will run at 25 FPS

    ## DO YOUR STUFF ##
    for event in simdsp.events: # User did something.
        if event.type == pygame.KEYDOWN: # user pressed a key
            print(f"User pressed {event.unicode}")
            if event.unicode == 'p':
                pause_data = not pause_data
            if event.unicode == 'r':
                x1=0
                x2=0
                x3=0
            if event.unicode == 'w':
                pressed_w = not pressed_w
            if event.unicode=='q':
                print('quitting..')
                simdsp.running=False  # This is not required, just here as an example

    simdsp.tprint("Pause My Data:  'p'")
    simdsp.tprint("Reset My Data:  'r'")
    simdsp.newline()
    simdsp.tprint('App2 counts down for the control items.')

    # app1 writes these shared memory items:
    if not pause_data:
        x1 = (x1-1.) % 1000
        x2 = (x2-2.) % 4000
        x3 = (x3-3.) % 15000

    ii=0
    for k in app2_names:
        sim_shm[k] = [x1,x2,x3][ii]
        ii = ( ii+1) %3

    # as an alternative to the dict interface:
    #     sim_shm.arr[7] will directly set index 7 of the shared array.

    simdsp.horz_line(length=150)
    # Now read and display all shared items
    simdsp.indent()
    for k in sim_shm.keys():
        if k in app1_names:
            simdsp.tprint(f"app1:  {k:>16s} = {sim_shm[k]:10.2f}")
    simdsp.horz_line(length=150)
    for k in sim_shm.keys():
        if k in app2_names:
            simdsp.tprint(f"app2:  {k:>16s} = {sim_shm[k]:10.2f}")

    simdsp.horz_line(length=150)
    simdsp.newline()
    simdsp.indent()
    simdsp.tprint("My first indented test string")
    simdsp.unindent()

    simdsp.tprint(f"W is {pressed_w}")


simdsp.close()
