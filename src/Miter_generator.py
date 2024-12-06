import re
import os

def remove_comments(text):
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text

def verilog_extractor(text) -> str:
    verilog = ""
    endmodule_count = text.count("endmodule")
    
    pattern = r'module\s+[^\(\s]+\s*(?:#\s*\(.*?\))?\s*\(.*?\)\s*;\s*?(?:(?!module\s).)*?\bendmodule'
    verilog_code_extracted = re.findall(pattern, text, re.DOTALL)
    for module in verilog_code_extracted:
        verilog += (module + '\n\n')
            
    if endmodule_count > len(verilog_code_extracted):
        print("Warning: Risk of missing some modules while extracting Verilog code.")
            
    return verilog

def extract_always_block(verilog_code):
    def find_matching_end(code, start):
        begin_count = 1
        pos = start
        while pos < len(code):
            if re.match(r'\bbegin\b', code[pos:]):
                begin_count += 1
                pos += 5  # 移过 'begin'
            elif re.match(r'\bend\b', code[pos:]):
                begin_count -= 1
                pos += 3  # 移过 'end'
                if begin_count == 0:
                    return pos
            else:
                pos += 1
        return None

    pattern = r'always\s*@\s*\([^)]*\)\s*begin'
    matches = []
    pos = 0

    while True:
        match = re.search(pattern, verilog_code[pos:])
        if not match:
            break

        start = pos + match.start()
        end = find_matching_end(verilog_code, start + match.end() - match.start())
        if end:
            matches.append(verilog_code[start:end + 1])
            pos = end + 1
        else:
            pos += match.end()

    return matches

def extract_always_trigger(text):
    pattern = r'always\s*@\s*\(([^)]*)\)'  # 匹配 always @(...) 中的括号内容
    conditions = re.findall(pattern, text)
    return conditions
    

def get_clk_from_always_block(text):
    trigger_list = extract_always_trigger(text)
    clk_candidate = set()
    for trigger in trigger_list:
        if '*' in trigger_list: continue
        elif not('posedge' in trigger or 'negedge' in trigger): continue
        trigger_var_list = re.split(r'[\(\)\n\;\, ]+|or', trigger.replace('posedge', '').replace('negedge', ''))
        trigger_var_list = [x.strip() for x in trigger_var_list if x]
        for trigger_var in trigger_var_list:
            clk_candidate.add(trigger_var)
            
    always_block_list = extract_always_block(text)
    for always_block in always_block_list:
        code_without_always = re.sub(r'always\s*@\s*\(([^)]*)\)', '', always_block, flags=re.DOTALL)
        if 'always' in code_without_always:
            print('error, erasing always fails')
        split_text = re.split(r'[\(\)\n\;\, ]+', code_without_always)
        split_text = [s for s in split_text if s]

        for var in split_text:
            if var in clk_candidate:
                clk_candidate.discard(var)
    
    candidate_list = list(clk_candidate)
    if len(clk_candidate) > 1:
        for item in candidate_list:
            if not('clk' in item.lower() or 'clock' in item.lower()):
                clk_candidate.discard(item)
                
    return list(clk_candidate)

def replace_def(text):
    def get_def_dict(param_state):
        param_list = param_state.split(',')
        param_list = [s.replace('parameter', '').strip().strip('\t') for s in param_list]
        def_dict = {}
        for param in param_list:
            var_list = param.split('=')
            if not len(var_list) == 2: continue
            var_list = [s.strip() for s in var_list]
            def_dict[var_list[0]] = var_list[1]
        return def_dict
        
    pattern = r'module\s+[^\(\s]+\s*#\s*\((.*?)\)\s*\(.*?\)\s*;'
    def_exp = re.match(pattern, text, re.DOTALL)
    if not def_exp:
        return text
    else:
        def_dict = get_def_dict(def_exp.group(1))
    for def_var, def_val in def_dict.items():
        text = text.replace(def_var, def_val)
        
    text =  re.sub(r'#\s*\([\s\S]*?\)', '', text, re.DOTALL)
    return text


class Miter_generator:
    def __init__(self, design_path1, design_path2, preprocess=True):
        with open(design_path1) as f:
            self.design1 = remove_comments(f.read())
        with open(design_path2) as f:
            self.design2 = remove_comments(f.read())
            
        if preprocess:
            self.design1 = replace_def(self.design1)
            self.design2 = replace_def(self.design2)
        
        self.design1_module_header = self.get_module_header(self.design1)
        self.design2_module_header = self.get_module_header(self.design2)
        self.design1_module_name = self.get_module_name_from_header(self.design1_module_header)
        self.design2_module_name = self.get_module_name_from_header(self.design2_module_header)
        self.header_var_list1 = self.get_header_var_list(self.design1_module_header)
        self.header_var_list2 = self.get_header_var_list(self.design2_module_header)
        
        self.input_width_dict = self.get_input_width_dict(1)
        self.output_width_dict = self.get_output_width_dict(1)
        
        self.clk = get_clk_from_always_block(verilog_extractor(self.design1))
        
        if not set(self.header_var_list1) == set(self.header_var_list2):
            raise Exception(f"The two design modules have different input output lists: {sorted(self.header_var_list1)} {sorted(self.header_var_list2)}")
                
        

        
    def force_same_IO(self):
        def regen_IO_def(text):
            # find insert id
            text_lines = text.split(';')
            for id in range(len(text_lines)):
                text_lines[id] = text_lines[id].strip()
            id_module = 0
            for id in range(len(text_lines)):
                if text_lines[id].startswith('module '):
                    id_module = id
                    break
            insert_id = id_module + 1
            
            # remove old IO
            id = 0
            while(id < len(text_lines)):
                if text_lines[id].startswith('input') or text_lines[id].startswith('output'):
                    text_lines.pop(id)
                    id -= 1
                id += 1
            
            # insert input
            for input in self.input_width_dict:
                text_lines.insert(insert_id, f'input [{self.input_width_dict[input] - 1}:0] {input}')
                
            # insert output
            for output in self.output_width_dict:
                text_lines.insert(insert_id, f'output [{self.output_width_dict[output] - 1}:0] {output}')
            
            text = ';\n'.join(text_lines)
            
            return text
            
        
        self.input_width_dict.update(self.get_input_width_dict(2))
        self.output_width_dict.update(self.get_output_width_dict(2))
        new_module_IO_list = ','.join(list(self.input_width_dict.keys()) + list(self.output_width_dict.keys()))
        new_design1_module_header = f'module {self.design1_module_name}({new_module_IO_list});'
        new_design2_module_header = f'module {self.design2_module_name}({new_module_IO_list});'
        
        self.design1 = self.design1.replace(self.design1_module_header, new_design1_module_header)
        self.design2 = self.design2.replace(self.design2_module_header, new_design2_module_header)
        
        self.design1 = regen_IO_def(self.design1)
        self.design2 = regen_IO_def(self.design2)
        
        self.design1_module_header = self.get_module_header(self.design1)
        self.design2_module_header = self.get_module_header(self.design2)
        self.design1_module_name = self.get_module_name_from_header(self.design1_module_header)
        self.design2_module_name = self.get_module_name_from_header(self.design2_module_header)
        self.header_var_list1 = self.get_header_var_list(self.design1_module_header)
        self.header_var_list2 = self.get_header_var_list(self.design2_module_header)
        self.input_width_dict = self.get_input_width_dict(1)
        self.output_width_dict = self.get_output_width_dict(1)
        
    
    def get_module_header(self, text):
        pattern = r'module\s+[^\(\s]+\s*(?:#\s*\(.*?\))?\s*\(.*?\)\s*;'
        verilog_code = re.findall(pattern, text, re.DOTALL)
        if len(verilog_code) == 0:
            raise ValueError("No module found in the given text.")
        verilog_code = verilog_code[0]
        return verilog_code
    
    def get_module_name_from_header(self, header):
        pattern = r'module\s+([^\(\s]+)'
        module_name = re.findall(pattern, header, re.DOTALL)[0]
        return module_name
        
    def get_header_var_list(self, header):
        pattern = r'[^#]\s*\((.*)\)'
        input_list = re.findall(pattern, header, re.DOTALL)[0]
        input_list = input_list.split(',')
        # input_list = [x.strip() for x in input_list]
        input_list = [x.strip().strip('\t') for x in input_list]
        var_list = []
        for var in input_list:
            # trigger_var_list = re.split(r'[\(\)\n\;\, ]+|or', trigger.replace('posedge', '').replace('negedge', ''))
            if not ']' in var: var_list.append(re.split(r'[\t ]+', var)[-1])
            else: var_list.append(var.split(']')[-1].strip(' ').strip('\t'))
        return var_list
    
    def parse_input(self, line):
        def get_width(width_text):
            width_text = width_text.replace(']', '').replace('[', '').replace(' ', '')
            # num_list = width_text.split(':')
            num_list = [eval(x) for x in width_text.split(':')]
            if len(num_list) != 2:
                raise ValueError(f"Invalid width format: {width_text}")
            return abs(int(num_list[0]) - int(num_list[1])) + 1

        pattern = r'input\s+(?:wire|reg|logic)?\s*(?:\[(.*?)\])?\s*([^\s;]*)'
        match = re.match(pattern, line)

        if not match:
            raise ValueError(f"Invalid input declaration: {line}")
        width_text = match.group(1)
        signal_part = match.group(2)

        input_width = get_width(width_text) if width_text else 1
        signal_names = [name.strip() for name in signal_part.split(',')]

        return {name: input_width for name in signal_names}
    
    def parse_output(self, line):
        def get_width(width_text):

            width_text = width_text.replace(']', '').replace('[', '').replace(' ', '')
            # num_list = width_text.split(':')
            num_list = [eval(x) for x in width_text.split(':')]
            if len(num_list) != 2:
                raise ValueError(f"Invalid width format: {width_text}")
            return abs(int(num_list[0]) - int(num_list[1])) + 1

        pattern = r'output\s+(?:wire|reg|logic)?\s*(?:\[(.*?)\])?\s*([^\s;]*)'
        match = re.match(pattern, line)

        if not match:
            raise ValueError(f"Invalid output declaration: {line}")

        width_text = match.group(1)
        signal_part = match.group(2)

        output_width = get_width(width_text) if width_text else 1
        signal_names = [name.strip() for name in signal_part.split(',')]

        return {name: output_width for name in signal_names}
        
    def get_input_width_dict(self, design_num):
        def get_input_width_dict_from_body():
            design_content = self.design1 if design_num == 1 else self.design2
            design_list = design_content.split(';')
            design_list = [x.strip() for x in design_list]
            input_list = [x for x in design_list if 'input' in re.split(r'[\t ]+', x) and 'module' not in re.split(r'[\t ]+', x)]
            input_width_dict = {}
            for input in input_list:
                input_width_dict = input_width_dict | self.parse_input(input)
            return input_width_dict
        
        def get_input_width_dict_from_header():
            header = self.design1_module_header if design_num == 1 else self.design2_module_header
            pattern = r'[^#]\s*\((.*)\)'
            input_list = re.findall(pattern, header, re.DOTALL)[0]
            input_list = input_list.split(',')
            input_list = [x.strip().strip('\t') for x in input_list]
            input_width_dict = {}
            for input in input_list:
                # if input.startswith('input'):
                if 'input' in re.split(r'[\t ]+', input):
                    input_width_dict = input_width_dict | self.parse_input(input)
            return input_width_dict
        
        return get_input_width_dict_from_body() | get_input_width_dict_from_header()
            
    def get_output_width_dict(self, design_num):
        def get_output_width_dict_from_body():
            design_content = self.design1 if design_num == 1 else self.design2
            design_list = design_content.split(';')
            design_list = [x.strip() for x in design_list]
            output_list = [x for x in design_list if 'output' in re.split(r'[\t ]+', x) and 'module' not in re.split(r'[\t ]+', x)]
            output_width_dict = {}    
            for output in output_list:
                output_width_dict = output_width_dict | self.parse_output(output)
            return output_width_dict
        
        def get_output_width_dict_from_header():
            header = self.design1_module_header if design_num == 1 else self.design2_module_header
            pattern = r'[^#]\s*\((.*)\)'
            output_list = re.findall(pattern, header, re.DOTALL)[0]
            output_list = output_list.split(',')
            output_list = [x.strip().strip('\t') for x in output_list]
            output_width_dict = {}
            for output in output_list:
                # if output.startswith('output'):
                if 'output' in re.split(r'[\t ]+', output):
                    output_width_dict = output_width_dict | self.parse_output(output)
            return output_width_dict
        
        return get_output_width_dict_from_body() | get_output_width_dict_from_header()
            
    def gen_miter_header(self):
        return 'module miter();\n'
    
    def gen_define_list(self):
        content = ''
        for output in self.output_width_dict:
            var_type = 'wire'
            bits = f'[{self.output_width_dict[output]-1}:0]' if self.output_width_dict[output] > 1 else ''
            name = f'{output}1, {output}2'
            content += f'{var_type} {bits} {name};\n'
        return content
    
    def gen_inst(self):
        content = ''
        for num in [1, 2]:
            module_type = f'design{num}'
            inst_name = f'inst{num}'
            var_state = ','.join([f'.{x}({x})' if x not in self.output_width_dict else f'.{x}({x}{num})' for x in self.header_var_list1])
            inst = f'{module_type} {inst_name} ({var_state});\n'
            content += inst
        return content
    
    def gen_compare(self):
        if len(self.clk):
            content = f'always @(posedge {self.clk[0]}) begin\n'
        else:
            content = 'always @* begin\n'
        
        asserts = ''
        for output in self.output_width_dict:
            asserts += f'assert({output}1 == {output}2);\n'
        content += asserts
        
        content += 'end\n'
        
        return content
    
    def gen_endmodule(self):
        return 'endmodule'
            
            
    def generate_miter_module(self):
        content = ''
        content += self.gen_miter_header()
        content += self.gen_define_list()
        content += self.gen_inst()
        content += self.gen_compare()
        content += self.gen_endmodule()
        return content
        
    def rename_module(self, new_name):
        if new_name == 'design1':
            pattern = rf'{self.design1_module_name}'
            new_text = re.sub(pattern, new_name, self.design1, count=1)
            return new_text
        else:
            pattern = rf'{self.design2_module_name}'
            new_text = re.sub(pattern, new_name, self.design2, count=1)
            return new_text
                

    def set_reg_init(self, text):
        def get_width(line):
            if not '[' in line:
                return 1
            width_state = line.split('[')[1].split(']')[0]
            param1 = int(eval((width_state.split(':')[0].strip())))
            param2 = int(eval((width_state.split(':')[1].strip())))
            return abs(param1 - param2) + 1
        
        text_lines = text.split('\n')
        for i, line in enumerate(text_lines):
            if line.strip().startswith('reg'):
                if not '=' in line:
                    text_lines[i] = line.replace(';', f" = {get_width(line)}\'d0;")
                elif '=' in line:
                    text1 = line.split('=')
                    text_lines[i] = text1[0] + f" = {get_width(text1[1])}'d0;"
        text = '\n'.join(text_lines)
        return text
                
            
    def parse_reg(line):
        def get_width(width_text):

            width_text = width_text.replace(']', '').replace('[', '').replace(' ', '')
            # num_list = width_text.split(':')
            num_list = [eval(x) for x in width_text.split(':')]
            if len(num_list) != 2:
                raise ValueError(f"Invalid width format: {width_text}")
            return abs(int(num_list[0]) - int(num_list[1])) + 1

        pattern = r'(?:output\s+)?reg\s*(?:\[(.*?)\])?\s*([^\s;]*)'
        match = re.match(pattern, line)

        if not match:
            raise ValueError(f"Invalid reg declaration: {line}")

        width_text = match.group(1)
        signal_part = match.group(2)

        reg_width = get_width(width_text) if width_text else 1

        signal_names = [name.strip() for name in signal_part.split(',')]

        return {name: reg_width for name in signal_names}


    def set_reg_init(self, text):

        def get_width(line):
            if not '[' in line:
                return 1
            width_state = line.split('[')[1].split(']')[0]
            param1 = int(width_state.split(':')[0].strip())
            param2 = int(width_state.split(':')[1].strip())
            return abs(param1 - param2) + 1
        def parse_reg(line):
            def get_width(width_text):

                width_text = width_text.replace(']', '').replace('[', '').replace(' ', '')
                num_list = width_text.split(':')
                if len(num_list) != 2:
                    raise ValueError(f"Invalid width format: {width_text}")
                return abs(int(num_list[0]) - int(num_list[1])) + 1

            pattern = r'(?:output\s+)?reg\s*(?:\[(.*?)\])?\s*([^\s;]*)'
            match = re.match(pattern, line)

            if not match:
                raise ValueError(f"Invalid reg declaration: {line}")

            width_text = match.group(1)
            signal_part = match.group(2)

            reg_width = get_width(width_text) if width_text else 1

            signal_names = [name.strip() for name in signal_part.split(',')]

            return {name: reg_width for name in signal_names}
        
        def get_reg_assign(reg_name_width_dict):
            def get_value(width):
                return f'{width}\'d0'
            
            assign_list = [f'{name} = {get_value(width)}' for name, width in reg_name_width_dict.items()]
            
            return ';\n'.join(assign_list)
        
        def get_reg_assgin_from_header():
            def get_value(width):
                return f'{width}\'d0'
            
            header = self.get_module_header(text)
            pattern = r'[^#]\s*\((.*)\)'
            var_list = re.findall(pattern, header, re.DOTALL)[0]
            var_list = var_list.split(',')
            var_list = [x.strip().strip('\t') for x in var_list]
            var_width_dict = {}
            for var in var_list:
                if 'reg' in var.strip(' ').strip('\t'):
                    var_width_dict = var_width_dict | self.parse_output(var)
            assign_list = [f'{name} = {get_value(width)}' for name, width in var_width_dict.items()]
            return ';\n'.join(assign_list)
        
        text_list = text.split(';')
        text_list = [line.strip().strip('\t') for line in text_list if line.strip()]
        for i in range(len(text_list)):
            line = text_list[i]
            if 'module' in line.strip(' ').strip('\t'):
                continue
            if 'reg' in line.strip(' ').strip('\t'):
                reg_name_width_dict = parse_reg(line)
                text_list[i] += f';\n{get_reg_assign(reg_name_width_dict)}'
        
        index = 0
        for i in range(len(text_list)):
            line = text_list[i]
            pattern = r'module\s+[^\(\s]+\s*(?:#\s*\(.*?\))?\s*\(.*?\)'
            verilog_code = re.findall(pattern, line, re.DOTALL)
            if len(verilog_code):
                index = i
                text_list.insert(index + 1, get_reg_assgin_from_header())
                break
        text = ';\n'.join(text_list)
        return text
                
    def generate_miter_file_content(self):
        content = ''
        # content += self.set_reg_init(self.rename_module('design1')) + '\n\n'
        # content += self.set_reg_init(self.rename_module('design2')) + '\n\n'
        content += self.rename_module('design1')+ '\n\n'
        content += self.rename_module('design2') + '\n\n'
        content += self.generate_miter_module()
        
        # ############### tackle plus1 bug
        # content = content.replace(':plus', '+:1')
        # ###############
        
        return content
    
    def write_miter(self, output_path):
        with open(output_path, 'w') as f:
            f.write(self.generate_miter_file_content())
    
        
if __name__ == "__main__":
    
    design1 = 'testbench/design_pair1/counter12_1.v'
    design2 = 'testbench/design_pair1/counter12_2.v'
    miter_generator = Miter_generator(design1, design2)
    # print(miter_generator.design1_module_header)
    # print(miter_generator.design1_module_name)
    print(miter_generator.generate_miter_file_content())
    miter_generator.write_miter(os.path.join(os.path.dirname(design1), 'miter.sv'))
    
    # yosys_commend = 'yosys -p "read_verilog -sv miter.sv; hierarchy -top miter; proc; flatten; sat -tempinduct -prove-asserts -verify;"'
        
    