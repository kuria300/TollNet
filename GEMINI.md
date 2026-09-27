# TollNet

TollNet is a Python SDK providing a compute-toll gateway for AI agents.

## Architecture & Code Organization

- **Package Structure**: All core library code must be organized into separate, modular files under a `tollnet/` folder (e.g., `src/tollnet/`). Avoid large monolithic files; each module should have a focused single responsibility.
- **Design Pattern**: Strictly follow the pattern of Abstract Base Classes (ABCs) paired with concrete implementations:
  - Define interfaces and contracts using Python's `abc.ABC` and `@abstractmethod`.
  - Provide modular, pluggable concrete implementations that extend those ABCs.
  - Favor composition and interface segregation over tight coupling.

## Development & Coding Rules

- **Type Hints**: Always use complete, strict type hints across all code (function arguments, return types, class attributes). Avoid untyped definitions (`Any` should be avoided unless strictly necessary).
- **Docstrings**: Write descriptive docstrings for every class, method, function, and module. Explain parameters, return types, raised exceptions, and usage semantics.
- **Modularity**: Break down components into clear submodules (e.g., interfaces, clients, models, middleware, protocols) within `tollnet/`.
