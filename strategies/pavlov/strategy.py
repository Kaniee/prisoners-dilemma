def pavlov():
    """
    Starts with cooperation.
    If both players made the same choice, cooperate.
    If players made different choices, defect.
    """
    my_last_move = "C"
    print("C", flush=True)  # First move

    while True:
        opponent_move = input().strip()

        if my_last_move == opponent_move:
            my_last_move = "C"
        else:
            my_last_move = "D"

        print(my_last_move, flush=True)


if __name__ == "__main__":
    pavlov()
