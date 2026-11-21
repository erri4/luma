from LumaExtBundle import Raw, ParseMe, Function, Class
from LumaTypes import LumaInterpreter

def constructor_err(msg, this: LumaInterpreter.InstancedLumaObject | None = None):
    setattr(this, "msg", msg)
    setattr(this, "tb", this.expose("traceback")())
constructor_err.__name__ = "constructor"


def trigger(this: LumaInterpreter.InstancedLumaObject | None = None):
    raise this.expose("LumaException")(this)


def stringify_err(this: LumaInterpreter.InstancedLumaObject | None = None):
    return ParseMe({"type": 'str', 'args': [Raw(getattr(this, "msg"))]})
stringify_err.__name__ = "@stringify"


def show(data = "", end = '\n'):
    print(data, end=str(end))

def inpt(prompt = ""):
    return ParseMe({"type": 'str', 'args': [Raw(input(prompt))]})
inpt.__name__ = 'input'

def constructor_null(this: LumaInterpreter.InstancedLumaObject | None = None):
    pass
constructor_null.__name__ = "constructor"

def stringify_null(this: LumaInterpreter.InstancedLumaObject | None = None):
    return ParseMe({"type": 'str', 'args': [Raw('null')]})
stringify_null.__name__ = "@stringify"

def repr_null(this: LumaInterpreter.InstancedLumaObject | None = None):
    return ParseMe({"type": 'str', 'args': [Raw('null')]})
repr_null.__name__ = "@repr"

def bool_null(this: LumaInterpreter.InstancedLumaObject | None = None):
    return ParseMe({"type": 'bool', 'args': [Raw(False)]})
bool_null.__name__ = "@bool"


LumaExtension = {
    "baseError": Class(
        "baseError",
        Function(
            constructor_err,
            [
                {"name": "this"},
                {"name": "msg", "default": {"type": "str", "args": [Raw("")]}},
            ],
        ),
        [
            Function(trigger, [{"name": "this"}]),
            Function(stringify_err, [{"name": "this"}]),
        ],
    ),
    "nullType": Class(
        "nullType",
        Function(
            constructor_null,
            [
                {"name": "this"},
            ],
        ),
        [
            Function(stringify_null, [{"name": "this"}]),
            Function(repr_null, [{"name": "this"}]),
            Function(bool_null, [{"name": "this"}]),
        ],
    ),
    "null": {
        "type": 'nullType',
        "args": []
    },
    "true": {
        "type": 'bool',
        "args": [Raw(True)]
    },
    "false": {
        "type": 'bool',
        "args": [Raw(False)]
    },
    "show": Function(show, [
        {"name": "data", "default": {"type": "str", "args": [Raw("")]}},
        {"name": "end", "default": {"type": "str", "args": [Raw("\n")]}},
    ]),
    "input": Function(inpt, [
        {"name": "prompt", "default": {"type": "str", "args": [Raw("")]}}
    ]),
}
