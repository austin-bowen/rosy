import unittest

from easymesh.utils import ephemeral_port_range


class EphemeralPortRangeTest(unittest.TestCase):
    def test_first_element_should_be_49152(self):
        result = None
        for result in ephemeral_port_range():
            break

        self.assertEqual(49152, result)

    def test_last_element_should_be_65535(self):
        result = None
        for result in ephemeral_port_range():
            pass

        self.assertEqual(65535, result)

    def test_len_should_be_16384(self):
        count = 0
        for _ in ephemeral_port_range():
            count += 1

        self.assertEqual(16384, count)
