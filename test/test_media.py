import unittest

import models.media
import test.model_validation_test_case


class TestMediaModelValidation(
    test.model_validation_test_case.ModelValidationTestCase,
):
    def validate(self, data):
        return models.media.validate(data)

    def from_dict(self, data):
        return models.media.from_dict(data)

    def valid_data(self):
        return {
            "device_defaults": {
                "randomize_method": "/dev/urandom",
                "readahead_sectors": 512,
                "nr_requests": 64,
            },
            "device_groups": [{
                "device_defaults": {
                    "randomize_method": "/dev/random",
                    "readahead_sectors": 256,
                    "nr_requests": 128,
                },
                "raid_volume": "array",
                "mount_volume": "storage",
                "devices": [{
                    "nr_requests": 32,
                    "path": "/some/disk",
                }, {
                    "path": "/some/other/disk",
                }],
            }],
        }

    def test_missing(self):
        data = self.valid_data()
        del data["device_defaults"]
        self.assert_valid(data)

        data = self.valid_data()
        del data["device_groups"]
        self.assert_missing(data, ["device_groups"])

        data = self.valid_data()
        del data["device_groups"][0]
        self.assert_invalid(data, ["not_empty"])

        data = self.valid_data()
        del data["device_groups"][0]["device_defaults"]
        self.assert_valid(data)

        data = self.valid_data()
        del data["device_groups"][0]["raid_volume"]
        self.assert_valid(data)

        data = self.valid_data()
        del data["device_groups"][0]["mount_volume"]
        self.assert_valid(data)

        data = self.valid_data()
        del data["device_groups"][0]["devices"]
        self.assert_missing(data, ["devices"])

        data = self.valid_data()
        data["device_groups"][0]["devices"] = []
        self.assert_invalid(data, ["not_empty"])

        data = self.valid_data()
        del data["device_defaults"]["randomize_method"]
        del data["device_groups"][0]["device_defaults"]
        self.assert_missing(data, ["randomize_method"])

        data = self.valid_data()
        del data["device_defaults"]["readahead_sectors"]
        del data["device_groups"][0]["device_defaults"]
        self.assert_missing(data, ["readahead_sectors"])

        data = self.valid_data()
        del data["device_defaults"]["nr_requests"]
        del data["device_groups"][0]["device_defaults"]
        self.assert_missing(data, ["nr_requests"])

        data = self.valid_data()
        del data["device_groups"][0]["devices"][1]["path"]
        self.assert_missing(data, ["path"])

    def test_extra(self):
        data = self.valid_data()
        data["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["device_defaults"]["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["device_groups"][0]["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["device_groups"][0]["device_defaults"]["extra"] = True
        self.assert_extra(data, ["extra"])

        data = self.valid_data()
        data["device_groups"][0]["devices"][0]["extra"] = True
        self.assert_extra(data, ["extra"])

    def test_defaults(self):
        data = self.valid_data()

        # DeviceGroup defaults should override Media defaults.
        # Device values should override DeviceGroup defaults.
        media = models.media.from_dict(data)
        print(media.device_groups[0].devices[0].__dict__)
        self.assertEqual(
            "/dev/random",
            media.device_groups[0].devices[0].randomize_method,
        )
        self.assertEqual(
            256,
            media.device_groups[0].devices[0].readahead_sectors,
        )
        self.assertEqual(
            32,
            media.device_groups[0].devices[0].nr_requests,
        )

        # Missing Media defaults should not be invalid.
        del data["device_defaults"]["randomize_method"]
        self.assert_valid(data)

        # Missing DeviceGroup defaults should not be invalid.
        del data["device_groups"][0]["device_defaults"]["nr_requests"]
        self.assert_valid(data)

        # Keys missing from Media defaults, DeviceGroup defaults, and Device
        # values should be invalid.
        del data["device_defaults"]
        self.assert_missing(data, ["nr_requests"])


if __name__ == "__main__":
    unittest.main()
