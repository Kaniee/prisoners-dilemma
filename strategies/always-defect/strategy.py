def always_defect():
    while True:
        print("D", flush=True)
        input()  # Read and ignore opponent's move


if __name__ == "__main__":
    always_defect()
