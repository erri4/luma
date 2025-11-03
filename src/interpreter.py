from typing import Any, Callable, Union, LiteralString
import importlib.util
import operator
import sys
import json
import re
import os


r"""
TODO:
OPTIMIZE
compile: nuitka --follow-imports .\src\luma.py --standalone --windows-console-mode=force

. pmfl
"""

EvaluatedType = Union["LumaInterpreter.InstancedLumaObject", int, str, dict]


class LumaInterpreter:
    _instance = None
    env: "dict[str, EvaluatedType | LumaInterpreter.LumaFunction | LumaInterpreter.LumaClass]" = {}
    localparams: list[dict[str, EvaluatedType]] = []
    LOGICAL_OPERATORS: list[str] = [
        " == ",
        " <= ",
        " =< ",
        " >= ",
        " > ",
        " < ",
        "not ",
        " and ",
        " or ",
    ]
    OPERATORS: dict[str, str] = {
        "-": "@subtraction",
        "+": "@addition",
        "/": "@division",
        "*": "@multiplication",
        "+=": "@addition",
        "-=": "@subtraction",
        "*=": "@multiplication",
        "/=": "@division",
    }
    REAL_OPERATORS: dict[str, Callable] = {
        "-": operator.sub,
        "+": operator.add,
        "/": operator.truediv,
        "*": operator.mul,
    }
    PY_IMPL_CLASSES = ["bool", "dict", "str"]
    NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")
    LOGICAL_OP_RE = re.compile(
        r"\s*(" + "|".join(re.escape(op) for op in LOGICAL_OPERATORS) + r")\s*"
    )
    SAVED_KEYWORDS: list[str] = ["set", "to", "function", "constructor", "class", "null", "false", "true", "import", "if", "extend", "elseif", "else", "as", "try", "catch", "while", "stop", "again", "return", "throw"]
    tb: list[tuple[int, str, str]] = []
    overloads: dict[str, list[Callable]] = {}
    overrides: dict[str, list[Callable]] = {}
    filename: str = None
    scopes: list[str] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self, program: str, filename: str):
        def nativecode(
            pytext: str, kwargs: LumaInterpreter.InstancedLumaObject | None = None
        ):
            sys.path.append(r"C:\PyLuma")
            sys.path.append(os.path.expanduser('~/PyLuma'))
            globs = {"filename": self.filename}
            data: dict[str | LumaInterpreter.InstancedLumaObject["str"], Any] = (
                kwargs.value if kwargs else {}
            )
            for key in list(data.keys()):
                data[str(key)] = data[key]
            r = eval(str(pytext), globs | data)
            return r

        self.env["nativecode"] = self.LumaFunction(
            "nativecode",
            [{"name": "pytext"}, {"name": "kwargs", "default": None}],
            nativecode,
            0,
            "INTERNAL",
        )

        module = self.LumaClass("module")
        self.env["module"] = module

        dictcls = self.LumaClassDict("dict")
        self.env["dict"] = dictcls
        boolcls = self.LumaClassBool("bool")
        self.env["bool"] = boolcls
        strcls = self.LumaClassStr("str")
        self.env["str"] = strcls
        BaseError = self.LumaClass("baseError")

        def constructor(msg, this=None):
            setattr(this, 'msg', msg)
            setattr(this, 'tb', LumaInterpreter().traceback())

        BaseError.functions["constructor"] = LumaInterpreter.LumaFunction(
            "constructor", [{"name": "msg", "default": self.env['str'].instance([""])}], constructor, 0, "INTERNAL",
        )
        def trigger(this=None):
            raise LumaInterpreter.LumaException(this)

        BaseError.functions["trigger"] = LumaInterpreter.LumaFunction(
            "trigger", [], trigger, 0, "INTERNAL",
        )
        def stringify(this=None):
            return getattr(this, 'msg')

        BaseError.functions["@stringify"] = LumaInterpreter.LumaFunction(
            "@stringify", [], stringify, 0, "INTERNAL",
        )
        self.env["baseError"] = BaseError

        self.filename = filename
        self.scopes.append(program)
        self.runimport(":builtins.lum", None)
        try:
            self.runsubprogram(program, infunc=False, file=self.filename)
        except LumaInterpreter.LumaException as e:
            print(e)

    @staticmethod
    def getfirstword(line: str):
        return line.split(" ")[0]

    def isnumber(self, data: str | int | float):
        if type(data) is str:
            return bool(re.match(self.NUMBER_RE, data))
        return isinstance(data, (int, float))

    @staticmethod
    def reverse_list(r):
        return r[::-1] if isinstance(r, list) else []
    
    def traceback(self):
        return self.tb

    def realvalue(self, expr: str, includelist=False):
        if not includelist:
            if self.isnumber(expr):
                if "." not in expr:
                    return int(expr)
                return float(expr)
            else:
                return expr
        else:
            if expr[0] == "[" and expr[-1] == "]":
                list_content = expr[1:-1].strip()
                if not list_content:
                    return {}
                items = LumaInterpreter.smrtsplt(list_content, ",")
                return {
                    self.evaluate(str(i)): self.evaluate(item.strip())
                    for i, item in enumerate(items)
                }
            elif expr[0] == "{" and expr[-1] == "}":
                dict_content = expr[1:-1].strip()
                if not dict_content:
                    return {}
                items = LumaInterpreter.smrtsplt(dict_content, ", ")
                result = {}
                for item in items:
                    if ":" not in item:
                        continue
                    key_str, value_str = item.split(": ", 1)
                    key = self.evaluate(key_str.strip())
                    value = self.evaluate(value_str.strip())
                    result[key] = value
                return result

    @staticmethod
    def removetab(line: str):
        return line.replace("    ", "", 1) if line.startswith("    ") else line

    @staticmethod
    def preprocess(prog: str):
        lines = prog.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("/*"):
                c = i
                while not lines[c].strip().endswith("*/"):
                    del lines[c]
                del lines[c]
                continue
            i += 1
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("//"):
                del lines[i]
                continue
            i += 1
        i = 0
        while i < len(lines):
            line = lines[i]
            if "; " in line:
                spacenum = len(line) - len(line.lstrip())
                lines[i] = line[: line.find("; ")]
                lines.insert(i + 1, " " * spacenum + line[line.find("; ") + 2 :])
            i += 1
        return "\n".join(lines)

    def generaterandomvarname(self):
        varname = "@tmpsysvar"
        while varname in self.env.keys():
            varname += "donottouch"
        return varname

    def runimport(self, module: str, name: str):
        if ":" in module:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            module = os.path.join(
                base_dir, module[: module.find(":")], module[module.find(":") + 1 :]
            )
        try:
            with open(module) as imported:
                subprogram = imported.read()
                if name is None:
                    self.runsubprogram(subprogram, infunc=False, file=module)
                else:
                    body = "class module {\n    constructor module (){\n        \n    }\n\n"
                    for line in subprogram.splitlines():
                        body += "    " + line + "\n"
                    body += "}"
                    self.runsubprogram(body, infunc=False, file=module)
                    self.runsubprogram(f"set {name} to new module ()", file=module)
        except FileNotFoundError:
            LumaInterpreter.throw(
                self.env["moduleNotFoundError"],
                f"No module named '{module}'",
            )

    def runext(self, ext: str):
        if ":" in ext:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            ext = os.path.join(
                base_dir, ext[: ext.find(":")], ext[ext.find(":") + 1 :]
            )
        module_name = os.path.splitext(os.path.basename(ext))[0]
        module_dir = os.path.dirname(ext)
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)

        try:
            spec = importlib.util.spec_from_file_location(module_name, ext)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except FileNotFoundError:
            LumaInterpreter.throw(self.env['extensionError'], f"The file at {ext} does not exist.")

        if hasattr(module, "LumaExtension"):
            for name in module.LumaExtension:
                self.env[name] = self.parse_py(module.LumaExtension[name])
        else:
            LumaInterpreter.throw(self.env['extensionError'], f"The extension at {ext} is not a valid extension: LumaExtension dict is not present")

    def parse_py(self, token):
        if type(token) is dict:
            if token.get('type', None) == 'classType':
                thecls = self.LumaClass(token['name'], [])
                if token['parent']:
                    parent = token['parent']
                    thecls.functions = self.env[parent].functions.copy()
                    thecls.vars = self.env[parent].vars.copy()
                    thecls.parents = self.env[parent].parents.copy()
                    thecls.parents.append(parent)
                thecls.vars |= {var['name']: self.parse_py(var) for var in token['vars']}
                thecls.functions |= {func['name']: self.parse_py(func) for func in token['functions']}
                thecls.classes |= {cls_['name']: self.parse_py(cls_) for cls_ in token['classes']}
                thecls.functions['constructor'] = self.parse_py(token['constructor']) if token['constructor'] else thecls.functions['constructor']
                return thecls
            if token.get('type', None) == 'functionType':
                args = token['args']
                for arg in args:
                    try:
                        arg['default'] = self.parse_py(arg['default'])
                    except KeyError: pass
                return self.LumaFunction(token['name'], args, token['body'], 0, "EXTERNAL")
            if type(token.get('type', None)).__name__ == 'Overload':
                funcname = token.get('type', None).funcname
                if not self.overloads.get(funcname, None):
                    self.overloads[funcname] = [token['function']]
                else:
                    self.overloads[funcname].append(token['function'])
            if type(token.get('type', None)).__name__ == 'Override':
                funcname = token.get('type', None).funcname
                if not self.overrides.get(funcname, None):
                    self.overrides[funcname] = [token['function']]
                else:
                    self.overrides[funcname].append(token['function'])
            if token.get('type', None) in self.env.keys():
                if type(self.env[token.get('type', None)]) is LumaInterpreter.LumaClass or token.get('type', None) in self.PY_IMPL_CLASSES:
                    return self.env[token['type']].instance([self.parse_py(tk) for tk in token['args']])
        if type(token).__name__ == "Raw":
            if type(token.data).__name__ == "DictToDict":
                newdct = {}
                for key in token.data.keys:
                    newdct[self.parse_py(key)] = self.parse_py(token.data[key])
                return newdct
            else:
                return token.data


    def runsubprogram(
        self, subprogram: str, Object=None, infunc: bool = True, realfunc: bool = False, line1: int = 1, file: str = ""
    ):
        if file == '': raise
        if Object is None:
            Object = self
        subprogram = LumaInterpreter.preprocess(subprogram)
        subprogram = subprogram.splitlines()
        if infunc:
            for i in range(len(subprogram)):
                subprogram[i] = LumaInterpreter.removetab(subprogram[i])
        subprogram = "\n".join(subprogram)
        self.scopes.append(subprogram)
        res = None
        l = 0
        for subline in subprogram.splitlines():
            l += 1
            self.tb.append([line1, subline, file])
            try:
                res = self.process(subline, line1 if not infunc else l, Object, file)
            except LumaInterpreter.SubProgramExitCode as e:
                if e.code == "return":
                    self.tb.pop()
                    self.scopes.pop()
                    return e.data
                else:
                    self.tb.pop()
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode(e.code, e.data) from e
            if subline.startswith("return"):
                if not realfunc:
                    self.tb.pop()
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode("return", res)
                else:
                    self.tb.pop()
                    break
            line1 += 1
            self.tb.pop()
        self.scopes.pop()
        return res

    def process(
        self,
        line: str,
        linenum: int,
        Object: "LumaInterpreter | LumaInterpreter.InstancedLumaObject | None" = None,
        file: str = '',
    ):
        line = line.replace(r"\n", "\n")
        for func in self.overloads.get('process', []):
            if func(self, line, linenum, Object, file):
                return
        if Object is None or type(Object) is LumaInterpreter:
            varis = self.env
            functions: dict[str, LumaInterpreter.LumaFunction] = self.env
            classes: dict[str, LumaInterpreter.LumaFunction] = self.env
        else:
            varis = Object.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = Object.functions
            classes: dict[str, LumaInterpreter.LumaClass] = Object.classes
        program = self.scopes[-1]
        firstword = LumaInterpreter.getfirstword(line)
        if firstword == "function":
            func_name = line[9 : line.find("(")].strip()
            args = self.parse_args(line[line.find("(") + 1 : line.rfind(")")])
            body = ''
            for subline in program.splitlines()[linenum:]:
                if (subline + " ")[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            if line[-1] == '}':
                body = ''
            functions[func_name] = self.LumaFunction(func_name, args, body, linenum+1, file)
        elif firstword == "throw":
            exc: LumaInterpreter.InstancedLumaObject = self.evaluate(line[6:])
            exc.callmethod('trigger', [])
        elif firstword == "class":
            class_name = line[6 : line.find(" {")]
            body = ''
            for subline in program.splitlines()[linenum:]:
                if (subline + " ")[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            if line[-1] == '}':
                body = ''
            parent = None
            classes[class_name] = self.LumaClass(
                class_name,
            )
            if "(" in class_name and ")" in class_name:
                parent = class_name[class_name.find("(") + 1 : class_name.find(")")]
                class_name = class_name[: class_name.find("(") - 1]
                classes[class_name] = self.LumaClass(
                    class_name,
                )
                classes[class_name].functions = classes[parent].functions.copy()
                classes[class_name].vars = classes[parent].vars.copy()
                classes[class_name].parents = classes[parent].parents.copy()
                classes[class_name].parents.append(parent)
            self.runsubprogram(body, classes[class_name], line1=linenum+1, file=file)
        elif firstword == "constructor":
            class_name = line[12 : line.find(" (")]
            args = self.parse_args(line[line.find(" (") + 2 : line.rfind(")")])
            body = ''
            for subline in program.splitlines()[linenum:]:
                if (subline + " ")[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            if line[-1] == '}':
                body = ''
            functions["constructor"] = self.LumaFunction(
                "constructor",
                args,
                body,
                linenum+1,
                file
            )
        elif firstword == "set":
            varname = line[4 : line.find("to") - 1]
            value = self.evaluate(line[line.find("to") + 3 :], varname)
            if varname.count(".") == 1:
                instancename = varname.split(".")[0]
                if instancename == "this":
                    scope: dict[str, LumaInterpreter.InstancedLumaObject] = (
                        self.localparams[-1]
                    )
                    if "this" in scope.keys():
                        scope["this"].vars[varname.split(".")[1]] = value
                elif varname.split(".")[0] in self.env.keys():
                    varis[instancename].vars[varname.split(".")[1]] = value
            else:
                if varname == "this":
                    LumaInterpreter.throw(
                        self.env["typeError"],
                        "cannot use 'this' keyword outside class method call",
                    )
                if varname in self.SAVED_KEYWORDS:
                    if varname in ['true', 'false', 'null']:
                        if not file.endswith("builtins.lum"):
                            LumaInterpreter.throw(
                                self.env["typeError"],
                                f"cannot assign to '{varname}': saved keyword",
                            )
                        else:
                            varis[varname] = value
                            return
                    LumaInterpreter.throw(
                        self.env["typeError"],
                        f"cannot assign to '{varname}': saved keyword",
                    )
                varis[varname] = value
        elif firstword == "import":
            module = LumaInterpreter.getfirstword(line[7:])
            name = None
            if LumaInterpreter.getfirstword(line[7:]) != line[7:]:
                name = line[11 + len(LumaInterpreter.getfirstword(line[7:])) :]
            self.runimport(module, name)
        elif firstword == "extend":
            module = LumaInterpreter.getfirstword(line[7:])
            self.runext(module)
        elif firstword == "try":
            body = ''
            for subline in program.splitlines()[linenum:]:
                if subline[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            linenu = int(linenum) + len(body.splitlines()) + 2
            subline = ""
            try:
                subline = LumaInterpreter.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            bodys = {}
            excs = []
            while subline.startswith("catch"):
                exc = subline[7 : subline.find(")")].split(' as ')
                bd = ''
                for subline in program.splitlines()[linenu:]:
                    if subline[0] == '}':
                        break
                    bd += subline + "\n"
                bd = bd.strip()
                excs.append([exc, linenu])

                bodys[exc[0]] = bd
                linenu += len(bd.splitlines()) + 2

                try:
                    subline = LumaInterpreter.removetab(
                        program.splitlines()[linenu - 1]
                    )
                except IndexError:
                    break
            try:
                self.runsubprogram(body, line1=linenum + 1, file=file)
            except LumaInterpreter.LumaException as e:
                catched = False
                for exc in excs:
                    if exc[0][0] == e.exc.typename:
                        try:
                            self.env[exc[0][1]] = e.exc
                        except IndexError: pass
                        self.runsubprogram(bodys[exc[0][0]], line1=exc[1] + 1, file=file)
                        catched = True
                if not catched:
                    for exc in excs:
                        if exc[0][0] == "anyError":
                            try:
                                self.env[exc[0][1]] = e.exc
                            except IndexError: pass
                            self.runsubprogram(bodys[exc[0][0]], line1=exc[1] + 1, file=file)
                            catched = True
                if not catched:
                    raise e from None
        elif firstword == "if":
            condition = line[4 : line.find("){")]
            body = ''
            for subline in program.splitlines()[linenum:].copy():
                if subline[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            conditions = []
            bodys = {}
            stops = {}
            linenu = int(linenum) + len(body.splitlines()) + 2
            subline = ""
            try:
                subline = LumaInterpreter.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            while subline.startswith("elseif"):
                cond = subline[8 : subline.find(")")]
                bd = ''
                for subline in program.splitlines()[linenu:]:
                    if subline[0] == '}':
                        break
                    bd += subline + "\n"
                bd = bd.strip()
                conditions.append(cond)

                bodys[cond] = bd
                stops[cond] = linenu
                linenu += len(bd.splitlines()) + 2

                try:
                    subline = LumaInterpreter.removetab(
                        program.splitlines()[linenu - 1]
                    )
                except IndexError:
                    break
            try:
                subline = LumaInterpreter.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            elsebody = ""
            if subline.startswith("else"):
                for subline in program.splitlines()[linenu:]:
                    if subline[0] == '}':
                        break
                    elsebody += subline + "\n"
                elsebody = elsebody.strip()
            stops['else'] = linenu
            r = None
            ifcond = self.evaluate(condition)
            if bool(ifcond):
                r = self.runsubprogram(body, line1=linenum + 1, file=file)
            else:
                foundelif = False
                for i in range(len(conditions)):
                    con = conditions[i]
                    bd: str = bodys[con]
                    if self.evaluate(con):
                        self.tb.append([stops[con], "elseif (" + con + "){", file])
                        r = self.runsubprogram(bd, line1=stops[con]+1, file=file)
                        self.tb.pop()
                        foundelif = True
                        break
                if not foundelif:
                    self.tb.append([stops['else'], "else {", file])
                    r = self.runsubprogram(elsebody, line1=stops['else']+1, file=file)
                    self.tb.pop()
            return r
        elif firstword == "while":
            condition = line[7 : line.find("){")]
            body = ''
            for subline in program.splitlines()[linenum:]:
                if subline[0] == '}':
                    break
                body += subline + "\n"
            body = body.strip()
            while self.evaluate(condition):
                try:
                    self.runsubprogram(body, line1 = linenum + 1, file=file)
                except LumaInterpreter.SubProgramExitCode as e:
                    if e.code == "stop":
                        break
                    elif e.code == "again":
                        continue
                    else:
                        raise LumaInterpreter.SubProgramExitCode(e.code, e.data)
        elif firstword == "return":
            if line == "return":
                return
            value = line[7:]
            r = self.evaluate(value.strip())
            return r
        elif line == "again":
            raise LumaInterpreter.SubProgramExitCode("again")
        elif line == "stop":
            raise LumaInterpreter.SubProgramExitCode("stop")
        elif (
            line.strip() == ""
            or line.startswith("    ")
            or line == "}"
            or firstword == "elseif"
            or firstword == "else"
            or firstword == "catch"
        ):
            pass
        else:
            self.evaluate(line, line=linenum)

    @staticmethod
    def throw(
        exc: "LumaInterpreter.LumaClass",
        msg: "str | LumaInterpreter.InstancedLumaObject",
    ) -> None:
        exc.instance([msg]).callmethod('trigger', [])

    def processcondition(self, condition: str):
        cond = self.splitbyop(condition)
        r: list[EvaluatedType | str] = []
        for part in cond:
            if part in self.LOGICAL_OPERATORS:
                r.append(part)
            else:
                epart = self.evaluate(part)
                r.append(epart)
        return r

    def parse_args(self, input_string: str):
        if input_string == "":
            return []
        result = []
        tokens = [token.strip() for token in input_string.split(",")]

        for token in tokens:
            if "=" in token:
                name, value = [x.strip() for x in token.split("=", 1)]
                result.append({"name": name, "default": self.evaluate(value)})
            else:
                result.append({"name": token})

        return result

    def splitbyop(self, expr: str):
        tokens = []
        while expr:
            match = re.search(self.LOGICAL_OP_RE, expr)
            if match:
                before = expr[: match.start()].strip()
                if before:
                    tokens.append(before)
                tokens.append(match.group(1))
                expr = expr[match.end() :]
            else:
                if expr.strip():
                    tokens.append(expr.strip())
                break
        return tokens
    
    @staticmethod
    def removebracket(string: str):
        if string:
            if string[0] == '(':
                return string[1:]
        return string

    def extractargs(self, line: str, funcname):
        rawargs = LumaInterpreter.removebracket(line[len(funcname) + 1 : -1].strip())
        if rawargs == "":
            return []
        splitted = LumaInterpreter.smrtsplt(rawargs, ", ")
        return [self.evaluate(arg) for arg in splitted]

    @staticmethod
    def termisclosed(term):
        stack = []
        opening = {"(": ")", "{": "}", "[": "]"}
        closing = {")", "}", "]"}
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

    def evaluatecond(self, cond: tuple[EvaluatedType, str, EvaluatedType]):
        if not cond:
            return False
        i = 0
        result = None
        invert_next = False
        while i < len(cond):
            if (
                type(cond[i]) is not LumaInterpreter.InstancedLumaObject
                and cond[i] == "not "
            ):
                invert_next = not invert_next
                i += 1
                continue

            if i + 2 >= len(cond):
                break
            left, op, right = cond[i], cond[i + 1], cond[i + 2]
            val = LumaInterpreter.eval_single_condition((left, op, right))
            if invert_next:
                val = not val
                invert_next = False
            i += 3

            if result is None:
                result = val
            else:
                if i < len(cond) and cond[i] == "and ":
                    result = result and val
                    i += 1
                elif i < len(cond) and cond[i] == "or ":
                    result = result or val
                    i += 1
                else:
                    result = val
        r = self.env["bool"].instance([int(result)])
        return r

    @staticmethod
    def eval_single_condition(parts: tuple[EvaluatedType, str, EvaluatedType]):
        left_val, op, right_val = parts
        if op == " == ":
            return left_val == right_val
        elif op in (" <= ", " =< "):
            return left_val <= right_val
        elif op == " >= ":
            return left_val >= right_val
        elif op == " > ":
            return left_val > right_val
        elif op == " < ":
            return left_val < right_val
        else:
            return False

    def is_condition_expression(self, expr: str) -> bool:
        return any(
            [
                (len(LumaInterpreter.smrtsplt(expr, op)) == 2)
                for op in self.LOGICAL_OPERATORS
            ]
        )

    @staticmethod
    def get_oldest_parent(cls):
        for ancestor in reversed(cls.__mro__):
            if ancestor is not object:
                return ancestor
        return cls

    @staticmethod
    def smrtsplt(expr: str, sep: str):
        if (
            "'" not in expr
            and '"' not in expr
            and "(" not in expr
            and "[" not in expr
            and "{" not in expr
        ):
            return expr.split(sep)
        parts = []
        stack = []
        in_quotes = False
        quote_char = None
        sep_len = len(sep)
        expr_len = len(expr)
        brackets_open = {"(": ")", "[": "]", "{": "}"}
        brackets_close = {")", "]", "}"}

        start = 0
        i = 0
        while i < expr_len:
            c = expr[i]
            if c in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = c
                elif quote_char == c:
                    in_quotes = False
                    quote_char = None
                i += 1
                continue

            if not in_quotes:
                if expr.startswith(sep, i) and not stack:
                    parts.append(expr[start:i])
                    i += sep_len
                    start = i
                    if sep in brackets_open:
                        stack.append(brackets_open[sep])
                    continue

                if c in brackets_open:
                    stack.append(brackets_open[c])
                elif c in brackets_close:
                    if stack and stack[-1] == c:
                        stack.pop()

            i += 1

        parts.append(expr[start:])

        return parts

    @staticmethod
    def namourtype(obj: EvaluatedType):
        if type(obj) is LumaInterpreter.InstancedLumaObject:
            return obj.typename
        if type(obj) is LumaInterpreter.LumaClass:
            return "classType"
        if type(obj) is LumaInterpreter.LumaFunction:
            return "functionType"
        return "raw " + type(obj).__name__

    @staticmethod
    def is_obj_call(expr: str):
        expr = expr.strip()
        if "(" not in expr or expr.startswith("new") or expr.startswith("throw"):
            return False
        for op in LumaInterpreter.OPERATORS:
            if len(LumaInterpreter.smrtsplt(expr, op)) > 1:
                return False
        splitted = expr.split("(")
        prefix, rest = "(".join(splitted[0:-1]), splitted[-1]
        if not prefix.strip():
            return False
        if not rest.endswith(")"):
            return False

        return True
    
    @staticmethod
    def is_index_call(expr: str):
        expr = expr.strip()
        if "[" not in expr:
            return False
        for op in LumaInterpreter.OPERATORS:
            if len(LumaInterpreter.smrtsplt(expr, op)) > 1:
                return False
        splitted = expr.split("[")
        prefix, rest = "[".join(splitted[0:-1]), splitted[-1]
        i = expr.find('[')
        prefix = expr[:i]
        rest = expr[i+1:]
        if not prefix.strip():
            return False
        if not rest.endswith("]"):
            return False
        return True

    def evaluate(
        self, expr: str, evalforwhat: str | None = None, line: int = 0
    ):
        if not evalforwhat:
            evalforwhat = self.generaterandomvarname()
        firstword = LumaInterpreter.getfirstword(expr.strip())

        expr = expr.strip()
        scope = self.localparams[-1] if self.localparams else {}

        if (
            expr.startswith("(")
            and expr.endswith(")")
            and LumaInterpreter.termisclosed(expr[1:-1])
        ):
            return self.evaluate(expr[1:-1])
        elif self.is_condition_expression(expr):
            processedcond = self.processcondition(expr)
            r = self.evaluatecond(processedcond)
            return r

        for op in self.OPERATORS:
            op_token = f" {op} "
            if op_token not in expr:
                continue
            splitted = LumaInterpreter.smrtsplt(expr, op_token)
            if op_token in expr and len(splitted) > 1:
                terms = splitted
                term0 = self.evaluate(op_token.join(terms[:-1]))
                if type(term0) is LumaInterpreter.InstancedLumaObject:
                    if self.OPERATORS[op] in term0.functions:
                        if op in ['+=', '/=', '-=', '*=']:
                            if op_token.join(terms[:-1]) in self.env:
                                self.env[op_token.join(terms[:-1])] = term0.callmethod(self.OPERATORS[op], [self.evaluate(terms[-1])])
                                return self.env[op_token.join(terms[:-1])]
                            else:
                                LumaInterpreter.throw(
                                    self.env["typeError"],
                                    f"unsupported operator: unable to perform in place operator {op} on non-global variable {op_token.join(terms[:-1])}: it's non-global",
                                )
                        opstr = term0.callmethod(self.OPERATORS[op], [self.evaluate(terms[-1])])
                        return opstr
                    else:
                        LumaInterpreter.throw(
                            self.env["typeError"],
                            f"unsupported operator: unable to perform operator {op} on types '{LumaInterpreter.namourtype(self.evaluate(f'{terms[0]}'))}' and '{LumaInterpreter.namourtype(self.evaluate(f'{op_token.join(terms[1:])}'))}'",
                        )
                try:
                    return self.REAL_OPERATORS[op](term0, self.evaluate(terms[-1]))
                except TypeError:
                    LumaInterpreter.throw(
                        self.env["typeError"],
                        f"unsupported operator: unable to perform operator {op} on types '{LumaInterpreter.namourtype(self.evaluate(f'{terms[0]}'))}' and '{LumaInterpreter.namourtype(self.evaluate(f'{op_token.join(terms[1:])}'))}'",
                    )
        
        if expr[0] == "&":
            data: LumaInterpreter.LumaClass = self.evaluate(expr[1:])
            if type(data) is LumaInterpreter.LumaClass:
                return self.env["classType"]
            return (
                self.env[data.typename]
                if type(data) is LumaInterpreter.InstancedLumaObject
                else self.env["raw"]
            )
        elif LumaInterpreter.is_obj_call(expr):
            splitted = LumaInterpreter.smrtsplt(expr, '(')
            prefix = "(".join(splitted[0:-1])
            obj: LumaInterpreter.InstancedLumaObject = self.evaluate(prefix)
            args = self.extractargs(expr, prefix)
            r = obj.call(args)
            if type(r).__name__ == "ParseMe":
                r = self.parse_py(getattr(r, "data"))
            if r is None:
                return self.env['null']
            return r
        elif LumaInterpreter.is_index_call(expr):
            splitted = LumaInterpreter.smrtsplt(expr, '[')
            prefix = "[".join(splitted[0:-1])
            obj: LumaInterpreter.InstancedLumaObject = self.evaluate(prefix)
            index = self.evaluate(expr[len(prefix) + 1:-1])
            r = obj.callmethod('at', [index])
            return r
        elif expr in scope.keys():
            r = scope[expr]
            return r
        if firstword == "this":
            LumaInterpreter.throw(
                self.env["typeError"],
                "cannot use 'this' keyword outside class method call",
            )
        dotparts = LumaInterpreter.smrtsplt(expr, ".")
        if self.isnumber(expr):
            args = [self.realvalue(expr)]
            int_ = self.env["int"]
            float_ = self.env["float"]
            return float_.instance(args) if "." in expr else int_.instance(args)
        elif expr.startswith('"') and expr.endswith('"') and '"' not in expr[1:-1]:
            return self.env["str"].instance([self.realvalue(expr[1:-1])])
        elif expr.startswith("{") and expr.endswith("}"):
            return self.env["dict"].instance([self.realvalue(expr, includelist=True)])
        elif expr.startswith("[") and expr.endswith("]"):
            return self.env["list"].instance([self.realvalue(expr, includelist=True)])
        elif expr.startswith("'") and expr.endswith("'") and "'" not in expr[1:-1]:
            return self.env["str"].instance([self.realvalue(expr[1:-1])])
        elif expr in self.env.keys():
            r = self.env[expr]
            return r
        elif len(dotparts) > 1:
            instancename = ".".join(dotparts[0:-1])
            propertyname = dotparts[-1]
            instance: LumaInterpreter.InstancedLumaObject = self.evaluate(instancename)
            if instance:
                if propertyname in instance.vars.keys():
                    r = instance.vars[propertyname]
                    return r
                elif propertyname in instance.functions.keys():
                    return instance.tie(propertyname)
                elif propertyname in instance.classes.keys():
                    args = self.extractargs(expr.strip(), firstword)
                    instance = instance.classes[propertyname].instance(args)
                    return instance
                else:
                    LumaInterpreter.throw(
                        self.env["typeError"],
                        f"{instancename} (type {self.evaluate(f'&{instancename}')}) has no attribute '{propertyname}'",
                    )
            else:
                LumaInterpreter.throw(
                    self.env["typeError"],
                    "nullType object has no attributes",
                )
        elif firstword == "new":
            splitted = LumaInterpreter.smrtsplt(expr[4:], '(')
            prefix = "(".join(splitted[0:-1])
            args = self.extractargs(expr[4:].strip(), prefix)
            cls: LumaInterpreter.LumaClass = self.evaluate(prefix)
            instance = cls.instance(args)
            return instance
        else:
            LumaInterpreter.throw(
                self.env["nameError"],
                f"undefined variable or function '{firstword}'",
            )

    class LumaClass:
        def __init__(self, name: str, parents: list[str] = []):
            self.actualname = name
            self.typename = "classType"
            self.parents = parents
            self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
            self.classes: dict[str, LumaInterpreter.LumaClass] = {}

            def stringify(this=None):
                return f"<{self.typename} object>"

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
                0,
                "INTERNALCLS",
            )

            def repre(this=None):
                return str(this)

            self.functions["@repr"] = LumaInterpreter.LumaFunction(
                "@repr",
                [],
                repre,
                0,
                "INTERNALCLS",
            )
            self.vars: dict[str, EvaluatedType] = {}

        def __lbool__(self):
            return False

        def __repr__(self):
            return f"<class {self.actualname}>"

        def __eq__(self, other: "EvaluatedType | LumaInterpreter.LumaClass") -> bool:
            if type(other) is LumaInterpreter.LumaClass:
                return other.actualname == self.actualname
            return False

        def call(self, args):
            raise NotImplementedError

        def instance(self, args: list):
            return LumaInterpreter.InstancedLumaObject(
                self.vars,
                self.functions,
                self.classes,
                self.actualname,
                args,
                self.parents,
            )

    class LumaFunction:
        def __init__(
            self,
            name: str,
            args: list[dict[str, str | EvaluatedType]],
            body: str | Callable[[Any], Any],
            line: int,
            file: str,
        ):
            self.typename = "functionType"
            self.actualname = name
            self.args = args
            self.body = body
            self.line = line
            self.file = file

        def run(
            self, args: list, Object=None, varsholder=None
        ) -> "Any | LumaInterpreter.InstancedLumaObject | None ":
            interpreter = LumaInterpreter()
            if interpreter is None:
                raise TypeError("Could not find an active interpreter.")
            argdict = self.bind_values(args)
            if varsholder is None:
                varsholder = interpreter.env
            if Object is not None:
                argdict["this"] = Object
            interpreter.localparams.append(argdict)
            orig_vars = set(varsholder.keys())
            r = None
            if type(self.body) is str:
                r = interpreter.runsubprogram(self.body, realfunc=True, line1=self.line + 1, file=self.file)
            elif callable(self.body):
                rargs = []
                for key in argdict:
                    rargs.append(argdict[key])
                r = self.body(*rargs)
            added_keys = set(varsholder.keys()) - orig_vars
            for key in added_keys:
                varsholder.pop(key, None)
            interpreter.localparams.pop()
            return r

        def call(self, args):
            return self.run(args)

        def __repr__(self):
            return f"<functionType object named {self.actualname}>"

        def bind_values(self, args):
            result = {}
            value_index = 0

            for var in self.args:
                name = var["name"]

                if value_index < len(args):
                    result[name] = args[value_index]
                    value_index += 1
                elif "default" in var:
                    result[name] = var["default"]
                else:
                    LumaInterpreter.throw(
                        LumaInterpreter().env["typeError"],
                        f"function '{self.actualname}' expected {len(self.args)} arguments but got {len(args)}",
                    )

            if value_index < len(args):
                LumaInterpreter.throw(
                    LumaInterpreter().env["typeError"],
                    f"function '{self.actualname}' expected {len(self.args)} arguments but got {len(args)}",
                )

            return result

    class LumaClassDict(LumaClass):
        def __init__(self, name, parents=[]):
            super().__init__(name, parents)

            def constructor(
                value: dict, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ):
                this.value = value.copy()

            self.functions["constructor"] = LumaInterpreter.LumaFunction(
                "constructor", [{"name": "value"}], constructor, 0, "INTERNAL",
            )

            def at(
                pos, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ) -> Any:
                return this.value[pos]

            self.functions["at"] = LumaInterpreter.LumaFunction(
                "at", [{"name": "pos"}], at, 0, "INTERNAL",
            )

            def dctset(
                pos, value, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ) -> None:
                this.value[pos] = value

            self.functions["set"] = LumaInterpreter.LumaFunction(
                "set", [{"name": "pos"}, {"name": "value"}], dctset, 0, "INTERNAL",
            )

            def stringify(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                interpreter = LumaInterpreter()
                dct = "{"
                items = list(this.value.items())
                for i in range(len(items)):
                    k, v = items[i][0], items[i][1]
                    dct += (
                        str(k.callmethod("@repr", []))
                        + ": "
                        + str(v.callmethod("@repr", []))
                        + (", " if i + 1 in range(len(items)) else "")
                    )
                dct += "}"
                return interpreter.env["str"].instance(
                    [dct],
                )

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
                0,
                "INTERNAL",
            )

            def repre(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject['str']":
                interpreter = LumaInterpreter()
                dct = "{"
                items = list(this.value.items())
                for i in range(len(items)):
                    k, v = items[i][0], items[i][1]
                    dct += (
                        str(k.callmethod("@repr", []))
                        + ": "
                        + str(v.callmethod("@repr", []))
                        + (", " if i + 1 in range(len(items)) else "")
                    )
                dct += "}"
                return interpreter.env["str"].instance(
                    [dct],
                )

            self.functions["@repr"] = LumaInterpreter.LumaFunction(
                "@repr",
                [],
                repre,
                0,
                "INTERNAL",
            )

            def length(
                this: "LumaInterpreter.InstancedLumaObject['dict'] | LumaInterpreter.InstancedLumaObject['list'] | None" = None,
            ):
                int_ = LumaInterpreter().env["int"]
                obj = int_.instance([len(this.value)])
                return obj

            self.functions["len"] = LumaInterpreter.LumaFunction(
                "len",
                [],
                length,
                0,
                "INTERNAL",
            )

            def lbool(
                this: "LumaInterpreter.InstancedLumaObject['dict'] | LumaInterpreter.InstancedLumaObject['list'] | None" = None,
            ):
                return LumaInterpreter().env["bool"].instance([bool(len(this.value))])

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                lbool,
                0,
                "INTERNAL",
            )

    class LumaClassBool(LumaClass):
        def __init__(self, name, parents=[]):
            super().__init__(name, parents)

            def constructor(
                value: EvaluatedType,
                this: "LumaInterpreter.InstancedLumaObject['bool'] | None" = None,
            ) -> None:
                if (
                    LumaInterpreter.get_oldest_parent(type(value))
                    is LumaInterpreter.LumaClass
                ):
                    this.value = bool(LumaInterpreter.LumaClassBool.lbool(value))
                else:
                    this.value = bool(value)

            self.functions["constructor"] = LumaInterpreter.LumaFunction(
                "constructor", [{"name": "value"}], constructor, 0, "INTERNAL",
            )

            def stringify(
                this: "LumaInterpreter.InstancedLumaObject['bool'] | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject['str']":
                interpreter = LumaInterpreter()
                return interpreter.env["str"].instance([str(this.value).lower()])

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
                0,
                "INTERNAL",
            )

            def selfbool(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                return this.value

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                selfbool,
                0,
                "INTERNAL",
            )

            def repre(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                interpreter = LumaInterpreter()
                return interpreter.env["str"].instance([str(this.value).lower()])

            self.functions["@repr"] = LumaInterpreter.LumaFunction(
                "@repr",
                [],
                repre,
                0,
                "INTERNAL",
            )

        @staticmethod
        def lbool(
            value: "LumaInterpreter.InstancedLumaObject",
        ) -> "Any | LumaInterpreter.InstancedLumaObject":
            return value.__lbool__()

    class LumaClassStr(LumaClass):
        def __init__(self, name, parents=[]):
            super().__init__(name, parents)

            def constructor(
                value, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ):
                if type(value) is LumaInterpreter.InstancedLumaObject:
                    if value.typename == "str":
                        this.value = value.value
                        return
                this.value = str(value)

            self.functions["constructor"] = LumaInterpreter.LumaFunction(
                "constructor", [{"name": "value"}], constructor, 0, "INTERNAL",
            )

            def add(other, this: "LumaInterpreter.InstancedLumaObject | None" = None):
                interpreter: LumaInterpreter = LumaInterpreter()
                return interpreter.env["str"].instance([this.value + str(other)])

            self.functions["@addition"] = LumaInterpreter.LumaFunction(
                "@addition", [{"name": "other"}], add, 0, "INTERNAL",
            )

            def at(
                pos: EvaluatedType, this: "LumaInterpreter.InstancedLumaObject" = None
            ) -> "LumaInterpreter.InstancedLumaObject":
                interpreter: LumaInterpreter = LumaInterpreter()
                if pos.typename == "int":
                    return interpreter.env["str"].instance(
                        [this.value[pos.vars["value"]]]
                    )
                else:
                    interpreter.throw(
                        interpreter.env["typeError"],
                        "str key must be an integer",
                        "idk",
                        "idk",
                        interpreter.filename,
                    )

            self.functions["at"] = LumaInterpreter.LumaFunction(
                "at", [{"name": "pos"}], at, 0, "INTERNAL",
            )

            def stringify(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                return LumaInterpreter().env['str'].instance([this.value])

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
                0,
                "INTERNAL",
            )

            def repre(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                if '"' in this.value and "'" not in this.value:
                    return (
                        LumaInterpreter().env["str"].instance(["'" + this.value + "'"])
                    )
                if "'" in this.value and '"' not in this.value:
                    return (
                        LumaInterpreter().env["str"].instance(['"' + this.value + '"'])
                    )
                return LumaInterpreter().env["str"].instance([json.dumps(this.value)])

            self.functions["@repr"] = LumaInterpreter.LumaFunction(
                "@repr",
                [],
                repre,
                0,
                "INTERNAL",
            )

            def length(this: "LumaInterpreter.InstancedLumaObject | None" = None):
                return LumaInterpreter().env["int"].instance([len(this.value)])

            self.functions["len"] = LumaInterpreter.LumaFunction(
                "len",
                [],
                length,
                0,
                "INTERNAL",
            )

            def lbool(this: "LumaInterpreter.InstancedLumaObject | None" = None):
                return LumaInterpreter().env["bool"].instance([len(this.value)])

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                lbool,
                0,
                "INTERNAL",
            )

    class InstancedLumaObject[ClassName: LiteralString]:
        def __init__(
            self,
            varis: dict[EvaluatedType],
            functions: "dict[str, LumaInterpreter.LumaFunction]",
            classes: "dict[str, LumaInterpreter.LumaClass]",
            name: ClassName,
            args: list[EvaluatedType],
            parents: list[str],
        ):
            self.value = None
            self.vars = varis.copy()
            self.parents = parents
            self.functions = functions.copy()
            self.classes = classes.copy()
            self.typename = name
            interpreter = LumaInterpreter()
            if self.functions['@stringify'].file == "INTERNALCLS":
                def stringify(this=None):
                    return f"<{self.typename} object>"

                self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                    "@stringify",
                    [],
                    stringify,
                    0,
                    "INTERNAL",
                )

            if self.functions['@repr'].file == "INTERNALCLS":
                def repre(this=None):
                    return str(this)

                self.functions["@repr"] = LumaInterpreter.LumaFunction(
                    "@repr",
                    [],
                    repre,
                    0,
                    "INTERNAL",
                )
            if interpreter is not None:
                if self.typename in interpreter.PY_IMPL_CLASSES:
                    self.value: (
                        dict[
                            EvaluatedType,
                            EvaluatedType,
                        ]
                        | bool
                        | str
                    )
                self.instance(args)
                return
            raise TypeError("Could not find an active interpreter.")

        def call(self, args, line):
            r = self.functions["@call"].run(args, self, callline=line)
            return r

        def tie(self, method: str):
            def wrapper(*args):
                return self.functions[method].run(args, self)

            return LumaInterpreter.LumaFunction(
                method,
                self.functions[method].args,
                wrapper,
                0,
                "INTERNAL",
            )
        
        

        def callmethod(self, method: str, args: list):
            methodf: LumaInterpreter.LumaFunction = self.functions[method]
            r = methodf.run(args, self)
            return r

        def instance(self, args: list):
            interpreter: LumaInterpreter | None = LumaInterpreter()
            if interpreter is None:
                raise TypeError("Could not find an active interpreter.")
            name = interpreter.generaterandomvarname()
            interpreter.env[name] = self
            self.callmethod("constructor", args)
            del interpreter.env[name]

        def __str__(self):
            r = self.functions["@stringify"].run([], self)
            if type(r) is LumaInterpreter.InstancedLumaObject:
                if r.typename == "str":
                    r = r.value
                else:
                    interpreter = LumaInterpreter()
                    LumaInterpreter.throw(
                        interpreter.env["typeError"],
                        f"@stringify must return a string and not {r.typename}",
                    )
            return r

        def __lbool__(self) -> "Any | LumaInterpreter.InstancedLumaObject":
            r = self.functions["@bool"].run([], self)
            return r

        def __bool__(self):
            if self.typename == "bool":
                return self.value
            return bool(super())

        def __eq__(self, other: EvaluatedType):
            if self.typename in LumaInterpreter().PY_IMPL_CLASSES:
                return self.value == other.value
            r = (
                self.functions["@equal"].run([other], self)
                if "@equal" in self.functions
                else (self.typename == other.typename and self.vars == other.vars)
            )
            return r

        def __ne__(self, other):
            r = self.functions["@nequal"].run([other], self)
            return r

        def __lt__(self, other):
            r = self.functions["@lesst"].run([other], self)
            return r

        def __le__(self, other):
            r = self.functions["@lequal"].run([other], self)
            return r

        def __gt__(self, other):
            r = self.functions["@greatert"].run([other], self)
            return r

        def __ge__(self, other):
            r = self.functions["@gequal"].run([other], self)
            return r

        def __int__(self):
            if self.typename == "int":
                return self.vars["value"]
            elif self.typename == "bool":
                return int(self.value)
            else:
                return 0

        def __hash__(self):
            try:
                vars_items = sorted(self.vars.items())
                if hasattr(self, "value"):
                    vars_items.append(self.value)
                vars_items = tuple(vars_items)
            except TypeError:
                raise TypeError(
                    "All keys and values in self.vars must be hashable to compute __hash__"
                )
            return hash((self.typename, vars_items))

    class SubProgramExitCode(Exception):
        def __init__(self, code, data=None):
            self.code = code
            self.data = data
            super().__init__()

    class LumaException(Exception):
        def __init__(self, exc: "LumaInterpreter.InstancedLumaObject"):
            self.exc = exc
            super().__init__('\n'.join([self.display(tb) for tb in getattr(exc, 'tb')]) + "\n\033[1m\033[95m" + exc.typename + "\033[0m" + (": \033[95m" if str(getattr(exc, 'msg')) != "" else "") + str(getattr(exc, 'msg')) + "\033[0m")


        def display(self, tbline: tuple[int, str, str]):
            return f'File \033[95m"{tbline[2]}"\033[0m, line \033[95m{tbline[0]}\033[0m\n    \033[31m{tbline[1]}\033[0m'
