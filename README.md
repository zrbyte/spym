# RHK STM data analysis tool

Based on the spym project (version 0.9), for personal use in our research group. If you want to contribute, please do so in the main [rescipy project](https://github.com/rescipy-project/spym).

Documentation can be found here: https://zrbyte.github.io/rhkpy/

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/zrbyte/rhkpy/HEAD)

## Main features
- Able to handle many kinds of spectroscopy measurements (both dI/dV and I(z)):
  - dI/dV maps
  - spectra along a line
  - individual spectra
- Resample dI/dV maps along a line (see [`mapsection`](https://zrbyte.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.mapsection))
- Quick, interactive visualization of spectroscopy data (see [`qplot`](https://zrbyte.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_loader.rhkdata.qplot))
- Recreating the "navigation" window in Rev9, by plotting the relative positions of measurements (see the [`navigation`](https://zrbyte.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.navigation) function).
- generating thumbnails of your measurements (see [`genthumbs`](https://zrbyte.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.genthumbs))
- peak fitting (see [`peakfit`](https://zrbyte.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.peakfit))

## Installation
`pip install rhkpy`

## Simple example
```python
import rhkpy

# Load an sm4 file
data = rhkpy.rhkdata('filename.sm4')

# "quick plot" of the data
data.qplot()

# make thumbnails of the sm4 files in the current working directory
rhkpy.genthumbs()
```

Also take a look the `demo.ipynb` and `tutorial.ipynb` Jupyter notebooks in this repository.

To make the most of rhkpy, also consult the xarray documentation and check out plotting examples, with HoloViews. The HoloViews website has examples on how to customize plots, as well as tutorial notebooks.
