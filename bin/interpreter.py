from types import FunctionType, ModuleType
from io import TextIOWrapper
from typing import Any
import operator
import sys
import json
import copy
import re
import os


###################################################
'''
TODO:
OPTIMIZE
. better bool

everything stored in self.globals

. handling errors (interpreter AND luma)

. python objects access from luma # for libraries like socket

. importing py # this will be extentions

ONLY when finished: self.keywords: [...] (not setable)

. luma extentions (`for loops` and stuff)
'''
class LumaInterpreter:
    LOGICAL_OPERATORS: list[str] = [' == ', ' <= ', ' =< ', ' >= ', ' > ', ' < ', 'not ', ' and ', ' or ']
    OPERATORS: dict[str, str] = {
        '-': '@subtraction',
        '+': '@addition',
        '/': '@division',
        '*': '@multiplication',
    }
    REAL_OPERATORS: dict[str, FunctionType] = {
        '-': operator.sub,
        '+': operator.add,
        '/': operator.truediv,
        '*': operator.mul,
    }
    PY_IMPL_CLASSES = ['bool', 'dict']
    NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")
    LOGICAL_OP_RE = re.compile(r'\s*(' + '|'.join(re.escape(op) for op in LOGICAL_OPERATORS) + r')\s*')


    def __init__(self):
        self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
        self.classes: dict[str, LumaInterpreter.LumaClass] = {}
        self.vars: dict[str, LumaInterpreter.IntancedLumaObject | str | int] = {}
        self.localparams: list[dict[str, LumaInterpreter.IntancedLumaObject | str | int]] = []


    def run(self, program: str, filename: str, glob: dict[str, Any]):
        self.glob = clear_uncopyable(glob)

        def nativecode(pytext, **kwargs):
            globs = {"filename": self.filename}
            r = eval(str(pytext), globs | kwargs)
            return r
        
        def packvalue(string):
            r = json.dumps(str(string))
            return r
        
        self.functions['nativecode'] = self.LumaFunction('nativecode', [{'name':'pytext'}], nativecode, self.glob)
        self.functions['packvalue'] = self.LumaFunction('packvalue', [{'name': 'string'}], packvalue, self.glob)

        module = self.LumaClass('module', glob)
        self.classes['module'] = module
        BaseError = self.LumaClass('BaseError', glob)
        def constructor(msg, this = None):
            raise LumaInterpreter.LumaException(['BaseError', msg])
        
        BaseError.functions['constructor'] = LumaInterpreter.LumaFunction('constructor', [{'name': 'msg'}], constructor, glob)
        self.classes['BaseError'] = BaseError

        dictcls = self.LumaClassDict('dict', glob)
        self.classes['dict'] = dictcls
        boolcls = self.LumaClassBool('bool', glob)
        self.classes['bool'] = boolcls

        self.filename = filename
        self.scopes: list[str] = [program]
        self.runimport(':builtins.lum', None)
        self.runsubprogram(program, infunc=False)
    

    def getfirstword(self, line: str):
        return line.split(' ')[0]
    

    def isnumber(self, data: str | int | float):
        if type(data) == str: return bool(re.match(self.NUMBER_RE, data))
        return isinstance(data, (int, float))
    

    def reverse_list(self, r):
        return r[::-1] if isinstance(r, list) else []
    

    def realvalue(self, expr: str, includelist = False):
        if not includelist:
            if self.isnumber(expr):
                if not '.' in expr:
                    return int(expr)
                return float(expr)
            else:
                return expr
        else:
            if expr[0] == '[' and expr[-1] == ']':
                list_content = expr[1:-1].strip()
                if not list_content:
                    return []
                items = self.smrtsplt(list_content, ',')
                def clean_item(item: str):
                    item = item.strip()
                    if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
                        return item[1:-1]
                    return item
                as_dict = {i: clean_item(item) for i, item in enumerate(items)}
                return self.realvalue(str(as_dict), True)
            elif expr[0] == '{' and expr[-1] == '}':
                dict_content = expr[1:-1].strip()
                if not dict_content:
                    return {}
                items = self.smrtsplt(dict_content, ', ')
                result = {}
                for item in items:
                    if ':' not in item:
                        continue
                    key_str, value_str = item.split(':', 1)
                    key = self.evaluate(key_str.strip())
                    value = self.evaluate(value_str.strip())
                    result[key] = value
                return result
    

    def removetab(self, line: str):
        return line.replace('    ', '', 1) if line.startswith('    ') else line
    

    def preprocess(self, prog: str):
        lines = prog.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('/*'):
                c = i
                while not lines[c].strip().endswith('*/'):
                    del lines[c]
                del lines[c]
                continue
            i += 1
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('//'):
                del lines[i]
                continue
            i += 1
        i = 0
        while i < len(lines):
            line = lines[i]
            if "; " in line:
                spacenum = len(line) - len(line.lstrip())
                lines[i] = line[:line.find('; ')]
                lines.insert(i + 1, ' ' * spacenum + line[line.find('; ') + 2:])
            i += 1
        return '\n'.join(lines)
    

    def generaterandomvarname(self):
        varname = '@tmpsysvar'
        while varname in self.vars.keys():
            varname += 'donottouch'
        return varname
    

    def runimport(self, module: str, name: str):
        if ':' in module:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            module = os.path.join(base_dir, module[:module.find(':')], module[module.find(":") + 1:])
        try:
            with open(module) as imported:
                subprogram = imported.read()
                if name == None:
                    self.runsubprogram(subprogram, infunc=False)
                else:
                    body = 'class module {\n    constructor module (){\n        \n    }\n\n'
                    for line in subprogram.splitlines():
                        body += '    ' + line + '\n'
                    body += '}'
                    self.runsubprogram(body, infunc=False)
                    self.runsubprogram(f'set {name} to module ()')
        except FileNotFoundError:
            self.throw(self.classes['ModuleNotFoundError'], f"No module named '{module}'")
    
    def runsubprogram(self, subprogram: str, Object = None, infunc: bool = True, realfunc: bool = False):
        if Object == None:
            Object = self
        linen = 1
        subprogram = self.preprocess(subprogram)
        subprogram = subprogram.splitlines()
        if infunc:
            for i in range(len(subprogram)):
                subprogram[i] = self.removetab(subprogram[i])
        subprogram = '\n'.join(subprogram)
        self.scopes.append(subprogram)
        res = None
        for subline in subprogram.splitlines():
            try:
                res = self.process(subline, linen, Object)
            except LumaInterpreter.SubProgramExitCode as e:
                if e.code == 'return':
                    self.scopes.pop()
                    return e.data
                else:
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode(e.code, e.data)
            if subline.startswith('return'):
                if not realfunc:
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode('return', res)
                else:
                    break
            linen += 1
        self.scopes.pop()
        return res

    
    def process(self, line: str, linenum: int, Object = None):
        line = line.replace(r'\n', '\n')
        if Object == None:
            varis = self.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = self.functions
            classes: dict[str, LumaInterpreter.LumaFunction] = self.classes
        else:
            Object: LumaInterpreter | LumaInterpreter.IntancedLumaObject = Object
            varis = Object.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = Object.functions
            classes: dict[str, LumaInterpreter.LumaClass] = Object.classes
        program = self.scopes[-1]
        progfind = program.find
        firstword = self.getfirstword(line)
        if firstword == 'function':
            func_name = line[9:line.find(' (')]
            args = self.parse_args(line[line.find(' (') + 2:line.find(')')])
            a = program[progfind(f'{func_name} (') + len(func_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions[func_name] = self.LumaFunction(func_name, args, body, self.glob)
        elif firstword == 'class':
            class_name = line[6:line.find(' {')]
            a = program[progfind(f'class {class_name}' + ' {') + len(class_name) + 2:]
            stop = len(a[:a.find(' {') + 3])
            for linee in a[a.find(' {') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find(' {') + 3:stop].strip()
            parent = None
            classes[class_name] = self.LumaClass(class_name, self.glob)
            if '(' in class_name and ')' in class_name:
                parent = class_name[class_name.find('(') + 1:class_name.find(')')]
                class_name = class_name[:class_name.find('(') - 1]
                classes[class_name] = self.LumaClass(class_name, self.glob)
                classes[class_name].functions = classes[parent].functions.copy()
                classes[class_name].vars = classes[parent].vars.copy()
                classes[class_name].parents = classes[parent].parents.copy()
                classes[class_name].parents.append(parent)
                classes[class_name].typename = class_name
                if 'BaseError' in classes[class_name].parents:
                    def constructor(msg, this = None):
                        raise LumaInterpreter.LumaException([class_name, msg])
                    
                    classes[class_name].functions['constructor'] = LumaInterpreter.LumaFunction('constructor', [{'name': 'msg'}], constructor, self.glob)
            self.runsubprogram(body, classes[class_name])
        elif firstword == 'constructor':
            class_name = line[12:line.find(' (')]
            args = self.parse_args(line[line.find(' (') + 2:line.find(')')])
            a = program[progfind(f'{class_name} (') + len(class_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions['constructor'] = self.LumaFunction('constructor', args, body, self.glob)
        elif firstword == 'set':
            varname = line[4:line.find('to') - 1]
            value = self.evaluate(line[line.find('to') + 3:], varname)
            if varname.count('.') == 1:
                instancename = varname.split('.')[0]
                if instancename == 'this':
                    scopes: list[dict[str, LumaInterpreter.IntancedLumaObject]] = self.reverse_list(self.localparams)
                    for scope in scopes:
                        if 'this' in scope.keys():
                            scope['this'].vars[varname.split('.')[1]] = value
                elif varname.split('.')[0] in self.vars.keys():
                    varis[instancename].vars[varname.split('.')[1]] = value
            else:
                varis[varname] = value
        elif firstword == 'import':
            module = self.getfirstword(line[7:])
            name = None
            if self.getfirstword(line[7:]) != line[7:]:
                name = line[11 + len(self.getfirstword(line[7:])):]
            self.runimport(module, name)
        elif firstword == 'if':
            condition = line[4:line.find('){')]
            a = "\n".join(program.splitlines()[linenum - 1:])
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            condition = self.processcondition(condition)
            conditions = []
            bodys = []
            linenu = int(linenum) + len(body.splitlines()) + 2
            subline = ''
            try:
                subline = self.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            while subline.startswith('elseif'):
                cond = subline[8:subline.find(')')]
                a = "\n".join(program.splitlines()[linenu - 1:])
                stop = len(a[:a.find('){') + 3])
                for linee in a[a.find('){') + 3:].splitlines():
                    if linee != '':
                        if linee[0] == '}':
                            break
                    stop += len(linee) + 1
                bd = a[a.find('){') + 3:stop].strip()
                conditions.append(self.processcondition(cond))

                bodys.append(bd)
                linenu += len(bd.splitlines()) + 2

                try:
                    subline = self.removetab(program.splitlines()[linenu - 1])
                except IndexError:
                    break
            try:
                subline = self.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            elsebody = ''
            if subline.startswith('else'):
                a = "\n".join(program.splitlines()[linenu - 1:])
                stop = len(a[:a.find('{') + 2])
                for linee in a[a.find('{') + 2:].splitlines():
                    if linee != '':
                        if linee[0] == '}':
                            break
                    stop += len(linee) + 1
                elsebody = a[a.find('{') + 2:stop].strip()
            r = None
            if self.evaluatecond(condition):
                r = self.runsubprogram(body)
            else:
                foundelif = False
                for i in range(len(conditions)):
                    con = conditions[i]
                    bd: str = bodys[i]
                    if self.evaluatecond(con):
                        r = self.runsubprogram(bd)
                        foundelif = True
                        break
                if not foundelif:
                    r = self.runsubprogram(elsebody)
            return r
        elif firstword == 'while':
            condition = line[7:line.find('){')]
            a = "\n".join(program.splitlines()[linenum - 1:])
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            processedcondition = self.processcondition(condition)
            while self.evaluatecond(processedcondition):
                try:
                    self.runsubprogram(body)
                except LumaInterpreter.SubProgramExitCode as e:
                    if e.code == 'stop':
                        break
                    elif e.code == 'again':
                        processedcondition = self.processcondition(condition)
                        continue
                    else:
                        raise LumaInterpreter.SubProgramExitCode(e.code, e.data)
                processedcondition = self.processcondition(condition)
        elif firstword == 'return':
            if line == 'return': return
            value = line[7:]
            r = self.evaluate(value.strip())
            return r
        elif line == 'again':
            raise LumaInterpreter.SubProgramExitCode('again')
        elif line == 'stop':
            raise LumaInterpreter.SubProgramExitCode('stop')
        elif line.strip() == '' or line.startswith('    ') or line == '}' or firstword == 'elseif' or firstword == 'else':
            pass
        elif line.count('.') > 0 and len(self.smrtsplt(line, '.')) > 1:
            dotparts = line.split('.')
            i = 0
            instancename = dotparts[i]
            while not self.termisclosed(instancename):
                i += 1
                instancename += '.' + dotparts[i]
            propertyname = self.getfirstword(dotparts[i + 1])
            instance = None
            instance: LumaInterpreter.IntancedLumaObject = self.evaluate(instancename)
            if instance:
                if propertyname in instance.functions.keys():
                    args = self.extractargs(line.strip(), f'{instancename}.{propertyname}')
                    instance.callmethod(propertyname, args)
                elif propertyname in instance.classes.keys():
                    args = self.extractargs(line.strip(), self.getfirstword(line.strip()))
                    instance = instance.classes[propertyname].instance(args, self.generaterandomvarname())
                else:
                    self.throw(self.classes['NameError'], f"{instancename} has no attribute '{propertyname}'")
            else:
                self.throw(self.classes['NameError'], f"undefined variable '{instancename}'")
        else:
            if firstword in functions.keys():
                func_name = firstword
                args = self.extractargs(line, func_name)
                functions[func_name].run(args)
            elif firstword == 'new':
                firstword = self.getfirstword(line[4:])
                args = self.extractargs(line[4:].strip(), firstword)
                cls: LumaInterpreter.LumaClass = self.evaluate(firstword)
                cls.instance(args, self.generaterandomvarname())
            else:
                isclass = False
                try:
                    if type(self.evaluate(firstword)) == LumaInterpreter.LumaClass:
                        isclass = True
                except:
                    pass
                self.throw(self.classes['TypeError'], 'object of type classType is not callable') if isclass else self.throw(self.classes['NameError'], f"undefined function {firstword}")


    def throw(self, exc, msg):
        exc: LumaInterpreter.LumaClass = exc
        exc.functions['constructor'].run([msg])
    

    def processcondition(self, condition: str):
        cond = self.splitbyop(condition)
        r = []
        for part in cond:
            if part in self.LOGICAL_OPERATORS:
                r.append(part)
            else:
                r.append(self.evaluate(part))
        return r
    

    def parse_args(self, input_string: str):
        if input_string == '': return []
        result = []
        tokens = [token.strip() for token in input_string.split(',')]

        seen_default = False

        for token in tokens:
            if '=' in token:
                name, value = [x.strip() for x in token.split('=', 1)]
                result.append({'name': name, 'default': self.evaluate(value)})
                seen_default = True
            else:
                if seen_default:
                    raise ValueError(f"Non-default variable '{token}' cannot follow a variable with a default value.")
                result.append({'name': token})

        return result



    def splitbyop(self, expr: str):
        tokens = []
        while expr:
            match = re.search(self.LOGICAL_OP_RE, expr)
            if match:
                before = expr[:match.start()].strip()
                if before:
                    tokens.append(before)
                tokens.append(match.group(1))
                expr = expr[match.end():]
            else:
                if expr.strip():
                    tokens.append(expr.strip())
                break
        return tokens


    def extractargs(self, line: str, funcname):
        rawargs = line[len(funcname) + 2:-1]
        if rawargs == '':
            return []
        return [self.evaluate(arg) for arg in self.smrtsplt(rawargs, ', ')]
    

    def termisclosed(self, term):
        stack = []
        opening = {'(': ')', '{': '}', '[': ']'}
        closing = {')', '}', ']'}
        in_quotes = False

        i = 0
        while i < len(term):
            char = term[i]
            
            if char == '"':
                in_quotes = not in_quotes
            
            elif not in_quotes:
                if char in opening:
                    stack.append(char)
                elif char in closing:
                    if not stack:
                        return False
                    last = stack.pop()
                    if opening[last] != char:
                        return False

            i += 1

        return not in_quotes and not stack
    

    def evaluatecond(self, cond: list[str]):
        if not cond:
            return False
        i = 0
        result = None
        invert_next = False
        while i < len(cond):
            if type(cond[i]) != LumaInterpreter.IntancedLumaObject and cond[i] == 'not ':
                invert_next = not invert_next
                i += 1
                continue


            if i + 2 >= len(cond):
                break
            left, op, right = cond[i], cond[i+1], cond[i+2]
            val = self.eval_single_condition([left, op, right])
            if invert_next:
                val = not val
                invert_next = False
            i += 3


            if result is None:
                result = val
            else:
                if i < len(cond) and cond[i] == 'and ':
                    result = result and val
                    i += 1
                elif i < len(cond) and cond[i] == 'or ':
                    result = result or val
                    i += 1
                else:
                    result = val
        return result

    def eval_single_condition(self, parts):
        left, op, right = parts
        try:
            left_val = float(left)
        except Exception:
            left_val = left
        try:
            right_val = float(right)
        except Exception:
            right_val = right
        if op == ' == ':
            return left_val == right_val
        elif op in (' <= ', ' =< '):
            return left_val <= right_val
        elif op == ' >= ':
            return left_val >= right_val
        elif op == ' > ':
            return left_val > right_val
        elif op == ' < ':
            return left_val < right_val
        else:
            return False


    def copyobj(self, obj):
        obj: LumaInterpreter.IntancedLumaObject = obj
        cp = copy.copy(obj)
        cp.vars = obj.vars.copy()
        return cp
    

    def get_oldest_parent(self, cls):
        for ancestor in reversed(cls.__mro__):
            if ancestor is not object:
                return ancestor
        return cls
    

    def smrtsplt(self, expr: str, sep: str):
        if '"' not in expr and '(' not in expr and '[' not in expr and '{' not in expr:
            return expr.split(sep)
        parts = []
        stack = []
        in_quotes = False
        sep_len = len(sep)
        expr_len = len(expr)
        brackets_open = {'(': ')', '[': ']', '{': '}'}
        brackets_close = {')', ']', '}'}
        stack_pop = stack.pop
        stack_append = stack.append
        expr_startswith = expr.startswith
        parts_append = parts.append

        start = 0
        i = 0
        while i < expr_len:
            c = expr[i]
            if c == '"':
                in_quotes = not in_quotes
            elif not in_quotes:
                if c in brackets_open:
                    stack_append(brackets_open[c])
                elif c in brackets_close:
                    if stack and stack[-1] == c:
                        stack_pop()
                elif not stack and expr_startswith(sep, i):
                    parts_append(expr[start:i])
                    i += sep_len
                    start = i
                    continue
            i += 1

        parts_append(expr[start:])

        return parts
    

    def copy_dict(self, d):
        if not isinstance(d, dict):
            return d
        out = {}
        for k, v in d.items():
            if isinstance(k, dict):
                k = self.copy_dict(k)
            elif isinstance(k, list):
                k = [self.copy_dict(i) if isinstance(i, dict) else i for i in k]
            elif isinstance(k, LumaInterpreter.IntancedLumaObject):
                obj_copy = copy.copy(k)
                obj_copy.vars = self.copy_dict(k.vars)
                obj_copy.functions = k.functions.copy()
                obj_copy.classes = k.classes.copy()
                if hasattr(k, 'value'):
                    obj_copy.value = self.copy_dict(k.value)
                k = obj_copy
            if isinstance(v, dict):
                out[k] = self.copy_dict(v)
            elif isinstance(v, list):
                out[k] = [self.copy_dict(i) if isinstance(i, dict) else i for i in v]
            elif isinstance(v, LumaInterpreter.IntancedLumaObject):
                obj_copy = copy.copy(v)
                obj_copy.vars = self.copy_dict(v.vars)
                obj_copy.functions = v.functions.copy()
                obj_copy.classes = v.classes.copy()
                if hasattr(v, 'value'):
                    obj_copy.value = self.copy_dict(v.value)
                out[k] = obj_copy
            else:
                out[k] = copy.copy(v)
        return out


    def evaluate(self, expr: str, evalforwhat = None):
        if not evalforwhat:
            evalforwhat = self.generaterandomvarname()
        firstword = self.getfirstword(expr.strip())
        
        expr = expr.strip()
        scopes: list[dict[str, LumaInterpreter.IntancedLumaObject]] = self.reverse_list(self.localparams)
        for scope in scopes:
            if expr in scope.keys():
                if type(scope[expr]) == LumaInterpreter.IntancedLumaObject:
                    r = copy.copy(scope[expr])
                    r.vars = self.copy_dict(scope[expr].vars)
                    if hasattr(r, 'value'):
                        r.value = self.copy_dict(scope[expr].value)
                else:
                    r = scope[expr]
                return r
            elif firstword in scope.keys():
                args = self.extractargs(expr.strip(), firstword)
                tmp = scope[firstword].call(args)
                r = copy.copy(tmp)
                if type(tmp) == LumaInterpreter.IntancedLumaObject:
                    r.vars = tmp.vars.copy()
                    if hasattr(r, 'value'):
                        r.value = self.copy_dict(tmp.value)
                return r
        for op in self.OPERATORS:
            op_token = f' {op} '
            if op_token not in expr:
                continue
            splitted = self.smrtsplt(expr, op_token)
            if op_token in expr and len(splitted) > 1:
                terms = splitted
                term0 = self.evaluate(op_token.join(terms[:-1]))
                if type(term0) == LumaInterpreter.IntancedLumaObject:
                    if self.OPERATORS[op] in term0.functions:
                        opstr = f'({op_token.join(terms[:-1])}).{self.OPERATORS[op]} ({terms[-1]})'
                        opstrr = self.evaluate(opstr)
                        return opstrr
                    else:
                        self.throw(self.classes['TypeError'], f"unsupported operator: unable to perform operator {op} on types '{self.evaluate(f'&{terms[0]}')}' and '{self.evaluate(f"&{op_token.join(terms[1:])}")}'")
                try:
                    return self.REAL_OPERATORS[op](term0, self.evaluate(terms[-1]))
                except TypeError:
                    self.throw(self.classes['TypeError'], f"unsupported operator: unable to perform operator {op} on types 'raw {type(self.evaluate(f'{terms[0]}')).__name__}' and 'raw {type(self.evaluate(f"{op_token.join(terms[1:])}")).__name__}'")
        dotparts = expr.split('.')
        if self.isnumber(expr):
            return self.evaluate(f'new float (r"{expr}")' if '.' in expr else f'new int (r"{expr}")', evalforwhat)
        elif expr.startswith('"') and expr.endswith('"') and not '"' in expr[1:-1]:
            return self.evaluate(f'new str (r"{expr[1:-1]}")', evalforwhat)
        elif expr.startswith('{') and expr.endswith('}'):
            return self.evaluate(f'new dict (rd"{expr}")', evalforwhat)
        elif expr.startswith('[') and expr.endswith(']'):
            return self.evaluate(f'new list (rd"{expr}")', evalforwhat)
        elif expr.startswith("'") and expr.endswith("'") and not "'" in expr[1:-1]:
            return self.evaluate(f'new str (r"{expr[1:-1]}")', evalforwhat)
        elif expr in self.vars.keys():
            if type(self.vars[expr]) == LumaInterpreter.IntancedLumaObject:
                r = copy.copy(self.vars[expr])
                r.vars = self.copy_dict(self.vars[expr].vars)
                if hasattr(r, 'value'):
                    r.value = self.copy_dict(self.vars[expr].value)
            else:
                r = self.vars[expr]
            return r
        elif expr in self.functions.keys():
            return self.functions[expr]
        elif expr in self.classes.keys():
            return self.classes[expr]
        elif expr[0] == '&':
            data: LumaInterpreter.LumaClass = self.evaluate(expr[1:])
            if type(data) == LumaInterpreter.LumaClass:
                return self.classes['classType']
            return self.classes[data.typename] if self.get_oldest_parent(type(data)) == LumaInterpreter.LumaClass else self.classes["raw"]
        elif expr.startswith('r"') and expr.endswith('"'):
            return self.realvalue(expr[2:-1])
        elif expr.startswith('rd"') and expr.endswith('"'):
            return self.realvalue(expr[3:-1], True)
        elif len(self.smrtsplt(expr, '.')) > 1:
            i = 0
            instancename = dotparts[i]
            while not self.termisclosed(instancename):
                i += 1
                instancename += '.' + dotparts[i]
            propertyname = self.getfirstword(dotparts[i + 1])
            instance = None
            instance: LumaInterpreter.IntancedLumaObject = self.evaluate(instancename)
            if instance:
                if propertyname in instance.vars.keys():
                    return instance.vars[propertyname]
                elif propertyname in instance.functions.keys():
                    args = self.extractargs(expr, f'{instancename}.{propertyname}')
                    tmp = instance.callmethod(propertyname, args)
                    r = copy.copy(tmp)
                    if type(tmp) == LumaInterpreter.IntancedLumaObject:
                        r.vars = tmp.vars.copy()
                        if hasattr(r, 'value'):
                            r.value = self.copy_dict(tmp.value)
                    return r
                elif propertyname in instance.classes.keys():
                    args = self.extractargs(expr.strip(), firstword)
                    instance = instance.classes[propertyname].instance(args, evalforwhat)
                    r = copy.copy(instance)
                    r.vars = instance.vars.copy()
                    if hasattr(r, 'value'):
                        r.value = self.copy_dict(instance.value)
                    return r
                else:
                    self.throw(self.classes['NameError'], f"{instancename} has no attribute '{propertyname}'")
            else:
                self.throw(self.classes['NameError'], f"undefined variable '{instancename}'")
        elif firstword == 'new':
            firstword = self.getfirstword(expr[4:])
            args = self.extractargs(expr[4:].strip(), firstword)
            cls: LumaInterpreter.LumaClass = self.evaluate(firstword)
            instance = cls.instance(args, evalforwhat)
            r = copy.copy(instance)
            r.vars = self.copy_dict(instance.vars)
            if hasattr(r, 'value'):
                r.value = self.copy_dict(instance.value)
            return r
        elif firstword in self.vars.keys():
            args = self.extractargs(expr.strip(), firstword)
            tmp = self.vars[firstword].call(args)
            r = copy.copy(tmp)
            if type(tmp) == LumaInterpreter.IntancedLumaObject:
                r.vars = tmp.vars.copy()
                if hasattr(r, 'value'):
                    r.value = self.copy_dict(tmp.value)
            return r
        elif firstword in self.functions.keys():
            args = self.extractargs(expr.strip(), firstword)
            tmp = self.functions[firstword].run(args)
            r = copy.copy(tmp)
            if type(tmp) == LumaInterpreter.IntancedLumaObject:
                r.vars = tmp.vars.copy()
                if hasattr(r, 'value'):
                    r.value = self.copy_dict(tmp.value)
            return r
        elif expr.startswith('(') and expr.endswith(')'):
            return self.evaluate(expr[1:-1])
        else:
            isclass = False
            try:
                if type(self.evaluate(firstword)) == LumaInterpreter.LumaClass:
                    isclass = True
            except:
                pass
            self.throw(self.classes['TypeError'], 'object of type classType is not callable') if isclass else self.throw(self.classes['NameError'], f"undefined variable or function '{firstword}'")

    
    class LumaClass:
        def __init__(self, name: str, glob: dict[str, Any], parents: list[str] = []):
            self.actualname = name
            self.typename = name
            self.parents = parents
            self.glob = glob
            self.instancen = None
            self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
            self.classes: dict[str, LumaInterpreter.LumaClass] = {}

            def stringify(placeholder):
                return f'<{self.actualname} object from luma>'
            
            self.functions['@stringify'] = LumaInterpreter.LumaFunction('@stringify', [], stringify, self.glob)
            self.vars: dict[str, LumaInterpreter.IntancedLumaObject | dict] = {}


        def __str__(self):
            return f'<class {self.typename}>'


        def call(self, args):
            self.instance(args, get_current_interpreter(self.glob).generaterandomvarname())


        def callmethod(self, method: str, args: list):
            method: LumaInterpreter.LumaFunction = self.functions[method]
            r = method.run(args, self)
            return r
        

        def instance(self, args: list, name):
            return LumaInterpreter.IntancedLumaObject(self.vars, self.functions, self.classes, self.actualname, args, name, self.glob, self.parents)
            
        
        def debug(self, trailing: str = '', prnt: bool = True):
            debugstr = ''
            debugdict: dict[str, str | list] = {'name': self.typename, 'vars': [], 'functions': {}}
            debugstr += f'Class: {self.typename}\n'
            debugstr += 'Functions:\n'
            for func in self.functions.keys():
                debugstr += f'    {func}\n'
                debugdict['functions'][func] = None
                if type(self.functions[func].body) == str:
                    debugstr += '    With body:\n'
                    debugstr += f'        {self.functions[func].body}\n'
                    debugdict['functions'][func] = self.functions[func].body
            debugstr += 'Variables:\n'
            for var in self.vars.keys():
                debugdict['vars'].append({var: self.vars[var]})
                debugstr += f'    {var}: {self.vars[var]}\n'
            debugstr = debugstr[:-1]
            if prnt:
                print(debugstr, trailing)
            return debugstr, debugdict
        

    class LumaFunction(LumaClass):
        def __init__(self, name: str, args: list[str], body: str | FunctionType, glob: dict[str, Any]):
            self.typename = 'functionType'
            self.actualname = name
            self.args = args
            self.body = body
            self.glob = glob


        def run(self, args: list, Object = None, varsholder = None):
            argdict = self.bind_values(args)
            interpreter: LumaInterpreter = get_current_interpreter(self.glob)
            if varsholder == None:
                varsholder = interpreter.vars
            if Object:
                argdict['this'] = Object
            interpreter.localparams.append(argdict)
            orig_func = set(interpreter.functions.keys())
            orig_vars = set(varsholder.keys())
            if type(self.body) == str:
                r = interpreter.runsubprogram(self.body, realfunc=True)
            else:
                rargs = []
                for key in argdict:
                    rargs.append(argdict[key])
                r = self.body(*rargs)
            added_keys = set(interpreter.functions.keys()) - orig_func
            for key in added_keys:
                interpreter.functions.pop(key, None)
            added_keys = set(varsholder.keys()) - orig_vars
            for key in added_keys:
                varsholder.pop(key, None)
            interpreter.localparams.pop()
            return r
        

        def call(self, args):
            self.run(args)
        

        def bind_values(self, args):
            result = {}
            value_index = 0

            for var in self.args:
                name = var['name']

                if value_index < len(args):
                    result[name] = args[value_index]
                    value_index += 1
                elif 'default' in var:
                    result[name] = var['default']
                else:
                    get_current_interpreter(self.glob).throw(get_current_interpreter(self.glob).classes['TypeError'], f"function '{self.name}' expected {len(self.args)} arguments but got {len(args)}")

            if value_index < len(args):
                get_current_interpreter(self.glob).throw(get_current_interpreter(self.glob).classes['TypeError'], f"function '{self.name}' expected {len(self.args)} arguments but got {len(args)}")

            return result
        
    
    class LumaClassDict(LumaClass):
        def __init__(self, name, glob, parents = []):
            super().__init__(name, glob, parents)
            def constructor(value: dict, this = None):
                this.value = value.copy()
            
            self.functions['constructor'] = LumaInterpreter.LumaFunction('constructor', [{'name': 'value'}], constructor, glob)

            def at(pos, this = None):
                return this.value[pos]
            
            self.functions['at'] = LumaInterpreter.LumaFunction('at', [{'name': 'pos'}], at, glob)

            def dctset (pos, value, this = None):
                this.value[pos] = value

            self.functions['set'] = LumaInterpreter.LumaFunction('set', [{'name': 'pos'}, {'name': 'value'}], dctset, glob)

            def stringify(this = None):
                return str({str(k): str(v) for k, v in this.value.items()})
            
            self.functions['@stringify'] = LumaInterpreter.LumaFunction('@stringify', [], stringify, self.glob)

            def length(this = None):
                return get_current_interpreter(glob).evaluate(f'new int (r"{len(this.value)}")')
            
            self.functions['len'] = LumaInterpreter.LumaFunction('len', [], length, self.glob)


    class LumaClassBool(LumaClass):
        def __init__(self, name, glob, parents = []):
            super().__init__(name, glob, parents)
            def constructor(value: bool, this = None):
                this.value = value
            
            self.functions['constructor'] = LumaInterpreter.LumaFunction('constructor', [{'name': 'value'}], constructor, glob)

            def stringify(this = None):
                return str(this.value).lower()
            
            self.functions['@stringify'] = LumaInterpreter.LumaFunction('@stringify', [], stringify, self.glob)

            def invert(this = None):
                this.value = not this.value
            
            self.functions['invert'] = LumaInterpreter.LumaFunction('invert', [], invert, self.glob)


    class IntancedLumaObject(LumaClass):
        def __init__(self, varis: dict, functions: dict, classes: dict, name: str, args: list[Any], instancename: str, glob: dict[str, Any], parents: list[str]):
            self.vars = varis
            self.parents = parents
            self.functions = functions.copy()
            self.classes = classes.copy()
            self.typename = name
            self.glob = glob
            self.instance(args, instancename)


        def call(self, args):
            pass

        
        def instance(self, args: list, name):
            interpreter: LumaInterpreter = get_current_interpreter(self.glob)
            self.instancen = name
            interpreter.vars[name] = self
            interpreter.vars[name].callmethod('constructor', args)
            del interpreter.vars[name]
            if 'BaseError' in self.parents:
                raise LumaInterpreter.LumaException([self.typename, args[0] if len(args) > 0 else ''])

        
        def __str__(self):
            r = self.functions['@stringify'].run([], self)
            return r
        def __eq__(self, other):
            if self.typename in get_current_interpreter(self.glob).PY_IMPL_CLASSES:
                return self.value == other.value
            r = self.functions['@equal'].run([other], self) if '@equal' in self.functions else (self.vars == other.vars and self.typename == other.typename)
            return r
        def	__ne__(self, other):
            r = self.functions['@nequal'].run([other], self)
            return r
        def __lt__(self, other):
            r = self.functions['@lesst'].run([other], self)
            return r
        def __le__(self, other):
            r = self.functions['@lequal'].run([other], self)
            return r
        def __gt__(self, other):
            r = self.functions['@greatert'].run([other], self)
            return r
        def __ge__(self, other):
            r = self.functions['@gequal'].run([other], self)
            return r
        def __int__(self):
            if self.typename == 'int':
                return self.vars['value']
            else:
                return None
            
        def __hash__(self):
            try:
                vars_items = sorted(self.vars.items())
                if hasattr(self, 'value'):
                    vars_items.append(self.value)
                vars_items = tuple(vars_items)
            except TypeError:
                raise TypeError("All keys and values in self.vars must be hashable to compute __hash__")
            return hash((self.typename, vars_items))


    class SubProgramExitCode(Exception):
        def __init__(self, code, data = None):
            self.code = code
            self.data = data
            super().__init__()
            

    class LumaException(Exception):
        def __init__(self, args):
            self.exc_t = args[0]
            self.args = args[1:]
            super().__init__(args[0] + ': ' + str(args[1]))


def get_current_interpreter(glob: dict[str, Any]) -> (LumaInterpreter | None):
    return next((v for v in glob.values() if isinstance(v, LumaInterpreter)), None)


def log(*texts):
    with open('log.txt', 'a') as logf:
        logf.write(', '.join(map(str, texts)) + '\n')


def clear_uncopyable(obj: dict):
    uncopyable_types = [ModuleType, TextIOWrapper]
    for key in list(obj.keys()):
        if type(obj[key]) in uncopyable_types:
            del obj[key]
    return obj