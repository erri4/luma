from interpreter import LumaInterpreter
import sys


# profile: python -m cProfile -s tottime ./src/luma.py ./main.lum

if __name__ == "__main__":
    filename = sys.argv[1]
    interpreter = LumaInterpreter()
    with open("log.txt", "w") as logf:
        logf.write("")
    if filename.endswith(".lum"):
        try:
            with open(f"{filename}") as file:
                program = file.read()
            interpreter.run(program, filename, globals())
        except FileNotFoundError:
            print(f"The file {filename} does not exists.")
    else:
        print(f"The file {filename} is not a luma program.")
