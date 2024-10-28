from smartprop_editor.element_id import *
from smartprop_editor.test_global_var_2 import test
for i in range(100):
    test()
class test2():
    def __init__(self):
        super().__init__()
        print(f'test2 {set_ElemntID(5)}')
test2()
# global m_nElementID
print(m_nElementID)