# llmoxie-analysis

Home to the llmoxie data analysis package

## Prerequisites

This project uses [Pixi](https://pixi.sh) for dependency management and task
execution. Install Pixi by following the
[installation instructions](https://pixi.sh/latest/#installation).

## Getting Started

### Installation

Install dependencies:

```bash
# Install dependencies (Pixi will automatically create the environment)
pixi install
```

### Onboarding

For first-time setup, use the onboarding environment to configure your
development environment:

```bash
pixi run -e onboard onboard
```

This will:

- Install pre-commit hooks in your git repository
- Set up shell completion for ssec-cli
- Run the SSEC onboarding process

## Project Structure

This project is organized using Pixi features for modular dependency management:

- **`pre-commit`**: Code quality and consistency checks
- **`gh-cli`**: GitHub CLI for repository interactions
- **`docs`**: MkDocs Material for building and previewing the documentation site
- **`onboard`**: Tools for project onboarding and setup

## Available Environments

- **`default`**: Standard development environment with pre-commit hooks, GitHub
  CLI, and documentation tooling
- **`onboard`**: Extended environment including onboarding tools

## Development

### Using Different Environments

Switch between environments as needed:

```bash
# Use default environment
pixi shell

# Use onboard environment
pixi shell -e onboard
```

### Adding Dependencies

Edit `pixi.toml` to add new dependencies:

```toml
[dependencies]
your-package = ">=1.0.0"
```

Then run:

```bash
pixi install
```

or

Directly add packages (this will edit the pixi toml and install):

```bash
pixi add your-package
```

## Documentation

The documentation site is plain Markdown under [`docs/`](docs/), built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and configured
in [`mkdocs.yml`](mkdocs.yml).

```bash
pixi run docs-serve    # live reload at http://127.0.0.1:8000
pixi run docs-build    # build into site/, failing on any warning
```

To add a page, create a Markdown file under `docs/` and list it in the `nav:`
section of `mkdocs.yml`.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of
conduct and the process for submitting pull requests. If you use AI tools while
contributing, read the [AI Policy](AI_POLICY.md) first: it covers disclosure,
review responsibility, and how to credit AI assistance in commits.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE)
file.
