# test = {'1':'2', '3':'4'}
# print(test)
# print(type(test))
# test.update({'1':'3'})
# print(test)
# print(type(test))




dat = {'_class': 'CSmartPropOperation_SetVariable', 'm_VariableValue': {'m_TargetName': 'Startpiece', 'm_DataType': 'BOOL', 'm_Value': False}}
for item in dat.items():
    if not item[0] == '_class':
        print(item)