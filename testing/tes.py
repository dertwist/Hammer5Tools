import ast

str_value = '[0.0, 1.0, 0.0, 0.0, 2.0, 3.0]'
value = ast.literal_eval(str_value)
for item in value:
    print(item)