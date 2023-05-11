import unittest
import yaml


class SigningConfigState:

    filename = "../signing-config.yaml"
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


class TestSigningConfigCore(unittest.TestCase):

    @property
    def data(self):
        return SigningConfigState.data()

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


class TestSigningConfigA(TestSigningConfigCore):

    def test_data_loads(self):
        if isinstance(self.data, Exception):
            raise self.data


class TestSigningConfigB(TestSigningConfigCore):

    def test_data_dict(self):
        self.require_data()
        self.assertIsInstance(self.data, dict)

    def test_streams_dict(self):
        self.require_data_dict()
        self.assertIn("streams", self.data)
        self.assertIsInstance(self.data["streams"], dict)

    def test_streams_keys(self):
        self.require_data_dict()
        for key_name in self.data.get("streams", {}):
            self.assertRegex(key_name, r"^[a-z9-9-]+$", "malformed key name")
