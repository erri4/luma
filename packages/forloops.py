from LumaExtBundle import Overload
import LumaTypes

def process(self: LumaTypes.LumaInterpreter, line: str, linenum: int, Object = None, file: str = ''):
    self.SAVED_KEYWORDS.append('for') if not 'for' in self.SAVED_KEYWORDS else None
    if line.startswith('for'):
        counter = self.smrtsplt(line[line.find('(')+ 1:line.rfind(')')].strip(), ', ')
        return 'for', counter
        self.process(counter[0], linenum)
        program = self.scopes[-1]
        body = ''
        for subline in program.splitlines()[linenum:]:
            if subline[0] == '}':
                break
            body += subline + "\n"
        body = body.strip()
        while self.evaluate(counter[1]):
            self.runsubprogram(body, Object, line=linenum + 1, file=file)
            self.process(counter[2], linenum)

def runsubprogram(self: LumaTypes.LumaInterpreter, subprogram: str, Object: LumaTypes.LumaInterpreter | LumaTypes.LumaInterpreter.InstancedLumaObject = None, line: int = 1, file: str = "", main: bool = False, ln: int = 0, code: tuple = ('for', ('','',''))):
    subline = subprogram.splitlines()[ln].replace(r"\n", "\n")
    counter = code[1]
    offset = 0
    body = ""
    scp = 1
    for c in '\n'.join(subprogram.splitlines()[ln + 1:]):
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
    offset = (len(body.splitlines()) + 1) if body else 0
    self.runsubprogram(counter[0], Object, line, file, main)
    while self.evaluate(counter[1]):
        self.runsubprogram(body + '\n' + counter[2], Object, line + 1, file, main)
    return offset
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
