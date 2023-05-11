import unittest
import yaml


class SruCycleState:

    filename = "../sru-cycle.yaml"
    _data = None

    @classmethod
    def data(cls):
        if cls._data is None:
            try:
                with open(cls.filename) as yfd:
                    cls._data = yaml.safe_load(yfd)
            except yaml.YAMLError as e:
                cls._data = e
        return cls._data


class TestSruCycleCore(unittest.TestCase):

    @property
    def data(self):
        return SruCycleState.data()

    @property
    def data_error(self):
        return isinstance(self.data, Exception)

    def require_data(self):
        if self.data_error:
            self.skipTest("data malformed, load failed")

    def require_data_dict(self):
        self.require_data()
        if not isinstance(self.data, dict):
            raise self.skipTest("top level dictionary expected")


class TestSruCycleA(TestSruCycleCore):

    def test_data_loads(self):
        if self.data_error:
            raise self.data


class TestSruCycleB(TestSruCycleCore):

    def test_data_dict(self):
        self.require_data()
        self.assertIsInstance(self.data, dict)

    def test_data_keys(self):
        self.require_data_dict()
        for cycle_name in self.data:
            self.assertRegex(cycle_name, r"^[dsc]?[0-9]{4}\.[0-9]{2}\.[0-9]{2}$", "malformed cycle name")
