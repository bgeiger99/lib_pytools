# -*- coding: utf-8 -*-
"""
Created on Sun Dec 31 14:34:26 2023

@author: brg
"""

import dearpygui.dearpygui as dpg
import toml
import sys
import argparse

from shared_mem_dict import SharedMemDict,SharedMemoryConfigurationError


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
        
        self.cfg_filename = ''
        self.shm_cfg = {}
        self.shm = None         
        self.table_rows = []
        self.table_vals_key={}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
    
    def create(self):
        with dpg.window(label="Shared Memory Viewer", 
                        width=800, 
                        height=800, 
                        pos=(100,100), 
                        tag="__main_window"):
            # with dpg.menu_bar():
            #     dpg.add_menu_item(label="Open...",callback=self.select_shm_cfg)
            #     dpg.add_menu_item(label="Info...",callback=self.show_shm_info_window)
            #     dpg.add_menu_item(label="Stream...",callback=self.stream_data)
            
            with dpg.group(horizontal=True):
                with dpg.group(tag="cfg_group"):
                    dpg.add_text('Paste TOML config below:')
                    with dpg.child_window(horizontal_scrollbar=True,border=True,width=400,height=500):
                        dpg.add_input_text(tag="InputTOMLText",
                                        multiline=True,
                                        default_value=default_toml_config,
                                        callback=self.get_shm_cfg_toml_text_input,
                                        on_enter = False,
                                        user_data=self,height=300,width=700,
                                        )
                        self.cfg_valid_status = dpg.add_text('--\n--')
                with dpg.group():
                    with dpg.table(header_row=True, row_background=True,
                                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                                   borders_outerV=True, delay_search=True) as self.data_table:
                        dpg.add_table_column(label="Name")
                        dpg.add_table_column(label="Value")
                # with dpg.group():
                #     dpg.add_text('names/value table goes here')  
                
            with dpg.file_dialog(directory_selector=False, 
                                 show=False, 
                                 callback=self.get_shm_cfg, 
                                 id="file_dialog_id", 
                                 width=700 ,
                                 height=400, 
                                 cancel_callback=cancel_callback,
                                 user_data=self):
                dpg.add_file_extension(".*", color=(150, 255, 150, 255))
                dpg.add_file_extension(".toml", color=(0, 255, 0, 255))
                dpg.add_file_extension(".yaml", color=(255, 255, 0, 210))
                
            # with dpg.window(label="TOML Text Input Box")
                

    @staticmethod
    def select_shm_cfg():
        dpg.show_item("file_dialog_id")
        
    @staticmethod
    def get_shm_cfg(sender,app_data,user_data):
        filename = list(app_data['selections'].values())[0]  
        user_data.cfg_filename = filename
        user_data.load_shm_config()
        
    @staticmethod
    def get_shm_cfg_toml_text_input(sender,app_data,user_data):
        try:
            cfg_dict = toml.loads(app_data)
        except toml.TomlDecodeError:
            cfg_dict = {}
        user_data.load_shm_config(cfg_dict)

        


    def load_shm_config(self,cfg):
        
        if isinstance(cfg,str):
            self.cfg_filename = cfg
            with open(self.cfg_filename,'r') as f:
                self.cfg_dict = toml.load(f)
        elif isinstance(cfg,dict):
            self.cfg_filename = ''
            self.cfg_dict = cfg
            
        # print(f"will load: {self.cfg_dict}")
        
        # close any existing shared memory
        if self.shm is not None:
            self.shm.close()
            self.shm = None
            
        if self.cfg_dict:
            try:
                self.shm = SharedMemDict(**self.cfg_dict)
            except SharedMemoryConfigurationError as e:
                # print(f'got an error: {e}')
                cfg_state_str = f"INVALID Configuration:\n{e}"
                self.shm = None
            else:
                cfg_state_str = "Valid Configuration"
        else:
            cfg_state_str = "INVALID Configuration"
        dpg.set_value(self.cfg_valid_status,cfg_state_str)
        
        if self.shm is not None:
            self.make_data_table()
    
        
    def clear_data_table(self):
        for row in self.table_rows:
            dpg.delete_item(row)
            
        self.table_rows = []
        self.table_vals_key={}
    
    
    def make_data_table(self):
        self.clear_data_table()
        
        for k,v in zip(self.shm.keys(),self.shm.values()):
            with dpg.table_row(parent=self.data_table) as row:
                dpg.add_text(f"{k}")
                self.table_vals_key[k] = dpg.add_text(f"{v}")
            self.table_rows.append(row)

        
        
    def update_data_table(self):
        if self.shm is not None:
            for k,v in self.table_vals_key.items():
                dpg.set_value(v,self.shm[k])

        
    
    @staticmethod
    def show_shm_info_window():
        pass
    
    @staticmethod
    def stream_data():
        pass
    
    def close_shm(self):
        if self.shm is not None:
            self.shm.close()

def run_gui():
    
    dpg.create_context()
    dpg.create_viewport(title='Shared Memory Viewer', width=700, height=600)
    
    MainWindow = main_window()
    MainWindow.create()
    dpg.set_primary_window("__main_window", True)
    
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # below replaces, start_dearpygui()
    while dpg.is_dearpygui_running():
        # insert here any code you would like to run in the render loop
        # you can manually stop by using stop_dearpygui()
        MainWindow.update_data_table()
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
