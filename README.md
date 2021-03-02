# LeCrunch3
A python3 tool to control a LeCroy scope and to acquire/process data

LeCrunch3 is based on LeCrunch2 by Benjamin Land: https://github.com/BenLand100/LeCrunch2
LeCrunch2 is based on LeCrunch by Anthony LaTorre <tlatorre9@gmail.com>

LeCrunch3 is a proting for python3 and adds some funcitionalities, like the possibility of saving easy to use h5 files:


import matplotlib.pyplot as plt
import h5py

f = h5py.File('testfile.h5', 'r')
fig, axes = plt.subplots(2,2, figsize=(50,20))
axes = axes.flatten()
for ch in range(1,5):
    numOfSegments = f[f'c{ch}_time'].shape[0]
    for i in range(numOfSegments):
        numOfSamples = f[f'c{ch}_time'][i].shape[0]
        v = f[f'c{ch}_samples'][i]
        t = f[f'c{ch}_time'][i]
        
        axes[ch-1].plot(t*1e9,v)
        axes[ch-1].set_title(f"Channel {ch}")
