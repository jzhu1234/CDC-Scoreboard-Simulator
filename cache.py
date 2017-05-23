
class ICACHE:
    def set_mem(self,file):
        f = open(file,"r")
        self.mem = dict()
        y = 0x0
        for line in f.readlines():
            val = line.upper()
            val = val.rstrip()
            self.mem[y] = val
            y += 4
        f.close()

    def __init__(self,file, num, size):
        self.set_mem(file)
        self.size = size  # Block size in words
        self.num_blc = num  # Number of blocks
        # Setup Cache
        setup = {"valid": False, "tag": None, "data": [None] * self.size}
        self.icache = []
        for i in range(0,num):
            self.icache.append(setup)

    def get_index(self, address):
        # Calculate which values we should look at
        address = address//4
        offset = address % self.size
        index = (address//self.size) % self.num_blc
        tag = address//(self.size*self.num_blc)
        return [tag,index,offset]

    def valid(self,address):
        [tag, index, offset] = self.get_index(address)
        # Checks valid bit and if tags are equal
        if (self.icache[index]["valid"] == True and tag == self.icache[index]["tag"]):
            return True
        else:
            return False

    # Function checks if memory address is in cache
    def access(self, address):
        [tag, index, offset] = self.get_index(address)
        return self.icache[index]["data"][offset]

    def add_block(self,address):
        # Get tag and index. Offset does not particularly matter since we will add entire block
        [tag,index,offset] = self.get_index(address)
        address -= offset*4
        data = []
        for i in range(0,self.size):
            try:
                data.append(self.mem[address+(0x4*i)])
            # Possibility of accessing outside instruction values
            except KeyError:
                # Populate with invalid data
                data.append("INVALID DATA")
        self.icache[index] = {'valid':True,'tag':tag,'data':data}
        return
    def printcache(self,cycle):
        print('Instruction Cache. Changed at Cycle: ',cycle)
        for i in range(0,self.num_blc):
            print('Block ',i,': Valid =',self.icache[i]['valid'],'. Tag = ',self.icache[i]['tag'],'. Data = ',self.icache[i]['data'])

class DCACHE:
    def set_mem(self,file):
        f = open(file,"r")
        self.mem = dict()
        y = 0x0
        for line in f.readlines():
            val = int(line,2)
            self.mem[0x100 + y] = val
            y += 4
        f.close()

    def __init__(self,file):
        # By default, this is a two way associative cache with four words in a block, four blocks in total
        self.set_mem(file)
        self.size = 4  # Block size in words
        self.blk_per_set = 2 # Number of blocks per set
        self.num_set = 2 # Number of sets
        # Setup Cache
        self.dcache = []
        set = {"valid": False,"tag": None,"dirty":False,"data":[None]*self.size}
        setup = [set]*self.blk_per_set
        for i in range(0,self.num_set):
            setup = [set] * self.blk_per_set
            # Done twice because we have 2 blks_per_set
            self.dcache.append(setup)

    def get_index(self, address):
        # Calculate which values we should look at
        address = address//4
        offset = address % self.size
        set = (address//self.size) % self.num_set
        tag = address//(self.size*self.num_set)
        return [tag,set,offset]

    def valid(self,address):
        [tag,set,offset] = self.get_index(address)
        for i in range(0,self.blk_per_set):
            # Checks valid bit and if tag matches
            if (self.dcache[set][i]["valid"]== True and tag == self.dcache[set][i]["tag"]):
                # If check is found, then we alter the order so that the value is at the farthest right of the set
                # [0,5] -> [5,0]. 5 is now LRU
                # Not very useful now, but would be useful for larger sets if necessary
                if(i != self.blk_per_set-1):
                    temp = self.dcache[set].pop(i)
                    self.dcache[set].append(temp)
                return True
        # If reached this point, then we did not find a match
        return False

    def need_write_back(self,address):
        # Check if we need to write back to memory by checking dirty bit
        # Should be run after valid command in Simulator.py
        [tag, set, offset] = self.get_index(address)
        return self.dcache[set][0]["dirty"]

    def access(self, address):
        [tag, set, offset] = self.get_index(address)
        # Cache is set up the LRU is at index 0, and currently used value is at the
        # end of the cache set
        for blk in self.dcache[set]:
            if (blk["tag"] == tag):
                return blk["data"][offset]
        #return self.dcache[set][self.blk_per_set-1]["data"][offset]

    def add_block(self,address):
        # Get tag and index. Offset does not particularly matter since we will add entire block
        [tag,set,offset] = self.get_index(address)
        # Get the data
        address -= offset*4
        data = []
        for i in range(0,self.size):
            data.append(self.mem[address+(i*0x4)])
        # Pop out first value, then append new block
        self.dcache[set].pop(0)
        self.dcache[set].append({"valid": True,"tag": tag,"dirty":False,"data":data})
        return

    def write_block(self,address,value):
        [tag, set, offset] = self.get_index(address)
        if(value != None):
            self.dcache[set][self.blk_per_set-1]["data"][offset] = value
        self.dcache[set][self.blk_per_set-1]["dirty"] = True

    def update_mem(self,address):
        # Take the LRU and write it into main memory
        [tag, set, offset] = self.get_index(address)
        addr_replace = self.dcache[set][0]['tag']*32 + set*16
        data = self.dcache[set][0]["data"]
        for i in range(0,self.size):
            self.mem[addr_replace+(i*0x4)] = data[i]
        return
    def printcache(self,cycle):
        print('Data Cache. Changed at Cycle: ',cycle)
        for i in range(0,self.num_set):
            for j in range(0,self.blk_per_set):
                print('Set ',i,' Block ', j,': Valid =',self.dcache[i][j]['valid'],'. Dirty =',self.dcache[i][j]['dirty'],'. Tag = ',self.dcache[i][j]['tag'],'. Data = ',self.dcache[i][j]['data'])