# -*- coding: utf-8 -*-
"""
Created on Thu Jan 28 10:50:58 2021

@author: geiger_br

helper class for shared memory with numpy arrays

Individual values in shared memory can be accessed in two different ways. Both are reasonably fast,
but the second is twice as fast as the first:

    1. If varnames are provided, individual elements can be read or modified using:
        val = shm['name']  or  val = shm.getvar('name')
        shm['name'] = val  or  shm.setvar('name', val)

    2. Directly writing to the numpy array using the desired index. This is about twice as fast
    as using the variable name:
        val = shm.arr[0]
        shm.arr[0] = val

This approach is ~10x faster than using a ShareableList, but it only allows a single data
type per shared memory area.

"""

# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.1.0'



import numpy as np
from multiprocessing import shared_memory

class SharedMemNumpyArr():
    def __init__(self,name,num,dtype,reset_shm=False,varnames=None):
        """Create or connect to a shared memory array via numpy buffer.

        This approach is ~10x faster than using a ShareableList, but it only allows a single data
        type per shared memory area.

        Params
        ------
        name : str
            Name of the shared memory array to create or connect to.
        num : int
            Length of the shared memory array.
        dtype : str or Numpy dtype object
            Datatype of the shared memory array. Any NumPy datatype is valid.
        reset_shm : bool
            Reset the shared memory area by unlinking it before creating it.
        varnames : list of str, Optional
            A list of names for each shared memory array element. This is used to provide dict-style
            access to individual elements. The default is None. The length of this list must be
            equal to num.

        Returns
        -------
        SharedMemNumpyArr object that is used to access individual list elements. See examples for
        usage.

        Example 1: Unnamed array
        ------------------------
            shm = SharedMemNumpyArr(name='example_shm_id', num=10, dtype='float64')
            shm[0] = 1.125
            shm.setvar(2,37.31)
            shm[9] = 18.7124
            print(shm.arr)
            print(shm.getvar(2))
            print(shm.keys())
            # do other things
            shm.unlink()  # when finished

        Example 2: Named Array
        ----------------------
            shm = SharedMemNumpyArr(name='example_named_shm_id', num=5, dtype='float64', varnames=['ab1','ab2','alt','mzl','dop'])

            shm['ab1'] = 1.125
            print(f"(shm['ab1']) {shm['ab1']} == {shm.arr[0]}  (shm.arr[0])")
            print(shm.keys())
            # do other things
            shm.unlink()  # when finished


        Notes
        -----

        When finished, close() should be called on all instances and unlink() should be called on the
        primary instance.

        if reset_shm, init will unlink any existing memory before creating new memory

        Note: This could be modified to include multiple data types by using slices of the shared
        memory buffer, example:
            a1 = np.array([1.0,2.0,3.0])
            a2 = np.array([4,5,6])
            shm = shared_memory.SharedMemory(name='aaaaaaaa',create=True,size=a1.nbytes + a2.nbytes)
            bf = np.ndarray(shape=a1.shape, dtype=a1.dtype, buffer=shm.buf[:a1.nbytes])   # <---- see here
            bi = np.ndarray(shape=a2.shape, dtype=a2.dtype, buffer=shm.buf[a1.nbytes:])   # <---- see here
        """

        self.name = name
        self.num = num
        self.shape = (self.num,)
        if isinstance(dtype,type):
            self.dtype = np.dtype(dtype).name
        self.dtype = dtype
        self.nbytes = self.num*np.dtype(dtype).itemsize

        if varnames is None:
            varnames = list(range(num))
        else:
            if len(varnames) != self.num:
                raise ValueError(f"Number of variable names ({len(varnames)}) do not match num given in init call ({num}).")
            if len(varnames) != len(set(varnames)):
                raise ValueError(f"Found repeated variable names: {[varnames.pop(varnames.index(k)) for k in set(varnames)]}")
        self.varnames = {var:i for var,i in zip(varnames,range(num))}

        # create the shared memory
        try:
            self.shm = shared_memory.SharedMemory(name=self.name,create=True,size=self.nbytes)
            self.shm.buf[:] = bytearray(self.nbytes) # init to zeros if we are creating
        except FileExistsError:
            if reset_shm:
                print(f'    shm reset: {self.name}')
                tmp = shared_memory.SharedMemory(name=self.name)
                tmp.unlink()
            self.shm = shared_memory.SharedMemory(name=self.name,create=False,size=self.nbytes)

        # connect shared memory buffer to a numpy ndarray obj
        self.arr = np.ndarray(shape=self.shape, dtype=self.dtype, buffer=self.shm.buf)

    def __getitem__(self,key):
        return self.arr[self.varnames[key]]

    def __setitem__(self,key,val):
        self.arr[self.varnames[key]] = val

    def keys(self):
        return self.varnames.keys()

    def getvar(self,varname):
        idx = self.varnames[varname]
        return self.arr[idx]

    def setvar(self,varname,value):
        idx = self.varnames[varname]
        self.arr[idx] = value

    def close(self):
        self.shm.close()
        self.arr = []

    def unlink(self):
        self.shm.unlink()
        self.arr = []


#%% ===== Examples =================================================================================

if __name__ == "__main__":

    # Example 1: unnammed array
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': None, # optional names for each variable
               }

    shm = SharedMemNumpyArr(**shm_cfg)
    shm[0] = 1.125
    shm.setvar(2,37.31)
    shm[9] = 18.7124
    print(shm.arr)
    print(shm.getvar(2))
    print(shm.keys())
    # %timeit shm[1]
    # %timeit shm.getvar(1)
    # %timeit shm[1] = 8124.11
    # %timeit shm.setvar(1,8124.11)
    # %timeit shm.arr[1]  # indexing the array directly is a little faster
    # %timeit shm.arr[1]=8124.11  # indexing the array directly is a little faster
    shm.close()
    shm.unlink()


    # Example 2: Named variables
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': ['ab1','ab2','alt','mzl','dop','los','psi','uw','orange','bolt',], # optional names for each variable
               }

    shm = SharedMemNumpyArr(**shm_cfg)
    shm['ab1'] = 1.125
    print(f"(shm['ab1']) {shm['ab1']} == {shm.arr[0]}  (shm.arr[0])")
    print(shm.keys())
    # %timeit shm['ab1']
    shm.close()
    shm.unlink()


