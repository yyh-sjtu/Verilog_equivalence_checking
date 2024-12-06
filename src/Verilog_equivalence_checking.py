import Miter_generator
import os
from glob import glob
import subprocess

# def run_yosys_sat(miter_path):
#     cmd = f'yosys -p "read_verilog -sv {miter_path}; hierarchy -top miter; proc; flatten; sat -tempinduct -prove-asserts -verify;"'
    
#     process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#     output = []
    
#     for line in process.stdout:
#         output.append(line)

#     process.wait()
#     stderr_output = process.stderr.read()
#     if stderr_output:
#         output.append(stderr_output)

#     return ''.join(output)


class SubprocessTimeoutException(Exception):
    """SubprocessTimeoutException"""
    pass

def run_yosys_sat(miter_path, timeout=30):

    # don't set step
    # cmd = f'yosys -p "read_verilog -sv {miter_path}; hierarchy -top miter; proc; flatten; clk2fflogic; sat -set-init-zero -tempinduct -prove-asserts -verify;"'
    
    # set timeout
    cmd = f'yosys -p "read_verilog -sv {miter_path}; hierarchy -top miter; proc; flatten; clk2fflogic; sat -set-init-zero -tempinduct -timeout 10 -prove-asserts -verify-no-timeout;"'
    
    # don't set step to 100
    # cmd = f'yosys -p "read_verilog -sv {miter_path}; hierarchy -top miter; proc; flatten; clk2fflogic; sat -set-init-zero -tempinduct -seq 100 -prove-asserts -verify;"'
    
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = process.communicate(timeout=timeout)

        output = []
        if stdout:
            output.append(stdout)
        if stderr:
            output.append(stderr)
        
        return ''.join(output)
    
    except subprocess.TimeoutExpired:
        process.kill()
        raise SubprocessTimeoutException(f"SAT timed out after {timeout} seconds")


def syntax_check(verilog_path):
    cmd = f'iverilog {verilog_path}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if 'error' in result.stderr.lower():
        return 'Syntax error'
    return 'Syntax correct'

def Verilog_equivalence_checking(rtl1_path, rtl2_path, miter_path, treat_timeout_as_equ=True, logger = None):
    if 'error' in syntax_check(rtl1_path):
        if logger: logger.write(f"Syntax error in {rtl1_path}")
        return 'Syntax error'
    if 'error' in syntax_check(rtl2_path):
        if logger: logger.write(f"Syntax error in {rtl2_path}")
        return 'Syntax error'
    
    # gen miter
    # miter_generator = Miter_generator.Miter_generator(origin_rtl_path, regen_rtl_path)
    miter_generator = Miter_generator.Miter_generator(rtl1_path, rtl2_path)
    miter_generator.write_miter(miter_path)
    
    output = run_yosys_sat(miter_path)
    
    # print(output)
    
    if "SUCCESS" in output:
        return "EQU"
    elif "TIMEOUT" in output:
        if treat_timeout_as_equ:
            return "EQU"
        else:
            return "TIMEOUT"
    else:
        return "NEQ"


if __name__ == '__main__':
    rtl1_path = "testbench/design_pair1/counter12_1.v"
    rtl2_path = "testbench/design_pair1/counter12_2.v"
    miter_path = "testbench/design_pair1/miter.sv"
    
    print(Verilog_equivalence_checking(rtl1_path, rtl2_path, miter_path))