# fasthep-curator

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

<!-- SPHINX-START -->

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/FAST-HEP/fasthep-curator/workflows/CI/badge.svg
[actions-link]:             https://github.com/FAST-HEP/fasthep-curator/actions

[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/FAST-HEP/fasthep/discussions
[pypi-link]:                https://pypi.org/project/fasthep-curator/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/fasthep-curator
[pypi-version]:             https://img.shields.io/pypi/v/fasthep-curator
[rtd-badge]:                https://readthedocs.org/projects/fasthep-curator/badge/?version=latest
[rtd-link]:                 https://fasthep-curator.readthedocs.io/en/latest/?badge=latest

[fasthep-logo]: https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-black.png
[fasthep-link]: https://github.com/fast-hep/fasthep
<!-- prettier-ignore-end -->

[![fasthep][fasthep-logo]][fasthep-link]

## Introduction

> [!NOTE]
>
> `fasthep-curator` is a port of
> [fast-curator](https://github.com/FAST-HEP/fast-curator) to modern Python and
> `uproot` versions as well as type hint support. It is not a drop-in
> replacement, but it is designed to be compatible with the original
> `fast-curator` API. Should you have any questions or issues, please
> [open an issue](https://github.com/FAST-HEP/fasthep-curator/issues).

**fasthep-curator** is a Python package that provides a set of components for
building data processing pipelines. It is designed to work with the
**fasthep-flow** library, which provides a framework for declaring and creating
data processing workflows. Historically, **fasthep-curator** was limited to ROOT
Trees as input and Pandas DataFrames as output. However, it has now been
extended to support many data formats.

## Documentation

his project is in early development. The documentation is available at
[fasthep-curator.readthedocs.io](https://fasthep-curator.readthedocs.io/en/latest/)
and contains mostly fictional features. The most useful information can be found
in the [FAST-HEP documentation](https://fast-hep.github.io/). It describes the
current status and plans for the FAST-HEP projects, including `fasthep-curator`
(see [Developer's Corner](https://fast-hep.github.io/developers-corner/)).

## Installation

You can install `fasthep-curator` using `pip`:

```bash
pip install fasthep-curator
```

## Contributing

You had a look and are interested to contribute? That's great! There are three
main ways to contribute to this project:

1. Head to the [issues tab](https://github.com/FAST-HEP/fasthep-curator/issues)
   and see if there is anything you can help with.
2. If you have a new feature in mind,
   [please open an issue](https://github.com/FAST-HEP/fasthep-curator/issues/new)
   first to discuss it. This way we can ensure that your work is not in vain.
3. You can also help by improving the documentation or fixing typos.

Once you have something to work on, you can have a look at the
[contributing guidelines](https://github.com/FAST-HEP/fasthep-curator/blob/main/LICENSE/.github/CONTRIBUTING.md).
It contains recommendations for setting up your development environment,
testing, and more (compiled by the Scientific Python Community).

> [!IMPORTANT]
>
> How you customise your development environment is up to you. You like
> [uv](https://github.com/astral-sh/uv)? Be our guest. You prefer
> [nox](https://nox.thea.codes/en/stable/)? That's fine too. You want to use
> <your custom workflow>? Go ahead. We are happy as long as you are happy.
> Ideally you should be able to run `pylint`, `pytest`, and the pre-commit
> hooks. If you can do that, you are good to go.

## License

This project is licensed under the terms of the Apache 2.0 license. See
[LICENSE](https://github.com/FAST-HEP/fasthep-curator/blob/main/LICENSE) for
more details.

## Acknowledgements

Special thanks to the gracious help of FAST-HEP contributors:

<!-- readme: collaborators,contributors -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/kreczko">
                    <img src="https://avatars.githubusercontent.com/u/1213276?v=4" width="100;" alt="kreczko"/>
                    <br />
                    <sub><b>Luke Kreczko</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: collaborators,contributors -end -->

## Previous iterations of this software

This software is a continuation of the work done in the
[fasthep-curator](https://github.com/FAST-HEP/fasthep-curator/tree/kreczko-1.0.0a1)
and [fast-curator](https://github.com/FAST-HEP/fast-curator) repositories. The
original code was developed by [Ben Krikler](https://github.com/benkrikler) and
has been adapted and improved by
[various collaborators](https://github.com/FAST-HEP/fast-curator/graphs/contributors).
The new version of the software is designed to be more flexible and extensible,
allowing users to easily create custom data processing pipelines.

Part of the development of this software was funded by the
[IRIS Digital Assets grant](https://www.iris.ac.uk/).
