def grudger():
    """
    Cooperates until opponent defects, then always defects.
    Also known as "Grim Trigger"
    """
    has_defected = False
    print("C", flush=True)  # First move

    while True:
        opponent_move = input().strip()
        if opponent_move == "D":
            has_defected = True

        if has_defected:
            print("D", flush=True)
        else:
            print("C", flush=True)


if __name__ == "__main__":
    grudger()
