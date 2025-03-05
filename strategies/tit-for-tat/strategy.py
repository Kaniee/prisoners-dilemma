def tit_for_tat():
    print("C", flush=True)  # First move

    while True:
        opponent_move = input().strip()
        # Copy opponent's last move
        print(opponent_move, flush=True)


if __name__ == "__main__":
    tit_for_tat()
