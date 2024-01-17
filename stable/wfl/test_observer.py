import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from wfl.errors import ShankError
from wfl.log import cinfo


class TestObserverError(ShankError):
    pass


class TestObserverResults:

    _url = "https://test-observer-api.canonical.com/v1"

    def __init__(self, url=None, data=False):
        if url is None:
            url = self._url

        self.url = url

        self._data = {}

    def _grab_json(self, url):
        try:
            headers = {"Content-Type": 'application/json'}
            req = Request(url, headers=headers, method="GET")
            with urlopen(req, timeout=30) as response:
                data = response.read()
        except HTTPError as e:
            if e.code != 404:
                raise TestObserverError("fetch failure -- " + str(e.reason))
            data = None
        except URLError as e:
            raise TestObserverError("fetch failure -- " + str(e.reason))

        if data is not None:
            if not isinstance(data, str):
                data = data.decode('utf-8')
            data = json.loads(data)

        return data

    def family(self, family):
        if family not in self._data:
            url = self.url + "/artefacts?family=" + family

            cinfo("TO family loading url={}".format(url))
            data = self._grab_json(url)

            if data is None:
                data = []

            self._data[family] = data

        return self._data[family]

        #cinfo("APW data={}".format(self.family))

    def annotate_result(self, data, family):
        # For snaps we should lookup and add the revision data.
        if family == "snap":
            url = self.url + "/artefacts/" + str(data["id"]) + "/builds"

            cinfo("TO SNAP loading url={}".format(url))
            builds = self._grab_json(url)
            cinfo("TO BUILDS json={}".format(builds))

            revisions = {}
            for build in builds:
                cinfo("TO BUILD build={}".format(build))
                revisions[build.get("architecture") or "??"] = build.get("revision") or "0"

            data[":revisions"] = revisions

    def lookup_results(self, family, series=None, track=None, stage=None, name=None, version=None):
        #cinfo("TO RESULTS={}".format(self.family(family)))
        cinfo("TO lookup_result({}, {}, {}, {}, {}, {})".format(family, series, track, stage, name, version))
        results = []
        for data in self.family(family):
            if (
                (version is not None and data.get("version") != version)
                or (series is not None and data.get("series") != series)
                or (track is not None and data.get("track") != series)
                or (stage is not None and data.get("stage") != stage)
                or (name is not None and data.get("name") != name)
            ):
                continue

            # Basic match ... callers should select more tightly.
            cinfo("MATCH data={}".format(data))

            self.annotate_result(data, family)

            results.append(data)
        return results

    def lookup_result(self, ident):
        url = self.url + "/artefacts/" + str(ident)

        cinfo("TO lookup_result loading url={}".format(url))
        data = self._grab_json(url)

        return data
