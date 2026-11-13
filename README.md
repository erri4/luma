# Luma
## Explanation
This is a langauge I am developing.
It is very slow, as it does not use the traditional way of tokenizing things, this is just plain string manipulations.
I am not planning anything for this language, and it probably has many hidden bugs.
The name has no source.

## Features and syntax
In luma, both curly braces and indents are necessary, don't forget them.
### Variables
This is an OOP language, very similar to python. A variable does not have a constant type, like python it can be any type and everything is dynamic.
For example, declaring/updating a variable:
```lum
set i to 0
```
`i` is the variable name, and `0` (`int`) is the value. Variable named can be anything made of `A-Z`, `a-z`, `0-9` and `@` (system/special functions and variables should start with `@`) and can even start with a number.
### I/O
To print a variable, say `var1`, you simply write:
```lum
show(var1)
```
The `show` function is very similar to the python `print`, it also accepts and `end` character to printed to stdout after `var1` (default is `'\n'`).
Again, just like python, we have an `input` function that prints a prompt (default is the empty string) and then returns from stdin (works exactly like python's `input`).
### Builtin types
(listed in order of reading at runtime)
- `Object`: an empty class, base of all luma classes.
> implemented in `builtins:@pylibs/lumastring.py`
- `str`: strings.<br>
    supports addition (string concatenation), casting to `int`, indexing, length and casting to `bool`.
> implemented in `builtins:@pylibs/lumastring.py`
- `bool`: boolean values.<br>
> implemented in `builtins:@pylibs/lumabool.py`
- `dict`: dictionaries.<br>
    supports indexing (accessing keys), item deletions, casting to `int` (returns length), assigning items, length and casting to `bool`.
> implemented in `builtins:@pylibs/lumadict.py`
- `int`: integers.<br>
    supports equality (including `geq`, `gt`, ...), arithmetics, and casting to `bool`.
> implemented in `builtins:@pylibs/lumanumbers.py`
- `float`: floating point numbers.<br>
    supports equality (including `geq`, `gt`, ...), arithmetics, and casting to `bool`.
> implemented in `builtins:@pylibs/lumanumbers.py`
- `baseError`: base of all errors.<br>
    supports triggering (throwing)
> implemented in `builtins:@pylibs/lumabuiltins.py`
- `module`: again an empty class, used as the type for imported modules.
> implemented in `builtins:builtins.lum`
- `nullType`: the type for the null value.<br>
    supports casting to `bool` (always `false`) and to `str` (always `"null"`)
> implemented in `builtins:builtins.lum`
- `classType` and `functionType`: dummy types for the types of classes and functions, actual types are internally defined.
They are also the first type seen in runtime.
> implemented internally
- Error types: the types of errors.<br>
    all subclasses of `baseError`.
    They all support triggering (throwing)
> implemented in `builtins:builtins.lum`
- `list`: dynamic lists<br>
    supports appending, clearing, indexing and item deletions.
> implemented in `builtins:builtins.lum`

By the way, you can create strings with `""` or with `''`, lists with `[]` and items seperated by commas, ints by typing the number, floats with a floating point, and dicts with `{}` with the python syntax.
### Functions
Functions are declared by the keyword `function` and their body is written inside curly braces. For example here is the creation of a function named `test1` accepting 2 required parameters (`p1`, `param2`) and a third one (`prm3`) with default value `"abc"`:
```lum
function test1(p1, param2, prm3 = "abc")
```
To return a value just use the `return` keyword.
### If-else statements
The syntax is very similar to many languages,
```lum
if (condition){
    do_stuff()
}
elseif (condition2){
    do_more_stuff()
}
else {
    do_else()
}
```
### While loops
In luma there are only while loops, no for loops. (if you really want for loops, see `extensions`.)
The syntax is again very simple:
```lum
while (condition){
    do_stuff()
}
```
### Classes
Classes are the way to define new types,
to define a new class use the keyword `class`. Inheritance is possible, and a class can contains nested classes:
```lum
class example(exampleParent){
    class nested{
        set var to 3
    }

    constructor example(i = 3){
        set this.i to i
    }

    function func(j = 123){
        show(this.i + j)
    }
}
```
To create new instances of classes use the `new` keyword (this really isn't necessary for the language. I just wanted it):
```lum
set x to new example(34)
set y to new example.nested()
```
### Exceptions and try-catch
An exception is any subclass of `baseError`. To throw one, just use `throw exc` where exc is an instance of the wanted exception. To handle exceptions, we use `try-catch` statements, and you can also use the `as` keyword:
```lum
try{
    do_stuff()
}
catch (baseError as be){
    show("baseError caught: " + new str(be))
}
catch (syntaxError as se){
    show("syntaxError caught: " + new str(be))
}
```
You can also catch any exception using `anyError`.
### Naming conventions
Classes should be camelCase, functions should be snake_case, and variables should be whatever you want (just be consistent)
System and special variables/functions start with a `@`.
### Builtin values and functions
- `range(start, end = null, jump = 1)`: return a list of integers in `[start, end)` with jumps `jump`
- `true`: an instance of `bool` with a `true` value. `bool` is <b>NOT</b> a singleton, so every `true` instance is different.
- `false`: an instance of `bool` with a `false` value.
- `null`: an instance of `nullType`. `nullType` is also not a singleton.
- `show` and `input`: specified under `I/O`
### Importing
To import a file/library, use the `import` statement, which accept a string and imports the given file. The `import` keyword on it's own just reads the file and runs it, so all the classes/functions/variables will be loaded into the enviroment. To access system libraries/packages, use the `:` delimitor between the system folder and the library name.
To import into a namespace, simply use the `as` keyword:
```lum
import "lib:sys.lum" as sys
```
and now you can use sys as a variable in your code.
### Builtin libraries
- `lib:sys.lum`:
1. `sys.version`: `str`
A string containing the version of luma.
2. `sys.exit`: `functionType`
When called, exit the program with code 0.
- `lib:files.lum`:
1. `file`: `classType`
The constructor accepts a file path, and the class has 3 functions:<br>
`read()`: Read the file and return the contents.<br>
`write(newfile)`: Write an `str` to the file (replacing old content).
`writeln(line)`: Write a line to the end of the file.
- `lib:math.lum`:
1. `math.pi`: `float` Pi.
2. `math.e`: `float` Euler's number.
3. `math.sin`: `functionType` sine function.
3. `math.arcsin`: `functionType` arcsine function.
3. `math.cos`: `functionType` cosine function.
3. `math.arccos`: `functionType` arccosine function.
3. `math.tan`: `functionType` tangent function.
3. `math.arctan`: `functionType` arctangent function.
3. `math.sqrt`: `functionType` the square root function.
### Extensions
This is a powerful tool that allows writing luma functions/classes in python, and even modifying the interpreter itself at runtime.
Given an extension (a `.py` file) you can use it in your code using the `extend` keyword, which works exactly like `import` (except it does not support `as`).
A powerful example of that is in `packages:discord.lum` (a `.lum` file, use `import` to import) where I ported the `discord.py` library into luma.
There is also an example of modifying the interpreter at `packages:forloops.py` which is an extension that adds for loops to the language:
```
extend "packages:forloops.py"
for (set i to 0, i < 10, i++){
    show(i)
}
```
### Writing extensions
The core lies at the interpreter reading a dict named `LumaExtension` from your file and interpreting it.
For your convenience, there are some builtin python files named `LumaTypes.py` (to help with typehinting the extensions) and `LumaExtBundle.py` (to help with the actual development).
To add a variable/function/class (and do not change the interpreter) just type into our `LumaExtension` a key-value pair with the key as the name for the item, and value a dictionary telling the interpreter how to create it.
To create a variable, set it's `type` field to the desired type, and `args` to a list of the arguments given to the object's constructor (also in the same format).
To assign the variable a python value, use the class `Raw` present in `LumaExtBundle.py`.
To create a function, use the `Function` function present in our `LumaExtBundle.py`, which accepts a `Callable` and a list of arguments it expects, in each as a dict containing a `name` field (required) and a `default` field if it has a default value.
To create a class, use the `Class` present in `LumaExtBundle.py` which accepts the name of the class, it's constructor as an output of the `Function` function, a list of class functions, a list of class variables, a list of nested classes, and the direct parent of the class.
If you want to implement a python function that returns a luma object, return from the function an instance of `ParseMe` (again, in `LumaExtBundle.py`) containing the creatiion instructions for the object.

If you do want to change the interpreter midrun, there are two cases:
1. You want to add a function that runs before/after a specified function runs (`Overload`).
2. You want to completely rewrite a function (`Override`).

<br>

1. Currently only after and before `process` are supported, to use it write a python function that accepts the exact same arguments as `process` (`self: LumaTypes.LumaInterpreter, line: str, linenum: int, Object = None, file: str = ''`) and in `LumaExtension` add a key-value pair, (the key does not matter) containing an instance of `LumaExtBundle.Overload` with a string of the desired overload (`"beforeprocess"` or `"afterprocess"`) in the `type` field, and the function overload in the `function` field.
Any `process` overload should return `True` if the processing should stop after it.

2. To override a function, do the same just use `LumaExtBundle.Override` instead of `LumaExtBundle.Overload`.
Currently only `process` and `evaluate` are supported for overriding.