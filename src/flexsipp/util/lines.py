class Line:
    def __init__(self, x0, x1, y0, y1):
        """A line from x0, y0 to x1, y1
        """
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1

        # Line is in the form y=ax+b
        self.a = (y1 - y0) / (x1 - x0)
        self.b = y0 - (self.a * x0)

    def __repr__(self):
        return f"Line y={self.a}x+{self.b}"

    def __eq__(self, other):
        if isinstance(other, Line):
            return self.x0 == other.x0 and self.x1 == other.x1 and self.y0 == other.y0 and self.y1 == other.y1
        return False

    def get_x_value(self, y: float) -> float:
        """Calculate where self intersects with y, and return the x value, inf if no intersection"""
        if min(self.y0, self.y1) <= y <= max(self.y0, self.y1):
            # Line between
            if self.a != 0:
                return (y - self.b) / (self.a)
            return self.x0
        return float("inf")