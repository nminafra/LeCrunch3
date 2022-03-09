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
from datetime import datetime
import string
import struct
import socket
import h5py
import json
import numpy as np
from LeCrunch3 import LeCrunch3

import logging

import motion

def measure(fileH5, nevents, nsequence, ip, timeout=10000):
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
        fileH5.attrs[command] = setting               
    current_dim = {}
    
    for channel in channels:
        wave_desc = scope.get_wavedesc(channel)
        current_dim[channel] = wave_desc['wave_array_count']//sequence_count
        fileH5.create_dataset(f'ch{channel}_samples', (nevents,current_dim[channel]), dtype=wave_desc['dtype'], maxshape=(nevents,None))
        ## Save attributes in the file
        for key, value in wave_desc.items():
            try:
                fileH5[f"ch{channel}_samples"].attrs[key] = value
            except ValueError:
                pass
        fileH5.create_dataset(f'ch{channel}_vert_offset', (nevents,), dtype='f8')
        fileH5.create_dataset(f'ch{channel}_vert_scale', (nevents,), dtype='f8')
        fileH5.create_dataset(f'ch{channel}_horiz_offset', (nevents,), dtype='f8')
        fileH5.create_dataset(f'ch{channel}_horiz_scale', (nevents,), dtype='f8')
        fileH5.create_dataset(f'ch{channel}_trig_offset', (nevents,), dtype='f8')
        fileH5.create_dataset(f'ch{channel}_trig_time', (nevents,), dtype='f8')

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
                        fileH5[f'ch{channel}_samples'][i+n] = scratch
                        fileH5[f'ch{channel}_vert_offset'][i+n] = wave_desc['vertical_offset']
                        fileH5[f'ch{channel}_vert_scale'][i+n] = wave_desc['vertical_gain']
                        fileH5[f'ch{channel}_horiz_offset'][i+n] = wave_desc['horiz_offset']
                        fileH5[f'ch{channel}_horiz_scale'][i+n] = wave_desc['horiz_interval']
                        fileH5[f'ch{channel}_trig_offset'][i+n] = trg_offsets[n]
                        fileH5[f'ch{channel}_trig_time'][i+n] = trg_times[n]

                        # Add here all measurements you want...
                        samples = -wave_desc['vertical_offset'] + scratch*wave_desc['vertical_gain']
                        if np.abs(np.max(samples) - np.min(samples)) > 12*np.std(samples[:100]):
                            filt_trg_times.append(trg_times[n])                                  
                    rate[channel].append(np.mean(np.diff(filt_trg_times)))
                    
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
        rate_val = -999.
        if len(maximum[channel])>1:
            rate_val = 1./np.mean(rate[channel])
            logging.debug(f'Channel {channel}:\t Avg rate: {rate_val:.3e} Hz')
            print(f'Channel {channel}:')
            print(f'\tAvg rate: {rate_val:.3e} Hz')
            print('')
            
        else:
            rate_val = 1./np.mean(rate[channel][0])
            logging.debug(f'Channel {channel}:\t Avg rate: {rate_val:.3e} Hz')
            print(f'Channel {channel}:', end='\t')
            print(f'Avg rate: {rate_val:.3e} Hz')
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
    parser.add_option("-o", type="str", dest="outfolder",
                      help="output scan folder name", default="Scan")
    parser.add_option("--time", action="store_true", dest="time",
                      help="append time string to filename", default=False)
    parser.add_option("--resume", action="store_true", dest="resume",
                      help="Resume where scan was interrupted", default=False)            
    (options, args) = parser.parse_args()          

    dirname = options.outfolder
    pathname = '.\\ScanResults\\'+dirname

    if(options.resume):
        logging.basicConfig(filename=f'{pathname}\{dirname}.log', level=logging.DEBUG, filemode='a')          
        #Get interrupted scan details from stored json file
        with open(f'{pathname}\{dirname}_info.json') as fileJS:
            info = fileJS.read()
        dict = json.loads(info)
        initialX = dict.get('initialX')
        initialY = dict.get('initialY')
        xes = np.linspace(dict.get('xMin'),dict.get('xMax'),dict.get('xMaxIdx')+1)
        yes = np.linspace(dict.get('yMin'),dict.get('yMax'),dict.get('yMaxIdx')+1)
        ntrig = dict.get('nTrig')

        #Get last coordinates of interrupted scan
        with open(f'{pathname}\{dirname}.txt', 'r') as file:
            last_line = file.readlines()[-1]
        last_coord = [float(val) for val in last_line.split()]            
        xlast = list(xes).index(last_coord[0])
        ylast = list(yes).index(last_coord[1])

        #delete last line of text file to resume scan there
        with open(f'{pathname}\{dirname}.txt', 'r+') as file:            
            lines = file.readlines()
            file.seek(0)
            file.truncate()
            file.writelines(lines[:-1])
            
        logging.info(f'Resuming {dirname} at x{xlast} = {last_coord[0]}[mm] and y{ylast} = {last_coord[1]}[mm]')
        print(f'Resuming {dirname} at x{xlast} = {last_coord[0]} and y{ylast} = {last_coord[1]}')
        print(f'Saving output to directory {pathname}/')
        file = open(pathname+"/"+options.outfolder+".txt", "a")

    else:
        #Check if all input is ready to begin scan correctly
        if options.nevents < 1:
            sys.exit("Arguments to -n must be positive")

        if (os.path.isdir(f'{pathname}')):
            sys.exit(f"{dirname} already exists! Use --resume for incomplete scan.")
        else:
            os.system(f"md {pathname}\hdf5")
            print(f'Beginning {dirname}')
            print(f'Saving output to directory {pathname}/')
            logging.basicConfig(filename=f'{pathname}\{dirname}.log', level=logging.DEBUG, filemode='w')
            logging.info(f'Beginning {dirname}')
            logging.info(f'Saving output to directory {pathname}/')

        #Set scan general details
        ntrig = options.nevents

        initialX = 100
        xMin = -25.
        xMax = 20.
        xSteps = 21
        xes = np.linspace(xMin, xMax, xSteps)
        print(xes)
        xlast = 0

        initialY = 110
        yMin = -20.
        yMax = 20.
        ySteps = 21
        yes = np.linspace(yMin, yMax, ySteps)
        print(yes)
        ylast = 0

        logging.info(f'Initial absolute position [mm]: ({initialX},{initialY})')
        logging.info(f'Relative scan positions in x[mm]: {xes}')
        logging.info(f'Relative scan positions in y[mm]: {yes}')

        #save details of scan as a dict in a json file
        d = {'nTrig':options.nevents,
            'initialX':initialX,
            'initialY':initialY,
            'xMaxIdx':xSteps-1,
            'yMaxIdx':ySteps-1,
            'xMin':xMin,
            'yMin':yMin,
            'xMax':xMax,
            'yMax':yMax}
        json.dump(d, open(f"{pathname}/{dirname}_info.json",'w'))

        file = open(pathname+"/"+options.outfolder+".txt", "w")
        file.write('x\ty\trates\n')       

    motors = motion.motion(port='COM3')
    time.sleep(1)
    motors.moveFor(-500,-500)

    motors.moveTo(initialX, initialY)
    motors.setHome()
    
    try:
        for x in xes[xlast:]:
            xidx = list(xes).index(x)
            for y in yes[ylast:]:
                yidx = list(yes).index(y)    
                logging.info(f'Moving to x{xidx} = {x}[mm], y{yidx}) = {y}[mm]')
                print((f'Moving to x{xidx} = {x}[mm], y{yidx}) = {y}[mm]'))
                motors.moveTo(x=x, y=y)
                file.write(f'{x}\t{y}\t')
                
                h5f = h5py.File(f'{pathname}/hdf5/x{xidx}_y{yidx}.hdf5','w')
                h5f.create_dataset('x',(1,), dtype='f8')
                h5f['x'][0] = x
                h5f.create_dataset('y',(1,), dtype='f8')
                h5f['y'][0] = y
                '''
                now = datetime.now()
                h5f.create_dataset('time',(1,), dtype='S')               
                h5f['time'][0] = now.strftime("%H:%M:%S")
                '''
                rates = measure(h5f, ntrig, ntrig, options.ip)
                for c,r in rates.items():
                    rate_val = r[0]
                    h5f.create_dataset(f'ch{c}_rate', (1,), dtype='f8')
                    if rate_val != 0:
                        rate_val = 1./rate_val
                    h5f[f'ch{c}_rate'][0] = rate_val
                    file.write(f'{rate_val}\t')
                file.write('\n')
            ylast = 0   
                    
    except Exception as e: 
        logging.error('Error 3\n' + str(e))
    finally:
        logging.info('!!! Wait for platform to return Home!!!!!')
        print('!!! Wait for platform to return Home!!!!!')
        file.close()
        motors.goHome()
        sys.exit(0)
