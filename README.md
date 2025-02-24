# probify
Complex dice sequence probability calculator written in Python.

# about  
I like knowing the exact probability of different dice sequences for balancing purposes. This program lets you write dice roll sequences in Python-style syntax, automatically calculates the exact probabilities mathematically, and displays the results as a bar chart. This is perfect for games like Dungeons & Dragons (D&D).

# why not just simulate the dice rolls?  
You could simulate a million rolls and estimate probabilities, but this is **slow and inaccurate**. This program **computes the exact probabilities** using math, not brute force. No randomness involved.

# web version
If you don't want to run the code yourself, you can use this very barebones web version I made:
https://illectrility.github.io/probify-web/

# installation
- Install Python (https://www.python.org/downloads/)
- Install matplotlib (https://matplotlib.org/stable/install/index.html)

# how to use
- Write your dice code in code.txt
- Run program using `python3 probify.py` on Linux or `python probify.py` if you're on Windows
- (https://docs.python.org/3/faq/windows.html#how-do-i-run-a-python-program-under-windows)

# features  
- Write dice sequences in **Python-style syntax**  
- Supports all common dice (d4, d6, d8, d10, d12, d20, etc.)  
- Supports **conditional rerolling** (e.g., "reroll if less than 3")  
- Supports **loops** (e.g., "roll 1d6 five times and sum the results")  
- Displays a **bar chart** of all possible results and their probabilities  
- Configurable **decimal places** for probability percentages  
- Can **hide low-probability labels** under a set threshold  

# syntax
- Dice rolls use `XdY` notation (e.g., `1d6`, `2d8`)  
- Use variables: `x = 1d6`
- Resulting variable is always called `result`
- Conditional rerolling:  
  ```python
  x = 1d6
  if x < 3:
      x = 1d6
  ```  
- Loops:  
  ```python
  result = 0
  for i in range(4):
      result += 1d6
  ```

- Simple example:
  ```python
  result = 0
  for i in range(6): # Repeat 6 times
      result += 1d6 # Add 1d6 to result
  ```

- Simple example 2:
  ```python
  result = 6d6 # Add 6d6 to result
  ```

- More complex example:
  ```python
  result = 0
  for i in range(4): # Repeat 4 times
      x = 1d8 # x is a d8 roll
      if x < 3: # If x is 1 or 2
          x = 1d8 # Re-roll x as a d8
      result += x # Add x to the result
  ```

- Complex example:  
  ```python
  result = 0
  for i in range(6): # Repeat 6 times
      x = 1d6 # x is a d6 roll
      if x < 3: # If x is 1 or 2
          x = 1d6 # Re-roll x as a d6
      result += x # Add x to the result
      # All of this is repeated 6 times

  y = 1d8 # y is a d8 roll
  if y < 3: # If y is 1 or 2
      y = 1d8 # Re-roll y as a d8
  result += y # Add y to the result
  # This isn't repeated

  result += 1d4 # Add a d4 to the result
  result += 15 # Add 15 to the result
  ```

# configuration  
- `DECIMAL_POINTS = 2` → How many decimal places to show for probabilities  
- `MIN_LABEL_PERCENT = 1.0` → Hide probability labels below this percentage
