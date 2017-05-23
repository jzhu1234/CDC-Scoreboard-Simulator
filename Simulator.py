import sys
from cache import ICACHE
from cache import DCACHE
from Instruction import INST

class SIM:
    def read_config(self):
        f = open(sys.argv[3],"r")
        i = 0
        for line in f.readlines():
            #Partition the line to get the number of units and execution cycles
            values = line.split(":")[1].split(",")
            if(i == 0):
                # First is the number of units. Second is the execution cycles
                self.FU["FP_ADD"] = [int(values[0]),int(values[1])]
            elif (i==1):
                self.FU["FP_MULT"] = [int(values[0]),int(values[1])]
            elif (i==2):
                self.FU["FP_DIV"] = [int(values[0]), int(values[1])]
            else:
                SIM.ICACHE_BLK = int(values[0]) # Number of blocks
                SIM.ICACHE_SIZE = int(values[1]) # Number of words in a block
            i = i+1
        self.FU['INT'] = [1,1]
        self.FU['LOAD/STORE'] = [1,1] #Number of cycles is dependent on other whether is double word or not
    def read_labels(self):
        f = open(sys.argv[1])
        i = 0
        for line in f.readlines():
            if(line.find(":") != -1):
                val = line.split(":")[0].strip()
                self.label_list[val] = i
            i += 4
        f.close()
    def __init__(self):
        self.label_list = dict()
        self.FU = dict()
        self.read_config()
        self.read_labels()
        self.ICache = ICACHE(sys.argv[1],SIM.ICACHE_BLK,SIM.ICACHE_SIZE)
        self.DCache = DCACHE(sys.argv[2])
        self.registers = dict()
        self.cycle = 0
        self.PC_MEM = 0x0
        self.done = False
        self.results = []
        self.icache_hit = 0
        self.dcache_hit = 0
        self.dcache_request = 0

        # Set up pipeline. Pipeline will contain instruction class objects
        self.pipe_reg = [[],[],[],[]]
        self.pipe_temp = [[],[],[],[]]
        self.pipeline = [None] * 5
        self.pipeline[0] = Fetch(self)
        self.pipeline[1] = Issue(self)
        self.pipeline[2] = Read(self)
        self.pipeline[3] = Execution(self)
        self.pipeline[4] = Write(self)

    def run(self):
        while not(self.done and self.pipe_reg == [[],[],[],[]]):
            self.step()

    def print_results(self,file):
        f = open(file,'w')
        f.write('                                    Read      Execute   Write \n')
        f.write('                      Fetch  Issue  Operands  Complete  Result  RAW  WAW  STRUCT\n')
        f.write('  Instruction       ------------------------------------------------------------\n')

        for instr in self.results:
            string = instr.string + ' '*(23-len(instr.string))
            val_list = [instr.FT,instr.IS,instr.RD,instr.EXE,instr.WR,instr.RAW,instr.WAW,instr.STRUCT]
            for val in val_list:
                if(val == False):
                    string += 'N       '
                elif(val == True):
                    string += 'Y       '
                elif(val == None):
                    string += '        '
                else:
                    string += str(val) + ' '*(8-len(str(val)))
            f.write(string+'\n')
        # Write down extra information
        if(self.icache_hit < 0):
            self.icache_hit = 0
        f.write('\n Total number of access requests for instruction cache: ' + str(len(self.results)))
        f.write('\n Number of instruction cache hits: '+str(self.icache_hit))
        f.write('\n Total number of access requests for data cache: '+str(self.dcache_request))
        f.write('\n Number of data cache hits: ' + str(self.dcache_hit))
        f.close()

    def step(self):
        self.cycle += 1
        if not self.done:
            self.pipeline[0].run(self.PC_MEM)
        self.pipeline[1].run(self.pipe_reg[0])
        self.pipeline[2].run(self.pipe_reg[1])
        self.pipeline[3].run(self.pipe_reg[2])
        self.pipeline[4].run(self.pipe_reg[3])

        # Pipeline registers
        for i in [3,2,1,0]:
            if(len(self.pipe_temp[i])!=0):
                self.pipe_reg[i] += self.pipe_temp[i]
                # Clear pipe_temp
                length = len(self.pipe_temp[i])
                for j in range(0,length):
                    self.pipe_temp[i].pop()

class Fetch:
    def __init__(self,simulator):
        self.simulator = simulator
        self.databus = False
        self.cachemiss = False
        self.stallcycles = 0
        self.address = 0x0

    def can_fetch(self,address):
        if (self.cachemiss==False):
            # Checks if address is valid
            if(self.simulator.ICache.valid(self.address)):
                # Check if Issue will be busy
                self.databus = False
                if(self.simulator.pipeline[1].can_issue(self.simulator.pipe_reg[0])):
                    self.simulator.icache_hit += 1
                    return True
                else:
                    return False
            else:
                # Check if EXE is using data bus
                if(self.simulator.pipeline[3].databus):
                    return False
                else:
                    self.databus = True
                    self.cachemiss = True
                    self.address = address
                    self.stallcycles = 3*self.simulator.ICACHE_SIZE
                    self.simulator.icache_hit -= 1
                    return False
        # If it doesn't fall into any of these conditions, return true
        else:
            return False
    def run(self,address):
        advance = self.can_fetch(address)
        if (advance):
            val = self.simulator.ICache.access(self.address)
            instr = INST(val)
            instr.FT = self.simulator.cycle
            self.simulator.results.append(instr)
            # Address was not reset due to branch or jump instruction
            if(address == self.address):
                self.simulator.pipe_temp[0].append(instr)
                self.simulator.PC_MEM += 0x4
                self.address = self.simulator.PC_MEM
            else:
                # Address was reset due branch or jump instruction
                self.address = address
        else:
            self.stall()

    def stall(self):
        if(self.databus):
            self.stallcycles -= 1
            if(self.stallcycles == 0):
                self.cachemiss = False
                self.simulator.ICache.add_block(self.address)
                self.simulator.ICache.printcache(self.simulator.cycle)

class Issue:
    def __init__(self,simulator):
        self.simulator = simulator
        self.branch_wait = False

    def can_issue(self,instructions):
        # Check if we are stalling the pipeline due to waiting for branch resolution
        if(self.branch_wait):
            return False
        cont = True
        # Idealistically should run either once or 0 times
        if(len(instructions)!=0):
            instr = instructions[0]
            # Check if Struct Hazard
            if (instr.unit != None and self.simulator.FU[instr.unit][0] == 0):
                instr.STRUCT = True
                cont = False
            # Check for WAW hazards. Store instructions can't have WAW hazards
            if not (instr.op in ['SW','S.D']):
                for i in range(1,4):
                    # Pipe_reg[3] and [4] have multiple instructions
                    for instr2 in self.simulator.pipe_reg[i]:
                        # Store instructions can't cause WAW hazards
                        if not(instr2.op in ['SW','S.D']):
                            if(instr.dest == instr2.dest):
                                instr.WAW = True
                                # If WAW hazard if found and STRUCT hazard is checked, can return immediately
                                return False
        return cont
    # Normally, only one instruction should be fed into issue stage
    def run(self,instructions):
        if(len(instructions)==0):
            return
        elif(len(instructions)>=2):
            print("Had a case where issue stage received two instructions. Should not happen")
        else:
            # In this case, we know that there should only be one instruction i self.simulator.pipe_reg[0]
            advance = self.can_issue(instructions)
            if(advance):
                instr = instructions[0]
                instr.IS = self.simulator.cycle
                # Decrement FU units available if instruction uses one
                if(instr.unit != None):
                    self.simulator.FU[instr.unit][0] -= 1
                else:
                    self.cntrl_logic(instr)
                # Don't want to let jump or halt instructions go further in the pipeline
                if not (instr.op in ['HLT','J']):
                    self.simulator.pipe_temp[1].append(instr)
                self.simulator.pipe_reg[0].pop()

    def cntrl_logic(self,instr):
        # Branch instruction
        if(instr.op in ['BNE','BEQ']):
            self.branch_wait = True
        elif(instr.op == 'J'):
            # Change PC_MEM
            self.simulator.PC_MEM = self.simulator.label_list[instr.jaddr]
            # Remove previously fetched instruction from pipeline
            for i in range(0,len(self.simulator.pipe_temp[0])):
                self.simulator.pipe_temp[i].pop()
        elif(instr.op == 'HLT'):
            self.simulator.done = True
            # Remove previously fetched instruction from pipeline
            for i in range(0, len(self.simulator.pipe_temp[0])):
                self.simulator.pipe_temp[i].pop()
        else:
            print("No logic to implement instruction")
            print(instr.op)

class Read:
    def __init__(self,simulator):
        self.simulator = simulator

    def can_read(self,instr,index):
        #Check for RAW Hazards

        for i in range(1,4):
            for instr2 in self.simulator.pipe_reg[i]:
                if(instr.op in ['SW','S.D']):
                    # Store: SW R1, 8(R2)
                    if((instr.dest == instr2.dest or instr.r2 == instr2.dest) and instr.string != instr2.string):
                        instr.RAW = True
                        return False
                else:
                    # Store instructions can't cause RAW hazards
                    if not(instr2.op in ['SW','S.D']):
                        if((instr.IS > instr2.IS) and (instr.string != instr2.string) and (instr2.dest == instr.r1 or instr2.dest == instr.r2)):
                            instr.RAW = True
                            return False
        return True

    def run(self,instructions):
        if(len(instructions)==0):
            return
        index = 0
        pop_list = []
        for instr in instructions:
            advance = self.can_read(instr,index)
            if(advance):
                # Read in values from register file
                if(instr.r1 in self.simulator.registers):
                    instr.r1 = self.simulator.registers[instr.r1]
                if (instr.r2 in self.simulator.registers):
                    instr.r2 = self.simulator.registers[instr.r2]
                instr.RD = self.simulator.cycle
                pop_list = [index] + pop_list
                # Check if branch instruction
                if(instr.op in ['BNE','BEQ']):
                    self.branch(instr)
                else:
                    self.simulator.pipe_temp[2].append(instr)
            index += 1
        for index in pop_list:
            self.simulator.pipe_reg[1].pop(index)

    def branch(self,instr):
        # Resolve branch
        cond1 = (instr.r1 == instr.r2)
        cond2 = (instr.op == 'BEQ')
        if not (cond1^cond2):
            # Taken branch - Jump to address
            self.simulator.PC_MEM = self.simulator.label_list[instr.jaddr]
            # Check if fetch is busy fetching an instruction. If it is, it has to fetch if first then continue
            # If not, then the next instruction will be fetched
            if(self.simulator.pipeline[0].databus == False):
                self.simulator.pipeline[0].address = self.simulator.PC_MEM
            # Clean out pipeline if necessary
            for i in range(0, len(self.simulator.pipe_reg[0])):
                self.simulator.pipe_reg[0].pop()
        #Untaken branch does nothing
        self.simulator.pipeline[1].branch_wait = False

class Execution:
    def __init__(self,simulator):
        self.simulator = simulator
        self.stallcycles = dict()
        self.databus = False
        self.databus_cycle = 0
        self.addr_access = []

    # Add instruction to pipeline registers and set number of stalls
    def add_instr(self,instr):
        self.stallcycles[instr.string] = self.simulator.FU[instr.unit][1]
        # Check if load/store instruction
        if (instr.unit == "LOAD/STORE"):
            # Check if double or single word
            #if(instr.op in ['LW'])
            if(instr.op.find(".")== -1):
                instr.result = int(instr.r1) + instr.r2
                self.addr_access.append(instr.result)
            else:
                #Double word
                self.addr_access += [int(instr.r1) + instr.r2,int(instr.r1) + instr.r2+0x4]

    def execute(self,instr):
        # Execute integer instructions
        # Return True to tell
        if (instr.unit == 'INT'):
            if(instr.op == 'LI'):
                instr.result = int(instr.r1)
            elif(instr.op == 'LUI'):
                instr.result = int(instr.r1)*65536
            elif(instr.op in ['DADD','DADDI']):
                # Second one is typecasted into integer. This is necessary for DADDI instructions
                instr.result = instr.r1 + int(instr.r2)
            elif(instr.op in ['DSUB','DSUBI']):
                instr.result = instr.r1 - int(instr.r2)
            elif (instr.op in ['AND', 'ANDI']):
                instr.result = instr.r1 & int(instr.r2)
            elif (instr.op in ['OR', 'ORI']):
                instr.result = instr.r1 | int(instr.r2)
            return True
        # Execute load and store instructions
        elif (instr.unit == 'LOAD/STORE'):
            # Check if we still need to fetch instructions
            valid = self.simulator.DCache.valid(self.addr_access[0])
            if(valid):
                # Remove address from self.addr_access
                addr = self.addr_access.pop(0)
                self.simulator.dcache_request += 1
                self.simulator.dcache_hit += 1
                if(instr.op=='LW'):
                    instr.result = self.simulator.DCache.access(addr)
                    return True
                elif(instr.op == 'SW'):
                    self.simulator.DCache.write_block(addr, self.simulator.registers[instr.dest])
                    self.simulator.DCache.printcache(self.simulator.cycle)
                    return True
                elif(instr.op in ['L.D','S.D']):
                    if(instr.op == 'S.D'):
                        # Sets block to dirty value
                        self.simulator.DCache.write_block(addr,None)
                        self.simulator.DCache.printcache(self.simulator.cycle)
                    # Check if we still have to fetch another instruction
                    if (len(self.addr_access) != 0):
                        self.stallcycles[instr.string] += 1
                        return False
                    else:
                        return True
            else:
                # Cache miss
                self.simulator.dcache_hit -= 1
                self.databus = True
                # Check if Fetch databus is busy
                if(self.simulator.pipeline[0].databus):
                    self.stallcycles[instr.string] += self.simulator.pipeline[0].stallcycles + 1
                self.stallcycles[instr.string] += 12
                # Check if overwritten block is dirty and has to be written back into memory
                if (self.simulator.DCache.need_write_back(self.addr_access[0])):
                    # Need to write back
                    self.stallcycles[instr.string] += 12
                    self.simulator.DCache.update_mem(self.addr_access[0])
                self.databus_cycle = self.stallcycles[instr.string] - 1
                self.simulator.DCache.add_block(self.addr_access[0])
                self.simulator.DCache.printcache(self.simulator.cycle+self.databus_cycle)
                return False
        else:
            return True
    def run(self,instructions):
        # Adds the instruction to the pipeline_registers
        if(len(instructions) != 0):
            # Check databus
            if(self.databus_cycle > 0):
                self.databus_cycle -= 1
                if(self.databus_cycle==0):
                    self.databus = False
            # Check if instr is already in instr
            index = 0
            pop_list = []
            for instr in instructions:
                # If this is true, then we have a new instruction
                if not(instr.string in self.stallcycles):
                    self.add_instr(instr)
                # Stall by one cycle
                self.stallcycles[instr.string] -= 1
                if(self.stallcycles[instr.string]==0):
                    advance = self.execute(instr)
                    # If return True, then move instruction into the next pipe_reg
                    if(advance):
                        instr.EXE = self.simulator.cycle
                        self.simulator.pipe_temp[3].append(instr)
                        # Store the values that will be popped later, which is necessary since popping affects the loop
                        pop_list = [index] + pop_list
                        del self.stallcycles[instr.string]
                index += 1
            for i in pop_list:
                self.simulator.pipe_reg[2].pop(i)

class Write:
    def __init__(self,simulator):
        self.simulator = simulator

    def run(self,instructions):
        if(len(instructions) != 0):
            pop_list = []
            index = 0
            for instr in instructions:
                instr.WR = self.simulator.cycle
                # Update registers
                if (instr.dest.find("R") != -1 and instr.op != "SW"):
                    self.simulator.registers[instr.dest] = instr.result
                # Free up FU
                self.simulator.FU[instr.unit][0] += 1
                # Remove instruction from pipeline
                pop_list = [index] + pop_list
            for index in pop_list:
                self.simulator.pipe_reg[3].pop(index)














