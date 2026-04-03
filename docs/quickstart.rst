Quickstart
==========

Installing
==========

`zuspec-fe-pss` depends on:

- `pssparser` for parsing and AST construction
- `zuspec-dataclasses` for IR and runtime support

In this workspace, both dependencies are provided through the managed
environment loaded by `direnv`.

Using `load_pss`
================

The simplest entrypoint is `load_pss`, which parses PSS text, translates the
AST to Zuspec IR, and returns a registry of generated Python classes.

.. code-block:: python

   from zuspec.fe.pss import load_pss

   ns = load_pss("""
   struct Packet {
       rand bit[8] addr;
   }
   """)

   pkt = ns.Packet()

Using `Parser` Directly
=======================

If you need direct control over parsing and linking, import `Parser` from
`zuspec.fe.pss`. The implementation is provided by `pssparser`.

.. code-block:: python

   from zuspec.fe.pss import Parser

   parser = Parser()
   parser.parses([(
       "inline.pss",
       """
       component pss_top {
           action A { }
       }
       """
   )])

   root = parser.link()

Translating To IR
=================

For lower-level access to the translation pipeline:

.. code-block:: python

   from zuspec.fe.pss import Parser
   from zuspec.fe.pss.ast_to_ir import AstToIrTranslator

   parser = Parser()
   parser.parses([("inline.pss", "struct S { int a; }")])
   root = parser.link()

   ctx = AstToIrTranslator().translate(root)
   assert not ctx.errors

Parser Documentation
====================

Parser- and AST-specific documentation now lives in the sibling
`packages/pssparser/docs` tree.
