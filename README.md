# LeCrunch3
A python3 tool to control a LeCroy scope and to acquire/process data

LeCrunch3 is based on LeCrunch2 by Benjamin Land: https://github.com/BenLand100/LeCrunch2
LeCrunch2 is based on LeCrunch by Anthony LaTorre <tlatorre9@gmail.com>

LeCrunch3 is a proting for python3 and adds some funcitionalities, like the possibility of saving easy to use h5 files:


    import matplotlib.pyplot as plt

    import h5py

    f = h5py.File('testfile.h5', 'r')

    numOfSegments = f[f'c1_time'].shape[0]

    for i in range(numOfSegments):

        plt.plot(f[f'c1_time'][i], f[f'c1_samples'][i])
    
And more importantly, the acquisition of trigger times and offset
