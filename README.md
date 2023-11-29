# LeCrunch3
A python3 tool to control a LeCroy scope and to acquire/process data

## Usage
LeCrunch3 adds some funcitionalities, like the possibility of saving easy to use HDF files:

```
import matplotlib.pyplot as plt
import h5py

f = h5py.File('testfile.h5', 'r')

numOfSegments = f[f'c1_time'].shape[0]

for i in range(numOfSegments):

plt.plot(f[f'c1_time'][i], f[f'c1_samples'][i])
```

And more importantly, the acquisition of trigger times and offset.

### Data acqusition

The comman below will connect to the scope available under IP address `10.10.111.78`, and collect 2 events, with 2 sequences in each.
The output will be saved to `output.h5` file.

```
python .\fetchAndSaveFast.py output -i 10.10.111.78 -n 2 -s 2
```

To enable verbose printout, which include `INFO` level logs, use single verbosity flag:

```
python .\fetchAndSaveFast.py output -i 10.10.111.78 -n 2 -s 2 -v
```

Even more verbose printout, including `DEBUG` level logs (like all the commands send to scope), can be enabled with double verbosity flag:

```
python .\fetchAndSaveFast.py output -i 10.10.111.78 -n 2 -s 2 -vv
```

The logs will be written (appended) to the `info.log` and `debug.log` files. All lines include precise date and time (including time since start of the program).

To suppres any printout during data acquisition stage add `-q` flag. This should speedout readout a bit:
```
python .\fetchAndSaveFast.py output -i 10.10.111.78 -n 2 -s 2 -q
```

## Installation

### Manual

Install required packages, like `h5py` and `numpy` using your favorite package manager.
Then clone the repository and in the directory where `fetchAndSaveFast.py` is located, run:

```shell
python3 fetchAndSaveFast.py --help
```

### Poetry

If you have poetry installed, you can avoid installation of dependencies system-wide by running:

```shell
poetry install
```

System-wide installation of dependencies is nowadays considered bad practice, as it can lead to conflicts between different versions of the same package. Poetry creates a virtual environment for you, where all dependencies are installed. This project is configured to install virtual environment in a hidden `.venv` directory inside the project directory.

Then you can run the script using `poetry run` which will activate the virtual environment and run the script:

```shell
poetry run python3 fetchAndSaveFast.py --help
```

## Resources

Good manual of LeCroy scopes can be found at https://cdn.teledynelecroy.com/files/manuals/maui-remote-control-and-automation-manual.pdf

## Authors

LeCrunch3 is based on LeCrunch2 by Benjamin Land: https://github.com/BenLand100/LeCrunch2
LeCrunch2 is based on LeCrunch by Anthony LaTorre <tlatorre9@gmail.com>
