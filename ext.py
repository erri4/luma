from LumaExtBundle import Raw, DictToDict


def func(arg=""):
    print(arg)
    print("hiii")


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
        "type": "FunctionType",
        "name": "func",
        "body": func,
        "args": [{"name": "arg"}],
    },
}
