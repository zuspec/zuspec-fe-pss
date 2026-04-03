API
===

Top-Level Package
=================

The public package entrypoint is `zuspec.fe.pss`.

Primary exports
===============

- `Parser`
- `ParseException`
- `load_pss`
- `load_pss_files`
- `PssTranslationError`
- `AstToIrTranslator`
- `AstToIrContext`
- `IrToRuntimeBuilder`
- `ClassRegistry`

Responsibilities
================

`zuspec-fe-pss` is responsible for:

- obtaining parser ASTs through `pssparser`
- translating parser AST nodes into Zuspec IR
- building executable Python runtime classes from the translated IR

Parser-specific APIs such as grammar coverage, AST structure internals, and the
parser CLI are documented in the sibling `packages/pssparser/docs` tree.

Translation Modules
===================

`zuspec.fe.pss.ast_to_ir`
-------------------------

Contains the AST-to-IR translation pipeline.

Key public types:

- `AstToIrTranslator`
- `AstToIrContext`

`zuspec.fe.pss.ir_to_runtime`
-----------------------------

Contains the IR-to-runtime conversion layer.

Key public types:

- `IrToRuntimeBuilder`
- `ClassRegistry`

Typical Usage
=============

.. code-block:: python

   from zuspec.fe.pss import Parser
   from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
   from zuspec.fe.pss.ir_to_runtime import IrToRuntimeBuilder

   parser = Parser()
   parser.parses([("inline.pss", "struct S { int a; }")])
   root = parser.link()

   ctx = AstToIrTranslator().translate(root)
   runtime = IrToRuntimeBuilder(ctx).build()
