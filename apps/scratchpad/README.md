# Enhanced Scratchpad Calculator - User Guide

## Overview
The Enhanced Scratchpad Calculator is a powerful mathematical expression evaluator with support for variables, functions, and advanced mathematical operations. Type expressions in the left pane and see results in the right pane in real-time.

## Supported Operations

### 2.1 Arithmetic Operations
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

### 2.2 Parentheses for Precedence
Use parentheses to control the order of operations:

Examples:
```
(2 + 3) * 4
2 * (3 + 4)
(10 - 2) / (3 + 1)
```

### 2.3 Mathematical Constants
- **π (pi)**: `pi` = 3.141592653589793
- **e**: `e` = 2.718281828459045

Examples:
```
pi
e
2 * pi
pi / 2
```

### 2.4 Built-in Functions

#### Basic Functions
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

Examples:
```
log(100)
ln(e)
log(1000)
ln(10)
```

### 2.5 Variables
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

### 2.6 Advanced Examples

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

#### Physics Calculations
```
# Kinetic energy
mass = 10
velocity = 20
kinetic_energy = 0.5 * mass * velocity^2

# Distance with acceleration
initial_velocity = 5
acceleration = 2
time = 3
distance = initial_velocity * time + 0.5 * acceleration * time^2
```

## Error Handling

The calculator provides descriptive error messages for various scenarios:

- **Division by zero**: "Error: Division by zero"
- **Undefined variables**: "Error: Undefined variable - name 'variable_name' is not defined"
- **Invalid syntax**: "Error: Invalid syntax"
- **Invalid values**: "Error: Invalid value - [specific error]"

## Comments
Lines starting with `#` are treated as comments and are ignored:

```
# This is a comment
x = 5  # This calculates something
y = x * 2
```

## Tips
1. **Empty lines**: Empty lines in the input will show as empty lines in the results
2. **Real-time updates**: Results update automatically as you type
3. **Variable persistence**: Variables are remembered throughout the session
4. **Case sensitivity**: Variable names are case-sensitive
5. **Valid variable names**: Use letters, numbers, and underscores; must start with a letter or underscore

## Limitations
- Variables are reset when the text changes completely
- Only basic mathematical operations and functions are supported
- Security: Uses a restricted evaluation environment for safety
