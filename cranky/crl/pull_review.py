"""Module to handle reviews requests.

"""

from typing import List
from dataclasses import dataclass


@dataclass
class RepoReview:
    repo: str
    url: str
    tag: str

    @classmethod
    def from_line(cls, line: str):
        repo, url, _, tag = line.strip().split(" ")
        repo = repo[:-1]
        return cls(repo, url, tag)

    @property
    def dir(self) -> str:
        if self.repo == "linux":
            return "linux-main"

        return self.repo


@dataclass
class Packages:
    url: str

    @classmethod
    def from_line(cls, line: str) -> "Packages":
        return cls(url=line.strip().split(" ")[1])

    @property
    def origin_handle(self) -> str:
        items = self.url.split("/")
        series = items[-2]
        kernel = items[-1]
        return f"{series}:{kernel}"

    @property
    def user(self) -> str:
        path = self.url.split(":")[1]
        return path.split("/")[0][1:]


@dataclass
class Review:
    repos: List[RepoReview]
    packages: Packages

    @classmethod
    def from_lines(cls, lines) -> "Review":
        repos = []
        packages = None
        for line in lines:
            try:
                repo = RepoReview.from_line(line)
                repos.append(repo)
            except ValueError:
                packages = Packages.from_line(line)

        if packages is None:
            raise ValueError("No packages found in input lines")

        return cls(repos, packages)

    @property
    def origin_handle(self) -> str:
        return self.packages.origin_handle

    @property
    def user(self) -> str:
        return self.packages.user

    @property
    def series(self) -> str:
        return self.origin_handle.split(":")[0]

    @property
    def kernel(self) -> str:
        return self.origin_handle.split(":")[1]

    @property
    def default_branch(self) -> str:
        b = self.kernel.strip("linux-")
        return f"{b}"
