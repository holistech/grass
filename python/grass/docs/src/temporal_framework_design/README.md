# The GRASS Temporal Framework: code design document

This folder holds the source of
`../Temporal-Framework-Code-Design.pdf`, "The GRASS Temporal Framework:
Object oriented code design with examples". It revises the supplementary
material of Gebbert and Pebesma (2017), which stays unchanged as
`../Temporal-Framework-API-Description.pdf`.

## Content

- `design.tex`: the text.
- `figures/*.tex`: the figures, TikZ with `pgf-umlcd`. A figure file writes
  names with plain underscores (`get_id()`); `design.tex` reads it with the
  underscore as an ordinary character.
- `examples/*.py`: the examples, each shown as a listing, and
  `examples/*.txt`: the output the document shows for each.
- `references.bib`: the bibliography.
- `Makefile`: the build.
- `digest.tex`: written by `make`, the SHA-256 of the sources, which the PDF
  carries as its keywords.

## Build

```sh
make        # builds design.pdf and copies it to ../Temporal-Framework-Code-Design.pdf
make clean  # removes what the build leaves behind
```

The build needs `pdflatex` and `bibtex` and the LaTeX packages `fontenc`,
`inputenc`, `lmodern`, `microtype`, `geometry`, `xcolor`, `booktabs`,
`caption`, `float`, `listings`, `natbib`, `hyperref`, `pgf` (TikZ, with the
libraries `fit` and `calc`) and `pgf-umlcd`. On Ubuntu 24.04, the packages
`texlive-latex-base`, `texlive-latex-recommended`, `texlive-pictures` and
`lmodern` provide them. The CI
does not build the PDF; check in the PDF and `digest.tex` together with the
changed sources.

## Tests

`temporal/tests/temporal_framework_design_test.py` checks the document
against the code:

- each example runs in the North Carolina sample dataset
  (`nc_spm_08_grass7`) in a new mapset `temporal_design` and prints the
  output of its `.txt` file;
- each example calls only what the public contract of `grass.temporal`
  lists (`python/grass/temporal/tests/data/public_contract.json`);
- each class, member, base class and composition that a figure draws exists;
- the keywords of the PDF equal the digest of the sources, so the PDF is
  built from the sources as they are;
- each listing in the PDF, read with `pdftotext`, is the example file.

After changing an example, run it as the test does and write its output
into the `.txt` file, then run `make`.

## Running the examples

Save the examples and run them in the order of the document, the first one
with `-c`, which creates the mapset:

```sh
grass -c ~/grassdata/nc_spm_08_grass7/temporal_design --exec python3 register.py
grass ~/grassdata/nc_spm_08_grass7/temporal_design --exec python3 aggregate.py
```

The examples never write into the mapset `PERMANENT` of the dataset.
