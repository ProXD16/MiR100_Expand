class Goal:
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'w': self.w
        }

    def __str__(self):
        return f"Goal(x={self.x}, y={self.y}, z={self.z}, w={self.w})"