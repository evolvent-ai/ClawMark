// =============================================================================
// Module: arbiter
// Description: 4-port round-robin arbiter with configurable priority
// Author: Mike Zhang
// Last Modified: 2026-03-15
// =============================================================================

module arbiter #(
    parameter NUM_PORTS = 4,
    parameter DATA_WIDTH = 32
) (
    input  logic                    clk,
    input  logic                    rst_n,

    // Request interface
    input  logic [NUM_PORTS-1:0]    req,
    input  logic [DATA_WIDTH-1:0]   data_in [NUM_PORTS],

    // Grant interface
    output logic [NUM_PORTS-1:0]    grant,
    output logic [DATA_WIDTH-1:0]   data_out,
    output logic                    valid_out,

    // Status
    output logic [1:0]              current_owner
);

    // =========================================================================
    // Internal signals
    // =========================================================================
    logic [1:0] last_grant;
    logic [1:0] next_grant;
    logic       any_req;
    logic [NUM_PORTS-1:0] masked_req;
    logic [NUM_PORTS-1:0] grant_next;

    assign any_req = |req;

    // =========================================================================
    // Round-robin pointer update
    // =========================================================================
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            last_grant <= 2'b01;
        end else if (any_req && |grant) begin
            last_grant <= next_grant;
        end
    end

    // =========================================================================
    // Masked request generation (round-robin fairness)
    // =========================================================================
    always_comb begin
        masked_req = '0;
        case (last_grant)
            2'b00: masked_req = req & 4'b1110;  // mask port 0 (already served)
            2'b01: masked_req = req & 4'b1100;  // mask ports 0-1
            2'b10: masked_req = req & 4'b1000;  // mask ports 0-2
            2'b11: masked_req = req & 4'b0000;  // mask all (wrap around)
            default: masked_req = req;
        endcase

        // If no higher-priority request, use unmasked (wrap-around)
        if (masked_req == '0)
            masked_req = req;
    end

    // =========================================================================
    // Priority encoder (find lowest set bit in masked request)
    // =========================================================================
    always_comb begin
        next_grant = 2'b00;
        grant_next = '0;

        if (any_req) begin
            if (masked_req[0]) begin
                next_grant = 2'b00;
                grant_next = 4'b0001;
            end else if (masked_req[1]) begin
                next_grant = 2'b01;
                grant_next = 4'b0010;
            end else if (masked_req[2]) begin
                next_grant = 2'b10;
                grant_next = 4'b0100;
            end else if (masked_req[3]) begin
                next_grant = 2'b11;
                grant_next = 4'b1000;
            end
        end
    end

    // =========================================================================
    // Grant output register
    // =========================================================================
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            grant     <= '0;
            valid_out <= 1'b0;
            data_out  <= '0;
            current_owner <= '0;
        end else begin
            grant     <= grant_next;
            valid_out <= any_req;
            current_owner <= next_grant;

            case (next_grant)
                2'b00: data_out <= data_in[0];
                2'b01: data_out <= data_in[1];
                2'b10: data_out <= data_in[2];
                2'b11: data_out <= data_in[3];
            endcase
        end
    end

endmodule
