class BitField:
    @staticmethod
    # Creates a bit mask that extracts bits in [start, end).
    def mask(start: int, end: int) -> int:
        if start < 0 or start > end:
            raise ValueError(
                f"Invalid range for Bitfield mask, start : {start}, end : {end}"
            )

        length = end - start
        bitmask = max(1, (1 << length) - 1)
        return bitmask << start

    @staticmethod
    def extract_from(data: int, start: int, end: int) -> int:
        return (data & BitField.mask(start, end)) >> start


class BitFieldExtractor:
    __data: int
    __cursor: int
    __max_width: int

    def __init__(self, data: int, max_width: int):
        if max_width <= 0:
            raise ValueError("Max width cannot be 0 for extracting bit field.")

        self.__data = data
        self.__cursor = 0
        self.__max_width = max_width

    def next(self, width: int) -> int:
        if width < 0:
            raise ValueError("Width cannot be negative.")

        advanced_cursor = min(self.__cursor + width, self.__max_width)
        extracted = BitField.extract_from(self.__data, self.__cursor, advanced_cursor)
        self.__cursor = advanced_cursor
        return extracted
