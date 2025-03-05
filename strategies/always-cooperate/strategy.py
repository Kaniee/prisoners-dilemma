def always_cooperate():
    while True:
        print("C", flush=True)
        input()  # Read and ignore opponent's move


if __name__ == "__main__":
    always_cooperate()
