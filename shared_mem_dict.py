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

This approach is between ~15x and ~55x faster than using shared_memory.ShareableList (python 3.11),
but it only allows a single data type per shared memory area.

"""

# The master version of this code is tracked in a separate repository - the
# latest version is available at:
#    http://gitlab/gitlab/reference/lib_pytools
#    -- or --
#    https://github.com/bgeiger99/lib_pytools
__version__ = '1.5.0'

"""
Changelog
=========

1.5.0 (2023-12-18)
------------------

- add configuration check including names, number, dtype, and version

1.4.1 (2023-07-31)
------------------

- Fixed duplicate name definition check

1.4.0 (2023-05-29)
------------------

- Update type checking for varnames input

1.3.0 (2023-02-02)
------------------

- Documentation update. Add items() method.
- adding uint16, int16, uint8, and int8 types


1.2.0 (2022-08-15)
------------------

I'm removing the use of numpy buffers in exchange for slicing and casting memoryviews.
This removes the numpy dependency and runs a little faster too. Shared memory sections are still
limited to a single data type, but this could be remedied by subslicing the memoryview and casting
as appropriate. The documentation of memoryview.format seems to suggest that disparate data types
could be intermingled, but that might require a memoryview per element. I originally considered
ctypes approach, but this worked out much more easily.



Development Notes
==================

2023-12-13: This is probably a better approach to shared memory with mixed types:
    https://docs.python.org/3/library/multiprocessing.html#module-multiprocessing.sharedctypes

How to mix datatypes with memoryview:
    import  struct
    import itertools

    mem_fmt = ['ii','dddd','iii']

    idxs = [None] + list(itertools.accumulate([struct.calcsize(f) for f in mem_fmt]))
    slices = [slice(idxs[i],idxs[i+1]) for i in range(len(idxs)-1)]
    sz = struct.calcsize(''.join(mem_fmt))
    buf = bytearray(sz)
    M = memoryview(buf)

    ints1 = M[slices[0]].cast('i')
    dbls  = M[slices[1]].cast('d')
    ints2 = M[slices[2]].cast('i')



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


import json
import hashlib
import struct
from multiprocessing import shared_memory

dtypes = {'float64':'d',
          'double':'d',
          'float':'f',
          'float32':'f',
          'int64':'q',
          'uint64':'Q',
          'int32':'l',  # 'l' or 'i' are equivalent
          'uint32':'L', # 'L' or 'I' are equivalent
          'int16':'h',
          'uint16':'H',
          'int8':'b',
          'uint8':'B',
          'bool':'?',  # '?' is the correct format char
          }

class SharedMemoryConfigurationError(Exception):
    pass

class SharedMemDict():
    def __init__(self,name,num,dtype,reset_shm=False,varnames=[],check_config=True,verbose=False):
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
        check_config : bool, Optional
            If True, calculate the sha256 hash of the configuration and compare
            it to the hash stored in a separate block of the shared memory
            area. If the hashes differ, raise the SharedMemoryConfigurationError.
            The default is True (always check). This should only be disabled if
            debugging is required.
        verbose : bool, Optional
            If True, print additional information during object creation. The 
            default is False.

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
        self.fmt = dtypes.get(dtype,None)
        
        if self.fmt is None:
            raise SharedMemoryConfigurationError(f"Invalid data type specified: '{dtype}'. You must use one of the following:\n {dtypes}")

        # Serialize the configuration
        my_cfg = {'name':name,'num':num,'dtype':dtype,'varnames':varnames,'version':__version__}
        my_cfg_json = json.dumps(my_cfg).encode('utf-8')
        my_cfg_sha256 = hashlib.sha256(my_cfg_json).digest()
        self.my_cfg_sha256 = my_cfg_sha256
        
        if verbose:
            print(my_cfg)

        # Calculate bytes required
        self.nbytes_data = struct.calcsize(self.fmt) * self.num
        self.nbytes_cfghash = len(my_cfg_sha256)
        self.nbytes = self.nbytes_data + self.nbytes_cfghash

        # If no variable names were supplied, make the default variable names
        # consisting of a list of int starting at 0.
        try:
            if varnames is None or len(varnames)==0:
                varnames = list(range(num))
        except TypeError as e:
            estr = f"'varnames' must be an iterable type (list, tuple) of length 0 or {num} ('num' argument)."
            raise SharedMemoryConfigurationError(estr).with_traceback(e.__traceback__)
            
        # Check for mismatch between length of varirable names and expected number of names
        if len(varnames) != self.num:
            raise SharedMemoryConfigurationError(f"Number of variable names (len(varnames)={len(varnames)}) do not match expected number (num={num}).")

        # Check for duplicate names
        if len(varnames) != len(set(varnames)):
            [varnames.pop(varnames.index(k)) for k in set(varnames)] # pop all names once; leftovers are the duplicates
            raise SharedMemoryConfigurationError(f"Found repeated variable names: {set(varnames)}")

        # Create the variable reference dict (name:index)
        self.varnames = {var:i for var,i in zip(varnames,range(num))}

        # Create the shared memory
        try:
            self.shm = shared_memory.SharedMemory(name=self.name,create=True,size=self.nbytes)
            self.shm.buf[:] = bytearray(self.nbytes) # init to zeros if we are creating
        except FileExistsError:
            if reset_shm:
                if verbose:
                    print(f'    shm reset: {self.name}')
                tmp = shared_memory.SharedMemory(name=self.name)
                tmp.unlink() # Calling unlink here causes all those "cannot close" errors
            self.shm = shared_memory.SharedMemory(name=self.name,create=False,size=self.nbytes)

        # Set up a memoryview cast to the correct data type
        self.arr = self.shm.buf[:self.nbytes_data].cast(self.fmt)
        self._cfg = self.shm.buf[self.nbytes_data:(self.nbytes_data+self.nbytes_cfghash)].cast('B')

        # Check for a matching configuration hash
        if check_config:
            all_zero = all([b==0 for b in self._cfg])
            cfg_match = all([self._cfg[i]==my_cfg_sha256[i] for i in range(self.nbytes_cfghash)])
            if all_zero:
                if verbose:
                    print(f"Config check area was all zeros. Writing my_cfg_sha256: {my_cfg_sha256.hex()}")
                self._cfg[:self.nbytes_cfghash] = my_cfg_sha256
            elif cfg_match:
                if verbose:
                    print("Config hash matched to existing hash: {my_cfg_sha256.hex()}")
            else:
                estr = f"    Shared Memory configuration does not match source configuration. " \
                        "Check that the configuration used by this instance is identical " \
                        "in variable name, case, and order. The configuration " \
                       f"used by this instance is:\n\n{my_cfg}\n\n" \
                       f"    This instance's config sha256 hash is: {my_cfg_sha256.hex()}\n" \
                       f"    The existing config sha256 hash is:    {self._cfg.hex()}" 
                self.close()
                raise SharedMemoryConfigurationError(estr)

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

    def __getitem__(self, key):
        return self.arr[ self.varnames[key] ]

    def __setitem__(self, key, value):
        self.arr[ self.varnames[key] ] = value

    def __len__(self):
        return self.num

    def __iter__(self):
        # return iter(self.)
        raise NotImplementedError

    def keys(self):
        return self.varnames.keys()

    def values(self):
        return list(self.arr[:self.num])
        # return [self.arr[i] for i in range(self.num)]  # NOTE: arr be longer than num

    def items(self):
        for key in self.keys():
            yield ( key, self.arr[self.varnames[key]])

    def getvar(self,key):
        return self.arr[ self.varnames[key] ]

    def setvar(self,key,value):
        # self[key] = value  # this is slow
        self.arr[ self.varnames[key] ] = value

    def close(self):
        # To prevent a memoryview error message (cannot close exported pointers exist), arr is
        # dereferenced from the shm.buf before close or unlink
        self.arr.release()
        self._cfg.release()
        self.shm.close()

    def unlink(self):
        self.close()
        self.shm.unlink()

#%% 
def _demo_process(cfg):
    import time
    """Demo: Increment the 7th item in a shared list. This is defined here to 
    avoid an error when running the example in iPython."""
    
    # Connect to the pre-defined shared instance
    shm = SharedMemDict(**cfg)
    n=400
    # print(shm.my_cfg_sha256)
    # Increment 
    for i in range(n):
        shm[7] = float(i)
        # print(f"{shm[7]}")
        time.sleep(0.01)
    shm.close()


#%% ===== Examples =================================================================================

if __name__ == "__main__":

    from multiprocessing import Process
    import time

    # Example 1: unnammed array
    print("\n\n===========================================")
    print("Example 1: unnammed array")
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': [], # optional names for each variable - if empty, indices count up from 0
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
    print(f" List all keys:   shm.keys(): {shm.keys()}")
    print(f" Get all values:  shm.values(): {shm.values()}")
    print(f"    getvar() : {[shm.getvar(i) for i in range(shm.num)]}")
    print(f" __getitem__ : {[shm[i] for i in range(shm.num)]}")
    print(f" array index : {[shm.arr[i] for i in range(shm.num)]}")
    # print(shm.my_cfg_sha256)

    print("\n    Spawning demo_process() in a new process to write values to shared memory...")
    p = Process(target=_demo_process,args=(shm_cfg,))
    p.start()
    time.sleep(1.0)
    print("    Reading values from shared memory:")
    for i in range(10):
        print(f"        Shared from demo_process: shm[7] = {shm[7]}")
        time.sleep(0.25)
    p.join()
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
    print("\n\n===========================================")
    print("Example 2: Named Variables")
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


    # Example 3 - config mismatch
    print("\n\n===========================================")
    print("Example 3: Configuration Error Test")
    shm_cfg = {'name': 'shm_area_test1_8u235',  # shared memory location identifier - can be anything you want
               'num':  10,  # number of variables in the shared memory array
               'dtype': 'float64',  # datatype of the shared memory array
               'varnames': ['ab1','ab2','alt','mzl','dop','los','psi','uw','orange','bolt',], # optional names for each variable
               }

    shm1 = SharedMemDict(**shm_cfg,verbose=True)
    shm_cfg['varnames'][0]='abb1' # introduce a name change
    try:
        shm2 = SharedMemDict(**shm_cfg) # This will cause a config error
    except SharedMemoryConfigurationError as e:
        print(f"Caught SharedMemoryConfigurationError error:\n\n {e}")
    shm1.close()
    shm1.unlink()

