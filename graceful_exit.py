# -*- coding: utf-8 -*-
"""
Created on Fri Jan 15 11:23:23 2021

@author: geiger_br

https://stackoverflow.com/questions/24426451/how-to-terminate-loop-gracefully-when-ctrlc-was-pressed-in-python/24426816

Example

import time
x = 1
flag = GracefulExiter()
while flag.proceed():
    print("Processing file #",x,"started...")
    time.sleep(1)
    x+=1
    print(" finished.")
    if flag.exit_now():
        break

"""

# The master version of this code is tracked separately. The latest version
# (which may not be compatible) is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
#
__version__ = '1.1.0'


try:
    """ Note: this will not work in the IPython console """
    import msvcrt
    msvcrt_avail = True
    def check_for_key(key):
        if msvcrt.kbhit():
            kp = msvcrt.getch()
            if kp == key:
                return True
        return False
except ImportError:
    msvcrt_avail = False





import signal


class GracefulExiter():

    def __init__(self,use_keyboard_key=None,verbose=False):
        self.reset()
        signal.signal(signal.SIGINT, self.change_state)
        if use_keyboard_key is not None and msvcrt_avail:
            if len(use_keyboard_key)!=1:
                raise ValueError('Exit key must be a single character.')
            # windows only...
            self.use_keyboard_key = use_keyboard_key.encode('utf-8')
        else:
            self.use_keyboard_key=None

        if verbose:
            print('Ctrl-C to exit loop.')
            if self.use_keyboard_key is not None:
                print(f"    or hit '{use_keyboard_key}'")

    def change_state(self, signum, frame):
        print("Exit command received (repeat to exit now).")
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.state = True

    def reset(self):
        self.state = False

    def exit_now(self):
        return self.state

    @property
    def proceed(self):
        if self.use_keyboard_key is not None:
            self.state = self.state | check_for_key(self.use_keyboard_key)
        return not self.state


if __name__=="__main__":
    import sys,itertools,time
    spinner = itertools.cycle('-/|\\')
    # loop_control = GracefulExiter(verbose=True)# use this for just Ctrl-C and/or not on Windows
    loop_control = GracefulExiter('q',verbose=True)
    print('Ctrl-C to exit loop.')
    while loop_control.proceed:
        outstr = f"{next(spinner)}"
        bs = len(outstr)*"\b"+"\b"
        sys.stdout.write(f"{bs}{outstr}")
        sys.stdout.flush()
        time.sleep(0.1)
    print('Loop exited')