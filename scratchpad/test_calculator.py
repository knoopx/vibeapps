#!/usr/bin/env python

"""Test script for the enhanced scratchpad calculator functionality"""

import math

def test_safe_eval():
    """Test the safe_eval functionality independently"""

    class MockCalculator:
        def __init__(self):
            self.variables = {}

        def safe_eval(self, expression):
            """Safely evaluate mathematical expressions with enhanced functionality"""
            # Create a safe namespace with math functions and constants
            safe_namespace = {
                '__builtins__': {},
                # Basic math operations
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                # Math functions
                'sqrt': math.sqrt,
                'floor': math.floor,
                'ceil': math.ceil,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log10,
                'ln': math.log,
                # Constants
                'pi': math.pi,
                'e': math.e,
                # Power operator replacement
                'pow': pow,
            }

            # Add user-defined variables
            safe_namespace.update(self.variables)

            # Replace ^ with ** for power operations
            expression = expression.replace('^', '**')

            return eval(expression, safe_namespace)

    calc = MockCalculator()

    # Test basic arithmetic
    print("Basic arithmetic:")
    print(f"2 + 3 = {calc.safe_eval('2 + 3')}")
    print(f"10 - 4 = {calc.safe_eval('10 - 4')}")
    print(f"5 * 6 = {calc.safe_eval('5 * 6')}")
    print(f"15 / 3 = {calc.safe_eval('15 / 3')}")
    print(f"2 ^ 3 = {calc.safe_eval('2 ^ 3')}")
    print(f"17 % 5 = {calc.safe_eval('17 % 5')}")

    # Test parentheses
    print("\nParentheses:")
    print(f"(2 + 3) * 4 = {calc.safe_eval('(2 + 3) * 4')}")
    print(f"2 + (3 * 4) = {calc.safe_eval('2 + (3 * 4)')}")

    # Test constants
    print("\nConstants:")
    print(f"pi = {calc.safe_eval('pi')}")
    print(f"e = {calc.safe_eval('e')}")
    print(f"2 * pi = {calc.safe_eval('2 * pi')}")

    # Test functions
    print("\nFunctions:")
    print(f"sqrt(16) = {calc.safe_eval('sqrt(16)')}")
    print(f"abs(-5) = {calc.safe_eval('abs(-5)')}")
    print(f"round(3.7) = {calc.safe_eval('round(3.7)')}")
    print(f"floor(3.7) = {calc.safe_eval('floor(3.7)')}")
    print(f"ceil(3.2) = {calc.safe_eval('ceil(3.2)')}")

    # Test trigonometry (in radians)
    print("\nTrigonometry:")
    print(f"sin(pi/2) = {calc.safe_eval('sin(pi/2)')}")
    print(f"cos(0) = {calc.safe_eval('cos(0)')}")
    print(f"tan(pi/4) = {calc.safe_eval('tan(pi/4)')}")

    # Test logarithms
    print("\nLogarithms:")
    print(f"log(100) = {calc.safe_eval('log(100)')}")  # log10
    print(f"ln(e) = {calc.safe_eval('ln(e)')}")  # natural log

    # Test variables
    print("\nVariables:")
    calc.variables['x'] = 5
    calc.variables['y'] = 10
    print(f"x = 5, y = 10")
    print(f"x + y = {calc.safe_eval('x + y')}")
    print(f"x * y = {calc.safe_eval('x * y')}")

    # Test complex expression
    print("\nComplex expression:")
    calc.variables['tax'] = 0.1
    total = calc.safe_eval('200 + 200 * tax')
    print(f"tax = 0.1, total = 200 + 200 * tax = {total}")

if __name__ == "__main__":
    test_safe_eval()
