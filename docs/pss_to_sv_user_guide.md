# PSS to SystemVerilog User Guide

## Quick Start

### From Python

```python
from zuspec.fe.pss import generate_sv

files = generate_sv("""
    component top_c {
        action hello {
            exec body { }
        }
    }
""", output_dir="./sv_out")

print("Generated:", [f.name for f in files])
```

### From PSS files

```python
from zuspec.fe.pss import generate_sv_files

files = generate_sv_files(
    ["dma.pss", "top.pss"],
    output_dir="./sv_out",
)
```

### Compiling and simulating

```bash
# VCS
vcs -sverilog -f sv_out/zsp_filelist.f -o simv && ./simv

# Questa/ModelSim
vlog -f sv_out/zsp_filelist.f && vsim -c zsp_test_top -do "run -all"

# Xcelium
xrun -f sv_out/zsp_filelist.f

# Verilator (compile check only -- limited class support)
verilator --sv --lint-only -f sv_out/zsp_filelist.f
```

---

## API Reference

### generate_sv()

```python
def generate_sv(
    pss_text: str,
    output_dir: str,
    *,
    multi_file: bool = True,
    comp_type: str = None,
    root_action_type: str = None,
    import_if_type: str = None,
    import_if_driver: str = None,
    watchdog_ns: int = 0,
) -> List[Path]
```

Parse PSS source text and generate SystemVerilog files.

**Parameters:**
- `pss_text` -- PSS source as a string.
- `output_dir` -- Directory to write generated files.
- `multi_file` -- When True (default), output is split into separate files per category. When False, all SV is written to a single `zsp_pkg.sv`.
- `comp_type` -- Top-level component class name (enables top module generation).
- `root_action_type` -- Root action class name (enables top module generation).
- `import_if_type` -- Import interface class name for the top module.
- `import_if_driver` -- Driver class name to instantiate in the top module.
- `watchdog_ns` -- Deadlock watchdog timeout in nanoseconds (0 disables).

**Returns:** List of `Path` objects for all written files.

### generate_sv_files()

Same as `generate_sv()` but accepts a list of `.pss` file paths instead of inline text.

---

## Output File Descriptions

| File | Contents |
|------|----------|
| `zsp_rt_pkg.sv` | Runtime library: base classes (`zsp_component`, `zsp_action`, `zsp_resource`, etc.), parameterized pools, trace macros |
| `zsp_pkg.sv` | Enums, struct/buffer/stream/state classes, forward declarations |
| `zsp_import_if.sv` | Virtual classes with `pure virtual` task/function declarations for each component's import functions |
| `zsp_components.sv` | Component class hierarchy with constructors, sub-component fields, pool fields |
| `zsp_actions.sv` | Action classes with `rand` fields, constraints, `body()` tasks |
| `zsp_activities.sv` | Compound action activity tasks (when separated from actions) |
| `zsp_top.sv` | Top-level `module zsp_test_top` with component construction, root action execution, seed control |
| `zsp_filelist.f` | Simulator file list in compilation order |

The file list (`zsp_filelist.f`) lists files in dependency order: runtime first, then types, imports, components, actions, and finally the top module.

---

## Import Function Implementation

PSS `import` functions declare interfaces that the generated SV code calls but does not implement. You must provide an implementation class.

### PSS source

```pss
component dma_c {
    function void do_transfer(bit[32] src, bit[16] len);
}
```

### Generated virtual class (in `zsp_import_if.sv`)

```systemverilog
virtual class dma_c_import_if;
    pure virtual task do_transfer(input bit [31:0] src, input bit [15:0] len);
endclass
```

### Your implementation

```systemverilog
class my_dma_driver extends dma_c_import_if;
    virtual task do_transfer(input bit [31:0] src, input bit [15:0] len);
        // Drive DUT signals here
        @(posedge clk);
        dut.src_addr <= src;
        dut.length <= len;
        dut.start <= 1;
        @(posedge clk);
        dut.start <= 0;
        wait(dut.done);
    endtask
endclass
```

### Wiring in the top module

Pass `import_if_driver="my_dma_driver"` and `import_if_type="dma_c_import_if"` to `generate_sv()`, or manually wire it in a custom top module.

---

## Seed Control and Reproducibility

The generated top module reads a seed from the simulator command line:

```bash
./simv +zsp_seed=12345
```

If `+zsp_seed` is not provided, the default seed is 42. The seed is passed to `$urandom()` for reproducible randomization. All `std::randomize()` calls use the simulator's built-in seeding, which is controlled by the simulator's own seed mechanisms.

---

## Trace Verbosity Control

The runtime library provides trace macros controlled by `zsp_rt_verbosity`:

| Level | Output |
|-------|--------|
| 0 | Silent -- no trace output |
| 1 | Action traversals (`ZSP_TRACE_ACTION`) |
| 2 | Resource operations (`ZSP_TRACE_RESOURCE`) |

Set at simulation time:

```bash
./simv +zsp_verbosity=2
```

Or set in the generated code / your testbench:

```systemverilog
zsp_rt_pkg::zsp_rt_verbosity = 2;
```

---

## Simulator Compatibility

| Simulator | Status | Notes |
|-----------|--------|-------|
| VCS | Supported | Full `std::randomize`, `fork/join`, `mailbox` support |
| Questa | Supported | Full support |
| Xcelium | Supported | Full support |
| Verilator | Limited | No `std::randomize` or `mailbox`; compile-check only |
| Icarus Verilog | Limited | No class support; not usable for generated code |

The generated SV uses IEEE 1800-2017 features: classes with `rand` fields, `constraint` blocks, `fork`/`join`, `mailbox`, `semaphore`, and `std::randomize`.

---

## UVM Integration

For UVM-based environments, wrap the generated code in a UVM test:

```systemverilog
class zsp_uvm_test extends uvm_test;
    `uvm_component_utils(zsp_uvm_test)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
        phase.raise_objection(this);

        my_dma_driver drv = new("drv", this);
        dma_c_import_if imp = new();
        pss_top pss = new("pss", null);
        pss.import_if = imp;

        begin
            root_action_t root = new();
            root.comp = pss;
            root.pre_solve();
            if (!root.randomize()) $fatal(1, "randomize failed");
            root.post_solve();
            root.activity();
        end

        phase.drop_objection(this);
    endtask
endclass
```

The generated files can be added to your UVM compilation alongside your existing testbench. The `zsp_test_top` module can be excluded when using UVM -- your UVM test replaces it.
