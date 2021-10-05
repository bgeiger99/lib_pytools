# -*- coding: utf-8 -*-
"""
Created on Mon Oct  4 14:15:52 2021

@author: geiger_br

sourced from some good stack exchange post but forgot to write it down

"""

# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.0.0'



import itertools

class Spinner:

    spinners = {'lines':'-/|\\',
                'braille_rnd':'⣾⣽⣻⢿⡿⣟⣯⣷',
                'riser':'▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▁',
                'squisher':'▉▊▋▌▍▎▏▎▍▌▋▊▉',
                'half_circle':'◐◓◑◒',
                'qtr_circle':"◴◷◶◵",
                'tri':"◢◣◤◥",
                'star':"✶✸✹✺✹✷",
                'braille':"⡀⡁⡂⡃⡄⡅⡆⡇⡈⡉⡊⡋⡌⡍⡎⡏⡐⡑⡒⡓⡔⡕⡖⡗⡘⡙⡚⡛⡜⡝⡞⡟⡠⡡⡢⡣⡤⡥⡦⡧⡨⡩⡪⡫⡬⡭⡮⡯⡰⡱⡲⡳⡴⡵⡶⡷⡸⡹⡺⡻⡼⡽⡾⡿⢀⢁⢂⢃⢄⢅⢆⢇⢈⢉⢊⢋⢌⢍⢎⢏⢐⢑⢒⢓⢔⢕⢖⢗⢘⢙⢚⢛⢜⢝⢞⢟⢠⢡⢢⢣⢤⢥⢦⢧⢨⢩⢪⢫⢬⢭⢮⢯⢰⢱⢲⢳⢴⢵⢶⢷⢸⢹⢺⢻⢼⢽⢾⢿⣀⣁⣂⣃⣄⣅⣆⣇⣈⣉⣊⣋⣌⣍⣎⣏⣐⣑⣒⣓⣔⣕⣖⣗⣘⣙⣚⣛⣜⣝⣞⣟⣠⣡⣢⣣⣤⣥⣦⣧⣨⣩⣪⣫⣬⣭⣮⣯⣰⣱⣲⣳⣴⣵⣶⣷⣸⣹⣺⣻⣼⣽⣾⣿",
                'hearts':"💛💙💜💚",
                'snake':"⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
                'clock':'🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚',
                'moon':"🌑🌒🌓🌔🌕🌖🌗🌘",
                'run':"🚶🏃",
                'grow':"🔹🔷🔵🔵🔷",
                }

    def __init__(self,name='lines'):
        self.name=name
        self.frames = self.spinners[name]
        self.spinner = itertools.cycle(self.frames)

    @property
    def spin(self):
        return next(self.spinner)

    def write(self,append_str=''):
        outstr = f"{spinner.spin}{append_str}"
        bs = len(outstr)*"\b"+"\b"
        sys.stdout.write(f"{bs}{outstr}")
        sys.stdout.flush()

#%%
if __name__ == "__main__":
    import sys,time
    demo = ['lines','hearts','braille']

    print('Ctrl-C to exit loop.')
    for name in demo:
        print(f"\n'{name}'")
        spinner = Spinner(name)
        for i in range(100):
            spinner.write(f" {i}")
            time.sleep(0.1)


