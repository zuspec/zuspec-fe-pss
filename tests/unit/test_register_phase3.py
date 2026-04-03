"""
import pytest
#pytestmark = pytest.mark.skip(reason="ast_to_ir.py missing - needs to be recreated")
Unit tests for Register IR Phase 3 Implementation

Tests register functions and register group creation.
"""
import pytest
from zuspec.fe.pss import Parser
from zuspec.fe.pss.ast_to_ir import AstToIrTranslator
from zuspec.dataclasses import ir


class TestRegisterFunctions:
    """Test built-in register functions"""
    
    def parse_and_translate(self, pss_code: str):
        """Helper to parse PSS and translate to IR"""
        parser = Parser()
        parser.parses([("test.pss", pss_code)])
        sym_tree_root = parser.link()
        
        translator = AstToIrTranslator(debug=False)
        ctx = translator.translate(sym_tree_root)
        
        return ctx
    
    def test_register_has_functions(self):
        """Test that registers have built-in functions"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_field = my_regs.fields[0]
        r1_type = r1_field.datatype
        
        assert isinstance(r1_type, ir.DataTypeRegister)
        assert len(r1_type.functions) > 0
        
        # Check function names
        func_names = [f.name for f in r1_type.functions]
        assert "read" in func_names
        assert "write" in func_names
        assert "read_val" in func_names
        assert "write_val" in func_names
    
    def test_register_read_function(self):
        """Test read() function signature"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_type = my_regs.fields[0].datatype
        
        # Find read function
        read_func = next((f for f in r1_type.functions if f.name == "read"), None)
        assert read_func is not None
        
        # Check signature
        assert read_func.returns is not None
        assert isinstance(read_func.returns, ir.DataTypeInt)
        assert read_func.returns.bits == 32
        assert read_func.is_import is True
        assert read_func.is_target is True
    
    def test_register_write_function(self):
        """Test write() function signature"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[16], READONLY, 16> r2;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r2_type = my_regs.fields[0].datatype
        
        # Find write function
        write_func = next((f for f in r2_type.functions if f.name == "write"), None)
        assert write_func is not None
        
        # Check signature
        assert write_func.returns is None  # void return
        assert write_func.args is not None
        assert len(write_func.args.args) == 1
        assert write_func.args.args[0].arg == "r"
        # Note: annotation is None for simplified function args
        assert write_func.is_import is True
        assert write_func.is_target is True
    
    def test_register_read_val_function(self):
        """Test read_val() function signature"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[64]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_type = my_regs.fields[0].datatype
        
        # Find read_val function
        read_val_func = next((f for f in r1_type.functions if f.name == "read_val"), None)
        assert read_val_func is not None
        
        # Check signature - returns bit[SZ2]
        assert read_val_func.returns is not None
        assert isinstance(read_val_func.returns, ir.DataTypeInt)
        assert read_val_func.returns.bits == 64  # SZ2 parameter
        assert read_val_func.is_import is True
        assert read_val_func.is_target is True
    
    def test_register_write_val_function(self):
        """Test write_val() function signature"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[8], WRITEONLY, 8> r3;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r3_type = my_regs.fields[0].datatype
        
        # Find write_val function
        write_val_func = next((f for f in r3_type.functions if f.name == "write_val"), None)
        assert write_val_func is not None
        
        # Check signature - takes bit[SZ2]
        assert write_val_func.returns is None  # void
        assert write_val_func.args is not None
        assert len(write_val_func.args.args) == 1
        assert write_val_func.args.args[0].arg == "r"
        # Note: annotation is None for simplified function args
        assert write_val_func.is_import is True
        assert write_val_func.is_target is True
    
    def test_different_register_widths_have_different_functions(self):
        """Test that registers with different widths have appropriately typed functions"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[16]> r1;
    reg_c<bit[32]> r2;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_type = my_regs.fields[0].datatype
        r2_type = my_regs.fields[1].datatype
        
        # Check r1 (16-bit)
        r1_read = next(f for f in r1_type.functions if f.name == "read")
        assert r1_read.returns.bits == 16
        
        # Check r2 (32-bit)
        r2_read = next(f for f in r2_type.functions if f.name == "read")
        assert r2_read.returns.bits == 32


class TestRegisterGroup:
    """Test DataTypeRegisterGroup creation and functions"""
    
    def parse_and_translate(self, pss_code: str):
        """Helper to parse PSS and translate to IR"""
        parser = Parser()
        parser.parses([("test.pss", pss_code)])
        sym_tree_root = parser.link()
        
        translator = AstToIrTranslator(debug=False)
        ctx = translator.translate(sym_tree_root)
        
        return ctx
    
    def test_component_inheriting_reg_group_c(self):
        """Test that component : reg_group_c creates DataTypeRegisterGroup"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        assert isinstance(my_regs, ir.DataTypeRegisterGroup)
        assert my_regs.is_pure is True
    
    def test_register_group_has_functions(self):
        """Test that register groups have built-in functions"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        assert len(my_regs.functions) >= 2  # At least get_offset functions
        
        func_names = [f.name for f in my_regs.functions]
        assert "get_offset_of_instance" in func_names
        assert "get_offset_of_instance_array" in func_names
    
    def test_register_group_get_offset_function(self):
        """Test get_offset_of_instance function signature"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        
        # Find get_offset_of_instance function
        offset_func = next((f for f in my_regs.functions if f.name == "get_offset_of_instance"), None)
        assert offset_func is not None
        
        # Check signature
        assert offset_func.returns is not None
        assert isinstance(offset_func.returns, ir.DataTypeInt)
        assert offset_func.returns.bits == 64
        assert offset_func.args is not None
        assert len(offset_func.args.args) == 1
        assert offset_func.args.args[0].arg == "name"
        # Note: annotation is None for simplified function args
    
    def test_register_group_contains_registers(self):
        """Test that register group can contain register fields"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
    reg_c<bit[16]> r2;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        assert isinstance(my_regs, ir.DataTypeRegisterGroup)
        assert len(my_regs.fields) == 2
        
        # Both fields should be DataTypeRegister
        assert isinstance(my_regs.fields[0].datatype, ir.DataTypeRegister)
        assert isinstance(my_regs.fields[1].datatype, ir.DataTypeRegister)
    
    def test_normal_component_not_register_group(self):
        """Test that normal components don't become register groups"""
        pss_code = """
component normal_comp {
    bit[32] field1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        normal_comp = ctx.type_map["normal_comp"]
        assert isinstance(normal_comp, ir.DataTypeComponent)
        assert not isinstance(normal_comp, ir.DataTypeRegisterGroup)


class TestRegisterFunctionImportTarget:
    """Test that register functions are marked as import target"""
    
    def parse_and_translate(self, pss_code: str):
        """Helper to parse PSS and translate to IR"""
        parser = Parser()
        parser.parses([("test.pss", pss_code)])
        sym_tree_root = parser.link()
        
        translator = AstToIrTranslator(debug=False)
        ctx = translator.translate(sym_tree_root)
        
        return ctx
    
    def test_all_register_access_functions_are_import_target(self):
        """Test that read/write functions are marked import target"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_type = my_regs.fields[0].datatype
        
        # Check all access functions
        for func_name in ["read", "write", "read_val", "write_val"]:
            func = next((f for f in r1_type.functions if f.name == func_name), None)
            assert func is not None, f"Function {func_name} not found"
            assert func.is_import is True, f"Function {func_name} should be import"
            assert func.is_target is True, f"Function {func_name} should be target"
    
    def test_get_handle_not_import_target(self):
        """Test that get_handle is not marked import target (Zuspec extension)"""
        pss_code = """
import addr_reg_pkg::*;

component my_regs : reg_group_c {
    reg_c<bit[32]> r1;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_regs = ctx.type_map["my_regs"]
        r1_type = my_regs.fields[0].datatype
        
        # get_handle might not exist if addr_handle_t not in context
        get_handle = next((f for f in r1_type.functions if f.name == "get_handle"), None)
        if get_handle:
            assert get_handle.is_import is False
            assert get_handle.is_target is False


class TestRegisterGroupIntegration:
    """Integration tests for register groups with multiple registers"""
    
    def parse_and_translate(self, pss_code: str):
        """Helper to parse PSS and translate to IR"""
        parser = Parser()
        parser.parses([("test.pss", pss_code)])
        sym_tree_root = parser.link()
        
        translator = AstToIrTranslator(debug=False)
        ctx = translator.translate(sym_tree_root)
        
        return ctx
    
    def test_complex_register_group(self):
        """Test register group with multiple different register types"""
        pss_code = """
import addr_reg_pkg::*;

struct csr_s : packed_s<> {
    bit[1] en;
    bit[1] rdy;
}

component my_periph : reg_group_c {
    reg_c<bit[32]>          STATUS;
    reg_c<bit[32]>          CONTROL;
    reg_c<csr_s, READWRITE, 32> CSR;
    reg_c<bit[16], READONLY, 16> VERSION;
}
"""
        ctx = self.parse_and_translate(pss_code)
        
        my_periph = ctx.type_map["my_periph"]
        assert isinstance(my_periph, ir.DataTypeRegisterGroup)
        assert len(my_periph.fields) == 4
        
        # Check all fields are registers
        for field in my_periph.fields:
            assert isinstance(field.datatype, ir.DataTypeRegister)
        
        # Check STATUS register
        status = my_periph.fields[0]
        assert status.name == "STATUS"
        assert status.datatype.size_bits == 32
        assert len(status.datatype.functions) >= 4
        
        # Check VERSION register (READONLY)
        version = my_periph.fields[3]
        assert version.name == "VERSION"
        assert version.datatype.access_mode == "READONLY"
        assert version.datatype.size_bits == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
