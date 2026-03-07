# PSS to Zuspec IR Translation Examples

This directory contains examples demonstrating the PSS to Zuspec IR translation functionality.

## Running the Examples

### Prerequisites

1. Build the C++ extensions:
```bash
cd /home/mballance/projects/zuspec/zuspec-fe-pss
python setup.py build_ext --inplace
```

2. Set PYTHONPATH to include the necessary modules:
```bash
export PYTHONPATH=python:packages/zuspec-dataclasses/src
```

### Available Examples

#### ast_to_ir_demo.py

A comprehensive demonstration of the AST to IR translation pipeline.

**Usage:**
```bash
python examples/ast_to_ir_demo.py
```

**What it demonstrates:**
- Parsing PSS code
- Linking AST
- Translating to IR
- Component translation with inheritance
- Field translation
- Function translation
- Error handling
- Accessing translated IR structures

**Sample Output:**
```
======================================================================
PSS to Zuspec IR Translation Example
======================================================================

Step 1: Parsing PSS code...
Step 2: Linking AST...
Step 3: Translating to IR...
✅ Translation successful!

======================================================================
Translated Components:
======================================================================

Component: Base
  Fields (1):
    - base_value: int<32,signed>

Component: MySystem
  Inherits from: <TypeIdentifier>
  Fields (3):
    - counter: int<32,signed>
    - status: int<32,unsigned>
    - control_reg: int<32,unsigned>
  Functions (2):
    - init(0 params) → void
    - reset(0 params) → void

...
```

## Creating Your Own Examples

### Basic Template

```python
from zsp_parser import Parser, AstToIrTranslator

# Your PSS code
pss_code = """
component MyComponent {
    int field1;
    
    function void my_func() {
    }
}
"""

# Parse and translate
parser = Parser()
parser.parses([("example.pss", pss_code)])
ast_root = parser.link()

translator = AstToIrTranslator()
ctx = translator.translate(ast_root)

# Access results
my_comp = ctx.type_map["MyComponent"]
print(f"Component: {my_comp.name}")
print(f"Fields: {[f.name for f in my_comp.fields]}")
print(f"Functions: {[f.name for f in my_comp.functions]}")
```

### With Debug Logging

```python
# Enable parser debug logging
from zsp_parser.core import Factory
factory = Factory.inst()
factory.getDebugMgr().enable(True)

# Enable translator debug logging
translator = AstToIrTranslator(debug=True)
```

### Error Handling

```python
ctx = translator.translate(ast_root)

if ctx.errors:
    print("Translation errors occurred:")
    for error in ctx.errors:
        print(f"  - {error}")
        if error.location:
            print(f"    at {error.location}")
else:
    print("Translation successful!")
```

## Supported PSS Features

### Currently Supported ✅

- **Components**: Basic structure, inheritance
- **Fields**: Data fields with primitive types
- **Functions**: Declarations with parameters and return types
- **Types**: int, bool, string, bit[N], int[N]

### Not Yet Supported ⚠️

- **Function Bodies**: Statements and expressions
- **Constraints**: Dynamic and static constraints
- **Actions**: Action definitions
- **Advanced Fields**: Ports, exports, pools
- **Register Model**: Address spaces, registers

## See Also

- **Tests**: `tests/python/test_ast_to_ir.py` - Comprehensive test suite
- **Documentation**: `docs/implementation_plan.md` - Full implementation plan
- **Progress**: `docs/progress_summary.md` - Current status and roadmap
