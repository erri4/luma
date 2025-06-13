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
GOAL: . add full builtin classes

. realvalue (includelist)

(. better importing (maybe module class?)

. stop (break) keyword, again (continue)

. throwing errors)

. dictinaries

. lists

. importing py

. handling errors (interpreter AND luma)

ONLY when finished: self.keywords: [...] (not setable)

. luma extentions (for loops and stuff)
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
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
    }
    NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")
    LOGICAL_OP_RE = re.compile(r'\s*(' + '|'.join(re.escape(op) for op in LOGICAL_OPERATORS) + r')\s*')


    def __init__(self):
        self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
        self.classes: dict[str, LumaInterpreter.LumaClass] = {}
        self.vars: dict[str, LumaInterpreter.IntancedLumaObject | str | int] = {}
        self.localparams: list[dict[str, LumaInterpreter.IntancedLumaObject | str | int]] = []


    def run(self, program: str, filename: str, glob: dict[str, Any]):
        for key in list(glob.keys()):
            if type(glob[key]) == TextIOWrapper or type(glob[key]) == ModuleType:
                del glob[key]
        self.glob = glob

        def nativecode(pytext):
            globs = {"filename": self.filename}
            r = eval(str(pytext), globs)
            return r
        
        def packvalue(string):
            r = json.dumps(str(string))
            return r
        
        self.functions['nativecode'] = self.LumaFunction('nativecode', [{'name':'pytext'}], nativecode, self.glob)
        self.functions['packvalue'] = self.LumaFunction('packvalue', [{'name': 'string'}], packvalue, self.glob)
        self.filename = filename
        self.scopes: list[str] = [program]
        self.runimport(':builtins.lum')
        self.runsubprogram(program, infunc=False)
    

    def getfirstword(self, line: str):
        return line.split(' ')[0]
    

    def isnumber(self, data: str | int | float):
        if type(data) in [int, float]: return True
        if type(data) != str: return False
        return bool(re.match(self.NUMBER_RE, data))
    

    def reverse_list(self, r):
        return r[::-1] if isinstance(r, list) else []
    

    def realvalue(self, expr: str):
        if self.isnumber(expr):
            if not '.' in expr:
                return int(expr)
            return float(expr)
        else:
            return expr
    

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
    

    def runimport(self, module: str):
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
                self.runsubprogram(subprogram, infunc=False)
        except FileNotFoundError:
            raise LumaInterpreter.LumaModuleNotFoundError(f"No module named '{module}'")
    
    def runsubprogram(self, subprogram: str, Object = None, infunc: bool = True):
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
            res = self.process(subline, linen, Object)
            if res:
                break
            linen += 1
        self.scopes.pop()
        return res

    
    def process(self, line: str, linenum: int, Object = None):
        line = line.replace(r'\n', '\n')
        if Object == None:
            varis = self.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = self.functions
        else:
            Object: LumaInterpreter | LumaInterpreter.IntancedLumaObject
            varis = Object.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = Object.functions
        program = self.scopes[-1]
        if line.startswith('function'):
            func_name = line[9:line.find(' (')]
            args = self.parse_args(line[line.find(' (') + 2:line.find(')')])
            a = program[program.find(f'{func_name} (') + len(func_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions[func_name] = self.LumaFunction(func_name, args, body, self.glob)
        elif line.startswith('class'):
            class_name = line[6:line.find(' {')]
            a = program[program.find(f'class {class_name}' + ' {') + len(class_name) + 2:]
            stop = len(a[:a.find(' {') + 3])
            for linee in a[a.find(' {') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find(' {') + 3:stop].strip()
            parent = None
            if '(' in class_name and ')' in class_name:
                parent = class_name[class_name.find('(') + 1:class_name.find(')')]
                class_name = class_name[:class_name.find('(') - 1]
                self.classes[class_name] = copy.copy(self.classes[parent])
                self.classes[class_name].functions = dict(self.classes[parent].functions)
                self.classes[class_name].vars = dict(self.classes[parent].vars)
                self.classes[class_name].parents = list(self.classes[parent].parents)
                self.classes[class_name].parents.append(parent)
                self.classes[class_name].name = class_name
            else:
                self.classes[class_name] = self.LumaClass(class_name, self.glob)
            self.runsubprogram(body, self.classes[class_name])
        elif line.startswith('constructor'):
            class_name = line[12:line.find(' (')]
            args = self.parse_args(line[line.find(' (') + 2:line.find(')')])
            a = program[program.find(f'{class_name} (') + len(class_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions['constructor'] = self.LumaFunction('constructor', args, body, self.glob)
        elif line.startswith('set'):
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
        elif line.startswith('import'):
            module = self.getfirstword(line[7:])
            self.runimport(module)
        elif line.startswith('if'):
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
            subline = self.removetab(program.splitlines()[linenu - 1])
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
            subline = self.removetab(program.splitlines()[linenu - 1])
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
            if eval(condition):
                r = self.runsubprogram(body)
            else:
                foundelif = False
                for i in range(len(conditions)):
                    con = conditions[i]
                    bd: str = bodys[i]
                    if eval(con):
                        r = self.runsubprogram(bd)
                        foundelif = True
                        break
                if not foundelif:
                    r = self.runsubprogram(elsebody)
            return r
        elif line.startswith('while'):
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
            while eval(processedcondition):
                self.runsubprogram(body)
                processedcondition = self.processcondition(condition)
        elif line.startswith('return'):
            value = line[7:]
            r = self.evaluate(value.strip())
            return r
        elif line.strip() == '' or line.startswith(' ') or line == '}' or line.startswith('elseif') or line.startswith('else'):
            pass
        elif line.count('.') == 1 and self.getfirstword(line).split('.')[0] in self.vars.keys():
            dexpr = self.getfirstword(line)
            instancename = dexpr.split('.')[0]
            propertyname = dexpr.split('.')[1]
            if propertyname in self.vars[instancename].functions.keys():
                args = self.extractargs(line.strip(), f'{instancename}.{propertyname}')
                self.vars[instancename].callmethod(propertyname, args)
            else:
                raise LumaInterpreter.LumaNameError(f"undefined function {self.getfirstword(line)}")
        else:
            if self.getfirstword(line) in functions.keys():
                func_name = self.getfirstword(line)
                args = self.extractargs(line, func_name)
                functions[func_name].run(args)
            else:
                raise LumaInterpreter.LumaNameError(f"undefined function {self.getfirstword(line)}")
    

    def processcondition(self, condition: str):
        cond = self.splitbyop(condition)
        r = []
        for part in cond:
            if part in self.LOGICAL_OPERATORS:
                r.append(part)
            else:
                if not self.isnumber(str(self.evaluate(part))):
                    r.append(json.dumps(str(self.evaluate(part))))
                else:
                    r.append(str(self.evaluate(part)))
        return ''.join(r)
    

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
    

    def smrtsplt(self, expr: str, sep: str):
        parts = []
        current = []
        stack = []
        in_quotes = False
        i = 0
        while i < len(expr):
            c = expr[i]
            if c == '"':
                in_quotes = not in_quotes
                current.append(c)
            elif not in_quotes and c in '([{':
                stack.append(c)
                current.append(c)
            elif not in_quotes and c in ')]}':
                if stack:
                    stack.pop()
                current.append(c)
            elif not in_quotes and not stack and expr[i:i+len(sep)] == sep:
                parts.append(''.join(current))
                current = []
                i += len(sep) - 1
            else:
                current.append(c)
            i += 1
        if current:
            parts.append(''.join(current))
        return parts


    def evaluate(self, expr: str, evalforwhat = None, d = False):
        if not evalforwhat:
            evalforwhat = self.generaterandomvarname()
        
        scopes: list[dict[str, LumaInterpreter.IntancedLumaObject]] = self.reverse_list(self.localparams)
        for scope in scopes:
            if expr in scope.keys():
                return scope[expr]
        for op in self.OPERATORS:
            if f' {op} ' in expr and len(self.smrtsplt(expr, f' {op} ')) > 1:
                terms = self.smrtsplt(expr, f' {op} ')
                term0 = self.evaluate(f' {op} '.join(terms[:-1]))
                if type(term0) == LumaInterpreter.IntancedLumaObject:
                    if self.OPERATORS[op] in term0.functions:
                        opstr = f'({f' {op} '.join(terms[:-1])}).{self.OPERATORS[op]} ({terms[-1]})'
                        opstrr = self.evaluate(opstr)
                        return opstrr
                    else:
                        raise LumaInterpreter.LumaTypeError(f"unsupported operator: unable to perform operator {op} on types '{self.evaluate(f'&{terms[0]}')}' and '{self.evaluate(f"&{f' {op} '.join(terms[1:])}")}'")
                try:
                    return self.REAL_OPERATORS[op](self.evaluate(f' {op} '.join(terms[:-1])), self.evaluate(terms[-1]))
                except TypeError:
                    raise LumaInterpreter.LumaTypeError(f"unsupported operator: unable to perform operator {op} on types 'raw {type(self.evaluate(f'{terms[0]}')).__name__}' and 'raw {type(self.evaluate(f"{f' {op} '.join(terms[1:])}")).__name__}'")
        if self.isnumber(expr):
            return self.evaluate(f'float (r"{expr}")' if '.' in expr else f'int (r"{expr}")', evalforwhat)
        elif expr.startswith('"') and expr.endswith('"') and not '"' in expr[1:-1]:
            return self.evaluate(f'str (r"{expr[1:-1]}")', evalforwhat)
        elif expr.startswith("'") and expr.endswith("'") and not "'" in expr[1:-1]:
            return self.evaluate(f'str (r"{expr[1:-1]}")', evalforwhat)
        elif expr in self.vars.keys():
            if type(self.vars[expr]) == LumaInterpreter.IntancedLumaObject:
                r = copy.copy(self.vars[expr])
                r.vars = dict(self.vars[expr].vars)
            else:
                r = self.vars[expr]
            return r
        elif expr[0] == '&':
            data: LumaInterpreter.IntancedLumaObject = self.evaluate(expr[1:])
            return data.name if type(data) == LumaInterpreter.IntancedLumaObject else "raw"
        elif expr.startswith('r"') and expr.endswith('"'):
            return self.realvalue(expr[2:-1])
        elif expr.count('.') > 0 and len(self.smrtsplt(expr, '.')) > 1:
            i = 0
            instancename = expr.split('.')[i]
            while not self.termisclosed(instancename):
                i += 1
                instancename += '.' + expr.split('.')[i]
            propertyname = self.getfirstword(expr.split('.')[i + 1])
            instance = None
            instance: LumaInterpreter.IntancedLumaObject = self.evaluate(instancename)
            if instance:
                if propertyname in instance.vars.keys():
                    return instance.vars[propertyname]
                elif propertyname in instance.functions.keys():
                    args = self.extractargs(expr.strip(), f'{instancename}.{propertyname}')
                    r = instance.callmethod(propertyname, args)
                    return r
                else:
                    raise LumaInterpreter.LumaAttributeError(f"undefined '{instancename}.{propertyname}'")
            else:
                raise LumaInterpreter.LumaNameError(f"undefined variable '{instancename}'")
        elif self.getfirstword(expr) in self.classes.keys():
            args = self.extractargs(expr.strip(), self.getfirstword(expr.strip()))
            instance = self.classes[self.getfirstword(expr.strip())].instance(args, evalforwhat)
            r = instance
            r.vars = dict(instance.vars)
            return r
        elif self.getfirstword(expr) in self.functions.keys():
            args = self.extractargs(expr.strip(), self.getfirstword(expr))
            r = self.functions[self.getfirstword(expr.strip())].run(args)
            return r
        elif expr.startswith('(') and expr.endswith(')'):
            return self.evaluate(expr[1:-1])
        else:
            raise LumaInterpreter.LumaNameError(f"undefined variable '{self.getfirstword(expr)}'")

    class LumaFunction:
        def __init__(self, name: str, args: list[str], body: str | FunctionType, glob: dict[str, Any]):
            self.name = name
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
                r = interpreter.runsubprogram(self.body)
            else:
                r = self.body(*args)
            added_keys = set(interpreter.functions.keys()) - orig_func
            for key in added_keys:
                interpreter.functions.pop(key, None)
            added_keys = set(varsholder.keys()) - orig_vars
            for key in added_keys:
                varsholder.pop(key, None)
            interpreter.localparams.pop()
            return r
        

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
                    raise LumaInterpreter.LumaTypeError(f"function '{self.name}' expected {len(self.args)} arguments but got {len(args)}")

            if value_index < len(args):
                raise LumaInterpreter.LumaTypeError(f"function '{self.name}' expected {len(self.args)} arguments but got {len(args)}")

            return result

    
    class LumaClass:
        def __init__(self, name: str, glob: dict[str, Any], parents: list[str] = []):
            self.name = name
            self.parents = parents
            self.glob = glob
            self.instancen = None
            self.functions: dict[str, LumaInterpreter.LumaFunction] = {}

            def stringify():
                return f'<{self.name} object from luma>'
            
            self.functions['@stringify'] = LumaInterpreter.LumaFunction('@stringify', [], stringify, self.glob)
            self.vars: dict[str] = {}


        def callmethod(self, method, args: list):
            method: LumaInterpreter.LumaFunction = self.functions[method]
            r = method.run(args, self)
            return r
        

        def instance(self, args: list, name):
            return LumaInterpreter.IntancedLumaObject(self.vars, self.functions, self.name, args, name, self.glob, self.parents)


        def __str__(self):
            r = self.functions['@stringify'].run([], self)
            return r
            
        
        def debug(self, trailing: str = '', prnt: bool = True):
            debugstr = ''
            debugdict: dict[str, str | list] = {'name': self.name, 'vars': [], 'functions': {}}
            debugstr += f'Class: {self.name}\n'
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


    class IntancedLumaObject(LumaClass):
        def __init__(self, varis: dict, functions: dict, name: str, args: list[Any], instancename: str, glob: dict[str, Any], parents: list[str]):
            self.vars = varis
            self.parents = parents
            self.functions = functions
            self.name = name
            self.glob = glob
            self.instance(args, instancename)

        
        def instance(self, args: list, name):
            interpreter: LumaInterpreter = get_current_interpreter(self.glob)
            self.instancen = name
            interpreter.vars[name] = self
            interpreter.vars[name].callmethod('constructor', args)
            del interpreter.vars[name]
            

    class LumaNameError(NameError):
        def __init__(self, *args):
            super().__init__(*args)


    class LumaTypeError(TypeError):
        def __init__(self, *args):
            super().__init__(*args)

    
    class LumaSyntaxError(SyntaxError):
        def __init__(self, *args):
            super().__init__(*args)

    
    class LumaAttributeError(AttributeError):
        def __init__(self, *args):
            super().__init__(*args)


    class LumaModuleNotFoundError(ModuleNotFoundError):
        def __init__(self, *args):
            super().__init__(*args)


    class LumaException(Exception):
        def __init__(self, *args):
            super().__init__(*args)


def get_current_interpreter(glob: dict[str, Any]) -> (LumaInterpreter | None):
    return next((v for v in glob.values() if isinstance(v, LumaInterpreter)), None)


def log(*texts):
    with open('log.txt', 'a') as logf:
        logf.write(', '.join(map(str, texts)) + '\n')