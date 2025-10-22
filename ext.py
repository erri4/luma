from LumaExtBundle import Raw, DictToDict, ParseMe


def func(arg=""):
    return ParseMe({"type": "str", "args": [Raw("stringhbhbiyb" + str(arg))]})


# TODO: add class support

LumaExtension = {
    "test": {
        "type": "list",
        "args": [
            Raw(
                DictToDict(
                    [{"type": "int", "args": [Raw(0)]}],
                    [{"type": "str", "args": [Raw("hi")]}],
                )
            )
        ],
    },
    "func": {
        "type": "functionType",
        "name": "func",
        "body": func,
        "args": [{"name": "arg", "default": Raw("")}],
    },
}
