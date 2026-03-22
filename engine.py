"""
Multi-Language Transpiler Engine
Supports: C <-> Python, C++ <-> Python
"""

import re


# ─────────────────────────────────────────────
# TOKENIZER
# ─────────────────────────────────────────────

TOKEN_PATTERNS = [
    ('COMMENT_SINGLE', r'//[^\n]*'),
    ('COMMENT_MULTI',  r'/\*[\s\S]*?\*/'),
    ('COMMENT_HASH',   r'#[^\n]*'),
    ('STRING',         r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),
    ('NUMBER',         r'\b\d+(\.\d+)?\b'),
    ('INCLUDE',        r'#\s*include\s*[<"][^>"]*[>"]'),
    ('USING',          r'\busing\s+namespace\s+\w+\s*;'),
    ('KEYWORD',        r'\b(int|float|double|char|void|bool|string|long|short|unsigned|'
                       r'return|if|else|for|while|do|break|continue|switch|case|default|'
                       r'class|struct|new|delete|nullptr|NULL|true|false|'
                       r'def|elif|in|not|and|or|pass|None|True|False|import|from|'
                       r'print|input|range|len|cout|cin|printf|scanf|endl)\b'),
    ('IDENTIFIER',     r'\b[a-zA-Z_]\w*\b'),
    ('OP',             r'<<|>>|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!&|^~]'),
    ('DELIM',          r'[(){}\[\];,.]'),
    ('NEWLINE',        r'\n'),
    ('WHITESPACE',     r'[ \t]+'),
    ('MISMATCH',       r'.'),
]

MASTER_PATTERN = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_PATTERNS)
)


def tokenize(code):
    tokens = []
    for mo in MASTER_PATTERN.finditer(code):
        kind = mo.lastgroup
        value = mo.group()
        if kind in ('WHITESPACE', 'COMMENT_SINGLE', 'COMMENT_MULTI', 'COMMENT_HASH',
                    'INCLUDE', 'USING'):
            continue  # skip these in token stream (handled separately)
        tokens.append((kind, value))
    return tokens


# ─────────────────────────────────────────────
# AST NODE TYPES
# ─────────────────────────────────────────────

class ASTNode:
    def __init__(self, node_type, **kwargs):
        self.type = node_type
        self.__dict__.update(kwargs)

    def __repr__(self):
        attrs = {k: v for k, v in self.__dict__.items() if k != 'type'}
        return f"ASTNode({self.type}, {attrs})"


# ─────────────────────────────────────────────
# MAIN TRANSPILE DISPATCHER
# ─────────────────────────────────────────────

def transpile(source_code, source_lang, target_lang):
    if source_lang in ('c', 'cpp') and target_lang == 'python':
        return c_to_python(source_code)
    elif source_lang == 'python' and target_lang in ('c', 'cpp'):
        return python_to_c(source_code, target_lang)
    else:
        raise ValueError(f"Conversion from {source_lang} to {target_lang} not supported")


# ─────────────────────────────────────────────
# C / C++ → PYTHON
# ─────────────────────────────────────────────

def c_to_python(code):
    lines = code.split('\n')
    result = []
    indent_level = 0
    skip_braces = False
    i = 0

    # Remove preprocessor / using namespace lines
    lines = [l for l in lines if not re.match(r'\s*#\s*(include|define|pragma)', l)
             and not re.match(r'\s*using\s+namespace', l)]

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty
        if not stripped:
            result.append('')
            i += 1
            continue

        # Skip standalone braces
        if stripped in ('{', '}', '};'):
            i += 1
            continue

        # Single-line comments
        stripped = re.sub(r'//.*', '', stripped).strip()
        if not stripped:
            i += 1
            continue

        # Determine current indent from brace depth tracking
        py_indent = '    ' * indent_level

        # ── Function definitions ──────────────────────────────
        func_match = re.match(
            r'(?:int|void|float|double|char\*?|bool|string)\s+(\w+)\s*\(([^)]*)\)\s*\{?', stripped)
        if func_match and not re.match(r'\b(if|while|for|else)\b', stripped):
            fname = func_match.group(1)
            params_raw = func_match.group(2).strip()
            params = _convert_params(params_raw)
            if fname == 'main':
                result.append(f'{py_indent}def main():')
            else:
                result.append(f'{py_indent}def {fname}({params}):')
            indent_level += 1
            if stripped.endswith('{'):
                i += 1
                continue
            i += 1
            continue

        # ── If / else if / else ──────────────────────────────
        if_match = re.match(r'if\s*\((.+)\)\s*\{?', stripped)
        elif_match = re.match(r'else\s+if\s*\((.+)\)\s*\{?', stripped)
        else_match = re.match(r'else\s*\{?', stripped)

        if elif_match:
            cond = _convert_condition(elif_match.group(1))
            result.append(f'{py_indent}elif {cond}:')
            indent_level += 1
            i += 1
            continue

        if if_match:
            cond = _convert_condition(if_match.group(1))
            result.append(f'{py_indent}if {cond}:')
            indent_level += 1
            i += 1
            continue

        if else_match:
            indent_level = max(0, indent_level - 1)
            py_indent = '    ' * indent_level
            result.append(f'{py_indent}else:')
            indent_level += 1
            i += 1
            continue

        # Closing brace reduces indent
        if stripped.startswith('}'):
            indent_level = max(0, indent_level - 1)
            py_indent = '    ' * indent_level
            # Handle else after closing brace
            rest = stripped[1:].strip()
            if rest.startswith('else if'):
                em = re.match(r'else\s+if\s*\((.+)\)\s*\{?', rest)
                if em:
                    cond = _convert_condition(em.group(1))
                    result.append(f'{py_indent}elif {cond}:')
                    indent_level += 1
            elif rest.startswith('else'):
                result.append(f'{py_indent}else:')
                indent_level += 1
            i += 1
            continue

        # ── For loop ─────────────────────────────────────────
        for_match = re.match(r'for\s*\(([^;]*);([^;]*);([^)]*)\)\s*\{?', stripped)
        if for_match:
            init = for_match.group(1).strip()
            cond = for_match.group(2).strip()
            incr = for_match.group(3).strip()
            py_for = _convert_for_loop(init, cond, incr)
            result.append(f'{py_indent}{py_for}')
            indent_level += 1
            i += 1
            continue

        # ── While loop ────────────────────────────────────────
        while_match = re.match(r'while\s*\((.+)\)\s*\{?', stripped)
        if while_match:
            cond = _convert_condition(while_match.group(1))
            result.append(f'{py_indent}while {cond}:')
            indent_level += 1
            i += 1
            continue

        # ── cout / printf → print ─────────────────────────────
        cout_line = _convert_cout(stripped)
        if cout_line:
            result.append(f'{py_indent}{cout_line}')
            i += 1
            continue

        printf_line = _convert_printf(stripped)
        if printf_line:
            result.append(f'{py_indent}{printf_line}')
            i += 1
            continue

        # ── cin / scanf → input ───────────────────────────────
        cin_line = _convert_cin(stripped)
        if cin_line:
            result.append(f'{py_indent}{cin_line}')
            i += 1
            continue

        # ── return ────────────────────────────────────────────
        ret_match = re.match(r'return\s*(.*?);?$', stripped)
        if ret_match:
            val = ret_match.group(1).strip().rstrip(';')
            result.append(f'{py_indent}return {val}')
            i += 1
            continue

        # ── Variable declarations ─────────────────────────────
        var_line = _convert_var_decl(stripped)
        if var_line:
            result.append(f'{py_indent}{var_line}')
            i += 1
            continue

        # ── Generic statement (remove trailing semicolon) ─────
        clean = stripped.rstrip(';')
        clean = _convert_condition(clean)  # handle && || !
        if clean:
            result.append(f'{py_indent}{clean}')
        i += 1

    # Add main call
    if any('def main():' in l for l in result):
        result.append('')
        result.append('if __name__ == "__main__":')
        result.append('    main()')

    return '\n'.join(result)


def _convert_params(params_raw):
    if not params_raw or params_raw.strip() == 'void':
        return ''
    params = [p.strip() for p in params_raw.split(',')]
    py_params = []
    for p in params:
        p = p.strip()
        # Remove type prefix: "int x" → "x", "int *x" → "x"
        parts = re.split(r'\s+', p)
        if len(parts) >= 2:
            py_params.append(parts[-1].lstrip('*&'))
        elif parts:
            py_params.append(parts[0].lstrip('*&'))
    return ', '.join(py_params)


def _convert_condition(cond):
    cond = cond.strip()
    cond = re.sub(r'&&', 'and', cond)
    cond = re.sub(r'\|\|', 'or', cond)
    cond = re.sub(r'(?<![=!<>])!(?!=)', 'not ', cond)
    cond = re.sub(r'\bNULL\b', 'None', cond)
    cond = re.sub(r'\btrue\b', 'True', cond)
    cond = re.sub(r'\bfalse\b', 'False', cond)
    return cond


def _convert_for_loop(init, cond, incr):
    # Try to detect "int i = 0; i < N; i++" pattern → range
    init_m = re.match(r'(?:int\s+)?(\w+)\s*=\s*(\d+)', init)
    cond_m = re.match(r'(\w+)\s*([<>]=?)\s*(.+)', cond)
    incr_m = re.match(r'(\w+)\s*(\+\+|--|[+\-]=\s*\d+)', incr)

    if init_m and cond_m and incr_m:
        var = init_m.group(1)
        start = init_m.group(2)
        op = cond_m.group(2)
        end = cond_m.group(3).strip()
        step = 1

        if incr_m.group(2) == '--':
            step = -1
        elif '+=' in incr_m.group(2):
            step_m = re.search(r'\d+', incr_m.group(2))
            if step_m:
                step = int(step_m.group())
        elif '-=' in incr_m.group(2):
            step_m = re.search(r'\d+', incr_m.group(2))
            if step_m:
                step = -int(step_m.group())

        if op == '<':
            range_end = end
        elif op == '<=':
            range_end = f'{end} + 1'
        else:
            range_end = end

        if step == 1:
            return f'for {var} in range({start}, {range_end}):'
        else:
            return f'for {var} in range({start}, {range_end}, {step}):'

    # Fallback
    return f'# for ({init}; {cond}; {incr}) — manual conversion needed'


def _convert_cout(line):
    # cout << "text" << var << endl;
    if not re.search(r'\bcout\b', line):
        return None
    line = re.sub(r'\bcout\s*', '', line)
    line = re.sub(r'\s*<<\s*endl\s*', '', line)
    line = re.sub(r'\s*<<\s*"\\n"\s*', '', line)
    line = line.rstrip(';').strip()
    parts = [p.strip() for p in re.split(r'\s*<<\s*', line) if p.strip()]
    if not parts:
        return 'print()'
    return f'print({", ".join(parts)})'


def _convert_printf(line):
    m = re.match(r'printf\s*\((.+)\)\s*;?$', line, re.DOTALL)
    if not m:
        return None
    args = m.group(1).strip()
    # Simple: printf("hello\n") → print("hello")
    # Split format string from args
    fmt_m = re.match(r'"((?:[^"\\]|\\.)*)"\s*,?\s*(.*)', args)
    if fmt_m:
        fmt = fmt_m.group(1)
        rest_args = [a.strip() for a in fmt_m.group(2).split(',') if a.strip()]
        # Replace format specifiers
        fmt_py = fmt.replace('\\n', '').replace('%d', '{}').replace('%f', '{}') \
                    .replace('%s', '{}').replace('%c', '{}').replace('%i', '{}') \
                    .replace('%ld', '{}').replace('%lf', '{}')
        if rest_args:
            return f'print("{fmt_py}".format({", ".join(rest_args)}))'
        else:
            return f'print("{fmt_py}")'
    return f'print({args})'


def _convert_cin(line):
    # cin >> var1 >> var2
    if not re.search(r'\bcin\b', line) and not re.search(r'\bscanf\b', line):
        return None
    if 'cin' in line:
        line = re.sub(r'\bcin\s*', '', line).rstrip(';').strip()
        vars_ = [v.strip() for v in re.split(r'\s*>>\s*', line) if v.strip()]
        if len(vars_) == 1:
            return f'{vars_[0]} = int(input())'
        else:
            return f'{", ".join(vars_)} = map(int, input().split())'
    # scanf fallback
    sc = re.match(r'scanf\s*\("([^"]*)",(.*)\)\s*;?', line)
    if sc:
        vars_ = [v.strip().lstrip('&') for v in sc.group(2).split(',')]
        if len(vars_) == 1:
            return f'{vars_[0]} = int(input())'
        return f'{", ".join(vars_)} = map(int, input().split())'
    return None


def _convert_var_decl(line):
    # int x = 5; / float y = 3.14; / string s = "hi"; / int a, b, c;
    m = re.match(r'(?:int|float|double|char|bool|long|short|string|auto)\s+(.+?)\s*;?$', line)
    if not m:
        return None
    body = m.group(1).strip()
    # Multiple declarations: int a, b, c;
    if ',' in body and '=' not in body:
        vars_ = [v.strip() for v in body.split(',')]
        return ' = '.join(vars_) + ' = 0'
    # Single with assignment
    if '=' in body:
        parts = body.split('=', 1)
        var = parts[0].strip().lstrip('*')
        val = parts[1].strip()
        # Convert NULL, true, false
        val = re.sub(r'\bNULL\b', 'None', val)
        val = re.sub(r'\btrue\b', 'True', val)
        val = re.sub(r'\bfalse\b', 'False', val)
        return f'{var} = {val}'
    # Declaration without assignment
    vars_ = [v.strip().lstrip('*') for v in body.split(',')]
    return ', '.join(vars_) + ' = ' + ', '.join(['0'] * len(vars_))


# ─────────────────────────────────────────────
# PYTHON → C / C++
# ─────────────────────────────────────────────

def python_to_c(code, target='c'):
    lines = code.split('\n')
    result = []
    indent_stack = [0]  # stack of indent levels
    is_cpp = target == 'cpp'

    # Headers
    if is_cpp:
        result.append('#include <iostream>')
        result.append('#include <string>')
        result.append('using namespace std;')
    else:
        result.append('#include <stdio.h>')
        result.append('#include <stdlib.h>')
        result.append('#include <string.h>')
    result.append('')

    # Detect if there's a main() function
    has_main = any(re.match(r'^def main\s*\(', l.strip()) for l in lines)
    in_function = False
    function_name = None
    pending_close_braces = 0

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()
        current_indent = len(raw_line) - len(raw_line.lstrip())

        # Skip empty
        if not stripped:
            result.append('')
            i += 1
            continue

        # Skip import lines
        if re.match(r'^(import|from)\s+', stripped):
            i += 1
            continue

        # Comments
        if stripped.startswith('#'):
            c_indent = '    ' * _get_c_depth(indent_stack, current_indent)
            result.append(f'{c_indent}// {stripped[1:].strip()}')
            i += 1
            continue

        # Close braces for dedent
        while len(indent_stack) > 1 and current_indent < indent_stack[-1]:
            indent_stack.pop()
            c_depth = len(indent_stack) - 1
            c_indent = '    ' * c_depth
            result.append(f'{c_indent}}}')

        c_depth = len(indent_stack) - 1
        c_indent = '    ' * c_depth

        # ── Function definitions ──────────────────────────────
        def_m = re.match(r'def\s+(\w+)\s*\(([^)]*)\)\s*:', stripped)
        if def_m:
            fname = def_m.group(1)
            params_raw = def_m.group(2).strip()
            params_c = _py_params_to_c(params_raw, is_cpp)
            if fname == 'main':
                result.append(f'int main() {{')
            else:
                result.append(f'void {fname}({params_c}) {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        # ── If / elif / else ──────────────────────────────────
        if_m = re.match(r'if\s+(.+):', stripped)
        elif_m = re.match(r'elif\s+(.+):', stripped)
        else_m = re.match(r'else\s*:', stripped)

        if elif_m:
            cond = _py_cond_to_c(elif_m.group(1))
            # Close previous block
            result.append(f'{c_indent}}} else if ({cond}) {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        if if_m:
            cond = _py_cond_to_c(if_m.group(1))
            result.append(f'{c_indent}if ({cond}) {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        if else_m:
            result.append(f'{c_indent}}} else {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        # ── For loop ─────────────────────────────────────────
        for_m = re.match(r'for\s+(\w+)\s+in\s+range\((.+)\)\s*:', stripped)
        if for_m:
            var = for_m.group(1)
            rng = for_m.group(2).strip()
            rng_parts = [p.strip() for p in rng.split(',')]
            if len(rng_parts) == 1:
                result.append(f'{c_indent}for (int {var} = 0; {var} < {rng_parts[0]}; {var}++) {{')
            elif len(rng_parts) == 2:
                result.append(f'{c_indent}for (int {var} = {rng_parts[0]}; {var} < {rng_parts[1]}; {var}++) {{')
            else:
                step = rng_parts[2]
                neg = step.startswith('-')
                op = '>=' if neg else '<'
                result.append(f'{c_indent}for (int {var} = {rng_parts[0]}; {var} {op} {rng_parts[1]}; {var} += {step}) {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        # For-in (non-range)
        forin_m = re.match(r'for\s+(\w+)\s+in\s+(.+):', stripped)
        if forin_m:
            var = forin_m.group(1)
            iterable = forin_m.group(2).strip()
            result.append(f'{c_indent}// for {var} in {iterable} — manual conversion needed')
            result.append(f'{c_indent}// {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        # ── While loop ────────────────────────────────────────
        while_m = re.match(r'while\s+(.+):', stripped)
        if while_m:
            cond = _py_cond_to_c(while_m.group(1))
            result.append(f'{c_indent}while ({cond}) {{')
            indent_stack.append(current_indent + 4)
            i += 1
            continue

        # ── print → printf / cout ─────────────────────────────
        print_m = re.match(r'print\s*\((.+)\)\s*$', stripped)
        if print_m:
            args = print_m.group(1).strip()
            if is_cpp:
                cout_line = _py_print_to_cout(args)
                result.append(f'{c_indent}{cout_line}')
            else:
                printf_line = _py_print_to_printf(args)
                result.append(f'{c_indent}{printf_line}')
            i += 1
            continue

        # ── input → scanf / cin ───────────────────────────────
        input_m = re.match(r'(\w+)\s*=\s*(?:int|float)?\s*\(?\s*input\s*\(([^)]*)\)\s*\)?', stripped)
        if input_m:
            var = input_m.group(1)
            prompt = input_m.group(2).strip().strip('"\'')
            if is_cpp:
                result.append(f'{c_indent}int {var};')
                if prompt:
                    result.append(f'{c_indent}cout << "{prompt}";')
                result.append(f'{c_indent}cin >> {var};')
            else:
                result.append(f'{c_indent}int {var};')
                if prompt:
                    result.append(f'{c_indent}printf("{prompt}");')
                result.append(f'{c_indent}scanf("%d", &{var});')
            i += 1
            continue

        # ── return ────────────────────────────────────────────
        ret_m = re.match(r'return\s*(.*)', stripped)
        if ret_m:
            val = ret_m.group(1).strip()
            result.append(f'{c_indent}return {val};')
            i += 1
            continue

        # ── pass ──────────────────────────────────────────────
        if stripped == 'pass':
            result.append(f'{c_indent}// pass')
            i += 1
            continue

        # ── Variable assignment ───────────────────────────────
        assign_m = re.match(r'(\w+)\s*=\s*(.+)', stripped)
        if assign_m and not any(kw in stripped for kw in ['if ', 'while ', 'for ', 'def ', 'class ']):
            var = assign_m.group(1)
            val = assign_m.group(2).strip()
            val = re.sub(r'\bTrue\b', '1', val)
            val = re.sub(r'\bFalse\b', '0', val)
            val = re.sub(r'\bNone\b', 'NULL', val)
            val = re.sub(r'\band\b', '&&', val)
            val = re.sub(r'\bor\b', '||', val)
            val = re.sub(r'\bnot\b', '!', val)
            # Infer type
            dtype = _infer_c_type(val, is_cpp)
            result.append(f'{c_indent}{dtype} {var} = {val};')
            i += 1
            continue

        # ── Generic statement ─────────────────────────────────
        stmt = _py_cond_to_c(stripped)
        result.append(f'{c_indent}{stmt};')
        i += 1

    # Close remaining open braces
    while len(indent_stack) > 1:
        indent_stack.pop()
        c_depth = len(indent_stack) - 1
        result.append('    ' * c_depth + '}')

    # Add return 0 to main if not present
    final_code = '\n'.join(result)
    if 'int main()' in final_code and 'return 0;' not in final_code:
        # Insert return 0 before last }
        lines_out = final_code.split('\n')
        for j in range(len(lines_out) - 1, -1, -1):
            if lines_out[j].strip() == '}':
                lines_out.insert(j, '    return 0;')
                break
        final_code = '\n'.join(lines_out)

    return final_code


def _get_c_depth(stack, current_indent):
    return max(0, len(stack) - 1)


def _py_params_to_c(params_raw, is_cpp):
    if not params_raw:
        return 'void' if not is_cpp else ''
    params = [p.strip() for p in params_raw.split(',')]
    return ', '.join(f'int {p}' for p in params if p)


def _py_cond_to_c(cond):
    cond = re.sub(r'\band\b', '&&', cond)
    cond = re.sub(r'\bor\b', '||', cond)
    cond = re.sub(r'\bnot\s+', '!', cond)
    cond = re.sub(r'\bTrue\b', '1', cond)
    cond = re.sub(r'\bFalse\b', '0', cond)
    cond = re.sub(r'\bNone\b', 'NULL', cond)
    return cond


def _py_print_to_cout(args):
    parts = [p.strip() for p in args.split(',')]
    items = ' << '.join(parts)
    return f'cout << {items} << endl;'


def _py_print_to_printf(args):
    parts = [p.strip() for p in args.split(',')]
    if len(parts) == 1:
        p = parts[0]
        if p.startswith('"') or p.startswith("'"):
            fmt = p.strip('"\'')
            return f'printf("{fmt}\\n");'
        else:
            return f'printf("%d\\n", {p});'
    # Multiple args
    fmt_parts = []
    val_parts = []
    for p in parts:
        if p.startswith('"') or p.startswith("'"):
            fmt_parts.append(p.strip('"\''))
        else:
            fmt_parts.append('%d')
            val_parts.append(p)
    fmt = ' '.join(fmt_parts)
    if val_parts:
        return f'printf("{fmt}\\n", {", ".join(val_parts)});'
    return f'printf("{fmt}\\n");'


def _infer_c_type(val, is_cpp):
    val = val.strip()
    if val.startswith('"') or val.startswith("'"):
        return 'char*' if not is_cpp else 'string'
    if re.match(r'^-?\d+$', val):
        return 'int'
    if re.match(r'^-?\d+\.\d+', val):
        return 'float'
    if val in ('1', '0', 'true', 'false'):
        return 'int'
    return 'int'  # default
