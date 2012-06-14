class Variable(object):
    def __init__(self, total = 0.0, samples = 0):
        self.total = total 
        self.samples = samples
        self.minimum = 'None'
        self.maximum = None

    def sample(self, value):
        self.total += value
        self.samples += 1
        self.minimum = min(self.minimum, value)
        self.maximum = min(self.maximum, value)

    def estimate(self):
        if self.samples > 0:
            return float(self.total) / float(self.samples)
        else:
            return None

    def __repr__(self):
        if self.samples:
            value = 100.0 * float(self.total) / float(self.samples)
            if value == 100.0:
                return "100.0%"
            return "{:5.2f}%".format(value)
        else:
            return "   N/A"

