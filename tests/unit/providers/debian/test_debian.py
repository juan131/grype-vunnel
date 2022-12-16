import os
import shutil

import pytest

from vunnel.providers.debian import Config, Provider, parser


@pytest.fixture
def disable_get_requests(monkeypatch):
    def disabled(*args, **kwargs):
        raise RuntimeError("requests disabled but HTTP GET attempted")

    monkeypatch.setattr(parser.requests, "get", disabled)


class TestParser:
    _sample_dsa_data_ = "test-fixtures/input/DSA"
    _sample_json_data_ = "test-fixtures/input/debian.json"

    def test_normalize_dsa_list(self, tmpdir, helpers, disable_get_requests):
        subject = parser.Parser(workspace=tmpdir)

        mock_data_path = helpers.local_dir(self._sample_dsa_data_)
        shutil.copy(mock_data_path, subject.dsa_file_path)

        ns_cve_dsalist = subject._normalize_dsa_list()
        assert isinstance(ns_cve_dsalist, dict)

        assert len(ns_cve_dsalist) > 0

        for ns, cve_dsalist in ns_cve_dsalist.items():
            assert isinstance(cve_dsalist, dict)
            assert len(cve_dsalist) > 0
            assert all(
                map(
                    lambda x: isinstance(x, list) and len(x) > 0,
                    cve_dsalist.values(),
                )
            )

            # print("Number of CVEs in {}: {}".format(ns, len(cve_dsalist)))
            # more_dsas = {x: y for x, y in cve_dsalist.items() if len(y) > 1}
            # print("Number of CVEs with more than 1 DSA: {}".format(len(more_dsas)))
            # # for cve, dsalist in sub.items():
            # #     print('{} in debian:{} namespace is mapped to {} DSAs. {}'.format(cve, ns, len(dsalist), dsalist))
            # print("")

    def test_get_dsa_map(self, tmpdir, helpers, disable_get_requests):
        subject = parser.Parser(workspace=tmpdir)

        mock_data_path = helpers.local_dir(self._sample_dsa_data_)
        shutil.copy(mock_data_path, subject.dsa_file_path)

        dsa_map = subject._get_dsa_map()
        dsas = {dsa["id"] for dsa_collection in dsa_map.values() for dsa in (dsa_collection.cves + dsa_collection.nocves)}
        # print("")
        # print("Total number of dsas: {}".format(len(dsas)))

        no_cves = [dsa for dsa_collection in dsa_map.values() for dsa in dsa_collection.nocves]
        weird_dsas = [dsa for dsa in no_cves if not dsa["fixed_in"]]
        # print("")
        # print("Number of DSAs with neither fixes nor CVEs: {}".format(len(weird_dsas)))
        assert 3 == len(weird_dsas)

        no_cve_dsas = [dsa for dsa in no_cves if dsa["fixed_in"]]
        # print("")
        # print("Number of DSAs with fixes and no CVEs: {}".format(len(no_cve_dsas)))
        assert 1 == len(no_cve_dsas)

    def test_normalize_json(self, tmpdir, helpers, disable_get_requests):
        subject = parser.Parser(workspace=tmpdir)

        dsa_mock_data_path = helpers.local_dir(self._sample_dsa_data_)
        json_mock_data_path = helpers.local_dir(self._sample_json_data_)
        shutil.copy(dsa_mock_data_path, subject.dsa_file_path)
        shutil.copy(json_mock_data_path, subject.json_file_path)

        ns_cve_dsalist = subject._normalize_dsa_list()
        vuln_records = subject._normalize_json(ns_cve_dsalist=ns_cve_dsalist)

        assert isinstance(vuln_records, dict)
        assert len(vuln_records) > 0

        for rel, vuln_dict in vuln_records.items():
            assert isinstance(vuln_dict, dict)
            assert len(vuln_dict) > 0
            assert all(map(lambda x: "Vulnerability" in x, vuln_dict.values()))

            assert all(x.get("Vulnerability", {}).get("Name") for x in vuln_dict.values())

            assert all(x.get("Vulnerability", {}).get("Description") is not None for x in vuln_dict.values())


def test_provider_schema(helpers, disable_get_requests):
    workspace = helpers.provider_workspace(name=Provider.name)

    provider = Provider(root=workspace.root, config=Config())

    mock_data_path = helpers.local_dir("test-fixtures/input")
    shutil.copytree(mock_data_path, workspace.input_dir, dirs_exist_ok=True)

    provider.update()

    assert 21 == workspace.num_result_entries()
    assert workspace.result_schemas_valid(require_entries=True)