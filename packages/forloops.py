from LumaExtBundle import Overload
import LumaTypes

def process(self: LumaTypes.LumaInterpreter, line: str, linenum: int, Object = None, file: str = ''):
    self.SAVED_KEYWORDS.append('for') if not 'for' in self.SAVED_KEYWORDS else None
    self.OPEN_BLOCK.append('for') if not 'for' in self.OPEN_BLOCK else None
    if line.startswith('for'):
        counter = self.smrtsplt(line[line.find('(')+ 1:line.rfind('{')].strip()[:-1], ', ')
        return 'for', counter

def runsubprogram(self: LumaTypes.LumaInterpreter, subprogram: str, Object: LumaTypes.LumaInterpreter | LumaTypes.LumaInterpreter.InstancedLumaObject = None, line: int = 1, file: str = "", main: bool = False, ln: int = 0, code: tuple = ('for', ('','',''))):
    LumaInterpreter = type(self)
    stk = 1
    ptr = ('\n'.join(subprogram.splitlines()[:ln + 1])).rfind('\n')
    while subprogram[ptr] != '(':
        ptr += 1
    ptr += 1
    ptr += self.find('\n'.join(subprogram.splitlines()[:ln + 1])[ptr:])
    ptr += '\n'.join(subprogram.splitlines()[:ln + 1])[ptr:].find('{')
    ptr += 1
    count = 0
    while stk > 0:
        if subprogram[ptr] == '\n': count += 1
        if subprogram[ptr] == '{':
            stk += 1
        if subprogram[ptr] == '}':
            stk -= 1
        ptr += 1
    subprogram = LumaInterpreter.preprocess('\n'.join(subprogram.splitlines()[ln:]))
    subline = subprogram.splitlines()[0].replace(r"\n", "\n")
    counter = code[1]
    body = ""
    scp = 1
    for c in '\n'.join(subprogram.splitlines()[1:]):
        if c == '}': scp -= 1
        if c == '{': scp += 1
        if scp == 0:
            break
        body += c
    lines = body.splitlines()
    for i in range(len(lines)):
        lines[i] = lines[i].strip()
    body = '\n'.join(lines)
    body = body.strip()
    if subline.endswith('}'):
        body = ""
    self.runsubprogram(counter[0], Object, line, file, main)
    while self.evaluate(counter[1]):
        self.runsubprogram(body + '\n' + counter[2], Object, line + 1, file, main)
    return count
runsubprogram.code = 'for'

LumaExtension = {
    "forloopcode": {
        "type": Overload("beforeprocess"),
        "function": process
    },
    "processor": {
        "type": Overload("subprogram"),
        "function": runsubprogram
    }
}
