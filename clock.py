# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 15:50:00 2019

@author: geiger_br

Windows only. This will probably stop working correctly in Windows 11.

Clock.sleep() for pretty much everything
Clock.sleep_b() for high accuracy but more cpu

call Clock.shutdown() at the end of the run

There is an alternative in NTDLL.DLL that can set timer resolution to 0.5 ms.
This dll also exposes timers, but I think they are the same ones used already (i.e. CreateWaitableTimerA calls them).
    https://github.com/bgeiger99/wres
    http://undocumented.ntinternals.net/UserMode/Undocumented%20Functions/NT%20Objects/Timer/NtSetTimer.html
    https://www.geoffchappell.com/studies/windows/km/ntoskrnl/inc/ntos/ntosdef_x/ktimer.htm

"""


# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.0.1'



import time
import sys
import ctypes
kernel32 = ctypes.windll.kernel32
winmm = ctypes.WinDLL('winmm')



#%%============================================================================
class Clock:
    """
    improve efficiency and accuracy of real time ticker (compared to time.sleep alone)

    Clock(fps)

    Clock.sleep()                     # wait for next tick (efficient)  (this one's probably good enough)
    Clock.sleep_b()                   # wait for next tick (higher accuracy, higher cpu)
    Clock.sleep_win_kernel_periodic() # very simple use of an auto resetting timer, works fine
    Clock.sleep_win_kernel_adj()      # alternate method; needs work
    Clock.sleep_win_kernel_subt()     # alternate method; needs work
    Clock.sleep_ns() # !! dont use this one

    Call Clock.shutdown() at the end of the run.

    """
    WINTIMER_RES_MS = ctypes.c_uint(1)

    def __init__(self, fps=20, sl0_thresh = int(0.005*1e9)):
        self.frame_length = 1/fps
        self.frame_len_ns = int(self.frame_length*1e9)

        # nanosecond threshold to switch from sleep(.001) to sleep(0)
        # increase this above .005 to improve accuracy at the expense of CPU time
        self.sl0_thresh = int(sl0_thresh)

        # Initialize internal object variables for various timer types.
        self.reset()

        # Enable single millisecond resolution timer
        winmm.timeBeginPeriod(self.WINTIMER_RES_MS)

        # This sets the priority of the process to realtime--the same priority as the mouse pointer.
        # kernel32.SetThreadPriority(kernel32.GetCurrentThread(), 31)
        # This creates a timer. This only needs to be done once.
        self.ktimer = kernel32.CreateWaitableTimerA(ctypes.c_void_p(), True, ctypes.c_void_p())


        bManualReset = ctypes.c_bool(False)
        self.otimer = kernel32.CreateWaitableTimerA(ctypes.c_void_p(), bManualReset, ctypes.c_void_p())
        delay = ctypes.c_longlong(-(1)) # delay must be negative in 100 nanosecond intervals
        interval = ctypes.c_long(int(self.frame_length*1000))
        ret=kernel32.SetWaitableTimer(self.otimer,ctypes.byref(delay), interval, ctypes.c_void_p(), ctypes.c_void_p(), False)



    @property
    def tick(self):
        """Return the integer number of ticks of ``frame_length`` since the start."""
        return (time.perf_counter_ns() - self.start_ns) // self.frame_len_ns

    @property
    def subtick(self):
        """Return the integer number of nanoseconds remaining in this current tick."""
        return (time.perf_counter_ns() - self.start_ns) % self.frame_len_ns

    def sleep(self):
        """Sleep until the next tick."""
        r = self.tick + 1
        while self.tick < r:
            time.sleep(0.001)

    def sleep_ns(self):
        rt = self.tick+1
        r = self.subtick
        tt = r+1

        if rt-self.prevtick<2:
            while tt > r:
                tr = self.frame_len_ns-tt
                if tr < self.sl0_thresh:
                    time.sleep(0)
                else:
                    time.sleep(0.001)
                tt=self.subtick
        else:
            self.dropped += 1
            # outstr = f' missed {rt-self.prevtick-1} @ {rt}'
            outstr = f' D:{self.dropped}'
            #print(outstr)
            sys.stdout.write(outstr)

        self.mytick=self.tick
        self.prevtick=rt

    def sleep_b(self):
        r = self.tick+1

        if r-self.prevtick<2:
            ns_next_tick = r*self.frame_len_ns + self.start_ns
            tt = time.perf_counter_ns()
            c_sl10_thresh = ns_next_tick - self.sl0_thresh
            while tt < ns_next_tick:
                if tt > c_sl10_thresh:
                    time.sleep(0)
                else:
                    time.sleep(0.001)
                tt=time.perf_counter_ns()
        else:
            self.dropped += 1
            # outstr = f' missed {r-self.prevtick-1} @ {r}'
            # outstr = f' D:{self.dropped}'
#            print(outstr)
            # sys.stdout.write(outstr)

#        self.mytick=self.tick
        self.prevtick=r


    def sleep_win_kernel_adj(self):
        """ this uses a delay adjustment that seems to work better than just subticks """
        delay = ctypes.c_longlong((-(self.frame_len_ns-self.subtick) + self.dly_adj)//100) # delay must be negative in 100 nanosecond intervals
        ret=kernel32.SetWaitableTimer(self.ktimer, ctypes.byref(delay), 0, ctypes.c_void_p(), ctypes.c_void_p(), False)
        kernel32.WaitForSingleObject(self.ktimer, 0xffffffff)

        # this doesn't really work well
        n=200 # averaging filter for dly_adj
        m=self.prevtick
        self.prevtick=time.perf_counter_ns()
        self.dly_adj = int((self.dly_adj*(n-1) + min((self.prevtick-m)-self.frame_len_ns,0.1*self.frame_len_ns))/n)


    def sleep_win_kernel_subt(self):
        """ this uses subticks, works ok. """
        delay = ctypes.c_longlong(-(self.frame_len_ns-self.subtick)//100) # delay must be negative in 100 nanosecond intervals
        ret=kernel32.SetWaitableTimer(self.ktimer, ctypes.byref(delay), 0, ctypes.c_void_p(), ctypes.c_void_p(), False)
        kernel32.WaitForSingleObject(self.ktimer, 0xffffffff)


    def sleep_win_kernel_periodic(self):
        kernel32.WaitForSingleObject(self.otimer, 0xffffffff)


    def reset(self):
        """Reset the clock object to prepare for switching to a different timer type."""
        self.prevtick=0
        self.dly_adj=0
        self.mytick=0
        self.dropped=0
        self.start_ns = time.perf_counter_ns()
        self.err=[]


    def shutdown(self):
        """Perform shutdown tasks."""
        winmm.timeEndPeriod(self.WINTIMER_RES_MS)


    def test(self,method='sleep',duration=10,duty_loops=50000):
        """Run a test on the given method for sleep."""

        import math
        import numpy as np
        import psutil

        mean_dt=self.frame_length
        sx,sxx,n,sigma,duty_f = 0,0,0,0,0
        tau = 2  # time const, sec
        alpha = 1-self.frame_length/(tau+self.frame_length)
        dtvec=[]
        proc_vec=[]

        m_dict = {'sleep':self.sleep,
                  'sleep_ns': self.sleep_ns,
                  'sleep_b':self.sleep_b,
                  'sleep_win_kernel_subt':self.sleep_win_kernel_subt,
                  'sleep_win_kernel_adj':self.sleep_win_kernel_adj,
                  'sleep_win_kernel_periodic':self.sleep_win_kernel_periodic,}
        fh = m_dict[method]

        print('\n')
        print(fh)
        print(f"FPS;         timestep; mean_ts;  std_dev;   duty_cycle;   processor_load")

        steps=int(duration/self.frame_length)


        fh();  fh()  # Call the function handle twice to get the internal state correct
        t1=time.perf_counter()
        t0=t1-self.frame_length # properly init t0/t1
        t0a=t0
        try:
            for i in range(steps):
                t1=time.perf_counter()
                dt=(t1-t0)
                duty=(t0a-t0)
                t0=t1
                n=n+1
                sx=float(sx)+float(dt)
                sxx=float(sxx)+float(dt)*float(dt)
                mean_dt = mean_dt*alpha + dt*(1-alpha)
                duty_f = duty_f*alpha + (duty/dt)*(1-alpha)
                sigma = sigma + (n*dt-sx)**2/(n*(n+1))
                dtvec.append(dt)
                proc_vec.append(psutil.cpu_percent())
                sys.stdout.write(f"\r\r{1/mean_dt:8.4f} Hz; {dt:8.6f}; {mean_dt:8.6f}; {math.sqrt(sigma/(n+1)):8.6f}; {100*duty_f:8.1f}%  {proc_vec[-1]:8.1f}   {self.tick:5d} {self.subtick:7d}  {int(self.dly_adj):7d} ")
                sys.stdout.flush()

                xx=0
                for i in range(duty_loops):
                    xx+=1

                t0a=time.perf_counter()

                fh() # call the requested sleep function here

        except (KeyboardInterrupt):
            print('\nExited Timing loop.')

        dtvec = np.array(dtvec[2:]) # remove first two, its bad
        print(f"\n    mean: {np.mean(dtvec):8.3g}, std dev: {np.std(dtvec):8.5g}, max: {max(dtvec):8.5g}, min:{min(dtvec):8.5g}, processor_load:{np.mean(proc_vec):5.2f}  HZmean={np.mean(1/dtvec):6.3f} HZstd={np.std(1/dtvec):6.3f}")
        print('\n')
        return dtvec,proc_vec




#%% ===========================================================================
if __name__ == "__main__":
    c=Clock(100)
    try:
        z=c.test(); c.reset()
        z=c.test('sleep_ns'); c.reset()
        z=c.test('sleep_b'); c.reset()
        z=c.test('sleep_win_kernel_adj'); c.reset()
        z=c.test('sleep_win_kernel_subt'); c.reset()
        z=c.test('sleep_win_kernel_periodic'); c.reset()
    finally:
        c.shutdown()
