#!/usr/bin/env python3
# LeCrunch3
# Copyright (C) 2021 Nicola Minafra
#
# based on
#
# LeCrunch2
# Copyright (C) 2014 Benjamin Land
#
# based on
#
# LeCrunch
# Copyright (C) 2010 Anthony LaTorre 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import string
import struct
import socket
import h5py
import json
import numpy as np
from LeCrunch3 import LeCrunch3

import logging
logging.basicConfig(filename='scanlog.log', level=logging.DEBUG)

import motion

def measure(f, nevents, nsequence, ip, timeout=10000):
    '''
    Fetch and save waveform traces from the oscilloscope.
    '''
    scope = LeCrunch3(ip, timeout=timeout)
    scope.clear()
    scope.set_sequence_mode(nsequence)
    channels = scope.get_channels()
    settings = scope.get_settings()

    minimum = {}
    maximum = {}
    rate = {}

    if b'ON' in settings['SEQUENCE']:
        sequence_count = int(settings['SEQUENCE'].split(b',')[1])
    else:
        sequence_count = 1
        
    if nsequence != sequence_count:
        logging.error('Could not configure sequence mode properly')
    if sequence_count != 1:
        logging.info(f'Using sequence mode with {sequence_count} traces per aquisition')
    
    for command, setting in settings.items():
        f.attrs[command] = setting               
    current_dim = {}
    
    for channel in channels:
        wave_desc = scope.get_wavedesc(channel)
        current_dim[channel] = wave_desc['wave_array_count']//sequence_count
        f.create_dataset(f'c{channel}_samples', (nevents,current_dim[channel]), dtype=wave_desc['dtype'], maxshape=(nevents,None))
        ## Save attributes in the file
        for key, value in wave_desc.items():
            try:
                f["c%i_samples"%channel].attrs[key] = value
            except ValueError:
                pass
        f.create_dataset("c%i_vert_offset"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_vert_scale"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_horiz_offset"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_horiz_scale"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_trig_offset"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_trig_time"%channel, (nevents,), dtype='f8')

        # Add here all measurements you want...
        minimum[channel] = []
        maximum[channel] = []
        rate[channel] = []

    try:
        i = 0
        while i < nevents:
            print(f'\rStarting acquisition of {i} triggers')
            logging.info(f'\rStarting acquisition of {i} triggers')
            sys.stdout.flush()
            try:
                scope.trigger()
                for channel in channels:
                    wave_desc, trg_times, trg_offsets, wave_array = scope.get_waveform_all(channel)
                    num_samples = wave_desc['wave_array_count']//sequence_count
                    filt_trg_times = []

                    if current_dim[channel] < num_samples:
                        current_dim[channel] = num_samples
                    traces = wave_array.reshape(sequence_count, wave_array.size//sequence_count)
                    # necessary because h5py does not like indexing and this is the fastest (and man is it slow) way
                    scratch = np.zeros((current_dim[channel],),dtype=wave_array.dtype)
                    for n in range(0,sequence_count):
                        scratch[0:num_samples] = traces[n]
                        f[f'c{channel}_samples'][i+n] = scratch
                        f['c%i_vert_offset'%channel][i+n] = wave_desc['vertical_offset']
                        f['c%i_vert_scale'%channel][i+n] = wave_desc['vertical_gain']
                        f['c%i_horiz_offset'%channel][i+n] = wave_desc['horiz_offset']
                        f['c%i_horiz_scale'%channel][i+n] = wave_desc['horiz_interval']
                        f['c%i_trig_offset'%channel][i+n] = trg_offsets[n]
                        f['c%i_trig_time'%channel][i+n] = trg_times[n]

                        # Add here all measurements you want...
                        samples = -wave_desc['vertical_offset'] + scratch*wave_desc['vertical_gain']
                        if np.abs(np.max(samples) - np.min(samples)) > 12*np.std(samples[:100]):
                            filt_trg_times.append(trg_times[n])
                    rate[channel].append( np.mean(np.diff(filt_trg_times)) )
                    
            except Exception as e:
                logging.error('Error\n' + str(e))
                scope.clear()
                logging.error('Returning 0 and moving on...')
                return {1:[0], 2:[0], 3:[0], 4:[0]}
            i += sequence_count
            
    except (KeyboardInterrupt, SystemExit):
        logging.error('\rUser interrupted fetch early')
        scope.clear()
        raise KeyboardInterrupt

    except Exception as e:
        logging.error('Error 2\n' + str(e))
        scope.clear()
        return {1:[0], 2:[0], 3:[0], 4:[0]}               

    print('\n')
    scope.clear()
    
    for channel in channels:
        if len(maximum[channel])>1:
            logging.debug(f'Channel {channel}:\t Avg rate: {np.mean(rate[channel]):.3e} Hz')
            print(f'Channel {channel}:')
            print(f'\tAvg rate: {np.mean(rate[channel]):.3e} Hz')
            print('')
        else:
            logging.debug(f'Channel {channel}:\t Avg rate: {rate[channel][0]:.3e} Hz')
            print(f'Channel {channel}:', end='\t')
            print(f'Avg rate: {rate[channel][0]:.3e} Hz')
            print('')

    return rate

if __name__ == '__main__':
    import optparse

    usage = "usage: %prog [-n]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-i", type="str", dest="ip",
                      help="IP address of the scope", default="127.0.0.1")
    parser.add_option("-n", type="int", dest="nevents",
                      help="number of events to capture in total", default=100)
    parser.add_option("-o", type="str", dest="outfile",
                      help="output file name", default="results.dat")
    parser.add_option("--time", action="store_true", dest="time",
                      help="append time string to filename", default=False)            
    (options, args) = parser.parse_args()

    initialX = 80
    xMin = -25.
    xMax = 20.
    xSteps = 21
    xes = np.linspace(xMin, xMax, xSteps)
    print(xes)
    logging.info(xes)

    initialY = 80
    yMin = -10.
    yMax = 20.
    ySteps = 21
    yes = np.linspace(yMin, yMax, ySteps)
    print(yes)
    logging.info(yes)

    if options.nevents < 1:
        sys.exit("Arguments to -n must be positive")

    motors = motion.motion(port='COM3')
    time.sleep(1)
    motors.moveFor(-500,-500)

    motors.moveTo(initialX, initialY)
    motors.setHome()

    dirname = options.outfile.replace('.txt','')
    if(os.path.isdir(f'{dirname}'):
       sys.exit(f"Scan instance with name {dirname} already exists!")
    else:
       os.system(f'mkdir -p {dirname}/hdf5')
    print(f'Saving output to directory {dirname}/')
    
    f = open(dirname+"/"+options.outfile, "w")
    f.write('x\ty\trates\n')

    #save details of scan as a dict in a txt file
    d = {'nTrig':options.nevents,
         'xMaxIdx':xSteps-1,
         'yMaxIdx':ySteps-1}
    json.dump(d, open(f"{dirname}/{dirname}_info.json",'w'))
    
    try:
        for x in xes:
            xidx = list(xes).index(x)
            for y in yes:
                yidx = list(yes).index(y)

                logging.info(f'Moving to {x},{y}')
                print((f'Moving to {x},{y}'))
                motors.moveTo(x=x, y=y)
                f.write(f'{x}\t{y}\t')
                
                h5f = h5py.File(f'{dirname}/hdf5/x{xidx}_y{yidx}.hdf5','w')
                h5f.create_dataset('x',(1,), dtype='f8')
                h5f['x'][0] = x
                h5f.create_dataset('y',(1,), dtype='f8')
                h5f['y'][0] = y
                
                rates = measure(h5f, options.nevents, options.nevents, options.ip)
                for c,r in rates.items():
                    f.write(f'{r[0]}\t')
                f.write('\n')
                    
    except Exception as e: 
        logging.error('Error 3\n' + str(e))
    finally:
        logging.info('!!! Wait for platform to return Home!!!!!')
        print('!!! Wait for platform to return Home!!!!!')
        f.close()
        motors.goHome()
        sys.exit(0)
