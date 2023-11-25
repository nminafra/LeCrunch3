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
python .\fetchAndSaveFast.py output.h5 -i 10.10.111.78 -n 2 -s 2
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

## Authors

LeCrunch3 is based on LeCrunch2 by Benjamin Land: https://github.com/BenLand100/LeCrunch2
LeCrunch2 is based on LeCrunch by Anthony LaTorre <tlatorre9@gmail.com>
