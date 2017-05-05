# pyifcb - Imaging FlowCytobot Python API, generation 2

## Overview

This module provides facilities for accessing and managing data generated by the Imaging FlowCytobot. It can read and write IFCB data in various formats, including the instrument's native format, and can serve as the basis of any application that uses IFCB data.

Generation 1 of this data system was called the IFCB Data Dashboard. In this, generation 2, features of the dashboard are being broken out into smaller, independent modules that can be used together.

## Authors and contributors

Joe Futrelle (jfutrelle@whoi.edu) - Woods Hole Oceanographic Institution

## Installation via anaconda

To create a conda environment called "pyifcb":

```
conda env create -f environment.yml
python setup.py install
```

Or with a Python 3 conda environment already activated:

```
conda install --file requirements.txt
python setup.py install
```

## Status

As of 2017-04-28 pyifcb requires Python 3.

As of 2017-01-04 this is mostly complete and the APIs are not likely to change much, but there is no stable release yet so APIs may still change. The Wiki and code-level documentation is up to date.

[![Build Status](https://travis-ci.org/joefutrelle/pyifcb.svg?branch=master)](https://travis-ci.org/joefutrelle/pyifcb)
