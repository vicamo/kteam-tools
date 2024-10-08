from dataclasses import dataclass
from typing import Optional
from urllib.request import urlopen
from launchpadlib.launchpad import Launchpad
import json
import yaml

# where the kernel-users repo is located.
KERNEL_USERS_URL = "http://config.kernel:8080/info/users.json"


@dataclass
class KernelUser:
    """Class for keeping track of a member in the kernel team. It will query launchpad
    to check who has upload rights
    """

    userid: str
    email: str
    name: str
    manager: str
    has_upload_rights: bool
    shell: Optional[str] = None
    nick: Optional[str] = None

    def __str__(self):
        upload_rights_str = "has upload rights" if self.has_upload_rights else "does not have upload rights"

        return "{} {}".format(self.userid, upload_rights_str)


@dataclass
class KernelUsers:
    users: dict["str", KernelUser]

    @classmethod
    def from_dict(cls, data):
        lp = Launchpad.login_anonymously("kernel-users", "production")
        uploaders = [uploader.member.name for uploader in lp.people["canonical-kernel-uploaders"].members_details]

        return cls.from_raw_dict(data, uploaders)

    @classmethod
    def from_raw_dict(cls, data, uploaders):
        users = {}

        for userid, info in data.items():
            dct = {
                "userid": userid,
                "email": info["email"],
                "name": info["name"],
                "manager": info.get("manager", None),
                "has_upload_rights": userid in uploaders,
            }

            user = KernelUser(**dct)
            users[userid] = user

        return cls(users=users)

    @classmethod
    def from_url(cls):
        response = urlopen(KERNEL_USERS_URL)
        data = response.read().decode("utf-8")

        return cls.from_dict(json.loads(data))

    @classmethod
    def from_yaml(cls, filename):
        with open(filename) as f:
            content = yaml.safe_load(f)

        return cls.from_dict(content)

    def get_subordinates(self, manager):
        subordinates = []

        for user_info in self.users.values():
            if user_info.manager == manager:
                subordinates.append(user_info)

        return subordinates

    def total_number(self):
        return len(self.users)

    def __str__(self):
        return "\n".join([str(user) for user in self.users.values()])
