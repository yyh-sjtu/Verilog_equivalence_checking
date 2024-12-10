<div style="text-align: center;">
    <h1>Verilog Equivalence Checkiing</h1>
</div>

<div style="text-align: right;">
    <div style="display: inline-block; text-align: left;">
        <span>Author: Yunhao Zhou</span></br>
        <span>Date: 2024-10-21</span>
    </div>
</div>


## 1. Introduction
This is a framework for Verilog code automated equivalence checking.

## 2. Requirements
Please install [Yosys](https://yosyshq.net/yosys/) before using this framework.

## 2. Usage
```python
from Verilog_equivalence_checking import *
res = Verilog_equivalence_checking(rtl1_path, rtl2_path)
```
Where rtl1_path and rtl2_path are the paths of two RTL files for equivalence checking, the res is to save the result of equivalence checking.