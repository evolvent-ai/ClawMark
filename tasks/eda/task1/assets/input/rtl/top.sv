// =============================================================================
// Module: top
// Description: Top-level wrapper integrating arbiter with peripheral logic
// Author: Mike Zhang
// Last Modified: 2026-03-10
// =============================================================================

module top #(
    parameter NUM_PORTS  = 4,
    parameter DATA_WIDTH = 32,
    parameter FIFO_DEPTH = 8
) (
    input  logic                    clk,
    input  logic                    rst_n,

    // External request interface
    input  logic [NUM_PORTS-1:0]    ext_req,
    input  logic [DATA_WIDTH-1:0]   ext_data [NUM_PORTS],

    // Output
    output logic [DATA_WIDTH-1:0]   out_data,
    output logic                    out_valid,
    output logic [1:0]              out_port_id,

    // Debug
    output logic [NUM_PORTS-1:0]    dbg_grant,
    output logic [NUM_PORTS-1:0]    dbg_req_latched
);

    // =========================================================================
    // Internal signals
    // =========================================================================
    logic [NUM_PORTS-1:0]    req_sync;
    logic [NUM_PORTS-1:0]    req_latched;
    logic [DATA_WIDTH-1:0]   data_sync [NUM_PORTS];
    logic [NUM_PORTS-1:0]    arb_grant;
    logic [DATA_WIDTH-1:0]   arb_data_out;
    logic                    arb_valid;
    logic [1:0]              arb_owner;

    // =========================================================================
    // Input synchronizer (2-stage FF for CDC)
    // =========================================================================
    logic [NUM_PORTS-1:0] req_meta;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            req_meta <= '0;
            req_sync <= '0;
        end else begin
            req_meta <= ext_req;
            req_sync <= req_meta;
        end
    end

    // Data synchronizer
    logic [DATA_WIDTH-1:0] data_meta [NUM_PORTS];

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            for (int i = 0; i < NUM_PORTS; i++) begin
                data_meta[i] <= '0;
                data_sync[i] <= '0;
            end
        end else begin
            for (int i = 0; i < NUM_PORTS; i++) begin
                data_meta[i] <= ext_data[i];
                data_sync[i] <= data_meta[i];
            end
        end
    end

    // =========================================================================
    // Request latch (hold request until granted)
    // =========================================================================
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            req_latched <= '0;
        end else begin
            for (int i = 0; i < NUM_PORTS; i++) begin
                if (arb_grant[i])
                    req_latched[i] <= 1'b0;    // clear on grant
                else if (req_sync[i])
                    req_latched[i] <= 1'b1;    // set on request
            end
        end
    end

    // =========================================================================
    // Arbiter instantiation
    // =========================================================================
    arbiter #(
        .NUM_PORTS  (NUM_PORTS),
        .DATA_WIDTH (DATA_WIDTH)
    ) u_arbiter (
        .clk          (clk),
        .rst_n        (rst_n),
        .req          (req_latched),
        .data_in      (data_sync),
        .grant        (arb_grant),
        .data_out     (arb_data_out),
        .valid_out    (arb_valid),
        .current_owner(arb_owner)
    );

    // =========================================================================
    // Output assignment
    // =========================================================================
    assign out_data    = arb_data_out;
    assign out_valid   = arb_valid;
    assign out_port_id = arb_owner;

    // Debug
    assign dbg_grant       = arb_grant;
    assign dbg_req_latched = req_latched;

endmodule
