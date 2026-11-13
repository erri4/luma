from typing import TypedDict, TypeVar, Any

EvaluatedType = TypeVar('EvaluatedType')

class InstancedLumaObject:
    value: dict | str | list | int | bool
    children: dict[str, Any]
    parents: list[str]
    typename: str
    def __init__(self, children: dict, name: str, args: list[EvaluatedType], parents: list[str]) -> None: ...
    def call(self, args, line): ...
    def expose(self, what: str): ...
    def tie(self, method: str): ...
    def callmethod(self, method: str, args: list): ...
    def instance(self, args: list): ...
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...
    def __lbool__(self) -> InstancedLumaObject: ...
    def __bool__(self) -> bool: ...
    def __eq__(self, other: EvaluatedType) -> InstancedLumaObject[bool]: ...
    def __ne__(self, other): ...
    def __lt__(self, other): ...
    def __le__(self, other): ...
    def __gt__(self, other): ...
    def __ge__(self, other): ...
    def __hash__(self): ...

class Raw:
    def __init__(self, data):
        self.data = data

class DictToDict:
    def __init__(self, keys: list = [], values: list = []):
        self.keys = keys
        self.values = values

    def __getitem__(self, key):
        return self.values[self.keys.index(key)]
    
class Override:
    def __init__(self, funcname):
        self.funcname = funcname

class Overload:
    def __init__(self, funcname):
        self.funcname = funcname
    
class ParseMe:
    def __init__(self, data: dict):
        self.data = data

class Arg(TypedDict):
    name: str
    default: EvaluatedType

def Function(f, args: list[Arg]):
    return {
        "type": "functionType",
        "name": f.__name__,
        "body": f,
        "args": args,
    }

def Class(c: str, constructor: dict, functions: list[dict] = [], classes: list[dict] = [], vars_: list = [], parent: str | None = 'Object'):
    return {
            "type": "classType",
            "name": c,
            "constructor": constructor,
            "functions": functions,
            "classes": classes,
            "vars": vars_,
            "parent": parent,
        }