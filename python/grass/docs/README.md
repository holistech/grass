# GRASS Python Docs

## Local Development

### Prerequisites

Install the following dependencies from the `requirements.txt` file: in
`python/grass/docs` directory.

* [sphinx (v8.1.3)](https://www.sphinx-doc.org/en/master/changes/8.1.html)
* [sphinx-material (v0.0.36)](https://bashtage.github.io/sphinx-material/)
* [sphinx-sitemap (v2.6.0)](https://sphinx-sitemap.readthedocs.io/en/latest/)
* [sphinx-last-updated-by-git](https://github.com/mgeier/sphinx-last-updated-by-git/)

```bash
pip install -r python/grass/docs/requirements.txt
```

The reference imports the GRASS Python packages, which need the packages of
`.github/workflows/python_requirements.txt` (among them numpy) as well:

```bash
pip install -r .github/workflows/python_requirements.txt
```

If only `python/grass/docs/requirements.txt` is installed, the build ends with
return code 0 and warnings, but the reference is empty: autodoc cannot import
`grass.temporal` without numpy and the pages stay empty. Check the build log
for `No module named 'numpy'`.

### Build the Documentation

To build the documentation, run the following command in the `python/grass/docs`
directory:

```bash
make sphinxdoclib
```

This will generate the documentation in the `dist` directory.

### View the Documentation

To view the documentation, open the `index.html` file in the
`dist/docs/html/libpython`
directory with a local web server.

## CI/CD

The documentation is built and deployed automatically using GitHub Actions.
The workflow is triggered on every push to the `main` branch `.github/workflows/documentation.yml`.
