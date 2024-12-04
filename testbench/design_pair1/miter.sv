module design1 
(
  input rst_n,
  input clk,
  input valid_count,

  output reg [3:0] out
);

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) 
	begin
      out <= 4'b0000;
    end 

	else if (valid_count) 
	begin
      if (out == 4'd11) 
	  begin
        out <= 4'b0000;
      end 
	  else begin
        out <= out + 1;
      end
    end 
	
	else begin
      out <= out; // Pause the count when valid_count is invalid
    end
  end

endmodule

module design2 
(
  input rst_n,
  input clk,
  input valid_count,

  output reg [3:0] out
);

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) 
	begin
      out <= 4'b0000;
    end 

	else if (valid_count) 
	begin
      if (out == 4'd11) 
	  begin
        out <= 4'b0000;
      end 
	  else begin
        out <= out + 1;
      end
    end 
	
	else begin
      out <= out; // Pause the count when valid_count is invalid
    end
  end

endmodule

module miter();
wire [3:0] out1, out2;
design1 inst1 (.rst_n(rst_n),.clk(clk),.valid_count(valid_count),.out(out1));
design2 inst2 (.rst_n(rst_n),.clk(clk),.valid_count(valid_count),.out(out2));
always @(posedge clk) begin
assert(out1 == out2);
end
endmodule