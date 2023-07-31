# -*- coding: utf-8 -*-
"""
Created on Fri Aug 27 07:58:01 2021

@author: geiger_br

Given a list or dict of names, return an object containing self updating values varying with time:

    # just use default options in TimeHistData class
    d = TimeHistDataset(['a','b','c'])
    d.demo()

    # customize each variable name
    varnames = {'a': {'period':2,'amp':5,'bias':5},
                'b':{},
                'c':{'period':.1,'waveform':'triangle'}}
    d = TimeHistDataset(varnames)
    print(d.a.v)
    time.sleep(1)
    print(d.a.v)
    d.demo()

    See utils repository.

"""

__version___ = '1.0'


import math
import time

class TimeHistData:
    """Implement a self-updating variable that changes with time.

    Parameters
    ----------
    period : float
        time period of oscillation in seconds (1/frequency)
    amp : float
        amplitude of signal variation
    phase : float
        phase angle offset of sinusoidal signal variation (only for sinusoid) in radians
    t0 : float
        time offset of signal variation in seconds
    bias : float
        bias value of signal variation
    waveform : {'sin', 'triangle'}, optional
        shape of signal variation, choices in brackets, default is 'sin'
    minmax : tuple or list of float, len=2, optional
        Default is None. If minmax is given, amp and bias are overridded by
        amp,bias = 0.5*(minmax[1]-minmax[0]), 0.5*(minmax[1]+minmax[0])

    The current value is given by calling val() or v.

    """

    def __init__(self, period=1.0, amp=1.0, phase=0, t0=0.0, bias=0.0, waveform='sin',minmax=None):
        if minmax:
            amp,bias = 0.5*(minmax[1]-minmax[0]), 0.5*(minmax[1]+minmax[0])
        self.dt,self.amp,self.phase,self.t0,self.bias,self.waveform = period,amp,phase,t0,bias,waveform
        self.freq = 1/self.dt

    def _t(self):
        """Return a monotonic time value in seconds."""
        return time.monotonic()

    def __get__(self):
        """Return the current value of the time history object."""
        return self.v

    def _val(self,t=None):
        """Output the current value or value at time t of the time history object."""
        t = self._t() if t==None else t
        if self.waveform == 'triangle':
            return 4*self.amp/self.dt * abs(((t-self.t0-self.dt/4) % self.dt) - self.dt/2) - self.amp + self.bias
        elif self.waveform == 'sin':
            return self.amp*math.sin(2*math.pi*self.freq*(t-self.t0) + self.phase) + self.bias
        else:
            raise NotImplementedError

    @property
    def v(self):
        """Return the current value of the time history object."""
        return self._val()


class TimeHistDataset:
    """Given a list or dict of varnames, create a self updating time history data set.

    If varnames is a dict, each key can include a set of options describing the
    time history behavior. Example:

    just use default options in TimeHistData class
    d = TimeHistDataset(['a','b','c'])
    d.demo()

    # customize each variable name
    varnames = {'a': {'period':2,'amp':5,'bias':5},
                'b':{},
                'c':{'period':.1,'waveform':'triangle'}}
    d = TimeHistDataset(varnames)
    d.demo()

    print(d.a.v,  d.b.v,  d.c.v)

    """

    def __init__(self, varnames ):

        if isinstance(varnames,(list,tuple,set)):
            varnames = dict.fromkeys(varnames,{})

        self._varnames = list(varnames)
        self._th_objs = {}

        for k,v in varnames.items():
            self._th_objs[k] = TimeHistData(**v)
            setattr(self, k, self._th_objs[k])  # this enables d.a.v to return an updated value
            # I want to be able to say d.a to return an updated value, but I can't figure it out
            # setattr(self,'get'+k,property(lambda xx: xx._th_objs[k].val()))
            # bb=property(getattr(self,'get'+k))
            # setattr(self, k, self._th_objs[k].val() )
        # a = property(self.a)
    # @property
    # def getaa(self):
        # return self._th_objs['a'].v
    # aa=property(geta)

    def get_all(self):
        """Get a dict of the current value of all time history objects in the set."""
        t=time.monotonic()
        return {k:getattr(self,k).val(t) for k in self._varnames}

    def demo(self,n=100,dt_sec=0.02):
        """Print a demo time history of all time history objects in the set."""
        for i in range(n):
            print(',  '.join([f"{k}={getattr(self,k).v:8.3f}" for k in self._varnames]))
            time.sleep(dt_sec)


#%% ===============================================================================================
if __name__=="__main__":

    # Use all defaults
    d = TimeHistDataset(['a','b','c'])
    d.demo()

    # Specify some specifics
    varnames = {'a': {'period':2,'amp':5,'bias':5},
                'b':{},
                'c':{'period':.1,'waveform':'triangle'}}
    d = TimeHistDataset(varnames)
    d.demo()
    print(f"d.a.v={d.a.v}")
    time.sleep(.5)
    print(f"d.a.v={d.a.v}")
    time.sleep(.5)
    print(f"d.a.v={d.a.v}")
