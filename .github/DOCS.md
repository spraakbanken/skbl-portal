# Github config and workflows

In this folder there is configuration for codecoverage, dependabot and ci workflows.

This folder can be merged using a `--allow-unrelated-histories` merge strategy from <https://github.com/spraakbanken/python-uv-ci-conf> which provides a reasonably sensible base for writing your own ci on. By using this strategy the history of the CI repo is included in your repo, and future updates to the CI can be merged later.

The workflows in this folder requires a root Makefile with a couple of targets defined.
As base can the Makefile in <https://github.com/spraakbanken/python-uv-make-conf> be used.

## Publish

The `publish`-step in [release.yml](./workflows/release.yml) is configured to use the GitHub environment `release`, create that or change to your preferred environment.
To publish to PyPI you must also configure your Pypi-project settings to use Trusted Publisher Management, by setting repo, workflow and environment on PyPI.

To perform this merge run:

```shell
git remote add ci git@github.com:spraakbanken/python-uv-ci-conf.git
git fetch ci
git merge --allow-unrelated-histories ci/main
```

or add the remote as `git remote add ci https://github.com/spraakbanken/python-uv-ci-conf.git`

To later merge updates to this repo, just run:

```shell
git fetch ci
get merge ci/main
```

This setup is inspired by <https://github.com/jonhoo/rust-ci-conf>.
