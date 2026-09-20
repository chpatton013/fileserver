import unittest

import schema


class UnimplementedMethodError(RuntimeError):
    pass


class ModelValidationTestCase(unittest.TestCase):
    def validate(self, data):
        raise UnimplementedMethodError()

    def from_dict(self, data):
        raise UnimplementedMethodError()

    def valid_data(self):
        raise UnimplementedMethodError()

    def assert_valid(self, data):
        self.validate(data) == data
        return self.from_dict(data)

    def assert_invalid(self, data, validators):
        with self.assertRaises(schema.SchemaError) as context:
           self.validate(data)

        for v in validators:
            self.assertRegex(context.exception.code, "\\b" + v + "\\b")

    def assert_extra(self, data, extra):
        extra_str = ", ".join(repr(k) for k in sorted(extra, key=repr))
        with self.assertRaisesRegex(
            schema.SchemaError,
            "Wrong keys " + extra_str,
        ):
            self.validate(data)

    def assert_missing(self, data, missing):
        missing_str = ", ".join(repr(k) for k in sorted(missing, key=repr))
        with self.assertRaisesRegex(
            schema.SchemaError,
            "Missing keys: " + missing_str,
        ):
            self.validate(data)

    def test_valid(self):
        self.assert_valid(self.valid_data())
