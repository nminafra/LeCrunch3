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

import logging
import os
import sys
import time
import h5py
import numpy as np
from LeCrunch3 import LeCrunch3


def get_size(file_path):
    size_bytes = os.path.getsize(file_path)
    size_units = ["B", "KB", "MB", "GB", "TB"]

    i = 0
    while size_bytes >= 1024 and i < len(size_units) - 1:
        size_bytes /= 1024.0
        i += 1

    return "{:.2f} {}".format(size_bytes, size_units[i])


def get_sequence_count(settings: dict) -> int:
    """
    Get the number of traces per aquisition from the settings dictionary
    """
    sequence_count = 1
    if b"ON" in settings["SEQUENCE"]:
        sequence_count = int(settings["SEQUENCE"].split(b",")[1])

    return sequence_count


def setup_scope(scope, nsequence: int = 1, b16acq: bool = True) -> dict:
    """
    Set number of seqences and binary format for the scope
    """
    logging.info("Setting scope settings...")
    scope.clear()
    scope.set_sequence_mode(nsequence)
    logging.info("Sequence mode set to %d sequences", nsequence)
    if b16acq:
        scopeSets = scope.get_settings()
        for k, v in scopeSets.items():
            scopeSets[k] = v.decode()
        scopeSets["COMM_FORMAT"] = "CFMT DEF9,WORD,BIN"
        scope.set_settings(scopeSets)
        logging.info("Scope configured to 16bits mode")

    settings = scope.get_settings()
    sequence_count = get_sequence_count(settings)
    if nsequence != sequence_count:
        print("Could not configure sequence mode properly")

    logging.info("Scope setting completed")
    return settings


def fetchAndSaveFast(
    filename, ip, nevents: int = 1, nsequence: int = 1, timeout: float = 1000, b16acq: bool = True, quiet: bool = False
) -> int:
    """
    Fetch and save waveform traces from the oscilloscope
    with ADC values and with all info needed to reconstruct the waveforms
    It is faster than fetchAndSaveSimple but it requires a bit more code to analyze the files
    """
    startTime = time.time()
    print(f"Connecting to {ip} with timeout {timeout} s")
    try:
        scope = LeCrunch3(ip, timeout=timeout)
        print(f"Connected to {ip}")
    except TimeoutError as e:
        print("Could not connect to scope\n" + str(e))
        return 0

    settings = setup_scope(scope, nsequence, b16acq)
    sequence_count = get_sequence_count(settings)
    if sequence_count != 1:
        print(f"Using sequence mode with {sequence_count} traces per aquisition")

    active_channels = scope.get_channels()
    logging.info("Active channels %s", active_channels)

    logging.info("Opening file %s", filename)
    f = h5py.File(filename, mode="w", driver="core")
    for command, setting in settings.items():
        f.attrs[command] = setting
    current_dim = {}

    print("Active channels: ", active_channels)
    for channel in active_channels:
        wave_desc = scope.get_wavedesc(channel)
        # wave_desc["wave_array_count"] is number of datapoints in all sequences in one event
        current_dim[channel] = wave_desc["wave_array_count"] // sequence_count
        f.create_dataset(
            name=f"c{channel}_samples",
            shape=(nevents, current_dim[channel]),
            dtype=wave_desc["dtype"],
            maxshape=(nevents, None),
        )
        # Save attributes of each channel in the file
        for key, value in wave_desc.items():
            try:
                f[f"c{channel}_samples"].attrs[key] = value
            except ValueError:
                pass
        f.create_dataset(name=f"c{channel}_vert_offset", shape=(nevents,), dtype="f8")
        f.create_dataset(name=f"c{channel}_vert_scale", shape=(nevents,), dtype="f8")
        f.create_dataset(name=f"c{channel}_horiz_offset", shape=(nevents,), dtype="f8")
        f.create_dataset(name=f"c{channel}_horiz_scale", shape=(nevents,), dtype="f8")
        f.create_dataset(name=f"c{channel}_trig_offset", shape=(nevents,), dtype="f8")
        f.create_dataset(name=f"c{channel}_trig_time", shape=(nevents,), dtype="f8")
    f.create_dataset(name="seconds_from_start", shape=(nevents,), dtype="f8")
    logging.info("Created dataset and metadata for all channels")

    try:
        i = 0
        start_time = time.time()
        while i < nevents:
            if not quiet:
                print(f"\rSCOPE: fetching event: {i}")
                sys.stdout.flush()
            logging.info(
                "Event %d, from start of acquisition %.3f seconds",
                i,
                time.time() - start_time,
            )
            try:
                f["seconds_from_start"][i] = float(time.time() - startTime)
                scope.trigger()
                logging.info("Acquiring data for event %d", i)
                for channel in active_channels:
                    (
                        wave_desc,
                        trg_times,
                        trg_offsets,
                        wave_array,
                    ) = scope.get_waveform_all(channel)
                    num_samples = wave_desc["wave_array_count"] // sequence_count
                    logging.debug(
                        "wave_array_count %d, sequence_count %d, number of samples %d",
                        wave_desc["wave_array_count"],
                        sequence_count,
                        num_samples,
                    )
                    logging.debug("trg_times len = %d", len(trg_times))
                    num_samples_toSave = int(1 * num_samples)  ##TORemove
                    if current_dim[channel] < num_samples_toSave:
                        current_dim[channel] = num_samples_toSave
                        f[f"c{channel}_samples"].resize(current_dim[channel], 1)
                    traces = wave_array.reshape(sequence_count, wave_array.size // sequence_count)
                    # necessary because h5py does not like indexing and this is the fastest (and man is it slow) way
                    scratch = np.zeros((current_dim[channel],), dtype=wave_array.dtype)
                    for n in range(sequence_count):
                        scratch[0:num_samples] = traces[n][:num_samples_toSave]
                        f[f"c{channel}_samples"][i + n] = scratch
                        f[f"c{channel}_vert_offset"][i + n] = wave_desc["vertical_offset"]
                        f[f"c{channel}_vert_scale"][i + n] = wave_desc["vertical_gain"]
                        f[f"c{channel}_horiz_offset"][i + n] = wave_desc["horiz_offset"]
                        f[f"c{channel}_horiz_scale"][i + n] = wave_desc["horiz_interval"]
                        # trigger offsets and trigger times may not be available in single sequence mode
                        if len(trg_offsets) > 0:
                            f[f"c{channel}_trig_offset"][i + n] = trg_offsets[n]
                        if len(trg_times) > 0:
                            f[f"c{channel}_trig_time"][i + n] = trg_times[n]

            except Exception as e:
                print("Error\n" + str(e))
                scope.clear()
                continue
            i += sequence_count
    except:
        print("\rUser interrupted fetch early or something happened...")
    finally:
        print("\rClosing the file")
        elapsed = time.time() - start_time
        if i > 0:
            print(f"Completed {i} events in {elapsed:.3f} seconds.")
            print(f"Averaged {elapsed/i:.5f} seconds per acquisition.")
        logging.info("Starting to close the file")
        f.close()
        logging.info("File close, starting to clear scope")
        print(f"Size on disk: {get_size(filename)}")
        scope.clear()
        logging.info("Scope cleared")
        return i


if __name__ == "__main__":
    import sys
    from cli import parse_options, setup_logging

    options, args = parse_options(args=sys.argv)
    setup_logging(verbosity=options.verbosity)

    # construct output file path
    time_insert = ""
    if options.time:
        time_insert = time.strftime("_%d_%b_%Y_%H:%M:%S", time.localtime())
    filename = f"{args[1]}{time_insert}.h5"
    print(f"Saving data to file {filename}")

    count = fetchAndSaveFast(
        filename=filename,
        ip=options.ip,
        nevents=options.nevents,
        nsequence=options.nsequence,
        b16acq=True,
        quiet=options.quiet,
    )
