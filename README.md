# probify
Complex dice sequence probability calculator written in Python.

# about  
I like knowing the exact probability of different dice sequences for balancing purposes. This program lets you write dice roll sequences in Python-style syntax, automatically calculates the exact probabilities mathematically, and displays the results as a bar chart.  

# why not just simulate the dice rolls?  
You could simulate a million rolls and estimate probabilities, but this is **slow and inaccurate**. This program **computes the exact probabilities** using math, not brute force. No randomness involved.  

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
- Conditional rerolling:  
  ```python
  x = 1d6
  if x < 3:
      x = 1d6
  ```  
- Loops:  
  ```python
  total = 0
  for i in range(4):
      total += 1d6
  ```  
- Complex example:  
  ```python
  val = 0
  for i in range(6):
      x = 1d6
      if x < 3:
          x = 1d6
      val += x

  y = 1d8
  if y < 3:
      y = 1d8
  val += y

  val += 1d4
  val += 15
  ```

# configuration  
- `DECIMAL_POINTS = 2` → How many decimal places to show for probabilities  
- `MIN_LABEL_PERCENT = 1.0` → Hide probability labels below this percentage  
