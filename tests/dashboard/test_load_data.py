from src.app import load_data
import pandas as pd


def test_tuple_output() -> None:
    """
    Test that the function returns a tuple.
    """
    assert type(load_data()) == tuple


def test_tuple_length() -> None:
    """
    Test that the function returns a tuple of length 3.
    """
    assert len(load_data()) == 3


def test_tuple_elements() -> None:
    """
    Test that the function returns a tuple with the correct elements.
    """
    for element in load_data():
        assert type(element) == pd.DataFrame
