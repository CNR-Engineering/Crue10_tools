Crue10 tools
============

> Tools to handle 1D hydraulic model file format called `Crue10` (CNR proprietary computation code).

## Crue10 API - files parser

- [Read studies](snippets/read_studies.py)
- [Read a submodel and its EMHs](snippets/read_submodel.py)
- [Read a model](snippets/read_model.py)
- [Read a run](snippets/read_run.py)
- [Read a model and an associated run](snippets/read_model.py)
- [Write a submodel from scratch](snippets/write_submodel_from_scratch.py)
- [Write a study from scratch](snippets/write_study_from_scratch.py)

## Command line scripts

TODO: documentate them automatically.

### XSD validator

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
