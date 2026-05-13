# fasthep-curator

[![CI](https://github.com/FAST-HEP/fasthep-curator/actions/workflows/ci.yml/badge.svg)](https://github.com/FAST-HEP/fasthep-curator/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fasthep-curator)](https://pypi.org/project/fasthep-curator/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fasthep-curator)](https://pypi.org/project/fasthep-curator/)
[![Documentation Status](https://readthedocs.org/projects/fasthep-curator/badge/?version=latest)](https://fasthep-curator.readthedocs.io/en/latest/)
[![Discussions](https://img.shields.io/static/v1?label=Discussions\&message=Ask\&color=blue\&logo=github)](https://github.com/FAST-HEP/fasthep/discussions)

<p align="center">
  <a href="https://github.com/FAST-HEP/fasthep">
    <picture>
      <source
        media="(prefers-color-scheme: dark)"
        srcset="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-white.png"
      >
      <source
        media="(prefers-color-scheme: light)"
        srcset="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-black.png"
      >
      <img
        alt="FAST-HEP"
        src="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-black.png"
        width="500"
      >
    </picture>
  </a>
</p>

`fasthep-curator` provides dataset inspection, metadata extraction, validation, and schema generation utilities for FAST-HEP workflows.

The Python import namespace is:

```python
import fasthep_curator
```

## Scope

`fasthep-curator` is responsible for:

* dataset inspection
* branch discovery
* schema generation
* metadata extraction
* validation helpers
* workflow diagnostics
* runtime error reporting helpers
* caching of inspection artifacts

It is the dataset and metadata management layer of the FAST-HEP ecosystem.

## Relationship to `fasthep-flow`

`fasthep-flow` provides:

* workflow compilation
* orchestration
* execution planning
* backend interfaces

`fasthep-curator` provides:

* dataset metadata
* source schemas
* validation utilities
* dataset inspection tooling
* diagnostics and reporting helpers

In practice, most HEP users will use both packages together.

## Recommended companion packages

* `fasthep-flow`

  * workflow language and execution engine

* `fasthep-carpenter`

  * HEP analysis transforms
  * histogramming
  * event processing

* `fasthep-render`

  * plotting
  * tables
  * reports

* `fasthep-cli`

  * the unified `fasthep` command-line interface

Alternatively, install the meta package:

```bash
pip install fasthep
```

## Installation

Install directly:

```bash
pip install fasthep-curator
```

Development environment:

```bash
pixi install
pixi run ci
```

## Minimal example

Example dataset inspection:

```yaml
datasets:
  DYJets:
    files:
      - /data/example.root
    source:
      type: root_tree
      tree: Events
```

Example metadata artifact:

```yaml
source_schema:
  events:
    pt: float
    eta: float
    phi: float
```

## Design principles

`fasthep-curator` focuses on:

* reproducible metadata
* reusable inspection artifacts
* declarative validation
* cached schema discovery
* workflow diagnostics
* experiment-agnostic interfaces where possible

The package intentionally separates dataset/metadata management from workflow orchestration and analysis execution.

## Documentation

Main FAST-HEP documentation:

* [https://fast-hep.github.io](https://fast-hep.github.io)

API documentation for this package:

* [https://fasthep-curator.readthedocs.io/en/latest/](https://fasthep-curator.readthedocs.io/en/latest/)

## Repository

Main FAST-HEP repository and project links:

* [https://github.com/FAST-HEP/fasthep](https://github.com/FAST-HEP/fasthep)

## Contributing

Contribution guidelines, development setup, and project-wide documentation are maintained centrally in the main FAST-HEP repository.

## Legacy branch

Earlier prototype implementations are preserved in legacy repositories and branches.

The current repository contains the split-package FAST-HEP architecture.

## Status

FAST-HEP is currently in active pre-alpha development.

Interfaces may evolve rapidly while the package split and stabilization work continues.
