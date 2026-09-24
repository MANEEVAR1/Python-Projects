def wordGuessingGame():
    from wonderwords import RandomWord
    import random
    print("$$$$$$$ Welcome to the Word Guessing Game $$$$$$$")
    print()
    print("🚨Information:\n● The player can select the length of the secret word to guess.\n● You will be shown some random letters from the secret word as a hint.\n● You will be given 5 chances to guess the secret word.\n● Only 0.001% people are able to guess the secret word.")
    print()
    while True:
        ready= input("Are you ready to play?: ")
        if ready.lower() not in ('y', 'n'):
            print("Invalid input. Please select 'y' or 'n'")
        elif ready.lower() == 'n':
            print("Goodbye!")
            break
        else:
            while True:
                wordLength = input("How long should the secret word be?: ")
                if not wordLength.isdigit():
                    print("Please enter a number like 5, 6, 7......")
                else:
                    wordLength = int(wordLength)
                    if wordLength < 3 or wordLength > 10:
                        print("Please enter a number between 3 and 10")
                    else:
                        break
            secretWord = RandomWord().word(word_min_length= int(wordLength), word_max_length= int(wordLength))
            hintLength = max(1, round(len(secretWord)*0.60))
            maxStartIndex = len(secretWord) - hintLength
            startIndex = random.randint(0,maxStartIndex)
            print()
            print(f"Hint Letters: {secretWord[startIndex: startIndex + hintLength]}")
            inputCount = 0
            while inputCount < 5:
                guess = input("Enter your guess: ")
                inputCount += 1
                if guess.lower() != secretWord.lower():
                    if (inputCount == 5):
                        print(
                            f"Oh no! You couldn't guess the word. It was {secretWord}.\nTold ya' only 0.001% are able to guess the secret word.")
                    else:
                        print("Wrong guess. Try again.")
                else:
                    print("Correct! You did it")
                    break
            print()
            keepPlaying = True
            while True:
                playAgain = input("Do you want to play again? (y/n): ")
                if playAgain.lower() not in ("y", "n"):
                    print("Invalid input. Please select 'y' or 'n'.")
                elif playAgain.lower() == "n":
                    print("Goodbye!")
                    keepPlaying = False
                    break
                else:
                    break
            if not keepPlaying:
                break

wordGuessingGame()