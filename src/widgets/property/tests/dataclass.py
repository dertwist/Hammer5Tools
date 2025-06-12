import unittest
from src.widgets.property.dataclass import VsmartVariableDataclass


class TestVsmartVariableDataclass(unittest.TestCase):
    def test_all_fields_present(self):
        obj = VsmartVariableDataclass(
            m_VariableName="Var1",
            m_DisplayName="Display1",
            m_ElementID=101,
            m_DefaultValue=5,
            m_nParamaterMinValue=0,
            m_nParamaterMaxValue=10,
            m_flParamaterMinValue=0.1,
            m_flParamaterMaxValue=1.5,
            m_sModelName="ModelX"
        )
        expected = {
            "m_VariableName": "Var1",
            "m_DisplayName": "Display1",
            "m_ElementID": 101,
            "m_DefaultValue": 5,
            "m_nParamaterMinValue": 0,
            "m_nParamaterMaxValue": 10,
            "m_flParamaterMinValue": 0.1,
            "m_flParamaterMaxValue": 1.5,
            "m_sModelName": "ModelX",
            "m_ShowChild": True
        }
        self.assertEqual(obj.to_dict(), expected)

    def test_missing_optional_fields(self):
        obj = VsmartVariableDataclass(
            m_VariableName="Var2",
            m_DisplayName="Display2",
            m_ElementID=202,
            m_DefaultValue=None,
        )
        expected = {
            "m_VariableName": "Var2",
            "m_DisplayName": "Display2",
            "m_ElementID": 202,
            "m_DefaultValue": "",
            "m_ShowChild": True
        }
        self.assertEqual(obj.to_dict(), expected)

    def test_some_fields_set(self):
        obj = VsmartVariableDataclass(
            m_VariableName="Var3",
            m_DisplayName=None,
            m_ElementID=303,
            m_DefaultValue="GreenPaint",
            m_nParamaterMinValue=None,
            m_nParamaterMaxValue=None,
            m_flParamaterMinValue=0.5,
            m_flParamaterMaxValue=None,
            m_sModelName=None
        )
        expected = {
            "m_VariableName": "Var3",
            "m_DisplayName": None,
            "m_ElementID": 303,
            "m_DefaultValue": "GreenPaint",
            "m_flParamaterMinValue": 0.5,
            "m_ShowChild": True
        }
        self.assertEqual(obj.to_dict(), expected)


if __name__ == '__main__':
    unittest.main()
