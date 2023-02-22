
class Region():
    """Region"""

    def __init__(self, region_number: int, bounding_box: tuple):
        self.region_number = region_number
        self.bounding_box = bounding_box

    def __str__(self) -> str:
        return f"{self.region_number}: {str(self.bounding_box)}"

    def __repr__(self) -> str:
        return self.__str__()
