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

    def test_data_entry_dict(self):
        self.require_data_dict()
        for cycle_name, cycle_data in self.data.items():
            self.assertIsInstance(cycle_data, dict, "cycle {} not a dictionary")

    def test_data_entry_content(self):
        self.require_data_dict()
        for cycle_name, cycle_data in self.data.items():
            with self.subTest(msg="cycle " + cycle_name):
                for cycle_key, cycle_val in cycle_data.items():
                    if cycle_key in ("start-date", "release-date", "cutoff-date"):
                        self.assertRegex(cycle_val, r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "{} malformed, expecting YYYY-MM-DD".format(cycle_key))
                    elif cycle_key == "complete":
                        self.assertIsInstance(cycle_val, bool, "{} is not boolean".format(cycle_key))
                    elif cycle_key == "stream":
                        self.assertIsInstance(cycle_val, int, "{} is not an integer".format(cycle_key))
                    else:
                        raise AssertionError("key {} invalid".format(cycle_key))
