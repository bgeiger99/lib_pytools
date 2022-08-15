# -*- coding: utf-8 -*-
"""
Created on Thu Jan 28 10:50:58 2021

@author: geiger_br

Class for communicating with other processes using shared memory.

Individual values in shared memory can be accessed in two different ways. Both are reasonably fast,
but the second is twice as fast as the first:

    1. If varnames are provided, individual elements can be read or modified using:
        val = shm['name']  or  val = shm.getvar('name')
        shm['name'] = val  or  shm.setvar('name', val)

    2. Directly writing to the numpy array using the desired index. This is about twice as fast
    as using the variable name:
        val = shm.arr[0]
        shm.arr[0] = val

This approach is between ~15x and ~55x faster than using shared_memory.ShareableList, but it only
allows a single data type per shared memory area.

"""

# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.2.0'

"""
Changelog
=========

1.2.0 (2022-08-15)
------------------

I'm removing the use of numpy buffers in exchange for slicing and casting memoryviews.
This removes the numpy dependency and runs a little faster too. Shared memory sections are still
limited to a single data type, but this could be remedied by subslicing the memoryview and casting
as appropriate. The documentation of memoryview.format seems to suggest that disparate data types
could be intermingled, but that might require a memoryview per element. I originally considered
ctypes approach, but this worked out much more easily.


"""




""" DEVELOPMENT Notes:
I think I can remove the numpy import if I use ctypes and connect it to the shm.buf memoryview. I
don't know enough currently to make this work but it seems possible.

https://stackoverflow.com/questions/9940859/fastest-way-to-pack-a-list-of-floats-into-bytes-in-python     **START HERE, read comments by Jonathan Hartley

then:   https://stackoverflow.com/questions/59574816/obtaining-a-memoryview-object-from-a-ctypes-c-void-p-object

https://docs.python.org/3/c-api/memoryview.html
https://stackoverflow.com/questions/28984692/ctypes-from-buffer-with-memoryviews-in-python-2-7-and-python-3-4
https://mattgwwalker.wordpress.com/2020/10/15/address-of-a-buffer-in-python/
https://stackoverflow.com/questions/43810423/what-is-the-most-efficient-way-to-copy-an-externally-provided-buffer-to-bytes

"""

# import ctypes
# import numpy as np

import struct
from multiprocessing import shared_memory

dtypes = {'float64':'d',
          'float32':'f',
          'int64':'q',
          'int32':'l',  # 'l' or 'i' are equivalent
          'bool':'?',  # '?' is the correct format char
          }


class SharedMemDict():
    def __init__(self,name,num,dtype,reset_shm=False,varnames=None):
        """Create or connect to a shared memory dict. Values in the dict can be accessed by name or
        by numerical index; the values are all a single data type.

        This approach is ~20x faster than using a ShareableList, but it only allows a single data
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
        SharedMemDict object that is used to access individual list elements. See examples for
        usage.

        Example 1: Unnamed array
        ------------------------
            shm = SharedMemDict(name='example_shm_id', num=10, dtype='float64')
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
            shm = SharedMemDict(name='example_named_shm_id', num=5, dtype='float64', varnames=['ab1','ab2','alt','mzl','dop'])

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

        Note: This could be modified to include multiple data types by using slices of the
        memoryview of the shared buffer. For example:
            nbf = struct.calcsize('3f')  # three floats
            nbi = struct.calcsize('3i')  # three ints
            nbytes =  nbf + nbi
            shm = shared_memory.SharedMemory(name='aaaaaaaa',create=True,size=nbytes)
            bf = shm.buf[:nbf].cast('f')
            bi = shm.buf[nbf:nbi].cast('i')
        """

        self.name = name
        self.num = num
        self.shape = (self.num,)
        self.dtype = dtype
        self.fmt = dtypes[dtype]
        self.nbytes = struct.calcsize(self.fmt) * self.num

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

        # Set up a memoryview cast to the correct data type
        self.arr = self.shm.buf.cast(self.fmt)

        # # connect shared memory buffer to a numpy ndarray obj
        # if no_numpy:
        #     self.arr = self.shm.buf.cast('d')
        # else:
        #     self.arr = np.ndarray(shape=self.shape, dtype=self.dtype, buffer=self.shm.buf)

# TODO: is this an alternate to memoryview slicing?
        # if self.dtype == 'float64':
        #     print(type(self.shm._buf))
        #     print(type(self.shm.buf.tobytes()))
        #     self.arr_c = ctypes.cast(self.shm.buf.tobytes(),ctypes.POINTER(ctypes.c_double*self.num))

    def __getitem__(self,key):
        return self.arr[ self.varnames[key] ]

    def __setitem__(self,key,value):
        self.arr[ self.varnames[key] ] = value

    def __len__(self):
        return self.num

    def keys(self):
        return self.varnames.keys()

    def values(self):
        return self.arr.tolist()[:self.num]

    def getvar(self,varname):
        return self.arr[ self.varnames[varname] ]

    def setvar(self,varname,value):
        self[varname] = value

    def close(self):
        # To prevent a memoryview error message (cannot close exported pointers exist), arr is
        # dereferenced from the shm.buf before close or unlink
        self.arr.release()
        self.shm.close()


    def unlink(self):
        self.close()
        self.shm.unlink()


#%% ===== Examples =================================================================================

if __name__ == "__main__":

    # Example 1: unnammed array
    print("\n\nExample 1: unnammed array")
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': None, # optional names for each variable
               }

    shm = SharedMemDict(**shm_cfg)
    print("    Set array items by index number.")
    shm[0] = 1.125
    shm.setvar(1,37.31)
    shm.arr[2] = 37.37
    shm[9] = 18.7124
    print( " Access values using three methods:")
    print(f"    Dict key:    shm[0]        -> {shm[0]}")
    print(f"    Array Index: shm.arr[0]    -> {shm.arr[0]}")
    print(f"    getvar():    shm.getvar(0) -> {shm.getvar(0)} (equivalent to dict key)")
    print(f" Get all values:  shm.values(): {shm.values()}")
    print(f" List all keys:   shm.keys(): {shm.keys()}")
    # %timeit shm[1]
    # %timeit shm.arr[1]  # indexing the array directly is 2-3x faster than using the dict key
    # %timeit shm.getvar(1)
    # %timeit shm[1] = 8124.11
    # %timeit shm.arr[1]=8124.11  # indexing the array directly is 2-3x faster than using the dict key
    # %timeit shm.setvar(1,8124.11)
    shm.close()
    shm.unlink()

    # Compare to ShareableList
    shm_list = shared_memory.ShareableList(10*[1.001])
    # %timeit shm_list[1]
    # %timeit shm_list[1]=8124.11


    # Example 2: Named variables
    print("\n\nExample 2: Named Variables")
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': ['ab1','ab2','alt','mzl','dop','los','psi','uw','orange','bolt',], # optional names for each variable
               }

    shm = SharedMemDict(**shm_cfg)
    shm['ab1'] = 1.125
    print( " Access values using three methods:")
    print(f"    Dict key:    shm['ab1']        -> {shm['ab1']}")
    print(f"    Array Index: shm.arr[0]        -> {shm.arr[0]}")
    print(f"    getvar():    shm.getvar('ab1') -> {shm.getvar('ab1')} (equivalent to dict key)")
    print(f" Get all values:  shm.values(): {shm.values()}")
    print(f" List all keys:   shm.keys(): {shm.keys()}")
    # %timeit shm['ab1']
    # %timeit shm.arr[0]
    shm.close()
    shm.unlink()

