#!/usr/bin/env python3
"""
Example demonstrating PSS to Zuspec IR translation
"""

from zuspec.fe.pss import Parser, AstToIrTranslator

# Example PSS code
pss_code = """
component Base {
    int base_value;
}

component MySystem : Base {
    int counter;
    bit[8] status;
    bit[16] control_reg;
    
    function void init() {
        return;
    }
    
    function void reset() {
        return;
    }
    
    function int add(int a, int b) {
        return a + b;
    }
    
    function int get_counter() {
        return 42;
    }
}

component pss_top {
    function void setup() {
        return;
    }
}
"""

def main():
    print("=" * 70)
    print("PSS to Zuspec IR Translation Example")
    print("=" * 70)
    print()
    
    # Parse PSS code
    print("Step 1: Parsing PSS code...")
    parser = Parser()
    parser.parses([("example.pss", pss_code)])
    
    # Link AST
    print("Step 2: Linking AST...")
    ast_root = parser.link()
    
    # Translate to IR
    print("Step 3: Translating to IR...")
    translator = AstToIrTranslator(debug=False)
    ctx = translator.translate(ast_root)
    
    # Check for errors
    if ctx.errors:
        print(f"\n⚠️  Translation errors: {len(ctx.errors)}")
        for err in ctx.errors:
            print(f"  - {err}")
        return
    
    print("✅ Translation successful!")
    print()
    
    # Display results
    print("=" * 70)
    print("Translated Components:")
    print("=" * 70)
    print()
    
    # Filter to just user components (skip built-in types)
    user_components = [name for name in ctx.type_map.keys() 
                      if name not in ['bool', 'int', 'string'] 
                      and not name.startswith('bit[') 
                      and not name.startswith('int[')]
    
    for comp_name in sorted(user_components):
        comp = ctx.type_map[comp_name]
        print(f"Component: {comp.name}")
        
        if comp.super:
            print(f"  Inherits from: {comp.super.ref_name if hasattr(comp.super, 'ref_name') else comp.super}")
        
        if comp.fields:
            print(f"  Fields ({len(comp.fields)}):")
            for field in comp.fields:
                field_type = field.datatype
                if hasattr(field_type, 'bits'):
                    type_str = f"int<{field_type.bits},{'signed' if field_type.signed else 'unsigned'}>"
                elif hasattr(field_type, 'name'):
                    type_str = field_type.name
                elif hasattr(field_type, 'ref_name'):
                    type_str = field_type.ref_name
                else:
                    type_str = type(field_type).__name__
                print(f"    - {field.name}: {type_str}")
        
        if comp.functions:
            print(f"  Functions ({len(comp.functions)}):")
            for func in comp.functions:
                return_str = func.returns.name if func.returns and hasattr(func.returns, 'name') else "void"
                param_count = len(func.args.args) if func.args else 0
                stmt_count = len(func.body) if func.body else 0
                print(f"    - {func.name}({param_count} params) → {return_str} [{stmt_count} stmts]")
        
        print()
    
    print("=" * 70)
    print("Statistics:")
    print("=" * 70)
    print(f"  Total types: {len(ctx.type_map)}")
    print(f"  User components: {len(user_components)}")
    print(f"  Built-in types: {len([k for k in ctx.type_map.keys() if k in ['bool', 'int', 'string'] or k.startswith('bit[') or k.startswith('int[')])}")
    print()

if __name__ == '__main__':
    main()
