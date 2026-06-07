import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from chronos.utils import BitField


class ChronosUtilUnitTests(unittest.TestCase):
    def test_bitfield_triggers_an_exception_on_invalid_range(self):
        with self.assertRaises(ValueError):
            BitField.mask(-1, 0)
        with self.assertRaises(ValueError):
            BitField.mask(1, 0)

    def test_bitfield_creates_proper_bitmask(self):
        # 1101 1110 1010 1101 1011 1110 1110 1111
        data = 0xDEADBEEF

        # Single bit
        self.assertEqual(data & BitField.mask(0, 0), 0x1)

        # 4 bits
        self.assertEqual(data & BitField.mask(0, 4), 0xF)
        self.assertEqual((data & BitField.mask(4, 8)) >> 4, 0xE)
        self.assertEqual((data & BitField.mask(8, 12)) >> 8, 0xE)
        self.assertEqual((data & BitField.mask(12, 16)) >> 12, 0xB)
        self.assertEqual((data & BitField.mask(16, 20)) >> 16, 0xD)
        self.assertEqual((data & BitField.mask(20, 24)) >> 20, 0xA)
        self.assertEqual((data & BitField.mask(24, 28)) >> 24, 0xE)
        self.assertEqual((data & BitField.mask(28, 32)) >> 28, 0xD)

        # 8 bits
        self.assertEqual(data & BitField.mask(0, 8), 0xEF)
        self.assertEqual((data & BitField.mask(8, 16)) >> 8, 0xBE)
        self.assertEqual((data & BitField.mask(16, 24)) >> 16, 0xAD)
        self.assertEqual((data & BitField.mask(24, 32)) >> 24, 0xDE)

        # 16 bits
        self.assertEqual(data & BitField.mask(0, 16), 0xBEEF)
        self.assertEqual((data & BitField.mask(16, 32)) >> 16, 0xDEAD)

        # 32 bits
        self.assertEqual(data & BitField.mask(0, 32), data)


if __name__ == "__main__":
    unittest.main()
