# Scratchpad

## Overview

A powerful mathematical expression evaluator with support for variables, functions, and advanced mathematical operations. Type expressions in the left pane and see results in real-time in the right pane with synchronized scrolling.

## Features

- Real-time expression evaluation
- Variable assignment and persistence
- Comprehensive mathematical functions
- Error highlighting and descriptive messages
- Synchronized scrolling between input and output panes
- Comment support
- Programming utilities (binary, hex, octal conversions)
- Time and memory unit constants

## Supported Operations

### 1. Arithmetic Operations

- **Addition**: `+`
- **Subtraction**: `-`
- **Multiplication**: `*`
- **Division**: `/`
- **Exponentiation**: `^` (converted to `**`)
- **Modulo**: `%`

Examples:

```
5 + 3
10 - 4
6 * 7
20 / 4
2 ^ 8
17 % 5
```

### 2. Parentheses for Precedence

Use parentheses to control the order of operations:

Examples:

```
(2 + 3) * 4
2 * (3 + 4)
(10 - 2) / (3 + 1)
```

### 3. Mathematical Constants

- **π (pi)**: `pi` = 3.141592653589793
- **e**: `e` = 2.718281828459045

Examples:

```
pi
e
2 * pi
pi / 2
```

### 4. Built-in Functions

#### Basic Functions

- **sqrt(x)**: Square root
- **abs(x)**: Absolute value
- **round(x)**: Round to nearest integer
- **floor(x)**: Round down to nearest integer
- **ceil(x)**: Round up to nearest integer
- **min(x, y, ...)**: Minimum value
- **max(x, y, ...)**: Maximum value
- **sum(iterable)**: Sum of values
- **len(iterable)**: Length of sequence
- **pow(x, y)**: Power function (x^y)

Examples:

```
sqrt(16)
abs(-5)
round(3.7)
floor(3.9)
ceil(3.1)
min(5, 3, 8)
max(2, 7, 4)
pow(2, 8)
```

#### Advanced Mathematical Functions

- **factorial(x)**: Factorial of x
- **gcd(x, y)**: Greatest common divisor
- **lcm(x, y)**: Least common multiple
- **log2(x)**: Base-2 logarithm
- **avg(x, y, ...)**: Average of values
- **median(x, y, ...)**: Median of values

Examples:

```
factorial(5)
gcd(48, 18)
lcm(12, 8)
log2(256)
avg(1, 2, 3, 4, 5)
median(1, 3, 2, 5, 4)
```

- **sqrt(x)**: Square root
- **abs(x)**: Absolute value
- **round(x)**: Round to nearest integer
- **floor(x)**: Round down to nearest integer
- **ceil(x)**: Round up to nearest integer
- **min(x, y, ...)**: Minimum value
- **max(x, y, ...)**: Maximum value

Examples:

```
sqrt(16)
abs(-5)
round(3.7)
floor(3.9)
ceil(3.1)
min(5, 3, 8)
max(2, 7, 4)
```

#### Trigonometric Functions (in radians)

- **sin(x)**: Sine
- **cos(x)**: Cosine
- **tan(x)**: Tangent

Examples:

```
sin(pi/2)
cos(0)
tan(pi/4)
sin(pi/6)
```

#### Logarithmic Functions

- **log(x)**: Base-10 logarithm
- **ln(x)**: Natural logarithm (base-e)
- **log2(x)**: Base-2 logarithm

Examples:

```
log(100)
ln(e)
log2(256)
log(1000)
ln(10)
```

#### Programming Utilities

- **bin(x)**: Binary representation (without 0b prefix)
- **hex(x)**: Hexadecimal representation (without 0x prefix)
- **oct(x)**: Octal representation (without 0o prefix)

Examples:

```
bin(15)     # Returns: 1111
hex(255)    # Returns: ff
oct(64)     # Returns: 100
```

### 5. Built-in Constants

#### Memory Units

- **kb**: 1024 (Kilobyte)
- **mb**: 1024² (Megabyte)
- **gb**: 1024³ (Gigabyte)
- **tb**: 1024⁴ (Terabyte)

Examples:

```
5 * gb          # 5 gigabytes in bytes
512 * mb        # 512 megabytes in bytes
2 * tb          # 2 terabytes in bytes
```

#### Time Units (in seconds)

- **seconds**: 1
- **minutes**: 60
- **hours**: 3600
- **days**: 86400
- **weeks**: 604800
- **years**: 31536000

Examples:

```
5 * minutes     # 5 minutes in seconds
2 * hours       # 2 hours in seconds
30 * days       # 30 days in seconds
```

### 6. Variables

Define and use variables in your calculations. Variables persist throughout the session and can be referenced in subsequent expressions.

#### Variable Assignment

```
variable_name = expression
```

#### Using Variables

Once defined, variables can be used in any expression:

Examples:

```
# Define variables
x = 5
y = 10
radius = 7

# Use variables in calculations
x + y
x * y
area = pi * radius^2
circumference = 2 * pi * radius

# More complex examples
tax_rate = 0.085
subtotal = 150
tax = subtotal * tax_rate
total = subtotal + tax
```

### 7. Advanced Examples

#### Compound Interest Calculation

```
principal = 1000
rate = 0.05
time = 3
amount = principal * (1 + rate)^time
interest = amount - principal
```

#### Geometry Calculations

```
# Circle
radius = 5
area = pi * radius^2
circumference = 2 * pi * radius

# Triangle (using Pythagorean theorem)
a = 3
b = 4
c = sqrt(a^2 + b^2)
```

#### Programming Calculations

```
# Binary, hex, octal conversions
decimal_value = 255
binary_rep = bin(decimal_value)    # 11111111
hex_rep = hex(decimal_value)       # ff
octal_rep = oct(decimal_value)     # 377

# Memory calculations
file_size_mb = 150
file_size_bytes = file_size_mb * mb
storage_capacity = 2 * tb
files_that_fit = storage_capacity / file_size_bytes
```

#### Statistical Calculations

```
# Dataset analysis
data_points = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
count = len(data_points)
average = avg(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
middle = median(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# Factorial and combinations
n = 10
r = 3
combinations = factorial(n) / (factorial(r) * factorial(n - r))
```

#### Time and Duration Calculations

```
# Convert time units
meeting_duration = 90 * minutes
project_deadline = 2 * weeks
work_hours_per_year = 40 * hours * 52 * weeks / years
```

## 8. Error Handling

The calculator provides descriptive error messages for various scenarios:

- **Division by zero**: "Division by zero"
- **Undefined variables**: "Undefined variable - name 'variable_name' is not defined"
- **Invalid syntax**: "Invalid syntax"
- **Invalid values**: "Invalid value - [specific error]"

Errors are highlighted in red in the results pane for easy identification.

## 9. Comments

Lines starting with `#` are treated as comments and are ignored:

```
# This is a comment
x = 5  # This calculates something
y = x * 2
```

## 10. Tips and Features

1. **Synchronized scrolling**: Input and output panes scroll together
2. **Empty lines**: Empty lines in the input will show as empty lines in the results
3. **Real-time updates**: Results update automatically as you type
4. **Variable persistence**: Variables are remembered throughout the session
5. **Case sensitivity**: Variable names are case-sensitive
6. **Valid variable names**: Use letters, numbers, and underscores; must start with a letter or underscore
7. **Error highlighting**: Errors appear in red text for easy identification
8. **Integer display**: Results that are whole numbers display without decimal points

## 11. Limitations

- Variables are reset when the text is completely cleared
- Uses a restricted evaluation environment for security
- Only mathematical operations and approved functions are available
- No file I/O or system operations for safety
