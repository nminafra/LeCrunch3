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

import io
import logging
from math import log10
import os
from pathlib import Path
import sys
import time
import h5py
import numpy as np
from LeCrunch3 import LeCrunch3


def datasize_human_readable(size_bytes: int) -> str:
    """
    Human readable size in automatically selected units
    """

    size_units = ["B", "KB", "MB", "GB", "TB", "PB"]

    i = 0
    while size_bytes >= 1024 and i < len(size_units) - 1:
        size_bytes /= 1024.0
        i += 1

    return "{:.2f} {}".format(size_bytes, size_units[i])


def get_optimal_prefix(number, tolerance=1e-10):
    """
    Get the optimal SI prefix for a given number
    """
    prefixes = {
        24: "Y",
        21: "Z",
        18: "E",
        15: "P",
        12: "T",
        9: "G",
        6: "M",
        3: "k",
        0: "",
        -3: "m",
        -6: "µ",
        -9: "n",
        -12: "p",
        -15: "f",
        -18: "a",
        -21: "z",
        -24: "y",
    }

    # If the number is 0, return '0' with no prefix
    if number == 0:
        return "0"

    # Calculate the exponent without rounding
    exp_exact = log10(abs(number)) // 3 * 3

    # Round up only if very close to the next integer
    exp_rounded = exp_exact if abs(exp_exact % 3) > tolerance else round(exp_exact)

    # Find the appropriate prefix for the given number
    exp = int(exp_rounded)
    prefix = prefixes.get(exp, "")

    # Format the result with the number and the prefix
    result = "{:.3f} {}".format(number / 10**exp, prefix)
    return result


def get_sequence_count(settings: dict) -> int:
    """
    Get the number of traces per aquisition (sequences) from the settings dictionary
    """
    sequence_count = 1
    if b"ON" in settings["SEQUENCE"]:
        sequence_count = int(settings["SEQUENCE"].split(b",")[1])

    return sequence_count


def setup_scope(scope, nsequence: int = 1, save_in_16bits: bool = True) -> dict:
    """
    Set number of seqences and binary format for the scope
    """
    logging.info("Setting scope settings...")
    scope.clear()
    scope.set_sequence_mode(nsequence)
    logging.info("Mode set to %d sequences", nsequence)

    # optionally set maximum sample points per segment
    # scope.send("MSIZ 10M")
    # scope.check_last_command()

    if save_in_16bits:
        scope_settings = scope.get_settings()
        for k, v in scope_settings.items():
            scope_settings[k] = v.decode()
        """
        The COMM_FORMAT command selects the format the oscilloscope uses to send waveform data. The
        available options allow the block format, the data type and the encoding mode to be modified from the
        default settings.
        Initial settings (after power-on) are: block format DEF9; data type WORD; encoding BIN
        Data Type
        BYTE transmits the waveform data as 8-bit signed integers (one byte).
        WORD transmits the waveform data as 16-bit signed integers (two bytes).
        Encoding
        BIN specifies Binary encoding. This is the only type of waveform data encoding supported by Teledyne
        LeCroy oscilloscopes.
        """
        scope_settings["COMM_FORMAT"] = "CFMT DEF9,WORD,BIN"

        scope.set_settings(scope_settings)
        logging.info("Scope configured to 16bits mode")
    # get the settings again to check that the scope is in proper mode
    settings = scope.get_settings()
    sequence_count = get_sequence_count(settings)
    if nsequence != sequence_count:
        print("Could not configure sequence mode properly")
    logging.info("Scope setting completed")
    return settings


def vert_horiz_summary(vert_offset: float, vert_gain: float, horiz_interval: float, horiz_offset: float):
    """
    Print a summary of the vertical and horizontal settings
    """
    time_offset_s = f"{get_optimal_prefix(horiz_offset)}s"
    time_interval_s = f"{get_optimal_prefix(horiz_interval)}s"
    time_freq_s = f"{get_optimal_prefix(1/horiz_interval)}Hz"
    vert_gain_V = f"{get_optimal_prefix(vert_gain)}V"
    vert_offset_V = f"{get_optimal_prefix(vert_offset)}V"
    print(f"\t horizontal: interval {time_interval_s}, freq {time_freq_s}, offset {time_offset_s}")
    print(f"\t   vertical: gain {vert_gain_V}, offset {vert_offset_V}")


def fetchAndSaveFast(
    filename: str,
    ip: str,
    nevents: int = 1,
    nsequence: int = 1,
    timeout: float = 1000,
    save_in_16bits: bool = True,
    quiet: bool = False,
) -> int:
    """
    Fetch and save waveform traces from the oscilloscope
    with ADC values and with all info needed to reconstruct the waveforms
    It is faster than fetchAndSaveSimple but it requires a bit more code to analyze the files
    """
    print(f"Connecting to {ip} with timeout {timeout} s... ", flush=True, end="")
    try:
        scope = LeCrunch3(ip, timeout=timeout)
        print("connected !")
    except TimeoutError as e:
        print("could not connect to scope")
        print(e)
        return 0

    settings = setup_scope(scope, nsequence, save_in_16bits)
    sequence_count = get_sequence_count(settings)
    if sequence_count != 1:
        print(f"Using sequence mode with {sequence_count} traces per aquisition")

    active_channels = scope.get_channels()
    logging.info("Active channels %s", active_channels)

    # the most direct to save the data would be to open a file and write the data to it
    # here we assume that our data is small enough to fit in memory and we use an in-memory file-like object
    # this is faster than writing to disk but it requires more memory
    # once the data is ready we write it to disk
    buf = io.BytesIO(b"")
    f = h5py.File(buf, mode="w", driver="fileobj")

    # save scope settings as attributes of the HDF file
    for command, setting in settings.items():
        f.attrs[command] = setting

    print("Active channels: ", active_channels)
    current_dim = {}
    for channel in active_channels:
        wave_desc = scope.get_wavedesc(channel)
        datapoints_no = wave_desc["wave_array_count"]
        current_dim[channel] = datapoints_no // sequence_count
        f.create_dataset(
            name=f"c{channel}_samples",
            shape=(nevents, current_dim[channel]),
            dtype=wave_desc["dtype"],
            maxshape=(nevents, None),
        )
        # save wave description as attributes of the dataset with samples
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
    logging.info("Created datasets with attributes for all channels")

    try:
        i = 0
        start_time = time.time()
        while i < nevents:
            if not quiet:
                if nsequence == 1:
                    print(f"\rSCOPE: fetching event: {i}", flush=True)
                else:
                    print(f"\rSCOPE: fetching events: {i}..{i+nsequence}", flush=True)
            time_from_start = time.time() - start_time
            logging.info(
                "Event %d, from start of acquisition %.3f seconds",
                i,
                time_from_start,
            )
            try:
                f["seconds_from_start"][i] = time_from_start
                scope.trigger()
                logging.info("Acquiring data for event %d", i)
                for channel in active_channels:
                    logging.info("Asking scope for channel %d data", channel)
                    time_before_waveform_query = time.time()
                    (
                        wave_desc,
                        trg_times,
                        trg_offsets,
                        wave_array,
                    ) = scope.get_waveform_all(channel)
                    logging.info("Data ready, took %.3f s", time.time() - time_before_waveform_query)
                    time_before_packing_data_to_hdf = time.time()
                    num_samples = wave_desc["wave_array_count"] // sequence_count
                    num_samples_to_save = int(1 * num_samples)  ##TORemove
                    if current_dim[channel] < num_samples_to_save:
                        current_dim[channel] = num_samples_to_save
                        f[f"c{channel}_samples"].resize(current_dim[channel], 1)
                    traces = wave_array.reshape(sequence_count, wave_array.size // sequence_count)
                    # necessary because h5py does not like indexing and this is the fastest (and man is it slow) way
                    scratch = np.zeros((current_dim[channel],), dtype=wave_array.dtype)
                    for n in range(sequence_count):
                        scratch[0:num_samples] = traces[n][:num_samples_to_save]
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
                    logging.info("Packing to HDF took %.3f s", time.time() - time_before_packing_data_to_hdf)
                    logging.info("Channel %d data packed in HDF,", channel)

            except Exception as e:
                print("Error\n" + str(e))
                scope.clear()
                continue
            i += sequence_count
    except:
        print("\rUser interrupted fetch early or something happened...")
    finally:
        print("\rClosing the file")
        if i > 0:
            elapsed = time.time() - start_time
            print(f"Completed {i} events in {elapsed:.3f} seconds.")
            print(f"Averaged {elapsed/i:.5f} seconds per event.")
            for channel in active_channels:
                print(f"Channel {channel}:")
                datapoints_no = f[f"c{channel}_samples"].attrs["wave_array_count"]
                no_samples = datapoints_no // nsequence
                size_bytes = f[f"c{channel}_samples"].attrs["wave_array_1"]
                print(f"\t {nsequence} (#seq)")
                print(f"\t {no_samples} == {get_optimal_prefix(no_samples)} (#samples)")
                print(f"\t {datapoints_no} == {get_optimal_prefix(datapoints_no)} (#datapoints)")
                print(f"\t {datapoints_no} == {nsequence} x {no_samples}")
                print(f"\t size of {nsequence} sequences: {datasize_human_readable(size_bytes)}")
                sequence_length_sec = no_samples * f[f"c{channel}_horiz_scale"][-1]
                print(f"\t sequence length {get_optimal_prefix(sequence_length_sec)}s")
                vert_horiz_summary(
                    horiz_offset=f[f"c{channel}_horiz_offset"][-1],
                    horiz_interval=f[f"c{channel}_horiz_scale"][-1],
                    vert_offset=f[f"c{channel}_vert_offset"][-1],
                    vert_gain=f[f"c{channel}_vert_scale"][-1],
                )
        f.close()
        logging.info("Closed the in-memory HDF file-like object")

        logging.info("Opening file on disk: %s", filename)
        time_before_save_to_dist = time.time()
        Path(filename).write_bytes(buf.getvalue())
        logging.info("File saved in %.3f s", time.time() - time_before_save_to_dist)
        size_bytes = os.path.getsize(filename)
        print(f"Size on disk: {datasize_human_readable(size_bytes)}")


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

    fetchAndSaveFast(
        filename=filename,
        ip=options.ip,
        nevents=options.nevents,
        nsequence=options.nsequence,
        save_in_16bits=True,
        quiet=options.quiet,
    )
