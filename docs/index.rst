zuspec-fe-pss Documentation
===========================

`zuspec-fe-pss` is the pure-Python front end that translates PSS source into
Zuspec IR and runtime classes. Parsing, AST construction, and parser-facing CLI
functionality now live in the separate `pssparser` package.

Overview
--------

This package focuses on:

- loading PSS through `pssparser`
- translating parser AST nodes to Zuspec IR
- building runnable Python classes from that IR

Parser-specific documentation has moved to `packages/pssparser/docs`.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api
