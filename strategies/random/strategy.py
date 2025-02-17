from random import choice

def random():
    while True:
        print(choice(['C', 'D']), flush=True)
        input()  # Read and ignore opponent's move

if __name__ == "__main__":
    random()
