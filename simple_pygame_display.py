# -*- coding: utf-8 -*-
"""
Created on Thu Jan 28 15:22:34 2021

@author: geiger_br


Simple PyGame Display

This is a basic class to get a simple text display GUI up and running at a controlled rate with
minimal setup.

Quickstart:

    import simple_pygame_display
    simdsp = simple_pygame_display.BaseSimpleDisplay(app_title="My First Display",
                                                     app_size = (450,350),  # (width, height)
                                                     fps_desired = 25.,
                                                     app_icon_filename = r"piac_icon.png",
                                                     fontname="Consolas",
                                                     fontsize=11,
                                                     )

    while simdsp.loop_controller():
        # this loop will run at 25 FPS

        ## DO YOUR STUFF ##

        for event in simdsp.events: # User did something.
            if event.type == simple_pygame_display.pygame.KEYDOWN: # user pressed a key
                print(f"User pressed {event.unicode}")
                if event.unicode=='q':
                    print('quitting..')
                    simdsp.running=False  # This is not required, just here as an example

        simdsp.tprint("My first test string")
        simdsp.horz_line(length=150)
        simdsp.newline()
        simdsp.indent()
        simdsp.tprint("My first indented test string")
        simdsp.unindent()
        var1=10.
        simdsp.tprint(f"My number is {var1}")


    simdsp.close()
"""


""" The master version of this code is tracked separately. The latest version
(which may not be compatible) is available at:
    http://gitlab/gitlab/reference/lib_pytools
    -- or --
    https://github.com/bgeiger99/lib_pytools
"""
__version__ = '1.1.0'  # see http://gitlab/gitlab/reference/lib_pytools for the latest version



import pygame
import time
import math
import os
# from . import clock   # see note at self.clock below

#%%
# Define some colors.
BLACK = pygame.Color('black')
WHITE = pygame.Color('white')
GREEN = pygame.Color('green')
RED = pygame.Color('red')
DARKBLU = pygame.Color(41,45,62,1)

BGCOLOR = DARKBLU
FGCOLOR = WHITE

# This is a simple class that will help us print to the screen.
class TextPrint(object):

    def __init__(self,screen,fontname=None,fontsize=11):
        self.reset()
        self.font = pygame.font.SysFont(fontname,fontsize)
        self.screen=screen

    def tprint(self, textString, color=FGCOLOR):
        textBitmap = self.font.render(textString, True, color)
        self.screen.blit(textBitmap, (self.x, self.y))
        self.y += self.line_height

    def tprint_xy(self, textString, color=FGCOLOR, x=None, y=None):
        if x is None:
            x=self.x
        if y is None:
            y=self.y
        textBitmap = self.font.render(textString, True, color)
        self.screen.blit(textBitmap, (x, y))
        trect = textBitmap.get_rect()
        return (self.x,self.y,trect.w+self.x,trect.h+self.y)

    def newline(self):
        self.y += self.line_height

    def horz_line(self,length=10,color=FGCOLOR,width=1):
        # self.y += self.line_height//2
        pygame.draw.line(self.screen,color,(self.x,self.y),(self.x+length,self.y),1)
        self.y += self.line_height//2

    def reset(self):
        self.x = 10
        self.y = 10
        self.line_height = 15

    def indent(self):
        self.x += 10

    def unindent(self):
        self.x -= 10

#%%
class BaseSimpleDisplay:
    """ Implements a basic GUI display for use with simulation tasks

        capabilities:
            app title
            app size
            app icon
            app update rate
            display text at various locations/colors
            fps tracking


    """

    def __init__(self,
                 app_title = "MyApp",
                 app_size  = (400,400),
                 fontname="Consolas",
                 fontsize=11,
                 fps_desired = 25.1,
                 app_icon_filename = None,
                 fg_color = FGCOLOR,
                 bg_color = BGCOLOR,
                 print_status_line = True,
                 ):

        self.app_title = app_title
        self.app_size = (self.app_width,self.app_height) = app_size
        self.BGCOLOR = bg_color
        self.FGCOLOR = fg_color
        self.print_status_line = print_status_line
        self.check_app_height_once=True
        self.loop_ctrl_flag = False  # True if the top matter of the loop controller has run, False after the bottom matter of the loop controller runs

        pygame.init()

        # Set the width and height of the screen (width, height).
        self.screen = pygame.display.set_mode(self.app_size)
        pygame.display.set_caption(self.app_title)

        # Get ready to print.
        self.textPrint = TextPrint(screen=self.screen,fontname=fontname,fontsize=fontsize)

        # Loop until the user clicks the close button.
        self.running = True

        # Used to manage how fast the screen updates.
        self.clock = pygame.time.Clock()
        # The pygame.time.Clock.tick() has gotten very inaccurate with the switch from SDL 1.x to 2.X
        # If timing consistency is important, use this clock regulator. Also see clock in run_at_bottom_of_loop
        # self.clock = clock.Clock(fps_desired)


        # clock.tick operates on integer milliseconds. So, if we request exactly 100 Hz, it will limit
        # on a msec tick up to, but not including, 10 msec. This results in a minimum frame time of 11 msec
        # which is 1000/11 = 90.0 Hz. Therefore, to get 100 fps, request just over 100 (such as 100.1) and
        # the tick will result in a minimum frame time of 10 msec.
        self.fps_desired = fps_desired+0.1

        if app_icon_filename is not None:
            try:
                icon_filename = os.path.abspath(os.path.join(os.path.dirname(__file__),"simple_pygame_display_assets/piac_icon.png"))
                with open(icon_filename, 'r') as f:
                    # doing it this way because passing a filename seems to be problematic for pygame.image.load
                    programIcon = pygame.image.load(f)
                pygame.display.set_icon(programIcon)
            except FileNotFoundError:
                print(f"Cant find app icon: {icon_filename}")


        self.n=0
        self.t0=time.perf_counter()
        self.t1=self.t0+1.0/fps_desired
        self.t_proc=0.5*1.0/fps_desired
        self.rate=fps_desired
        self.smoothing_frames = 2

    def loop_controller(self):
        """ I might change this later but this was the easy way to eliminate putting
        run_at_top_of_loop() and run_at_bottom_of_loop in user's GUI code"""

        if self.loop_ctrl_flag is True:
            self.run_at_bottom_of_loop()

        loop_is_running = self.run_at_top_of_loop()

        return loop_is_running


    def run_at_top_of_loop(self):
        self.n+=1
        self.t0=self.t1
        self.t1=time.perf_counter()
        self.nsmp=math.ceil(self.smoothing_frames*self.fps_desired) # fps_desired might change, this will behave more consistently than leaving it constant
        self.rate = (self.rate*(self.nsmp-1) + 1.0/(self.t1-self.t0))/self.nsmp

        self.events = pygame.event.get()

        # Get Events
        for event in self.events:
            if event.type == pygame.QUIT: # If user clicked close.
                self.running = False # Flag that we are done so we exit this loop.

        #
        # Clear the screen for the next iteration
        #
        # First, clear the screen to white. Don't put other drawing commands
        # above this, or they will be erased with this command.
        self.screen.fill(self.BGCOLOR)
        self.textPrint.reset()

        self.loop_ctrl_flag = True # true so that run_at_bottom_of_loop is called next time.

        return self.running

    def run_at_bottom_of_loop(self):

        # This is a status printer
        if self.print_status_line:
            if self.check_app_height_once and self.textPrint.y+25>self.app_height:
                self.check_app_height_once = False
                self.app_height = self.textPrint.y + 25
                self.app_size = (self.app_width,self.app_height)
                print(f'increasing app height to: {self.app_height}')
                print('you should increase your app height in your code to accomodate the status display')
                self.screen = pygame.display.set_mode(self.app_size)

            # fps = self.clock.get_fps() # not going to use this pygame derived fps anymore
            status_line_y = self.app_height-20
            status_line_len=self.app_width-20
            pygame.draw.line(self.screen,self.FGCOLOR,(10,status_line_y-5),(10+status_line_len,status_line_y-5),1)
            load_pct = 100*self.fps_desired*self.t_proc
            # self.tprint_xy(f"Update: {self.rate:6.2f} Hz  t_proc={self.t_proc:5.4f} sec ({load_pct:3.0f}%) n={self.n}  ",x=10,y=status_line_y)
            self.tprint_xy(f"{self.rate:6.2f} Hz | {load_pct:3.0f}% duty ({self.t_proc:5.4f} sec) | n={self.n}  ",x=10,y=status_line_y)

        # update the screen with what we've drawn.
        pygame.display.flip()

        # Track processing time
        self.t_proc = (self.t_proc*(self.nsmp-1) + (time.perf_counter()-self.t1))/self.nsmp

        # self.loop_ctrl_flag = False # false to prevent getting called again before run_at_top_of_loop is called

        # Limit  frames per second.
        # clock.tick operates on integer milliseconds. So, if we request exactly 100 Hz, it will limit
        # on a msec tick up to, but not including, 10 msec. This results in a minimum frame time of 11 msec
        # which is 1000/11 = 90.0 Hz. Therefore, to get 100 fps, request just over 100 (such as 100.1) and
        # the tick will result in a minimum frame time of 10 msec.
        self.clock.tick(self.fps_desired)
        # self.clock.sleep() # see note above at self.clock



    def close(self):
        """ run this when exiting the app """
        pygame.quit()


    # this could be inherited
    def tprint(self,textString,color=FGCOLOR):
        self.textPrint.tprint(textString,color=color)
    def tprint_xy(self, textString, color=FGCOLOR, x=None, y=None):
        return self.textPrint.tprint_xy(textString,color=color,x=x,y=y)
    def horz_line(self,length=10,color=FGCOLOR,width=1):
        self.textPrint.horz_line(length=length,color=color,width=width)
    def newline(self):
        self.textPrint.newline()
    def reset(self):
        self.textPrint.reset()
    def indent(self):
        self.textPrint.indent()
    def unindent(self):
         self.textPrint.unindent()
    @property
    def txt_ypos(self):
        return self.textPrint.y

    def draw_rect(self,color,pos,width=0,border_radius=0):
        pygame.draw.rect(self.screen, pygame.Color(color), pos, width=width,border_radius=border_radius)





#%% ===== Example =================================================================================
if __name__ == "__main__":
    simdsp = BaseSimpleDisplay(app_title="My First Display",
                               app_size = (450,350),  # (width, height)
                               fps_desired = 50,
                               app_icon_filename = r"piac_icon.png",
                               fontname="Consolas",
                               fontsize=11,
                              )

    while simdsp.loop_controller():
        # this loop will run at 25 FPS

        ## DO YOUR STUFF ##
        for event in simdsp.events: # User did something.
            if event.type == pygame.KEYDOWN: # user pressed a key
                print(f"User pressed {event.unicode}")
                if event.unicode=='q':
                    print('quitting..')
                    simdsp.running=False  # This is not required, just here as an example

        x=0
        for i in range(30000):
            x+=1

        simdsp.tprint("My first test string")
        simdsp.horz_line(length=150)
        simdsp.newline()
        simdsp.indent()
        simdsp.tprint("My first indented test string")
        simdsp.unindent()
        var1=10.
        simdsp.tprint(f"My number is {var1}")


    simdsp.close()
