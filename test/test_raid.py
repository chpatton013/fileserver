import unittest

import models.raid
import test.model_validation_test_case


class TestRaidModelValidation(
    test.model_validation_test_case.ModelValidationTestCase,
):
    def validate(self, data):
        return models.raid.validate(data)

    def from_dict(self, data):
        return models.raid.from_dict(data)

    def valid_data(self):
        return {
            "mdadm_config": {
                "device": ["device"],
                "mailaddr": "mailaddr",
                "mailfrom": "mailaddr",
                "program": "program",
                "create": {
                    "owner": "root",
                    "group": "disk",
                    "mode": "0600",
                    "auto": "yes",
                    "metadata": "1.2",
                    "symlinks": "no",
                    "names": "yes",
                    "bbl": "no",
                },
                "homehost": "homehost",
                "auto": ["+all"],
                "policy": [{
                    "domain": "domain",
                    "metadata": 1.2,
                    "path": "/some/path",
                    "type": "part",
                    "action": "include",
                    "auto": "yes",
                }],
            },
            "speed_limit_min": 1000,
            "speed_limit_max": 200000,
            "volumes": [{
                "name": "array",
                "label": "md0",
                "raid_level": 6,
                "devices": [{
                    "path": "/some/partition",
                }, {
                    "path": "/some/other/partition",
                }],
            }],
        }

    def test_missing(self):
        data = self.valid_data()
        del data["mdadm_config"]
        self.assert_valid(data)

        data = self.valid_data()
        del data["speed_limit_min"]
        self.assert_missing(data, ["speed_limit_min"])

        data = self.valid_data()
        del data["speed_limit_max"]
        self.assert_missing(data, ["speed_limit_max"])

        data = self.valid_data()
        del data["volumes"]
        self.assert_missing(data, ["volumes"])

        data = self.valid_data()
        del data["volumes"][0]
        self.assert_invalid(data, ["not_empty"])

        data = self.valid_data()
        del data["volumes"][0]["name"]
        self.assert_missing(data, ["name"])

        data = self.valid_data()
        del data["volumes"][0]["label"]
        self.assert_missing(data, ["label"])

        data = self.valid_data()
        del data["volumes"][0]["raid_level"]
        self.assert_missing(data, ["raid_level"])

        data = self.valid_data()
        del data["volumes"][0]["devices"]
        self.assert_missing(data, ["devices"])

        data = self.valid_data()
        del data["volumes"][0]["devices"][0]
        del data["volumes"][0]["devices"][0]
        self.assert_invalid(data, ["not_empty"])

        data = self.valid_data()
        del data["volumes"][0]["devices"][0]["path"]
        self.assert_missing(data, ["path"])

    def test_extra(self):
        data = self.valid_data()
        data["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["mdadm_config"]["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["volumes"][0]["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["volumes"][0]["devices"][0]["extra"] = True
        self.assert_extra(data, ["extra"])


if __name__ == "__main__":
    unittest.main()
