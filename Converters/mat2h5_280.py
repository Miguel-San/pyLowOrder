#!/usr/bin/env python
#
# Conversor of MAT file to HDF5 file.
#
# Last revision: 03/08/2021
from __future__ import print_function, division

import numpy as np
from scipy.io import loadmat
import h5py

import pyLOM


## Parameters
MATFILE = 'Examples/Data/Tensor_re280.mat'
OUTFILE = 'Examples/Data/Tensor_re280.h5'


## Load MAT file
f   = h5py.File(MATFILE,'r')
mat = { k:np.array(v) for k,v in f.items() }
f.close()
DT  = 1

tensor = mat['Tensor']
tensor = np.transpose(tensor, (4, 3, 2, 1, 0))
[UVW, Nx, Ny, Nz, Nt] = tensor.shape
n_UVW    = np.arange(0, UVW)
x_slides = np.arange(0, Nx)
y_slides = np.arange(0, Ny)
z_slides = np.arange(0, Nz)
n_t      = np.arange(280, 400)
T_small = tensor[:, :, :, :, 280:400]
T_reshaped = np.reshape(T_small, (UVW*Nx*Ny*Nz,n_t.size), order = 'F')

## Build mesh information dictionary
mesh = {'type':'struct3D','nx':Nx,'ny':Ny, 'nz':Nz}

# Build node positions
x = np.linspace(0, 10, Nx)
y = np.linspace(-2, 2, Ny)
z = np.linspace(0, 1.67, Nz)
xx, yy, zz = np.meshgrid(x, y, z)
xyz = np.zeros((mesh['nx']*mesh['ny']*mesh['nz'],3),dtype=np.double)
xyz[:,0] = xx.reshape((mesh['nx']*mesh['ny']*mesh['nz'],), order = 'C')
xyz[:,1] = yy.reshape((mesh['nx']*mesh['ny']*mesh['nz'],), order = 'C')
xyz[:,2] = zz.reshape((mesh['nx']*mesh['ny']*mesh['nz'],), order = 'C')

# Build time instants
time = DT*np.arange(T_reshaped.shape[1]) + DT


## Create dataset for pyLOM
d = pyLOM.Dataset(mesh=mesh, xyz=xyz, time=time,
	# Now add all the arrays to be stored in the dataset
	# It is important to convert them as C contiguous arrays
	T_reshaped = np.ascontiguousarray(T_reshaped.astype(np.double)),
)
print(d)

# Store dataset
d.save(OUTFILE)

pyLOM.cr_info()
