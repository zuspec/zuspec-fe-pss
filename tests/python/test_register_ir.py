"""
Unit tests for Register IR Phase 1 Implementation

Tests the basic IR data structures for registers and template parameters.
"""
import pytest
from zuspec.dataclasses import ir


class TestTemplateParameters:
    """Test template parameter classes"""
    
    def test_template_param_type(self):
        """Test type template parameter"""
        param = ir.TemplateParamType(
            name="R",
            kind=ir.TemplateParamKind.TYPE,
            constraint_type=None,
            default_value=None
        )
        assert param.name == "R"
        assert param.kind == ir.TemplateParamKind.TYPE
        assert param.constraint_type is None
        assert param.default_value is None
    
    def test_template_param_value(self):
        """Test value template parameter"""
        int_type = ir.DataTypeInt(name="int", bits=32, signed=True)
        param = ir.TemplateParamValue(
            name="SZ2",
            kind=ir.TemplateParamKind.VALUE,
            value_type=int_type,
            default_value=None
        )
        assert param.name == "SZ2"
        assert param.kind == ir.TemplateParamKind.VALUE
        assert param.value_type == int_type
    
    def test_template_param_enum(self):
        """Test enum template parameter"""
        enum_type = ir.DataTypeEnum(name="reg_access")
        param = ir.TemplateParamEnum(
            name="ACC",
            kind=ir.TemplateParamKind.ENUM,
            enum_type=enum_type,
            default_value="READWRITE"
        )
        assert param.name == "ACC"
        assert param.kind == ir.TemplateParamKind.ENUM
        assert param.enum_type == enum_type
        assert param.default_value == "READWRITE"


class TestTemplateArguments:
    """Test template argument classes"""
    
    def test_template_arg_type(self):
        """Test type argument"""
        bit32_type = ir.DataTypeInt(name="bit", bits=32, signed=False)
        arg = ir.TemplateArgType(
            param_name="R",
            type_value=bit32_type
        )
        assert arg.param_name == "R"
        assert arg.type_value == bit32_type
        assert arg.type_value.bits == 32
    
    def test_template_arg_value(self):
        """Test value argument"""
        value_expr = ir.ExprConstant(value=32)
        arg = ir.TemplateArgValue(
            param_name="SZ2",
            value_expr=value_expr
        )
        assert arg.param_name == "SZ2"
        assert arg.value_expr == value_expr
    
    def test_template_arg_enum(self):
        """Test enum argument"""
        arg = ir.TemplateArgEnum(
            param_name="ACC",
            enum_value="READWRITE"
        )
        assert arg.param_name == "ACC"
        assert arg.enum_value == "READWRITE"


class TestParameterizedTypes:
    """Test parameterized and specialized types"""
    
    def test_data_type_parameterized(self):
        """Test parameterized type (uninstantiated template)"""
        # Create reg_c template
        r_param = ir.TemplateParamType(
            name="R",
            kind=ir.TemplateParamKind.TYPE
        )
        acc_param = ir.TemplateParamEnum(
            name="ACC",
            kind=ir.TemplateParamKind.ENUM,
            enum_type=ir.DataTypeEnum(name="reg_access"),
            default_value="READWRITE"
        )
        sz_param = ir.TemplateParamValue(
            name="SZ2",
            kind=ir.TemplateParamKind.VALUE,
            value_type=ir.DataTypeInt(name="int", bits=32, signed=True)
        )
        
        reg_c_template = ir.DataTypeParameterized(
            name="reg_c",
            template_params=[r_param, acc_param, sz_param]
        )
        
        assert reg_c_template.name == "reg_c"
        assert len(reg_c_template.template_params) == 3
        assert reg_c_template.template_params[0].name == "R"
        assert reg_c_template.template_params[1].name == "ACC"
        assert reg_c_template.template_params[2].name == "SZ2"
    
    def test_data_type_specialized(self):
        """Test specialized type with get_template_arg methods"""
        # Create base template
        reg_c_template = ir.DataTypeParameterized(
            name="reg_c",
            template_params=[]
        )
        
        # Create template arguments
        r_arg = ir.TemplateArgType(
            param_name="R",
            type_value=ir.DataTypeInt(name="bit", bits=32, signed=False)
        )
        acc_arg = ir.TemplateArgEnum(
            param_name="ACC",
            enum_value="WRITEONLY"
        )
        sz_arg = ir.TemplateArgValue(
            param_name="SZ2",
            value_expr=ir.ExprConstant(value=32)
        )
        
        specialized = ir.DataTypeSpecialized(
            name="reg_c_bit32_WRITEONLY_32",
            base_template=reg_c_template,
            template_args=[r_arg, acc_arg, sz_arg],
            specialized_name="reg_c_bit32_WRITEONLY_32"
        )
        
        # Test get_template_arg
        r_retrieved = specialized.get_template_arg("R")
        assert r_retrieved is not None
        assert r_retrieved.param_name == "R"
        assert isinstance(r_retrieved, ir.TemplateArgType)
        
        # Test get_template_arg_value
        r_type = specialized.get_template_arg_value("R")
        assert isinstance(r_type, ir.DataTypeInt)
        assert r_type.bits == 32
        
        acc_value = specialized.get_template_arg_value("ACC")
        assert acc_value == "WRITEONLY"
        
        sz_expr = specialized.get_template_arg_value("SZ2")
        assert isinstance(sz_expr, ir.ExprConstant)
        
        # Test non-existent parameter
        assert specialized.get_template_arg("NONEXISTENT") is None
        assert specialized.get_template_arg_value("NONEXISTENT") is None


class TestRegisterTypes:
    """Test register-specific IR types"""
    
    def test_simple_register_type(self):
        """Test reg_c<bit[32]>"""
        reg = ir.DataTypeRegister(
            name="reg_c_bit32_READWRITE_32",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32
        )
        
        assert reg.name == "reg_c_bit32_READWRITE_32"
        assert reg.register_value_type.bits == 32
        assert reg.access_mode == "READWRITE"
        assert reg.size_bits == 32
        assert reg.is_pure is True
    
    def test_parameterized_register(self):
        """Test reg_c<MyStruct, READONLY, 64>"""
        # Create packed struct
        struct_type = ir.DataTypeStruct(
            name="csr_s",
            super=None,
            fields=[
                ir.Field(name="en", datatype=ir.DataTypeInt(name="bit", bits=1, signed=False)),
                ir.Field(name="rdy", datatype=ir.DataTypeInt(name="bit", bits=1, signed=False)),
            ]
        )
        
        reg = ir.DataTypeRegister(
            name="reg_c_csr_s_READONLY_64",
            super=None,
            register_value_type=struct_type,
            access_mode="READONLY",
            size_bits=64
        )
        
        assert reg.register_value_type.name == "csr_s"
        assert reg.access_mode == "READONLY"
        assert reg.size_bits == 64
        assert len(reg.register_value_type.fields) == 2
    
    def test_register_group(self):
        """Test reg_group_c with multiple registers"""
        # Create registers
        r1 = ir.DataTypeRegister(
            name="r1",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32
        )
        r2 = ir.DataTypeRegister(
            name="r2",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32
        )
        
        # Create register group
        reg_group = ir.DataTypeRegisterGroup(
            name="my_regs",
            super=None,
            fields=[
                ir.Field(name="r1", datatype=r1),
                ir.Field(name="r2", datatype=r2),
            ],
            offset_map={
                "r1": 0x0,
                "r2": 0x4,
            }
        )
        
        assert reg_group.name == "my_regs"
        assert len(reg_group.fields) == 2
        assert reg_group.offset_map["r1"] == 0x0
        assert reg_group.offset_map["r2"] == 0x4
        assert reg_group.is_pure is True
    
    def test_register_functions(self):
        """Test register access functions"""
        # Create a register with functions
        reg = ir.DataTypeRegister(
            name="test_reg",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32,
            functions=[
                ir.Function(
                    name="read",
                    returns=ir.DataTypeInt(name="bit", bits=32, signed=False),
                    is_import=True,
                    is_target=True
                ),
                ir.Function(
                    name="write",
                    is_import=True,
                    is_target=True
                ),
            ]
        )
        
        assert len(reg.functions) == 2
        assert reg.functions[0].name == "read"
        assert reg.functions[0].is_import is True
        assert reg.functions[0].is_target is True
        assert reg.functions[1].name == "write"


class TestParameterRetrieval:
    """Test different access patterns for template parameters"""
    
    def test_parameter_retrieval_direct(self):
        """Test direct access to register parameters"""
        reg = ir.DataTypeRegister(
            name="test_reg",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32
        )
        
        # Direct field access
        assert reg.register_value_type.bits == 32
        assert reg.access_mode == "READWRITE"
        assert reg.size_bits == 32
    
    def test_parameter_retrieval_via_method(self):
        """Test convenience method for parameter access"""
        reg = ir.DataTypeRegister(
            name="test_reg",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=64, signed=False),
            access_mode="READONLY",
            size_bits=64
        )
        
        # Convenience method access
        r_type = reg.get_register_param('R')
        assert r_type.bits == 64
        
        assert reg.get_register_param('ACC') == "READONLY"
        assert reg.get_register_param('SZ2') == 64
        assert reg.get_register_param('SZ') == 64  # Alternative name
        
        # Non-existent parameter
        assert reg.get_register_param('INVALID') is None
    
    def test_parameter_retrieval_from_template_args(self):
        """Test generic template argument access"""
        # Setup template args
        args = [
            ir.TemplateArgType(
                param_name='R',
                type_value=ir.DataTypeInt(name="bit", bits=32, signed=False)
            ),
            ir.TemplateArgEnum(
                param_name='ACC',
                enum_value='WRITEONLY'
            ),
            ir.TemplateArgValue(
                param_name='SZ2',
                value_expr=ir.ExprConstant(value=32)
            )
        ]
        
        reg = ir.DataTypeRegister(
            name="test_reg",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="WRITEONLY",
            size_bits=32,
            template_args=args
        )
        
        # Generic access via template_args
        r_arg = reg.template_args[0]
        assert r_arg.param_name == 'R'
        assert isinstance(r_arg, ir.TemplateArgType)
        assert r_arg.type_value.bits == 32
        
        acc_arg = reg.template_args[1]
        assert acc_arg.param_name == 'ACC'
        assert isinstance(acc_arg, ir.TemplateArgEnum)
        assert acc_arg.enum_value == 'WRITEONLY'
        
        sz_arg = reg.template_args[2]
        assert sz_arg.param_name == 'SZ2'
        assert isinstance(sz_arg, ir.TemplateArgValue)
    
    def test_struct_based_register_params(self):
        """Test register with packed struct value type"""
        # Create packed struct type
        struct_type = ir.DataTypeStruct(
            name="csr_s",
            super=None,
            fields=[
                ir.Field(name="en", datatype=ir.DataTypeInt(name="bit", bits=1, signed=False)),
                ir.Field(name="rdy", datatype=ir.DataTypeInt(name="bit", bits=1, signed=False)),
            ]
        )
        
        # Register with struct type
        reg = ir.DataTypeRegister(
            name="CSR",
            super=None,
            register_value_type=struct_type,
            access_mode="READWRITE",
            size_bits=32
        )
        
        # Verify parameters
        assert reg.register_value_type.name == "csr_s"
        assert len(reg.register_value_type.fields) == 2
        assert reg.size_bits == 32  # Explicit size, larger than struct
        
        # Tool can extract field info
        field_names = [f.name for f in reg.register_value_type.fields]
        assert "en" in field_names
        assert "rdy" in field_names


class TestSystemRDLCompatibility:
    """Test SystemRDL compatibility features"""
    
    def test_systemrdl_width_compatibility(self):
        """Test SystemRDL power-of-2 width computation"""
        test_cases = [
            (24, 32),   # 24 bits -> 32 (next power of 2)
            (32, 32),   # 32 bits -> 32 (already power of 2)
            (33, 64),   # 33 bits -> 64
            (7, 8),     # 7 bits -> 8 (minimum)
            (8, 8),     # 8 bits -> 8
            (16, 16),   # 16 bits -> 16
            (17, 32),   # 17 bits -> 32
        ]
        
        for pss_width, expected_rdl_width in test_cases:
            reg = ir.DataTypeRegister(
                name=f"test_reg_{pss_width}",
                super=None,
                register_value_type=ir.DataTypeInt(name="bit", bits=pss_width, signed=False),
                access_mode="READWRITE",
                size_bits=pss_width
            )
            
            computed_width = reg.compute_systemrdl_width()
            assert computed_width == expected_rdl_width, \
                f"For {pss_width} bits, expected {expected_rdl_width}, got {computed_width}"
    
    def test_systemrdl_fields(self):
        """Test SystemRDL-specific fields"""
        reg = ir.DataTypeRegister(
            name="test_reg",
            super=None,
            register_value_type=ir.DataTypeInt(name="bit", bits=32, signed=False),
            access_mode="READWRITE",
            size_bits=32,
            systemrdl_regwidth=32,
            systemrdl_accesswidth=32
        )
        
        assert reg.systemrdl_regwidth == 32
        assert reg.systemrdl_accesswidth == 32


class TestFunctionImportFlags:
    """Test function import/target/solve flags"""
    
    def test_import_target_function(self):
        """Test import target function flags"""
        func = ir.Function(
            name="read",
            returns=ir.DataTypeInt(name="bit", bits=32, signed=False),
            is_import=True,
            is_target=True,
            is_solve=False
        )
        
        assert func.is_import is True
        assert func.is_target is True
        assert func.is_solve is False
    
    def test_import_solve_function(self):
        """Test import solve function flags"""
        func = ir.Function(
            name="set_handle",
            is_import=True,
            is_target=False,
            is_solve=True
        )
        
        assert func.is_import is True
        assert func.is_target is False
        assert func.is_solve is True
    
    def test_regular_function(self):
        """Test regular function (no import flags)"""
        func = ir.Function(
            name="compute",
            returns=ir.DataTypeInt(name="int", bits=32, signed=True)
        )
        
        assert func.is_import is False
        assert func.is_target is False
        assert func.is_solve is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
