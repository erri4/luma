from LumaExtBundle import Raw, ParseMe, Function
import math

sin = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.sin(float(x)))]}
        )
sin.__name__ = 'sin'


arcsin = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.asin(float(x)))]}
        )
arcsin.__name__ = 'arcsin'

cos = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.cos(float(x)))]}
        )
cos.__name__ = 'cos'

arccos = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.acos(float(x)))]}
        )
arccos.__name__ = 'arccos'

tan = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.tan(float(x)))]}
        )
tan.__name__ = 'tan'

arctan = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.atan(float(x)))]}
        )
arctan.__name__ = 'arctan'

sqrt = lambda x: ParseMe(
            {"type": "float", "args": [Raw(math.sqrt(float(x)))]}
        )
sqrt.__name__ = 'sqrt'

LumaExtension = {
    "pi": {
        "type": "float",
        "args": [Raw(math.pi)],
    },
    "e": {
        "type": "float",
        "args": [Raw(math.e)],
    },
    "sin": Function(
        sin,
        [{"name": "x"}],
    ),
    "arcsin": Function(
        arcsin,
        [{"name": "x"}],
    ),
    "cos": Function(
        cos,
        [{"name": "x"}],
    ),
    "arccos": Function(
        arccos,
        [{"name": "x"}],
    ),
    "tan": Function(
        tan,
        [{"name": "x"}],
    ),
    "arctan": Function(
        arctan,
        [{"name": "x"}],
    ),
    "sqrt": Function(
        sqrt,
        [{"name": "x"}],
    ),
}
