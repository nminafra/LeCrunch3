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
import numpy as np
from LeCrunch3 import LeCrunch3

def measure(nevents, ip, timeout=1000):
    '''
    Fetch and save waveform traces from the oscilloscope.
    '''
    print(ip)
    scope = LeCrunch3(ip, timeout=timeout)
    scope.clear()
    scope.set_sequence_mode(nevents)
    channels = scope.get_channels()
    settings = scope.get_settings()

    minimum = {}
    maximum = {}
    triggerTimes = []

    if b'ON' in settings['SEQUENCE']:
        sequence_count = int(settings['SEQUENCE'].split(b',')[1])
    else:
        sequence_count = 1
    print(sequence_count)
        
    if nevents != sequence_count:
        print('Could not configure sequence mode properly')
    if sequence_count != 1:
        print(f'Using sequence mode with {sequence_count} traces per aquisition')
    
   
    current_dim = {}
    
    for channel in channels:
        wave_desc = scope.get_wavedesc(channel)
        current_dim[channel] = wave_desc['wave_array_count']//sequence_count

        # Add here all measurements you want...
        minimum[channel] = []
        maximum[channel] = []

    try:
        i = 0
        while i < nevents:
            print(f'\rfetching event: {i}')
            sys.stdout.flush()
            try:
                scope.trigger()
                for channel in channels:
                    wave_desc,wave_array = scope.get_waveform(channel)
                    num_samples = wave_desc['wave_array_count']//sequence_count

                    # Get trigger times (only once)
                    # if len(triggerTimes) < 1:
                    #     triggerTimes = wave_desc['wathever']

                    if current_dim[channel] < num_samples:
                        current_dim[channel] = num_samples
                    traces = wave_array.reshape(sequence_count, wave_array.size//sequence_count)
                    #necessary because h5py does not like indexing and this is the fastest (and man is it slow) way
                    scratch = np.zeros((current_dim[channel],),dtype=wave_array.dtype)
                    for n in range(0,sequence_count):
                        scratch[0:num_samples] = traces[n] 

                        # Add here all measurements you want...
                        minimum[channel].append( np.min(-wave_desc['vertical_offset'] + scratch*wave_desc['vertical_gain']) )
                        maximum[channel].append( np.max(-wave_desc['vertical_offset'] + scratch*wave_desc['vertical_gain']) )
                    
            except (socket.error, struct.error) as e:
                print('Error\n' + str(e))
                scope.clear()
                continue
            i += sequence_count
    except KeyboardInterrupt:
        print('\rUser interrupted fetch early')
    finally:
        print('\r', )
        scope.clear()

        for channel in channels:
            print(f'Avg maximum for ch {channel}: {np.mean(maximum[channel])} V')
            print(f'Avg minimum for ch {channel}: {np.mean(minimum[channel])} V')
        
        triggerRate = np.mean(np.diff(triggerTimes))
        print(f'Avg trigger rate: {triggerRate} Hz')

        return triggerRate

if __name__ == '__main__':
    import optparse

    usage = "usage: %prog [-n]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-i", type="str", dest="ip",
                      help="IP address of the scope", default="127.0.0.0")
    parser.add_option("-n", type="int", dest="nevents",
                      help="number of events to capture in total", default=0)
    (options, args) = parser.parse_args()

    
    if options.nevents < 1:
        sys.exit("Arguments to -s or -n must be positive")

    start = time.time()
    count = measure(options.nevents, options.ip)
    elapsed = time.time() - start
    if count > 0:
        print(f'Completed {count} events in {elapsed:.3f} seconds.')
        print(f'Averaged {elapsed/count:.5f} seconds per acquisition.')
