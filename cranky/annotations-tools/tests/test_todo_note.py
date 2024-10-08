import unittest

from tests import utils

from kconfig.annotations import Annotation, KConfig


class TestTodoNote(unittest.TestCase):
    def test_todo(self):
        a = Annotation("annotations-tools/tests/data/annotations.todo-note.1")
        c = KConfig("annotations-tools/tests/data/config.todo-note.1")
        a.update(c, arch="amd64", flavour="gcp")
        r = utils.load_json("annotations-tools/tests/data/annotations.todo-note.1.result")
        self.assertEqual(utils.to_dict(a), r)
