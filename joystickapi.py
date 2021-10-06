# -*- coding: utf-8 -*-
"""
Created on Thu Aug  5 08:05:44 2021

The current implementation will just use the first joystick found. Modifications
are required to use data from more than one joystick.

https://discourse.panda3d.org/t/game-controllers-on-windows-without-pygame/14129
https://gist.github.com/rdb/8883307

pyglet alternatively uses DirectInput to read joysticks:
    http://code.google.com/p/pyglet/source/browse/pyglet/libs/win32/dinput.py
    http://code.google.com/p/pyglet/source/browse/pyglet/input/directinput.py


# Released by rdb under the Unlicense (unlicense.org)
# Further reading about the WinMM Joystick API:
# http://msdn.microsoft.com/en-us/library/windows/desktop/dd757116(v=vs.85).aspx
"""

# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.0.2'


import ctypes
import winreg
from ctypes.wintypes import WORD, UINT, DWORD
from ctypes.wintypes import WCHAR as TCHAR

# Fetch function pointers
joyGetNumDevs = ctypes.windll.winmm.joyGetNumDevs
joyGetPos = ctypes.windll.winmm.joyGetPos
joyGetPosEx = ctypes.windll.winmm.joyGetPosEx
joyGetDevCaps = ctypes.windll.winmm.joyGetDevCapsW

# Define constants
MAXPNAMELEN = 32
MAX_JOYSTICKOEMVXDNAME = 260

JOYERR_NOERROR = 0
JOY_RETURNX = 0x1
JOY_RETURNY = 0x2
JOY_RETURNZ = 0x4
JOY_RETURNR = 0x8
JOY_RETURNU = 0x10
JOY_RETURNV = 0x20
JOY_RETURNPOV = 0x40
JOY_RETURNBUTTONS = 0x80
JOY_RETURNRAWDATA = 0x100
JOY_RETURNPOVCTS = 0x200
JOY_RETURNCENTERED = 0x400
JOY_USEDEADZONE = 0x800
JOY_RETURNALL = JOY_RETURNX | JOY_RETURNY | JOY_RETURNZ | JOY_RETURNR | JOY_RETURNU | JOY_RETURNV | JOY_RETURNPOV | JOY_RETURNBUTTONS


# Define some structures from WinMM that we will use in function calls.
class JOYCAPS(ctypes.Structure):
    _fields_ = [
        ('wMid', WORD),
        ('wPid', WORD),
        ('szPname', TCHAR * MAXPNAMELEN),
        ('wXmin', UINT),
        ('wXmax', UINT),
        ('wYmin', UINT),
        ('wYmax', UINT),
        ('wZmin', UINT),
        ('wZmax', UINT),
        ('wNumButtons', UINT),
        ('wPeriodMin', UINT),
        ('wPeriodMax', UINT),
        ('wRmin', UINT),
        ('wRmax', UINT),
        ('wUmin', UINT),
        ('wUmax', UINT),
        ('wVmin', UINT),
        ('wVmax', UINT),
        ('wCaps', UINT),
        ('wMaxAxes', UINT),
        ('wNumAxes', UINT),
        ('wMaxButtons', UINT),
        ('szRegKey', TCHAR * MAXPNAMELEN),
        ('szOEMVxD', TCHAR * MAX_JOYSTICKOEMVXDNAME),
    ]

class JOYINFO(ctypes.Structure):
    _fields_ = [
        ('wXpos', UINT),
        ('wYpos', UINT),
        ('wZpos', UINT),
        ('wButtons', UINT),
    ]

class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ('dwSize', DWORD),
        ('dwFlags', DWORD),
        ('dwXpos', DWORD),
        ('dwYpos', DWORD),
        ('dwZpos', DWORD),
        ('dwRpos', DWORD),
        ('dwUpos', DWORD),
        ('dwVpos', DWORD),
        ('dwButtons', DWORD),
        ('dwButtonNumber', DWORD),
        ('dwPOV', DWORD),
        ('dwReserved1', DWORD),
        ('dwReserved2', DWORD),
    ]


#%%
class Joystick:
    """Implement a single joystick object."""

    def __init__(self,n_axes,n_btns,n_hats,name,caps,flags):
        self.n_axes = n_axes
        self.n_btns = n_btns
        self.n_hats = n_hats
        self.axes = [None]*n_axes
        self.btns = [None]*n_btns
        self.hats = [(None,None)]*n_hats # each hat is two-axis
        self.caps = caps
        self.flags = flags
        self.name = name
        self.midval = (caps.wXmax-caps.wXmin)//2 # assumes all axes are the same
        self.fresh = 0
        self.ERROR = True

    def get_axis(self,j):
        return self.axes[j] if j<self.n_axes else None

    def get_button(self,j):
        return self.btns[j] if j<self.n_btns else None

    def get_hat(self,j):
        return self.hats[j] if j<self.n_hats else None

    def get_numaxes(self):
        return len(self.axes)
    def get_numbtns(self):
        return len(self.btns)
    def get_numhats(self):
        return len(self.hats)

    def get_axes_str(self,sp=' '):
        """Output a convenient string with joystick axes state."""
        return f',{sp}'.join([f"{j}:{self.get_axis(j):6.3f}" for j in range(self.n_axes)])

    def get_btns_str(self,sp=''):
        """Output a convenient string with joystick button states."""
        return f"{sp}".join(["X" if b else "-" for b in self.btns])


#%%
class JoystickReader:
    """Impement a class that reads all joysticks and returns their data in a joystick object."""

    # Using joyGetPosEx() always returns 6 axes values regardless of hardware.
    # See https://docs.microsoft.com/en-us/previous-versions/dd757112(v=vs.85)
    NUM_JOY_AXES = 6

    hats_4way = {0:    ( 0, 1),
                 4500: ( 1, 1),
                 9000: ( 1, 0),
                 13500:( 1,-1),
                 18000:( 0,-1),
                 22500:(-1,-1),
                 27000:(-1, 0),
                 31500:(-1, 1),
                 65535:( 0, 0),
                 }

    def __init__(self):
        self.initialize()

    def initialize(self):
        """Check for an existing joystick and initialize its object if found.

        This will reset self.stk dict when called. If no joysticks are connected,
        this function can be quite slow as it cycles through all possible
        joystick ids.
        """
        self.stk = {}
        self.info = JOYINFO()
        self.p_info = ctypes.pointer(self.info)

        self.num_js = joyGetNumDevs()
        if self.num_js == 0:
            print("Joystick driver not loaded.")

        for jsid in range(self.num_js):
            if joyGetPos(jsid, self.p_info) == JOYERR_NOERROR:
                caps = JOYCAPS()
                if joyGetDevCaps(jsid, ctypes.pointer(caps), ctypes.sizeof(JOYCAPS)) != 0:
                    print(f"Failed to get device {jsid} capabilities.")
                else:
                    js_name = self._get_jsname_from_reg(caps.szRegKey,jsid)
                    flags = {k:(1 << i) & caps.wCaps != 0 for i,k in enumerate(['HASZ','HASR','HASU','HASV','HASPOV','POV4dir','POVCTS'])}
                    self.stk[jsid] = Joystick(n_axes=caps.wNumAxes,
                                              n_btns=caps.wNumButtons,
                                              n_hats=1,
                                              name = js_name,
                                              caps = caps,
                                              flags = flags)

        if not self.stk:
            self.NO_JOY = True
            # print("no joysticks detected")
        else:
            self.NO_JOY = False
            #init storage - these are reused across multiple joysticks
            self.info_ex  = JOYINFOEX()
            self.info_ex.dwSize = ctypes.sizeof(JOYINFOEX)
            self.info_ex.dwFlags = JOY_RETURNBUTTONS | JOY_RETURNCENTERED | JOY_RETURNPOV | JOY_RETURNR | JOY_RETURNU | JOY_RETURNV | JOY_RETURNX | JOY_RETURNY | JOY_RETURNZ
            self.p_info_ex = ctypes.pointer(self.info_ex)


    def _get_jsname_from_reg(self,szRegKey,jsid):
        """Fetch the name from registry."""
        js_name = ''
        key = None
        if len(szRegKey) > 0:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "System\\CurrentControlSet\\Control\\MediaResources\\Joystick\\%s\\CurrentJoystickSettings" % (szRegKey))
            except WindowsError:
                key = None

        if key:
            oem_name = winreg.QueryValueEx(key, "Joystick%dOEMName" % (jsid + 1))
            if oem_name:
                key2 = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "System\\CurrentControlSet\\Control\\MediaProperties\\PrivateProperties\\Joystick\\OEM\\%s" % (oem_name[0]))
                if key2:
                    oem_name = winreg.QueryValueEx(key2, "OEMName")
                    js_name = oem_name[0]
                key2.Close()
        return js_name


    def get_count(self):
        """Return the number of joystick objects."""
        return len(self.stk)


    def get_first_jsobj(self):
        """Return the first joystick object if it exists."""
        return next(iter(self.stk.values())) if self.stk else None


    def get_jsobj_by_index(self,idx=0):
        return self.stk[list(self.stk)[idx]] if self.stk else None


    def read_joystick(self,jsid):
        """Read all joystick axes, buttons, and hats."""
        js = self.stk[jsid]
        flags = js.flags
        if joyGetPosEx(jsid, self.p_info_ex) == JOYERR_NOERROR:

            js.axes[0] = (self.info_ex.dwXpos-js.midval)/(js.midval+1.0)
            js.axes[1] = (self.info_ex.dwYpos-js.midval)/(js.midval+1.0)
            if flags['HASZ']: js.axes[2] = (self.info_ex.dwZpos-js.midval)/(js.midval+1.0)
            if flags['HASR']: js.axes[3] = (self.info_ex.dwRpos-js.midval)/(js.midval+1.0)
            if flags['HASU']: js.axes[4] = (self.info_ex.dwUpos-js.midval)/(js.midval+1.0)
            if flags['HASV']: js.axes[5] = (self.info_ex.dwVpos-js.midval)/(js.midval+1.0)

            js.btns = [(1 << i) & self.info_ex.dwButtons != 0 for i in range(js.n_btns)]

            if js.flags['HASPOV']:
                if js.flags['POVCTS']:
                    # continuous hat
                    js.hats[0] = (0,0)
                    raise NotImplementedError('Continuous hat not implemented')
                else:
                    # 4-way hat
                    js.hats[0] = self.hats_4way.get(self.info_ex.dwPOV,(0,0))
            js.fresh =  (js.fresh + 1) % 256
            js.ERROR=False
        else:
            # could not read joystick
            js.ERROR=True


    def process_joysticks(self,joystick_to_use=-1):
        """Perform joystick input processing."""
        # This will only take the first joystick found. If you plan to have multiple joysticks
        # connected, this will need modification.
        if self.get_count()==0:
            self.initialize() # look for a new joystick -  this can be slow
        else:
           for i in self.stk.keys():
               self.read_joystick(i)







#%%
if __name__ == '__main__':
    import time
    js_reader = JoystickReader()

    jsid=0
    mean_dt = 0
    i=0
    while True:
        i+=1
        t0=time.perf_counter()
        js_reader.process_joysticks()
        dt=time.perf_counter()-t0
        mean_dt=((i-1)*mean_dt + dt)/i
        if jsid in js_reader.stk:
            stk = js_reader.stk[jsid]
            ax = ','.join([f"{x:6.3f}" for x in stk.axes])
            if stk.ERROR:
                print("Cant read")
            else:
                print(f"{mean_dt*1e6:5.1f}us {dt*1e6:5.1f}us {stk.fresh:3d} Joystick {jsid}: axes:[{ax}] btns:{stk.btns} hats:{stk.hats}")
        else:
            print(f'{i} no joystick')
        time.sleep(.1)


