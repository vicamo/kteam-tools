import pytest

from crl.pull_review import RepoReview, Packages, Review


# Fixtures


@pytest.fixture
def repo():
    return RepoReview(
        repo="linux",
        url="ssh://kathleen/~roger/bionic-linux",
        tag="Ubuntu-azure-4.15-4.15.0-1178.193",
    )


@pytest.fixture
def packages():
    return Packages(url="kathleen:~roger/s2024.04.29/bionic/linux-azure-4.15")


@pytest.fixture
def review():
    return Review(
        repos=[
            RepoReview(
                repo="linux",
                url="ssh://kathleen/~roger/bionic-linux",
                tag="Ubuntu-azure-4.15-4.15.0-1178.193",
            ),
            RepoReview(
                repo="linux-meta",
                url="ssh://kathleen/~roger/bionic-linux-meta",
                tag="Ubuntu-azure-4.15-4.15.0.1178.146",
            ),
            RepoReview(
                repo="linux-signed",
                url="ssh://kathleen/~roger/bionic-linux-signed",
                tag="Ubuntu-azure-4.15-4.15.0-1178.193",
            ),
            RepoReview(
                repo="linux-lrm",
                url="ssh://kathleen/~roger/bionic-linux-lrm",
                tag="Ubuntu-azure-4.15-4.15.0-1178.193",
            ),
        ],
        packages=Packages(
            url="kathleen:~roger/s2024.04.29/bionic/linux-azure-4.15",
        ),
    )


# Tests


def test_reporeview_from_line(repo):
    line = "linux: ssh://kathleen/~roger/bionic-linux tag Ubuntu-azure-4.15-4.15.0-1178.193\n"
    r = RepoReview.from_line(line)

    assert r == repo


def test_packages_from_line(packages):
    line = "packages: kathleen:~roger/s2024.04.29/bionic/linux-azure-4.15\n"
    p = Packages.from_line(line)

    assert p == packages


def test_packages_origin_handle(packages):
    assert packages.origin_handle == "bionic:linux-azure-4.15"


def test_packages_user(packages):
    assert packages.user == "roger"


# Review


def test_review_from_line(review):
    lines = (
        "linux: ssh://kathleen/~roger/bionic-linux tag Ubuntu-azure-4.15-4.15.0-1178.193\n",
        "linux-meta: ssh://kathleen/~roger/bionic-linux-meta tag Ubuntu-azure-4.15-4.15.0.1178.146\n",
        "linux-signed: ssh://kathleen/~roger/bionic-linux-signed tag Ubuntu-azure-4.15-4.15.0-1178.193\n",
        "linux-lrm: ssh://kathleen/~roger/bionic-linux-lrm tag Ubuntu-azure-4.15-4.15.0-1178.193\n",
        "packages: kathleen:~roger/s2024.04.29/bionic/linux-azure-4.15\n",
    )
    r = Review.from_lines(lines)

    assert r == review


def test_review_origin_handle(review):
    assert review.origin_handle == "bionic:linux-azure-4.15"


def test_review_series(review):
    assert review.series == "bionic"


def test_review_kernel(review):
    assert review.kernel == "linux-azure-4.15"


def test_review_default_branch(review):
    assert review.default_branch == "azure-4.15"


def test_review_user(review):
    assert review.user == "roger"
