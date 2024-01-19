# -*- coding: utf-8 -*-
"""
Created on Sun Dec 31 14:34:26 2023

@author: brg

"""

__version__ = '1.0.0'

"""
Changelog
=========

1.0.0 (2024-01-02)
------------------

- Initial GUI Release

"""


import dearpygui.dearpygui as dpg
import toml
import sys
import argparse

from shared_mem_dict import SharedMemDict,SharedMemoryConfigurationError

RED = [100,0,0,255]
YELLOW = [185,190,70]
GREEN = [0,80,0,255]
GREEN_HOT = [0,200,0,255]
BROWN = [55, 59, 29]
BLUE = [0, 31, 64]
TABLE_HEADER_COLOR = (38,72,125)

def callback(sender, app_data):
    print('OK was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)

def cancel_callback(sender, app_data):
    print('Cancel was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)
    
default_toml_config='name = "shm_area_test1_8u235"\nnum = 10\ndtype = "float64"\nvarnames = [ "ab1", "ab2", "alt", "mzl", "dop", "los", "psi", "uw", "orange", "bolt",]\n'
    

class main_window:
    
    def __init__(self):
        self.cfg_dict = {}
        self.cfg_filename = ''
        self.shm_cfg = {}
        self.shm = None         
        self.table_rows = {}
        self.table_vals_key={}


    def create(self):
        with dpg.window(label="Shared Memory Viewer",  
                        pos=(100,100), 
                        tag="__main_window"):
            # with dpg.menu_bar():
            #     dpg.add_menu_item(label="Open...",callback=self.select_shm_cfg)
            #     dpg.add_menu_item(label="Info...",callback=self.show_shm_info_window)
            #     dpg.add_menu_item(label="Stream...",callback=self.stream_data)

            with dpg.tab_bar() as tb:
                with dpg.tab(label="Home"):
                    with dpg.group():
                        with dpg.group(tag="cfg_group"):
                            with dpg.group(horizontal=True):
                                dpg.add_text('Config Validity:')
                                self.cfg_valid_status = dpg.add_text('-----') 
                            with dpg.group(horizontal=True):
                                dpg.add_button(label="File Explorer", callback=lambda: dpg.show_item("file_dialog_id"))
                                dpg.add_text('or paste TOML config below:')
                            with dpg.child_window(border=True,width=-1,height=-1, horizontal_scrollbar=True):
                                dpg.add_input_text(tag="InputTOMLText",
                                                multiline=True,
                                                default_value=default_toml_config,
                                                callback=lambda sender, app_data: self.get_shm_cfg_toml_text_input(sender, app_data, self, tb),
                                                on_enter = False,
                                                user_data=self,height=-1,width=10000,
                                                )
                        with dpg.file_dialog(directory_selector=False, 
                                            show=False, 
                                            modal=True,
                                            callback=lambda sender, app_data: self.get_shm_cfg(sender, app_data, self, parent_tab_bar=tb), 
                                            id="file_dialog_id", 
                                            width=800 ,
                                            height=600, 
                                            cancel_callback=cancel_callback,
                                            user_data=self):
                            dpg.add_file_extension("", color=(0, 150, 255, 255))
                            dpg.add_file_extension(".*", color=(150, 255, 150, 255))
                            dpg.add_file_extension(".toml", color=(0, 255, 0, 255))
                            dpg.add_file_extension(".yaml", color=(255, 255, 0, 210))
                        
                

    @staticmethod
    def select_shm_cfg():
        dpg.show_item("file_dialog_id")
        
    @staticmethod
    def get_shm_cfg(sender,app_data,user_data, parent_tab_bar):
        filename = list(app_data['selections'].values())[0]  
        user_data.cfg_filename = filename
        cfg_dict = toml.load(filename)
        dpg.set_value("InputTOMLText",toml.dumps(cfg_dict))
        user_data.load_shm_config(cfg_dict, parent_tab_bar)
        
    @staticmethod
    def get_shm_cfg_toml_text_input(sender,app_data,user_data, parent_tab_bar):
        try:
            cfg_dict = toml.loads(app_data)
        except toml.TomlDecodeError:
            cfg_dict = {}
        user_data.load_shm_config(cfg_dict, parent_tab_bar)


    def load_shm_config(self,cfg, parent_tab_bar):
        self.cfg_dict = cfg
        self.data_tables = {}
        self.shm = {}  # Change this to a dictionary

        if self.cfg_dict:
            for section in self.cfg_dict:
                print(f"section: {section}")
                # Check if the section is a dictionary (which means it has subsections)
                if isinstance(self.cfg_dict[section], dict):
                    print("is a dict")
                    # Iterate over each subsection in the section
                    for subsection in self.cfg_dict[section]:
                        print(f"subsection: {subsection}")
                        self.table_rows[subsection] = []
                        # close any existing shared memory
                        if subsection in self.shm:  # Check if the subsection already has a SharedMemDict
                            print(f"closing existing shm for {subsection}")
                            self.shm[subsection].close()
                            self.shm[subsection] = None

                        try:
                            self.shm[subsection] = SharedMemDict(**self.cfg_dict[section][subsection])  # Create a new SharedMemDict for the subsection
                        except SharedMemoryConfigurationError as e:
                            print(f'got an error: {e}')
                            cfg_state_str = f"INVALID Configuration: {e}"
                            self.shm[subsection] = None
                        else:
                            cfg_state_str = "Valid Configuration"
                            print(f"making tab for {subsection}...")
                            self.make_tabs(subsection, parent_tab_bar)
        else:
            cfg_state_str = "INVALID Configuration"
        dpg.set_value(self.cfg_valid_status,cfg_state_str)
    
        
    def make_tabs(self, subsection, parent_tab_bar):
        with dpg.tab(label=subsection, parent=parent_tab_bar):
            print(f"{subsection} tab added!")

            # Make a data table for this specific subsection
            print(f"making data table for {subsection}...")
            self.make_data_table(subsection)


    def clear_data_table(self, subsection):
        for row in self.table_rows[subsection]:
            dpg.delete_item(row)

        self.table_rows[subsection] = []
        self.table_vals_key[subsection] = {}


    def make_data_table(self, subsection):
        self.clear_data_table(subsection)
        with dpg.table(header_row=True, row_background=True, borders_innerH=True, borders_outerH=True, 
                       borders_innerV=True, borders_outerV=True, delay_search=True) as self.data_tables[subsection]:
            dpg.add_table_column(label=subsection)
            dpg.add_table_column(label="Value")
            for k, v in zip(self.shm[subsection].keys(),self.shm[subsection].values()):
                with dpg.table_row(parent=self.data_tables[subsection]) as row:
                    dpg.add_text(f"{k}")
                    self.table_vals_key[subsection][k] = dpg.add_text(f"{v}")
                    print(f"adding entry {k} : {v} to data table for {subsection}...")
                self.table_rows[subsection].append(row)
            print(f"made data table for {subsection}!\n")


    def update_data_tables(self):
        if self.cfg_dict:
            for section in self.cfg_dict:
                for subsection in self.cfg_dict[section]:
                    self.update_data_table(subsection)

    def update_data_table(self, subsection):
        if subsection in self.shm and self.shm[subsection] is not None:
            for k,v in self.table_vals_key[subsection].items():
                dpg.set_value(v,self.shm[subsection][k])
    
    
    @staticmethod
    def show_shm_info_window():
        pass
    
    @staticmethod
    def stream_data():
        pass
    
    def close_shm(self):
        for key, resource in self.shm.items():
            resource.close()    

def run_gui():
    
    dpg.create_context()

    # Theme
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 140, 23), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4,1, category=dpg.mvThemeCat_Core) # default is 4,2
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg,TABLE_HEADER_COLOR,category=dpg.mvThemeCat_Core)
        # with dpg.theme_component(dpg.mvInputInt):
        #     dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (140, 255, 23), category=dpg.mvThemeCat_Core)
        #     dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
        with dpg.theme_component(dpg.mvLineSeries):
            # dpg.add_theme_color(dpg.mvPlotCol_Line,(60,150,200),category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker,dpg.mvPlotMarker_Circle,category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize,1.5,category=dpg.mvThemeCat_Plots)
            # dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline,None,category=dpg.mvThemeCat_Plots)

    dpg.bind_theme(global_theme)

    dpg.create_viewport(title='Shared Memory Viewer', width=1200, height=800)
    
    MainWindow = main_window()
    MainWindow.create()
    dpg.set_primary_window("__main_window", True)
    
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # below replaces, start_dearpygui()
    while dpg.is_dearpygui_running():
        # insert here any code you would like to run in the render loop
        # you can manually stop by using stop_dearpygui()
        MainWindow.update_data_tables()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()
    
    MainWindow.close_shm()


def demo_data():
    import time
    cfg = toml.loads(default_toml_config)
    shm = SharedMemDict(**cfg,verbose=True)
    
    t0=time.perf_counter()
    while True:
        shm.arr[0] = time.perf_counter()-t0
        shm.arr[1] = 2*(time.perf_counter()-t0)
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d','--demo-data',required=False, action='store_true')
    
    args = parser.parse_args()
    
    if args.demo_data:
        demo_data()
    else:
        run_gui()


if __name__ == "__main__":
    main()