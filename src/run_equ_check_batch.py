from glob import glob
from Verilog_equivalence_checking import *
import os
import argparse
import time
from utils.logger import Logger

def get_parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_dir', type=str, default='dataset_9_14')

    args = parser.parse_args()
    return args

def get_logger():
    
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    if not os.path.exists('log/'):
        os.makedirs('log/')
    logger = Logger(f'log/log_{timestamp}.txt')
    return logger

base_dir = "RTLRewriter-Bench/short_benchmark/basic"
design_dirs = glob(os.path.join(base_dir, "*"))
logger = get_logger()
for design_dir in design_dirs:
    
    designs = glob(os.path.join(design_dir, '*.v'))
    rtl1_path = designs[0]
    rtl2_path = designs[1]
    rtl1_name = os.path.basename(rtl1_path).split('.')[0]
    rtl2_name = os.path.basename(rtl2_path).split('.')[0]
    miter_path = os.path.join(os.path.dirname(rtl1_path), f"{rtl1_name}_{rtl2_name}_miter.sv")
    print(design_dir)
    logger.write(design_dir + '\n')
    logger.write(rtl1_path + '\n')
    logger.write(rtl2_path + '\n')
    logger.write(Verilog_equivalence_checking(rtl1_path, rtl2_path, miter_path) + '\n')