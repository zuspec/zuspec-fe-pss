# SystemVerilog Runtime Library Reference (`zsp_rt_pkg`)

## Overview

`zsp_rt_pkg` is a self-contained SystemVerilog package that provides
base classes and utilities for PSS-generated SystemVerilog code.  It
ships as part of `zuspec-fe-pss` and must be compiled before any
generated code.

**Location**: `packages/zuspec-fe-pss/src/zuspec/fe/pss/share/sv/zsp_rt_pkg.sv`

**Simulator compatibility**: VCS 2024.09+, Questa 2026.1+, Xcelium
(untested but expected to work).

---

## Base Classes

### `zsp_component`

Base class for all generated PSS component classes.

| Member | Type | Description |
|--------|------|-------------|
| `name` | `string` | Component instance name |
| `parent` | `zsp_component` | Parent component (null for root) |
| `atomic_sem` | `semaphore` | Semaphore for `atomic` activity blocks (initialized to 1) |

| Method | Signature | Description |
|--------|-----------|-------------|
| `new` | `function new(string name = "", zsp_component parent = null)` | Constructor |
| `get_full_name` | `function string get_full_name()` | Returns dot-separated hierarchical name |

### `zsp_action`

Base class for all generated PSS action classes.

| Member | Type | Description |
|--------|------|-------------|
| `comp_base` | `zsp_component` | Component context for this action |

| Method | Signature | Description |
|--------|-----------|-------------|
| `body` | `virtual task body()` | Action body (override in generated code) |
| `pre_solve` | `virtual function void pre_solve()` | Called before randomization |
| `post_solve` | `virtual function void post_solve()` | Called after randomization |

### `zsp_resource`

Base class for PSS resource types.

| Member | Type | Description |
|--------|------|-------------|
| `instance_id` | `int` | Pool instance index (set by pool constructor) |

### `zsp_buffer`, `zsp_stream`, `zsp_state`

Empty base classes for PSS buffer, stream, and state flow-object types.

---

## Parameterized Pool Classes

### `zsp_resource_pool #(type T = zsp_resource)`

Manages a fixed-size pool of resource instances with lock/share semantics.

| Member | Type | Description |
|--------|------|-------------|
| `instances[]` | `T` | Dynamic array of resource instances |
| `lock_held[]` | `bit` | Per-instance exclusive lock flag |
| `share_count[]` | `int` | Per-instance shared-access counter |
| `lock_sem[]` | `semaphore` | Per-instance blocking semaphore |

| Method | Signature | Description |
|--------|-----------|-------------|
| `new` | `function new(int pool_size)` | Construct pool with `pool_size` instances |
| `pool_size` | `function int pool_size()` | Returns number of instances |
| `try_lock` | `function bit try_lock(int id)` | Non-blocking exclusive lock attempt |
| `lock` | `task lock(int id)` | Blocking exclusive lock (waits on semaphore) |
| `force_lock` | `function void force_lock(int id)` | Immediate lock for pre-assigned head actions |
| `unlock` | `function void unlock(int id)` | Release exclusive lock |
| `try_share` | `function bit try_share(int id)` | Non-blocking shared access attempt |
| `unshare` | `function void unshare(int id)` | Release shared access |

### `zsp_stream_channel #(type T = zsp_stream)`

Mailbox-based channel for stream flow-object producer/consumer patterns.

| Method | Signature | Description |
|--------|-----------|-------------|
| `new` | `function new()` | Construct channel with depth-1 mailbox |
| `put` | `task put(T item)` | Blocking put |
| `get` | `task get(output T item)` | Blocking get |

### `zsp_state_pool #(type T = zsp_state)`

Persistent state storage with read/write access and semaphore protection.

| Method | Signature | Description |
|--------|-----------|-------------|
| `new` | `function new()` | Construct with default-initialized state |
| `write` | `task write(T new_val)` | Write new state value (blocking, semaphore-protected) |
| `read` | `function T read()` | Read current state value |
| `is_initialized` | `function bit is_initialized()` | Returns 1 after first write |

---

## Trace Macros

Controlled by `zsp_rt_pkg::zsp_rt_verbosity` (default: 1).

| Macro | Verbosity | Description |
|-------|-----------|-------------|
| `` `ZSP_TRACE(msg) `` | >= 1 | General trace message |
| `` `ZSP_TRACE_ACTION(act_name, comp_name) `` | >= 1 | Action traversal trace |
| `` `ZSP_TRACE_RESOURCE(op, pool_name, id) `` | >= 2 | Resource lock/unlock/share trace |

**Usage**: Call with trailing semicolon: `` `ZSP_TRACE("message"); ``

**Verbosity levels**:
- 0: Silent
- 1: Action-level tracing (default)
- 2: Resource-level tracing

Set at runtime via plusarg: `+zsp_verbosity=2`
(requires user code to parse and assign `zsp_rt_pkg::zsp_rt_verbosity`).

---

## Include Guard

The file is protected by `` `ifndef ZSP_RT_PKG_SV ``. It is safe to
`` `include "zsp_rt_pkg.sv" `` from multiple files.
