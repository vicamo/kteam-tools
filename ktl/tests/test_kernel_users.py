"""ktl/kernel_users unit tests
"""

import unittest
from ktl.kernel_users import KernelUsers


class TestKernelUsers(unittest.TestCase):
    data = {
        "member1": {
            "email": "email1",
            "name": "name1",
            "manager": "manager1",
        },
        "member2": {
            "email": "email2",
            "name": "name2",
            "manager": "manager2",
        },
        "member3": {
            "email": "email2",
            "name": "name3",
            "manager": "manager1",
        },
    }

    uploaders = ["member2", "member3"]

    def test_get_subordinates(self):
        ks_users = KernelUsers.from_raw_dict(self.data, self.uploaders)
        members = [member.userid for member in ks_users.get_subordinates("manager1")]
        expected_members = ["member1", "member3"]

        self.assertListEqual(members, expected_members)

    def test_print(self):
        ks_users = KernelUsers.from_raw_dict(self.data, self.uploaders)
        expected_str = "member1 does not have upload rights\nmember2 has upload rights\nmember3 has upload rights"

        self.assertEqual(str(ks_users), expected_str)
