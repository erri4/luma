from types import FunctionType, GeneratorType
from typing import Any, TypedDict, Callable, Union, LiteralString
import operator
import sys
import json
import copy
import re
import os


####### for removal
# (also LumaInterpreter.InstancedLumaObject.debug)


def cp(f):
    def wrapper(*args, **kwargs):
        return copy.deepcopy(f(*args, **kwargs))

    return wrapper


def log(*texts):
    if len(texts) == 0:
        return
    texts = list(texts)
    for i in range(len(texts)):
        if type(texts[i]) is GeneratorType:
            texts[i] = [str(text) for text in texts[i]]
    with open("log.txt", "a") as logf:
        logf.write(", ".join(map(str, texts)) + "\n")


###################################################
"""
TODO:
OPTIMIZE
. handling errors (interpreter)

. python objects access from luma # for libraries like socket ## i think... i have already?

. importing py # this will be extentions

ONLY when finished: self.keywords: [...] (not setable)

. luma extentions (`for loops` and stuff)
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
    }
    REAL_OPERATORS: dict[str, FunctionType] = {
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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def run(self, program: str, filename: str):
        def nativecode(
            pytext: str, kwargs: LumaInterpreter.InstancedLumaObject | None = None
        ):
            globs = {"filename": self.filename}
            data: dict[str | LumaInterpreter.InstancedLumaObject["str"], Any] = (
                kwargs.value if kwargs else {}
            )
            for key in list(data.keys()):
                data[str(key)] = data[key]
            r = eval(str(pytext), globs | data)
            return r

        def packvalue(string):
            r = json.dumps(str(string))
            return r

        self.env["nativecode"] = self.LumaFunction(
            "nativecode",
            [{"name": "pytext"}, {"name": "kwargs", "default": None}],
            nativecode,
        )
        self.env["packvalue"] = self.LumaFunction(
            "packvalue", [{"name": "string"}], packvalue
        )

        module = self.LumaClass("module")
        self.env["module"] = module

        dictcls = self.LumaClassDict("dict")
        self.env["dict"] = dictcls
        boolcls = self.LumaClassBool("bool")
        self.env["bool"] = boolcls
        strcls = self.LumaClassStr("str")
        self.env["str"] = strcls
        BaseError = self.LumaClass("BaseError")

        def constructor(msg, this=None):
            setattr(this, 'msg', msg)

        BaseError.functions["constructor"] = LumaInterpreter.LumaFunction(
            "constructor", [{"name": "msg", "default": self.env['str'].instance([""])}], constructor
        )
        def trigger(this=None):
            raise LumaInterpreter.LumaException(this, [getattr(this, 'msg')])

        BaseError.functions["trigger"] = LumaInterpreter.LumaFunction(
            "trigger", [], trigger
        )
        def stringify(this=None):
            return getattr(this, 'msg')

        BaseError.functions["@stringify"] = LumaInterpreter.LumaFunction(
            "@stringify", [], stringify
        )
        self.env["BaseError"] = BaseError

        self.filename = filename
        self.scopes: list[str] = [program]
        self.runimport(":builtins.lum", None)
        self.runsubprogram(program, infunc=False)

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
                    self.runsubprogram(subprogram, infunc=False)
                else:
                    body = "class module {\n    constructor module (){\n        \n    }\n\n"
                    for line in subprogram.splitlines():
                        body += "    " + line + "\n"
                    body += "}"
                    self.runsubprogram(body, infunc=False)
                    self.runsubprogram(f"set {name} to new module ()")
        except FileNotFoundError:
            LumaInterpreter.throw(
                self.env["ModuleNotFoundError"],
                f"No module named '{module}'",
                "idk",
                f"import {module}" + f" as {name}" if name else "",
                self.filename,
            )

    def runsubprogram(
        self, subprogram: str, Object=None, infunc: bool = True, realfunc: bool = False
    ):
        if Object is None:
            Object = self
        linen = 1
        subprogram = LumaInterpreter.preprocess(subprogram)
        subprogram = subprogram.splitlines()
        if infunc:
            for i in range(len(subprogram)):
                subprogram[i] = LumaInterpreter.removetab(subprogram[i])
        subprogram = "\n".join(subprogram)
        self.scopes.append(subprogram)
        res = None
        for subline in subprogram.splitlines():
            try:
                res = self.process(subline, linen, Object)
            except LumaInterpreter.SubProgramExitCode as e:
                if e.code == "return":
                    self.scopes.pop()
                    return e.data
                else:
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode(e.code, e.data) from e
            if subline.startswith("return"):
                if not realfunc:
                    self.scopes.pop()
                    raise LumaInterpreter.SubProgramExitCode("return", res)
                else:
                    break
            linen += 1
        self.scopes.pop()
        return res

    def process(
        self,
        line: str,
        linenum: int,
        Object: "LumaInterpreter | LumaInterpreter.InstancedLumaObject | None" = None,
    ):
        line = line.replace(r"\n", "\n")
        if Object is None or type(Object) is LumaInterpreter:
            varis = self.env
            functions: dict[str, LumaInterpreter.LumaFunction] = self.env
            classes: dict[str, LumaInterpreter.LumaFunction] = self.env
        else:
            varis = Object.vars
            functions: dict[str, LumaInterpreter.LumaFunction] = Object.functions
            classes: dict[str, LumaInterpreter.LumaClass] = Object.classes
        program = self.scopes[-1]
        progfind = program.find
        firstword = LumaInterpreter.getfirstword(line)
        if firstword == "function":
            func_name = line[9 : line.find(" (")]
            args = self.parse_args(line[line.find(" (") + 2 : line.find(")")])
            a = program[progfind(f"{func_name} (") + len(func_name) + 2 :]
            stop = len(a[: a.find("){") + 3])
            for linee in a[a.find("){") + 3 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find("){") + 3 : stop].strip()
            functions[func_name] = self.LumaFunction(func_name, args, body)
        elif firstword == "class":
            class_name = line[6 : line.find(" {")]
            a = program[progfind(f"class {class_name}" + " {") + len(class_name) + 2 :]
            stop = len(a[: a.find(" {") + 3])
            for linee in a[a.find(" {") + 3 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find(" {") + 3 : stop].strip()
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
                classes[class_name].typename = class_name
            self.runsubprogram(body, classes[class_name])
        elif firstword == "constructor":
            class_name = line[12 : line.find(" (")]
            args = self.parse_args(line[line.find(" (") + 2 : line.find(")")])
            a = program[progfind(f"{class_name} (") + len(class_name) + 2 :]
            stop = len(a[: a.find("){") + 3])
            for linee in a[a.find("){") + 3 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find("){") + 3 : stop].strip()
            functions["constructor"] = self.LumaFunction(
                "constructor",
                args,
                body,
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
                        self.env["TypeError"],
                        "cannot use this outside class method call",
                        linenum,
                        line,
                        self.filename,
                    )
                varis[varname] = value
        elif firstword == "import":
            module = LumaInterpreter.getfirstword(line[7:])
            name = None
            if LumaInterpreter.getfirstword(line[7:]) != line[7:]:
                name = line[11 + len(LumaInterpreter.getfirstword(line[7:])) :]
            self.runimport(module, name)
        elif firstword == "try":
            a = "\n".join(program.splitlines()[linenum - 1 :])
            stop = len(a[: a.find("{") + 2])
            for linee in a[a.find("{") + 2 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find("{") + 2 : stop].strip()
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
                a = "\n".join(program.splitlines()[linenu - 1 :])
                stop = len(a[: a.find("){") + 3])
                for linee in a[a.find("){") + 3 :].splitlines():
                    if linee != "":
                        if linee[0] == "}":
                            break
                    stop += len(linee) + 1
                bd = a[a.find("){") + 3 : stop].strip()
                excs.append(exc)

                bodys[exc[0]] = bd
                linenu += len(bd.splitlines()) + 2

                try:
                    subline = LumaInterpreter.removetab(
                        program.splitlines()[linenu - 1]
                    )
                except IndexError:
                    break
            try:
                self.runsubprogram(body)
            except LumaInterpreter.LumaException as e:
                catched = False
                for exc in excs:
                    if exc[0] == e.exc.typename:
                        try:
                            self.env[exc[1]] = e.exc
                        except IndexError: pass
                        self.runsubprogram(bodys[exc[0]])
                        catched = True
                if not catched:
                    for exc in excs:
                        if exc[0] == "AnyException":
                            try:
                                self.env[exc[1]] = e.exc
                            except IndexError: pass
                            self.runsubprogram(bodys[exc[0]])
                            catched = True
                if not catched:
                    raise e from None
        elif firstword == "if":
            condition = line[4 : line.find("){")]
            a = "\n".join(program.splitlines()[linenum - 1 :])
            stop = len(a[: a.find("){") + 3])
            for linee in a[a.find("){") + 3 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find("){") + 3 : stop].strip()
            conditions = []
            bodys = {}
            linenu = int(linenum) + len(body.splitlines()) + 2
            subline = ""
            try:
                subline = LumaInterpreter.removetab(program.splitlines()[linenu - 1])
            except IndexError:
                pass
            while subline.startswith("elseif"):
                cond = subline[8 : subline.find(")")]
                a = "\n".join(program.splitlines()[linenu - 1 :])
                stop = len(a[: a.find("){") + 3])
                for linee in a[a.find("){") + 3 :].splitlines():
                    if linee != "":
                        if linee[0] == "}":
                            break
                    stop += len(linee) + 1
                bd = a[a.find("){") + 3 : stop].strip()
                conditions.append(cond)

                bodys[cond] = bd
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
                a = "\n".join(program.splitlines()[linenu - 1 :])
                stop = len(a[: a.find("{") + 2])
                for linee in a[a.find("{") + 2 :].splitlines():
                    if linee != "":
                        if linee[0] == "}":
                            break
                    stop += len(linee) + 1
                elsebody = a[a.find("{") + 2 : stop].strip()
            r = None
            ifcond = self.evaluate(condition)
            if bool(ifcond):
                r = self.runsubprogram(body)
            else:
                foundelif = False
                for i in range(len(conditions)):
                    con = conditions[i]
                    bd: str = bodys[con]
                    if self.evaluate(con):
                        r = self.runsubprogram(bd)
                        foundelif = True
                        break
                if not foundelif:
                    r = self.runsubprogram(elsebody)
            return r
        elif firstword == "while":
            condition = line[7 : line.find("){")]
            a = "\n".join(program.splitlines()[linenum - 1 :])
            stop = len(a[: a.find("){") + 3])
            for linee in a[a.find("){") + 3 :].splitlines():
                if linee != "":
                    if linee[0] == "}":
                        break
                stop += len(linee) + 1
            body = a[a.find("){") + 3 : stop].strip()
            while self.evaluate(condition):
                try:
                    self.runsubprogram(body)
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
            self.evaluate(line)

    @staticmethod
    def throw(
        exc: "LumaInterpreter.LumaClass",
        msg: "str | LumaInterpreter.InstancedLumaObject",
        linenum: "int | LumaInterpreter.InstancedLumaObject",
        line: "str | LumaInterpreter.InstancedLumaObject",
        file: "str | LumaInterpreter.InstancedLumaObject",
    ) -> None:
        exc.functions["constructor"].run(
            [f"\n{msg}\n    at line {linenum} in {line}\n    at file {file}"]
        )

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

    def extractargs(self, line: str, funcname):
        rawargs = line[len(funcname) + 2 : -1]
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
            val = LumaInterpreter.eval_single_condition([left, op, right])
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
        return self.env["bool"].instance([int(result)])

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
        char = None
        sep_len = len(sep)
        expr_len = len(expr)
        brackets_open = {"(": ")", "[": "]", "{": "}"}
        brackets_close = {")", "]", "}"}
        stack_pop = stack.pop
        stack_append = stack.append
        expr_startswith = expr.startswith
        parts_append = parts.append

        start = 0
        i = 0
        while i < expr_len:
            c = expr[i]
            if c in ('"', "'") and not in_quotes:
                char = str(c)
                in_quotes = not in_quotes
            elif c == char and in_quotes:
                in_quotes = not in_quotes
                char = None
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

    @staticmethod
    def namourtype(obj: EvaluatedType):
        if type(obj) is LumaInterpreter.InstancedLumaObject:
            return obj.typename
        if type(obj) is LumaInterpreter.LumaClass:
            return "ClassType"
        if type(obj) is LumaInterpreter.LumaFunction:
            return "FunctionType"
        return "raw " + type(obj).__name__

    @staticmethod
    def is_obj_call(expr: str):
        expr = expr.strip()
        if " (" not in expr or expr.startswith("new") or expr.startswith("throw"):
            return False
        for op in LumaInterpreter.OPERATORS:
            if len(LumaInterpreter.smrtsplt(expr, op)) > 1:
                return False
        splitted = expr.split(" (")
        prefix, rest = " (".join(splitted[0:-1]), splitted[-1]
        if not prefix.strip():
            return False
        if not rest.endswith(")"):
            return False

        return True

    @staticmethod
    def copy_dict(d):
        if not isinstance(d, dict):
            return d
        out = {}
        for k, v in d.items():
            if isinstance(k, dict):
                k = LumaInterpreter.copy_dict(k)
            elif isinstance(k, list):
                k = [
                    LumaInterpreter.copy_dict(i) if isinstance(i, dict) else i
                    for i in k
                ]
            elif isinstance(k, LumaInterpreter.InstancedLumaObject):
                obj_copy = copy.copy(k)
                obj_copy.vars = LumaInterpreter.copy_dict(k.vars)
                obj_copy.functions = k.functions.copy()
                obj_copy.classes = k.classes.copy()
                if hasattr(k, "value"):
                    obj_copy.value = LumaInterpreter.copy_dict(k.value)
                k = obj_copy
            if isinstance(v, dict):
                out[k] = LumaInterpreter.copy_dict(v)
            elif isinstance(v, list):
                out[k] = [LumaInterpreter.copy_dict(i) for i in v]
            elif isinstance(v, LumaInterpreter.InstancedLumaObject):
                obj_copy = copy.copy(v)
                obj_copy.vars = LumaInterpreter.copy_dict(v.vars)
                obj_copy.functions = v.functions.copy()
                obj_copy.classes = v.classes.copy()
                if hasattr(v, "value"):
                    obj_copy.value = LumaInterpreter.copy_dict(v.value)
                out[k] = obj_copy
            else:
                out[k] = copy.copy(v)
        return out

    def evaluate(
        self, expr: str, evalforwhat: str | None = None, doyouwantit: bool = False
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
                        opstr = f"({op_token.join(terms[:-1])}).{self.OPERATORS[op]} ({terms[-1]})"
                        opstrr = self.evaluate(opstr)
                        return opstrr
                    else:
                        LumaInterpreter.throw(
                            self.env["TypeError"],
                            f"unsupported operator: unable to perform operator {op} on types '{LumaInterpreter.namourtype(self.evaluate(f'{terms[0]}'))}' and '{LumaInterpreter.namourtype(self.evaluate(f'{op_token.join(terms[1:])}'))}'",
                            "idk",
                            expr,
                            self.filename,
                        )
                try:
                    return self.REAL_OPERATORS[op](term0, self.evaluate(terms[-1]))
                except TypeError:
                    LumaInterpreter.throw(
                        self.env["TypeError"],
                        f"unsupported operator: unable to perform operator {op} on types '{LumaInterpreter.namourtype(self.evaluate(f'{terms[0]}'))}' and '{LumaInterpreter.namourtype(self.evaluate(f'{op_token.join(terms[1:])}'))}'",
                        "idk",
                        expr,
                        self.filename,
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
            splitted = LumaInterpreter.smrtsplt(expr, " ")
            prefix = " ".join(splitted[0:-1])
            obj: LumaInterpreter.InstancedLumaObject = self.evaluate(prefix)
            args = self.extractargs(expr, prefix)
            return obj.call(args)
        elif expr in scope.keys():
            if (
                type(scope[expr]) is LumaInterpreter.InstancedLumaObject
                and not doyouwantit
            ):
                r = copy.copy(scope[expr])
                r.vars = LumaInterpreter.copy_dict(scope[expr].vars)
                if hasattr(r, "value"):
                    r.value = LumaInterpreter.copy_dict(scope[expr].value)
            else:
                r = scope[expr]
            return r
        if firstword == "this":
            LumaInterpreter.throw(
                self.env["TypeError"],
                "cannot use 'this' outside class method call",
                "idk",
                "idk",
                self.filename,
            )
        dotparts = LumaInterpreter.smrtsplt(expr, ".")
        if self.isnumber(expr):
            args = [self.realvalue(expr)]
            int_ = self.env["int"]
            log(int_.vars)
            float_ = self.env["float"]
            tmp = float_.instance(args) if "." in expr else int_.instance(args)
            r = copy.copy(tmp)
            r.vars = LumaInterpreter.copy_dict(tmp.vars)
            return r
        elif expr.startswith('"') and expr.endswith('"') and '"' not in expr[1:-1]:
            return self.env["str"].instance([self.realvalue(expr[1:-1])])
        elif expr.startswith("{") and expr.endswith("}"):
            return self.env["dict"].instance([self.realvalue(expr, includelist=True)])
        elif expr.startswith("[") and expr.endswith("]"):
            return self.env["list"].instance([self.realvalue(expr, includelist=True)])
        elif expr.startswith("'") and expr.endswith("'") and "'" not in expr[1:-1]:
            return self.env["str"].instance([self.realvalue(expr[1:-1])])
        elif expr in self.env.keys():
            if (
                type(self.env[expr]) is LumaInterpreter.InstancedLumaObject
                and not doyouwantit
            ):
                r = copy.copy(self.env[expr])
                r.vars = LumaInterpreter.copy_dict(self.env[expr].vars)
                if hasattr(r, "value"):
                    r.value = LumaInterpreter.copy_dict(self.env[expr].value)
            else:
                r = self.env[expr]
            return r
        elif len(dotparts) > 1:
            instancename = ".".join(dotparts[0:-1])
            propertyname = dotparts[-1]
            instance: LumaInterpreter.InstancedLumaObject = self.evaluate(instancename)
            if instance:
                if propertyname in instance.vars.keys():
                    r = instance.vars[propertyname]
                    if type(r) is LumaInterpreter.InstancedLumaObject:
                        r = copy.copy(instance.vars[propertyname])
                        r.vars = LumaInterpreter.copy_dict(
                            instance.vars[propertyname].vars
                        )
                        if hasattr(r, "value"):
                            r.value = LumaInterpreter.copy_dict(
                                instance.vars[propertyname].value
                            )
                    return r
                elif propertyname in instance.functions.keys():
                    return instance.tie(propertyname)
                elif propertyname in instance.classes.keys():
                    args = self.extractargs(expr.strip(), firstword)
                    instance = instance.classes[propertyname].instance(args)
                    r = copy.copy(instance)
                    r.vars = LumaInterpreter.copy_dict(instance.vars)
                    if hasattr(r, "value"):
                        r.value = LumaInterpreter.copy_dict(instance.value)
                    return r
                else:
                    LumaInterpreter.throw(
                        self.env["TypeError"],
                        f"{instancename} (type {self.evaluate(f'&{instancename}')}) has no attribute '{propertyname}'",
                        "idk",
                        expr,
                        self.filename,
                    )
            else:
                LumaInterpreter.throw(
                    self.env["TypeError"],
                    "NoneType object has no attributes",
                    "idk",
                    expr,
                    self.filename,
                )
        elif firstword == "new":
            firstword = LumaInterpreter.getfirstword(expr[4:])
            args = self.extractargs(expr[4:].strip(), firstword)
            cls: LumaInterpreter.LumaClass = self.evaluate(firstword)
            instance = cls.instance(args)
            r = copy.copy(instance)
            r.vars = LumaInterpreter.copy_dict(instance.vars)
            if hasattr(r, "value"):
                r.value = LumaInterpreter.copy_dict(instance.value)
            return r
        elif firstword == "throw":
            exc: LumaInterpreter.InstancedLumaObject = self.evaluate(expr[6:])
            exc.callmethod('trigger', [])
        else:
            LumaInterpreter.throw(
                self.env["NameError"],
                f"undefined variable or function '{firstword}'",
                "idk",
                expr,
                self.filename,
            )

    class LumaClass:
        def __init__(self, name: str, parents: list[str] = []):
            self.actualname = name
            self.typename = "ClassType"
            self.parents = parents
            self.functions: dict[str, LumaInterpreter.LumaFunction] = {}
            self.classes: dict[str, LumaInterpreter.LumaClass] = {}

            def stringify(this=None):
                return f"<{self.typename} object>"

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
            )

            def repre(this=None):
                return str(this)

            self.functions["@repr"] = LumaInterpreter.LumaFunction(
                "@repr",
                [],
                repre,
            )
            self.vars: dict[str, EvaluatedType] = {}

        def __lbool__(self):
            return False

        def __repr__(self):
            return f"<class {self.actualname} from luma>"

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

        def debug(self, trailing: str = "", prnt: bool = True):
            class DebugDict(TypedDict):
                name: str
                vars: list[
                    dict[str, LumaInterpreter.InstancedLumaObject | dict[Any, Any]]
                ]
                functions: dict[str, str]

            debugstr = ""
            debugdict: DebugDict = {
                "name": self.typename,
                "vars": [],
                "functions": {},
            }
            debugstr += f"Class: {self.typename}\n"
            debugstr += "Functions:\n"
            for func in self.functions.keys():
                debugstr += f"    {func}\n"
                debugdict["functions"][func] = ""
                function = self.functions[func]
                if type(function.body) is str:
                    debugstr += "    With body:\n"
                    debugstr += f"        {function.body}\n"
                    debugdict["functions"][func] = function.body
            debugstr += "Variables:\n"
            for var in self.vars.keys():
                debugdict["vars"].append({var: self.vars[var]})
                debugstr += f"    {var}: {self.vars[var]}\n"
            debugstr = debugstr[:-1]
            if prnt:
                print(debugstr, trailing)
            return debugstr, debugdict

    class LumaFunction:
        def __init__(
            self,
            name: str,
            args: list,
            body: str | Callable[[Any], Any],
        ):
            self.typename = "functionType"
            self.actualname = name
            self.args = args
            self.body = body

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
            if type(self.body) is str:
                r = interpreter.runsubprogram(self.body, realfunc=True)
            elif type(self.body) is FunctionType:
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
            return f"<FunctionType object named {self.actualname}>"

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
                        LumaInterpreter().env["TypeError"],
                        f"function '{self.actualname}' expected {len(self.args)} arguments but got {len(args)}",
                        "idk",
                        "idk bro",
                        LumaInterpreter().filename,
                    )

            if value_index < len(args):
                LumaInterpreter.throw(
                    LumaInterpreter().env["TypeError"],
                    f"function '{self.actualname}' expected {len(self.args)} arguments but got {len(args)}",
                    "idk",
                    "idk bro",
                    LumaInterpreter().filename,
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
                "constructor", [{"name": "value"}], constructor
            )

            def at(
                pos, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ) -> Any:
                return this.value[pos]

            self.functions["at"] = LumaInterpreter.LumaFunction(
                "at", [{"name": "pos"}], at
            )

            def dctset(
                pos, value, this: "LumaInterpreter.InstancedLumaObject | None" = None
            ) -> None:
                this.value[pos] = value

            self.functions["set"] = LumaInterpreter.LumaFunction(
                "set", [{"name": "pos"}, {"name": "value"}], dctset
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
            )

            def lbool(
                this: "LumaInterpreter.InstancedLumaObject['dict'] | LumaInterpreter.InstancedLumaObject['list'] | None" = None,
            ):
                return LumaInterpreter().env["bool"].instance([bool(len(this.value))])

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                lbool,
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
                "constructor", [{"name": "value"}], constructor
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
            )

            def selfbool(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                return this.value

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                selfbool,
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
                "constructor", [{"name": "value"}], constructor
            )

            def add(other, this: "LumaInterpreter.InstancedLumaObject | None" = None):
                interpreter: LumaInterpreter = LumaInterpreter()
                return interpreter.env["str"].instance([this.value + str(other)])

            self.functions["@addition"] = LumaInterpreter.LumaFunction(
                "@addition", [{"name": "other"}], add
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
                        interpreter.env["TypeError"],
                        "str key must be an integer",
                        "idk",
                        "idk",
                        interpreter.filename,
                    )

            self.functions["at"] = LumaInterpreter.LumaFunction(
                "at", [{"name": "pos"}], at
            )

            def stringify(
                this: "LumaInterpreter.InstancedLumaObject | None" = None,
            ) -> "LumaInterpreter.InstancedLumaObject":
                return this

            self.functions["@stringify"] = LumaInterpreter.LumaFunction(
                "@stringify",
                [],
                stringify,
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
            )

            def length(this: "LumaInterpreter.InstancedLumaObject | None" = None):
                return LumaInterpreter().env["int"].instance([len(this.value)])

            self.functions["len"] = LumaInterpreter.LumaFunction(
                "len",
                [],
                length,
            )

            def lbool(this: "LumaInterpreter.InstancedLumaObject | None" = None):
                return LumaInterpreter().env["bool"].instance([len(this.value)])

            self.functions["@bool"] = LumaInterpreter.LumaFunction(
                "@bool",
                [],
                lbool,
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
            self.vars = varis.copy()
            self.parents = parents
            self.functions = functions.copy()
            self.classes = classes.copy()
            self.typename = name
            interpreter = LumaInterpreter()
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

        def call(self, args):
            r = self.functions["@call"].run(args, self)
            return r

        def tie(self, method: str):
            def wrapper(*args):
                return self.functions[method].run(args, self)

            return LumaInterpreter.LumaFunction(
                method,
                self.functions[method].args,
                wrapper,
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
                        interpreter.env["TypeError"],
                        f"@stringify must return a string and not {r.typename}",
                        "idk",
                        "idk",
                        interpreter.filename,
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
        def __init__(self, exc: "LumaInterpreter.InstancedLumaObject", args):
            self.exc = exc
            self.args = args
            super().__init__(exc.typename + ": " + ', '.join(map(str, args)))
