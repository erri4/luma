from functions import isnumber, reverse_list
from types import FunctionType
import sys
import json
import copy
import re

###################################################
'''
TODO:
. realvalue (includelist)
. add builtin classes
# r"data": raw data
# when eval this: return py str
# when eval "data": return lm str (r"data")

. better cond eval

. import lib:lib.lum

. one liner; ez

. lists (length)

. dictinaries

ONLY when finished: self.keywords: [...] (not setable)
'''
class LumaInterpreter:
    LOGICAL_OPERATORS: list[str] = [' == ', ' =< ', ' >= ', ' > ', ' < ', ' in ', 'not ', ' and ', ' or ']
    OPERATORS: dict[str, str] = {
        '-': '@subtraction',
        '+': '@addition',
        '/': '@division',
        '*': '@multiplication',
    }


    def __init__(self):
        self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
        def nativecode(pytext):
            r = eval(str(pytext))
            return r
        
        def packstr(string):
            r = json.dumps(str(string))
            return r
        self.functions['nativecode'] = self.LumaFunction('nativecode', ['pytext'], nativecode)
        self.functions['packstr'] = self.LumaFunction('packstr', ['string'], packstr)
        self.classes: dict[str, LumaInterpreter.LumaClass] = {}
        self.vars: dict[str] = {}
        self.localparams: list[dict[str]] = []


    def run(self, program: str, filename: str):
        self.scopes: list[str] = [program]
        self.runimport('builtins.lum')
        linenum = 1
        for line in program.splitlines():
            self.process(line, linenum - 1)
            linenum += 1
            '''except LumaInterpreter.LumaNameError as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
            '''except LumaInterpreter.LumaSyntaxError as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
            '''except LumaInterpreter.LumaAttributeError as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
            '''except LumaInterpreter.LumaTypeError as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
            '''except LumaInterpreter.LumaException as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
            '''except Exception as e:
                print(f'File "{filename}", line {linenum}')
                print(f'    {line}')
                print(e)
                break'''
    

    def getfirstword(self, line: str):
        return line.split(' ')[0]
    

    def realvalue(self, expr: str):
        if isnumber(expr):
            if not '.' in expr:
                return int(expr)
            return float(expr)
        else:
            return expr
    

    def removetab(self, line: str):
        return line.replace('    ', '', 1) if line.startswith('    ') else line
    

    def generaterandomvarname(self):
        varname = '@sysvar'
        while varname in self.vars.keys():
            varname += 'donottouch'
        return varname
    

    def runimport(self, module):
        try:
            with open(module) as imported:
                linen = 1
                subprogram = imported.read()
                self.scopes.append(subprogram)
                for subline in subprogram.splitlines():
                    self.process(subline, linen)
                    linen += 1
                self.scopes.pop()
        except FileNotFoundError:
            raise LumaInterpreter.LumaModuleNotFoundError(f"No module named '{module}'")
    

    def runsubprogram(self, subprogram: str, Object = None):
        if Object == None:
            Object = self
        linen = 1
        subprogram = subprogram.splitlines()
        for i in range(len(subprogram)):
            subprogram[i] = self.removetab(subprogram[i])
        subprogram = '\n'.join(subprogram)
        self.scopes.append(subprogram)
        for subline in subprogram.splitlines():
            res = self.process(subline, linen, Object)
            if subline.startswith('return'):
                break
            linen += 1
        self.scopes.pop()
        return res if res else None

    
    def process(self, line: str, linenum: int, Object = None):
        if Object == None:
            vars = self.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = self.functions
        else:
            Object: LumaInterpreter | LumaInterpreter.LumaClass
            vars = Object.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = Object.functions
        program = self.scopes[-1]
        if line.startswith('function'):
            func_name = line[9:line.find(' (')]
            args = line[line.find(' (') + 2:line.find(')')].split(', ')
            if args == ['']:
                args = []
            a = program[program.find(f'{func_name} (') + len(func_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions[func_name] = self.LumaFunction(func_name, args, body)
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
                self.classes[class_name] = copy.deepcopy(self.classes[parent])
                self.classes[class_name].name = class_name
            else:
                self.classes[class_name] = self.LumaClass(class_name)
            self.runsubprogram(body, self.classes[class_name])
        elif line.startswith('constructor'):
            class_name = line[12:line.find(' (')]
            args = line[line.find(' (') + 2:line.find(')')].split(', ')
            if args == ['']:
                args = []
            a = program[program.find(f'{class_name} (') + len(class_name) + 2:]
            stop = len(a[:a.find('){') + 3])
            for linee in a[a.find('){') + 3:].splitlines():
                if linee != '':
                    if linee[0] == '}':
                        break
                stop += len(linee) + 1
            body = a[a.find('){') + 3:stop].strip()
            functions['constructor'] = self.LumaFunction('constructor', args, body)
        elif line.startswith('set'):
            varname = line[4:line.find('to') - 1]
            value = self.evaluate(line[line.find('to') + 3:], varname)
            if varname.count('.') == 1:
                instancename = varname.split('.')[0]
                if instancename == 'this':
                    scopes: list[dict] = reverse_list(self.localparams)
                    for scope in scopes:
                        if 'this' in scope.keys():
                            scope['this'].vars[varname.split('.')[1]] = value
                elif varname.split('.')[0] in self.vars.keys():
                    vars[instancename].vars[varname.split('.')[1]] = value
            else:
                vars[varname] = value
        elif line.startswith('import'):
            module = line[7:]
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
            if eval(condition):
                self.runsubprogram(body)
            else:
                foundelif = False
                for i in range(len(conditions)):
                    con = conditions[i]
                    bd: str = bodys[i]
                    if eval(con):
                        self.runsubprogram(bd)
                        foundelif = True
                        break
                if not foundelif:
                    self.runsubprogram(elsebody)
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
            return self.evaluate(value.strip())
        elif line.startswith('//') or line == '' or line.startswith(' ') or line == '}' or line.startswith('elseif') or line.startswith('else'):
            pass
        elif line.count('.') == 1 and self.getfirstword(line).split('.')[0] in self.vars.keys():
            dexpr = self.getfirstword(line)
            self.vars: dict[str, LumaInterpreter.LumaClass]
            instancename = dexpr.split('.')[0]
            propertyname = dexpr.split('.')[1]
            if propertyname in self.vars[instancename].functions.keys():
                args = self.extractargs(line.strip(), f'{instancename}.{propertyname}')
                if len(args) == len(self.vars[instancename].functions[propertyname].args):
                    self.vars[instancename].callmethod(propertyname, args, instancename)
                else:
                    raise LumaInterpreter.LumaTypeError(f"function '{instancename}.{propertyname}' expected {len(self.vars[instancename].functions[propertyname].args)} arguments but got {len(args)}")
        else:
            if self.getfirstword(line) in functions.keys():
                func_name = self.getfirstword(line)
                args = self.extractargs(line, func_name)
                if len(args) == len(functions[func_name].args):
                    functions[func_name].run(args)
                else:
                    raise LumaInterpreter.LumaTypeError(f"function '{func_name}' expected {len(self.functions[func_name].args)} arguments but got {len(args)}")
            else:
                raise LumaInterpreter.LumaNameError(f"undefined function {self.getfirstword(line)}")
    

    def processcondition(self, condition: str):
        cond = self.splitbyop(condition)
        r = []
        for part in cond:
            if part in self.LOGICAL_OPERATORS:
                r.append(part)
            else:
                r.append(json.dumps(self.evaluate(part)))
        return ''.join(r)
    

    def splitbyop(self, expr):
        pattern = r'\s*(' + '|'.join(re.escape(op) for op in self.LOGICAL_OPERATORS) + r')\s*'

        tokens = []
        while expr:
            match = re.search(pattern, expr)
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
        a = line[line.find(' (') + 2:-1]
        opened = 0
        for char in a:
            if char == '(':
                opened += 1
            elif char == ')':
                opened -= 1
        rawargs = line[len(funcname) + 2:-1]
        if rawargs == '':
            return []
        args = self.smrtsplt(rawargs, ', ')
        for i in range(len(args)):
            args[i] = self.evaluate(args[i])
        return args
    

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
        parts = expr.split(sep)
        i = 0
        while i < len(parts):
            part = parts[i]
            if not self.termisclosed(part):
                parts[i] = sep.join(parts[i:i + 2])
                del parts[i + 1]
                continue
            i += 1

        return parts


    def evaluate(self, expr: str, evalforwhat = None, cond = False):
        if not evalforwhat:
            evalforwhat = self.generaterandomvarname()
        
        scopes: list[dict] = reverse_list(self.localparams)
        for scope in scopes:
            if expr in scope.keys():
                scope: dict[str, LumaInterpreter.LumaClass]
                return scope[expr]
        for op in self.OPERATORS:
            if f' {op} ' in expr and len(self.smrtsplt(expr, f' {op} ')) > 1:
                res = ''
                terms = self.smrtsplt(expr, f' {op} ')
                term0 = self.evaluate(terms[0])
                if type(term0) == LumaInterpreter.LumaClass:
                    if self.OPERATORS[op] in term0.functions:
                        opstr = f'{terms[0]}.{self.OPERATORS[op]} ({f' {op} '.join(terms[1:])})'
                        opstrr = self.evaluate(opstr)
                        return opstrr
                    else:
                        raise LumaInterpreter.LumaTypeError(f"unsupported opertaor: unable to perform operator {op} on types '{self.evaluate(f'&{term0}')}' and '{self.evaluate(f"&{f' {op} '.join(terms[1:])}")}'")
                for term in terms:
                    res += str(self.evaluate(term))
                return res
        if isnumber(expr):
            return self.evaluate(f'int (r"{expr}")', evalforwhat)
        elif expr.startswith('"') and expr.endswith('"') and not '"' in expr[1:-1]:
            return self.evaluate(f'str (r"{expr[1:-1]}")', evalforwhat)
        elif expr in self.vars.keys():
            return self.vars[expr]
        elif expr[0] == '&':
            data: LumaInterpreter.LumaClass = self.evaluate(expr[1:])
            return data.name if type(data) == LumaInterpreter.LumaClass else "raw " + type(data).__name__
        elif expr.startswith('r"') and expr.endswith('"') and not '"' in expr[2:-1]:
            return self.realvalue(expr[2:-1])
        elif expr.count('.') > 0 and len(self.smrtsplt(expr, '.')) > 1:
            i = 0
            instancename = expr.split('.')[i]
            while not self.termisclosed(instancename):
                i += 1
                instancename += '.' + expr.split('.')[i]
            propertyname = self.getfirstword(expr.split('.')[i + 1])
            instance = None
            instance: LumaInterpreter.LumaClass = self.evaluate(instancename)
            if instance:
                if propertyname in instance.vars.keys():
                    return instance.vars[propertyname]
                elif propertyname in instance.functions.keys():
                    args = self.extractargs(expr.strip(), f'{instancename}.{propertyname}')
                    if len(args) == len(instance.functions[propertyname].args):
                        r = instance.callmethod(propertyname, args)
                        return r
                    raise LumaInterpreter.LumaTypeError(f"function '{propertyname}' expected {len(instance.functions[propertyname].args)} arguments but got {len(args)}")
                else:
                    raise LumaInterpreter.LumaAttributeError(f"undefined '{instancename}.{propertyname}'")
            else:
                raise LumaInterpreter.LumaNameError(f"undefined variable '{instancename}'")
        elif self.getfirstword(expr) in self.classes.keys():
            args = self.extractargs(expr.strip(), self.getfirstword(expr.strip()))
            if len(args) == len(self.classes[self.getfirstword(expr.strip())].functions['constructor'].args):
                instance = self.classes[self.getfirstword(expr.strip())].instance(args, evalforwhat)
                return instance
            else:
                raise LumaInterpreter.LumaTypeError(f"function '{self.getfirstword(expr)}.constructor' expected {len(self.classes[self.getfirstword(expr.strip())].functions['constructor'].args)} arguments but got {len(args)}")
        elif self.getfirstword(expr) in self.functions.keys():
            args = self.extractargs(expr.strip(), self.getfirstword(expr))
            if len(args) == len(self.functions[self.getfirstword(expr.strip())].args):
                r = self.functions[self.getfirstword(expr.strip())].run(args)
                return r
            else:
                raise LumaInterpreter.LumaTypeError(f"function '{self.getfirstword(expr)}' expected {len(self.functions[self.getfirstword(expr)].args)} arguments but got {len(args)}")
        else:
            raise LumaInterpreter.LumaNameError(f"undefined variable '{expr}'")

    class LumaFunction:
        def __init__(self, name: str, args: list[str], body: str | FunctionType):
            self.name = name
            self.args = args
            self.body = body


        def run(self, args: list, Object = None, varsholder = None):
            argdict = {}
            interpreter: LumaInterpreter = get_current_interpreter()
            if varsholder == None:
                varsholder = interpreter.vars
            Object: LumaInterpreter.LumaClass | None
            for i in range(len(args)):
                argdict[self.args[i]] = args[i]
            if Object:
                argdict['this'] = Object
            interpreter: LumaInterpreter
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

    
    class LumaClass:
        def __init__(self, name):
            self.name = name
            self.instancen = None
            self.functions: dict[str, LumaInterpreter.LumaFunction] = {}

            def stringify():
                return f'<{self.name} object from luma>'
            
            self.functions['@stringify'] = LumaInterpreter.LumaFunction('@stringify', [], stringify)
            self.vars: dict[str] = {}


        def instance(self, args: list, name):
            interpreter: LumaInterpreter = get_current_interpreter()
            instance = copy.deepcopy(self)
            instance.instancen = name
            interpreter.vars[name] = instance
            interpreter.vars[name].callmethod('constructor', args)
            del interpreter.vars[name]
            return instance


        def callmethod(self, method, args: list, varsholder = None):
            method: LumaInterpreter.LumaFunction = self.functions[method]
            r = method.run(args, self, varsholder)
            return r


        def __str__(self):
            r = self.functions['@stringify'].run([], self)
            return r
            

        def debug(self):
            print(f'Class: {self.name}')
            print('Functions:')
            for func in self.functions.keys():
                print(f'    {func}')
            print('Variables:')
            for var in self.vars.keys():
                print(f'    {var}: {self.vars[var]}')
            

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


def get_current_interpreter() -> (LumaInterpreter | None):
    for var in globals().keys():
        if type(globals()[var]) == LumaInterpreter:
            return globals()[var]
    return None


def log(*texts):
        with open('log.txt', 'a') as log:
            text = ''
            for txt in texts:
                if type(text) == str:
                    text += str(txt) + ', '
            log.write(text[:-2] + '\n')


if __name__ == '__main__':
    filename = sys.argv[1]
    interpreter = LumaInterpreter()
    with open('log.txt', 'w') as logf:
            logf.write('')
    if filename.endswith('.lum'):
        try:
            with open(f'{filename}') as file:
                program = file.read()
            interpreter.run(program, filename)
        except FileNotFoundError:
            print(f'The file {filename} does not exists.')
    else:
        print(f'The file {filename} is not a luma program.')
