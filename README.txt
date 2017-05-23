To execute this project in Windows, type in the command:

python run.py inst.txt data.txt config.txt results.txt

During the run, it will print out the instruction cache and data cache if the cache changes. 
This will occur when block is added or a store instruction occurs.

Data Cache is set so that block 0 is always the LRU block, where block 1 and block 0 form a queue.