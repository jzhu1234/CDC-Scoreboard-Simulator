import sys
from Simulator import SIM

def main():
    # Check if files were provided
    if (len(sys.argv) == 5):
        if(sys.argv[1:5] == ["inst.txt","data.txt","config.txt","results.txt"]):
            sim = SIM()
            sim.run()
            sim.print_results(sys.argv[4])
        else:
            print("Usage: simulator inst.txt data.txt config.txt result.txt")
    else:
        print("Usage: simulator inst.txt data.txt config.txt result.txt")

if __name__ == "__main__":
    main()