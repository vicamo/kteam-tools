import os
import unittest

import utils

from kconfig.annotations import Annotation, KConfig


class TestTodoNote(unittest.TestCase):
    def test_todo(self):
        data = os.path.join(os.path.dirname(__file__), "data")
        a = Annotation(os.path.join(data, "annotations.todo-note.1"))
        c = KConfig(os.path.join(data, "config.todo-note.1"))
        a.update(c, arch="amd64", flavour="gcp")
        r = utils.load_json(os.path.join(data, "annotations.todo-note.1.result"))
        self.assertEqual(utils.to_dict(a), r)
