"""
核心抽象層

定義語言無關的接口和抽象基類。
"""

from .phonetic_interface import PhoneticSystem
from .tokenizer_interface import Tokenizer
from .fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
    convert_to_simple_list,
)

__all__ = [
    "PhoneticSystem",
    "Tokenizer",
    "BaseFuzzyGenerator",
    "PhoneticVariant",
    "VariantSource",
    "convert_to_simple_list",
]
