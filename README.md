Crue10 tools
============

> Tools to handle 1D hydraulic model file format called `Crue10`.

## Read Crue10 submodel

See example in file `snippets/read_crue_submodel.py`.

## Read Crue10 result file (rcal/bin)

See example in file `snippets/read_crue_run.py`.

## XSD Validator

Use cli script: `cli/crue10_xsd_validator.py`:

```bash
usage: crue10_xsd_validator.py [-h] [-v] etu_path

Check against XSD validation files every crue10 xml files included in the
target study (etu.xml file)

positional arguments:
  etu_path       path to etu.xml file

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  increase output verbosity
```

## TODO
* support reading of dcsp
* convert html entities in comments
* write shp files
