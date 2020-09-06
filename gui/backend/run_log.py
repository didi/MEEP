import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(sys.path[0]))
)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_log.py <log_number>")
    __import__('logs.log_{}'.format(sys.argv[1]))
