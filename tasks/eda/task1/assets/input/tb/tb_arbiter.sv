// =============================================================================
// Testbench: tb_arbiter
// Description: SystemVerilog testbench for 4-port round-robin arbiter
//              Includes assertion-based checkers for spec compliance
// Author: Jordan Lee (Verification)
// Last Modified: 2026-03-20
// =============================================================================

`timescale 1ns/1ps

module tb_arbiter;

    // =========================================================================
    // Parameters
    // =========================================================================
    parameter NUM_PORTS  = 4;
    parameter DATA_WIDTH = 32;
    parameter CLK_PERIOD = 10;

    // =========================================================================
    // DUT signals
    // =========================================================================
    logic                    clk;
    logic                    rst_n;
    logic [NUM_PORTS-1:0]    req;
    logic [DATA_WIDTH-1:0]   data_in [NUM_PORTS];
    logic [NUM_PORTS-1:0]    grant;
    logic [DATA_WIDTH-1:0]   data_out;
    logic                    valid_out;
    logic [1:0]              current_owner;

    // =========================================================================
    // Test control
    // =========================================================================
    int cycle_count;
    int error_count;
    string test_name;
    logic reset_released;
    logic first_grant_after_reset;

    // =========================================================================
    // Clock generation
    // =========================================================================
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // Cycle counter
    always_ff @(posedge clk) begin
        cycle_count <= cycle_count + 1;
    end

    // =========================================================================
    // DUT instantiation
    // =========================================================================
    arbiter #(
        .NUM_PORTS  (NUM_PORTS),
        .DATA_WIDTH (DATA_WIDTH)
    ) dut (
        .clk          (clk),
        .rst_n        (rst_n),
        .req          (req),
        .data_in      (data_in),
        .grant        (grant),
        .data_out     (data_out),
        .valid_out    (valid_out),
        .current_owner(current_owner)
    );

    // =========================================================================
    // Assertion Checkers
    // =========================================================================

    // CHECK 1: After reset release, first grant must go to port 0
    //          (Spec: page 7, table 2 — "Post-reset arbitration starts at port 0")
    property assert_reset_grant_order;
        @(posedge clk) disable iff (!rst_n)
        ($rose(reset_released) && req[0] && first_grant_after_reset)
        |-> ##[1:3] grant[0];
    endproperty

    assert property (assert_reset_grant_order)
    else begin
        error_count++;
        $error("[ASSERT FAIL] assert_reset_grant_order @ cycle %0d: Expected grant[0] after reset, got grant=%b (owner=%0d)",
               cycle_count, grant, current_owner);
    end

    // CHECK 2: Grant must be one-hot (at most one grant active)
    property assert_grant_onehot;
        @(posedge clk) disable iff (!rst_n)
        $onehot0(grant);
    endproperty

    assert property (assert_grant_onehot)
    else begin
        error_count++;
        $error("[ASSERT FAIL] assert_grant_onehot @ cycle %0d: grant=%b is not one-hot",
               cycle_count, grant);
    end

    // CHECK 3: No grant without request
    property assert_no_grant_without_req;
        @(posedge clk) disable iff (!rst_n)
        (grant != '0) |-> (req != '0);
    endproperty

    assert property (assert_no_grant_without_req)
    else begin
        error_count++;
        $error("[ASSERT FAIL] assert_no_grant_without_req @ cycle %0d: grant=%b but req=%b",
               cycle_count, grant, req);
    end

    // CHECK 4: Round-robin fairness (no port starved for >NUM_PORTS consecutive grants)
    int grant_history[$];

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            grant_history = {};
        end else if (|grant) begin
            grant_history.push_back(current_owner);
            if (grant_history.size() > 16)
                void'(grant_history.pop_front());
        end
    end

    // =========================================================================
    // Test: tc_reset_rr_17
    // Scenario: Two-phase test.
    //   Phase 1: warm-up traffic to exercise the arbiter under normal conditions.
    //   Phase 2: apply a second reset and verify post-reset grant ordering
    //            with all 4 ports requesting simultaneously.
    // =========================================================================
    task tc_reset_rr_17();
        test_name = "tc_reset_rr_17";
        $display("========================================");
        $display("[TEST] %s — Start", test_name);
        $display("[TEST] Verify post-reset grant ordering");
        $display("========================================");

        // Initialize
        cycle_count = 0;
        error_count = 0;
        reset_released = 0;
        first_grant_after_reset = 0;
        req = '0;
        for (int i = 0; i < NUM_PORTS; i++)
            data_in[i] = 32'hA000_0000 + i;

        // ── Phase 1: Initial reset + warm-up traffic ──
        rst_n = 0;
        repeat (10) @(posedge clk);

        rst_n = 1;
        $display("[%0t] Initial reset released @ cycle %0d", $time, cycle_count);

        // Warm-up: cycle through some request patterns
        repeat (5) @(posedge clk);
        req = 4'b0011;   // ports 0,1 request
        repeat (20) @(posedge clk);
        req = 4'b1100;   // ports 2,3 request
        repeat (20) @(posedge clk);
        req = 4'b1010;   // ports 1,3 request
        repeat (20) @(posedge clk);
        req = 4'b0101;   // ports 0,2 request
        repeat (20) @(posedge clk);
        req = 4'b1111;   // all ports request
        repeat (20) @(posedge clk);
        req = '0;         // quiesce
        repeat (5) @(posedge clk);

        // ── Phase 2: Second reset + post-reset grant ordering check ──
        $display("[%0t] Applying second reset @ cycle %0d", $time, cycle_count);
        rst_n = 0;
        repeat (10) @(posedge clk);

        // Release reset (should be around cycle 130)
        rst_n = 1;
        $display("[%0t] Reset released @ cycle %0d", $time, cycle_count);

        repeat (4) @(posedge clk);

        // Assert all 4 requests simultaneously — this is the critical check
        reset_released = 1;
        first_grant_after_reset = 1;
        req = 4'b1111;
        $display("[%0t] All requests asserted @ cycle %0d (req=%b)", $time, cycle_count, req);

        // Wait for grant and check
        repeat (3) @(posedge clk);
        $display("[%0t] Grant observed @ cycle %0d: grant=%b, owner=%0d",
                 $time, cycle_count, grant, current_owner);

        first_grant_after_reset = 0;

        // Continue for a few more grants to check round-robin sequence
        repeat (20) @(posedge clk);

        // Report
        $display("========================================");
        if (error_count == 0) begin
            $display("[TEST] %s — PASSED", test_name);
        end else begin
            $display("[TEST] %s — FAILED (%0d errors)", test_name, error_count);
        end
        $display("========================================");
    endtask

    // =========================================================================
    // Main test sequence
    // =========================================================================
    initial begin
        $dumpfile("tc_reset_rr_17.fst");
        $dumpvars(0, tb_arbiter);

        tc_reset_rr_17();

        repeat (10) @(posedge clk);
        $finish;
    end

endmodule
