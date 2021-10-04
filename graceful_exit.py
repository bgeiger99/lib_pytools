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
__version__ = '1.0.0'



import signal


class GracefulExiter():

    def __init__(self):
        self.reset()
        signal.signal(signal.SIGINT, self.change_state)

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
        return not self.state


if __name__=="__main__":
    import sys,itertools,time
    spinner = itertools.cycle('-/|\\')
    loop_control = GracefulExiter()
    print('Ctrl-C to exit loop.')
    while loop_control.proceed:
        outstr = f"{next(spinner)}"
        bs = len(outstr)*"\b"+"\b"
        sys.stdout.write(f"{bs}{outstr}")
        sys.stdout.flush()
        time.sleep(0.1)
    print('Loop exited')