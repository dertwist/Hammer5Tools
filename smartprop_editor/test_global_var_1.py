import time
from smartprop_editor.element_id import *
from smartprop_editor.test_global_var_2 import test

start_time = time.time()

for i in range(20200):
    test()

class test2():
    def __init__(self):
        super().__init__()
        print(f'test2 {set_ElementId(5)}')

test2()

# global m_nElementID
print(m_nElementID)

end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")