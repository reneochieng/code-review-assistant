"""A deliberately messy module used to demonstrate the analyzer's output."""
import os
import sys
from collections import *


def append_item(item, target=[]):   # mutable default + missing 'sys'/'os' usage
    target.append(item)
    return target


def find(data):
    # 'find' shadows a name? no -- but this has a None comparison and bare except
    result = 0
    unused = 42
    for row in data:
        if row == None:
            continue
        try:
            result += int(row)
        except:
            pass
    return result


def classify(x):
    if type(x) == int:
        return "int"
    return "other"


def busy(a, b, c, d, e, f, g):        # too many arguments
    total = 0
    for i in range(a):
        if i % 2 and i % 3 and i % 5:
            total += 1
        elif i > b:
            total -= 1
        while total > c:
            total -= 1
    return total


class widget:                          # shadows builtin? no -- lowercase, but missing docstring
    def run(self):
        # TODO: implement this properly
        return None
