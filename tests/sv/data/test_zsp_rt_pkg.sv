// ==========================================================================
// test_zsp_rt_pkg.sv -- Standalone testbench exercising zsp_rt_pkg
// ==========================================================================

`include "zsp_rt_pkg.sv"

module test_zsp_rt_top;
    import zsp_rt_pkg::*;

    int pass_count = 0;
    int fail_count = 0;

    task check(string test_name, bit condition);
        if (condition) begin
            $display("  PASS: %s", test_name);
            pass_count++;
        end else begin
            $display("  FAIL: %s", test_name);
            fail_count++;
        end
    endtask

    // ---- Test: Component tree and get_full_name ----
    task test_component_tree();
        zsp_component root, child, grandchild;
        $display("--- test_component_tree ---");

        root = new("root", null);
        child = new("child", root);
        grandchild = new("gc", child);

        check("root name", root.get_full_name() == "root");
        check("child full name", child.get_full_name() == "root.child");
        check("grandchild full name", grandchild.get_full_name() == "root.child.gc");
        check("root parent is null", root.parent == null);
        check("child parent is root", child.parent == root);
    endtask

    // ---- Test: Component atomic semaphore ----
    task test_component_atomic_sem();
        zsp_component comp;
        $display("--- test_component_atomic_sem ---");

        comp = new("comp", null);
        // Semaphore should be initialized with count 1
        check("atomic_sem initialized", comp.atomic_sem != null);
        // try_get should succeed once
        check("atomic_sem try_get", comp.atomic_sem.try_get(1));
        // second try_get should fail (semaphore exhausted)
        check("atomic_sem exhausted", !comp.atomic_sem.try_get(1));
        // put it back
        comp.atomic_sem.put(1);
        check("atomic_sem restored", comp.atomic_sem.try_get(1));
    endtask

    // ---- Test: Resource pool lock/unlock ----
    task test_resource_pool_lock();
        zsp_resource_pool #(zsp_resource) pool;
        bit ok;
        $display("--- test_resource_pool_lock ---");

        pool = new(4);
        check("pool_size", pool.pool_size() == 4);
        check("instance_id[0]", pool.instances[0].instance_id == 0);
        check("instance_id[3]", pool.instances[3].instance_id == 3);

        // try_lock on free resource
        ok = pool.try_lock(1);
        check("try_lock free", ok == 1);
        check("lock_held set", pool.lock_held[1] == 1);

        // try_lock on locked resource should fail
        ok = pool.try_lock(1);
        check("try_lock locked fails", ok == 0);

        // unlock
        pool.unlock(1);
        check("lock_held cleared", pool.lock_held[1] == 0);

        // try_lock again after unlock
        ok = pool.try_lock(1);
        check("try_lock after unlock", ok == 1);
        pool.unlock(1);
    endtask

    // ---- Test: Resource pool share/unshare ----
    task test_resource_pool_share();
        zsp_resource_pool #(zsp_resource) pool;
        bit ok;
        $display("--- test_resource_pool_share ---");

        pool = new(2);

        // share on free resource
        ok = pool.try_share(0);
        check("try_share free", ok == 1);
        check("share_count 1", pool.share_count[0] == 1);

        // multiple shares allowed
        ok = pool.try_share(0);
        check("try_share second", ok == 1);
        check("share_count 2", pool.share_count[0] == 2);

        // try_lock on shared resource should fail
        ok = pool.try_lock(0);
        check("try_lock on shared fails", ok == 0);

        // unshare
        pool.unshare(0);
        check("share_count after unshare", pool.share_count[0] == 1);
        pool.unshare(0);
        check("share_count zero", pool.share_count[0] == 0);

        // try_share on locked resource should fail
        pool.force_lock(1);
        ok = pool.try_share(1);
        check("try_share on locked fails", ok == 0);
        pool.unlock(1);
    endtask

    // ---- Test: Resource pool force_lock ----
    task test_resource_pool_force_lock();
        zsp_resource_pool #(zsp_resource) pool;
        $display("--- test_resource_pool_force_lock ---");

        pool = new(2);
        pool.force_lock(0);
        check("force_lock sets held", pool.lock_held[0] == 1);
        pool.unlock(0);
        check("unlock after force_lock", pool.lock_held[0] == 0);
    endtask

    // ---- Test: Stream channel put/get ----
    task test_stream_channel();
        zsp_stream_channel #(zsp_stream) chan;
        zsp_stream item_in, item_out;
        $display("--- test_stream_channel ---");

        chan = new();
        item_in = new();

        fork
            chan.put(item_in);
            chan.get(item_out);
        join

        check("stream get matches put", item_out == item_in);
    endtask

    // ---- Test: State pool write/read ----
    task test_state_pool();
        zsp_state_pool #(zsp_state) sp;
        zsp_state val1, val2, read_val;
        $display("--- test_state_pool ---");

        sp = new();
        check("not initialized initially", sp.is_initialized() == 0);

        val1 = new();
        sp.write(val1);
        check("initialized after write", sp.is_initialized() == 1);

        read_val = sp.read();
        check("read matches written", read_val == val1);

        val2 = new();
        sp.write(val2);
        read_val = sp.read();
        check("read matches second write", read_val == val2);
    endtask

    // ---- Test: Trace macro output ----
    task test_trace_macros();
        $display("--- test_trace_macros ---");
        // Set verbosity to capture all levels
        zsp_rt_pkg::zsp_rt_verbosity = 2;

        `ZSP_TRACE("basic trace message");
        `ZSP_TRACE_ACTION("my_action", "my_comp");
        `ZSP_TRACE_RESOURCE("LOCK", "pool", 0);

        // Reduce verbosity -- resource trace should be suppressed
        zsp_rt_pkg::zsp_rt_verbosity = 1;
        `ZSP_TRACE("still visible");

        // Silent mode
        zsp_rt_pkg::zsp_rt_verbosity = 0;
        `ZSP_TRACE("should not appear");

        // Restore
        zsp_rt_pkg::zsp_rt_verbosity = 1;
        check("trace macros executed", 1);
    endtask

    // ---- Main ----
    initial begin
        $display("========================================");
        $display("zsp_rt_pkg Testbench");
        $display("========================================");

        test_component_tree();
        test_component_atomic_sem();
        test_resource_pool_lock();
        test_resource_pool_share();
        test_resource_pool_force_lock();
        test_stream_channel();
        test_state_pool();
        test_trace_macros();

        $display("========================================");
        $display("Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        $display("========================================");

        if (fail_count > 0)
            $fatal(1, "TESTS FAILED");
        else
            $display("ALL TESTS PASSED");

        $finish;
    end
endmodule
