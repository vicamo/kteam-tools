import unittest
import yaml


class KernelSeriesState:

    filename = "../kernel-series.yaml"
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


class TestKernelSeriesCore(unittest.TestCase):

    @property
    def data(self):
        return KernelSeriesState.data()

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


class TestKernelSeriesA(TestKernelSeriesCore):

    def test_data_loads(self):
        if isinstance(self.data, Exception):
            raise self.data


class TestKernelSeriesB(TestKernelSeriesCore):

    def test_data_dict(self):
        self.require_data()
        self.assertIsInstance(self.data, dict)

    def test_data_keys(self):
        self.require_data_dict()
        for series_name in self.data:
            if series_name == "defaults":
                continue
            self.assertRegex(series_name, r"^[0-9]{1,2}\.[0-9]{2}$", msg=f"malformed series name")

class TestKernelSeriesSource(TestKernelSeriesCore):

    def test_source_variants(self):
        self.require_data_dict()
        for series_name, series in self.data.items():
            if series_name == "defaults":
                continue
            if "sources" not in series:
                continue
            for source in series["sources"].values():
                if "variants" not in source:
                    continue
                for variant in source["variants"]:
                    self.assertRegex(variant, r"^-[a-z0-9.\-]+$", msg="malformed variant name")
