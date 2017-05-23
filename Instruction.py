import re

instructionSet = {
    'FP_ADD': ['ADD.D','SUB.D'],
    'FP_MULT': ['MUL.D'],
    'FP_DIV': ['DIV.D'],
    'INT': ['DADD','DADDI','DSUB','DSUBI','AND','ANDI','OR','ORI','LI'],
    'LOAD/STORE': ['LW','SW','L.D','S.D'],
    'J': ['J'],
    'BRANCH': ['BNE', 'BEQ'],
}
class INST:
    def __init__(self,string):
        # Instruction Registers and Values
        self.string = string
        self.unit = None
        self.op = None
        self.dest = None
        self.r1 = None
        self.r2 = None
        self.result = None
        self.jaddr = None

        #Result section
        self.FT = None
        self.IS = None
        self.RD = None
        self.EXE = None
        self.WR = None
        self.RAW = False
        self.WAW = False
        self.STRUCT = False
        self.parse(self.string)

    def parse(self,string):
        # Strip it of labels. Labels have already been read in Simulator class
        if(string.find(":")!=-1):
            string = self.string.split(":")[1]
        match = re.findall("[0-9.A-Z-]+",string)
        self.op = match[0]
        if (self.op in instructionSet['FP_ADD']):
            self.unit = 'FP_ADD'
            self.dest = match[1]
            self.r1 = match[2]
            self.r2 = match[3]
        elif (self.op in instructionSet['FP_MULT']):
            self.unit = 'FP_MULT'
            self.dest = match[1]
            self.r1 = match[2]
            self.r2 = match[3]
        elif (self.op in instructionSet['FP_DIV']):
            self.unit = 'FP_DIV'
            self.dest = match[1]
            self.r1 = match[2]
            self.r2 = match[3]
        elif (self.op in instructionSet['LOAD/STORE']):
            self.unit = 'LOAD/STORE'
            self.dest = match[1]
            self.r1 = match[2]
            self.r2 = match[3]

        elif (self.op in instructionSet['INT']):
            self.unit = 'INT'
            self.dest = match[1]
            self.r1 = match[2]
            if(self.op != "LI"):
                self.r2 = match[3]
        elif (self.op in instructionSet['BRANCH']):
            self.r1 = match[1]
            self.r2 = match[2]
            self.jaddr = match[3]
        elif (self.op in instructionSet['J']):
            self.jaddr = match[1]
