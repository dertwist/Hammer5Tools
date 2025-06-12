from dataclasses import dataclass, field
from typing import Dict
from typing import Union, Optional
import unittest

@dataclass
class BasePropertyDataclass:
    m_label: str
    m_ShowChild: bool = True

    def to_dict(self) -> dict:
        return {
            "m_Label": self.m_label,
            "m_ShowChild": self.m_ShowChild
        }


@dataclass
class VsmartVariableDataclass:
    _class: str
    m_VariableName: str
    m_DisplayName: Optional[str]
    m_ElementID: int
    m_DefaultValue: Union[str, float, int, list, None]
    m_nParamaterMinValue: Optional[int] = None
    m_nParamaterMaxValue: Optional[int] = None
    m_flParamaterMinValue: Optional[float] = None
    m_flParamaterMaxValue: Optional[float] = None
    m_sModelName: Optional[str] = None
    m_bExposeAsParameter: bool = False
    m_ShowChild: bool = True


    def to_dict(self) -> dict:
        data = {
            "m_VariableName": self.m_VariableName,
            "m_bExposeAsParameter": self.m_bExposeAsParameter,
            "m_DisplayName": self.m_DisplayName,
            "m_ElementID": self.m_ElementID,
            "m_DefaultValue": self.m_DefaultValue if self.m_DefaultValue is not None else "",
            "m_ShowChild": self.m_ShowChild
        }

        if self.m_nParamaterMinValue is not None:
            data["m_nParamaterMinValue"] = self.m_nParamaterMinValue

        if self.m_nParamaterMaxValue is not None:
            data["m_nParamaterMaxValue"] = self.m_nParamaterMaxValue

        if self.m_flParamaterMinValue is not None:
            data["m_flParamaterMinValue"] = self.m_flParamaterMinValue

        if self.m_flParamaterMaxValue is not None:
            data["m_flParamaterMaxValue"] = self.m_flParamaterMaxValue

        if self.m_sModelName is not None:
            data["m_sModelName"] = self.m_sModelName

        return data


@dataclass
class VsmartPropertyDataclass:
    m_Label: str
    m_ElementID: int
    m_Class: str
    m_Data: Dict = field(default_factory=dict)
    m_ShowChild: bool = True

    def to_dict(self) -> dict:
        return {
            "m_Label": self.m_Label,
            "m_ElementID": self.m_ElementID,
            "m_Class": self.m_Class,
            "m_Data": self.m_Data,
            "m_ShowChild": self.m_ShowChild
        }


@dataclass
class SoundEventPropertyDataclass:
    m_Class: str
    m_Data: Dict = field(default_factory=dict)
    m_ShowChild: bool = True

    def to_dict(self) -> dict:
        return {
            "m_Class": self.m_Class,
            "m_Data": self.m_Data,
            "m_ShowChild": self.m_ShowChild
        }

