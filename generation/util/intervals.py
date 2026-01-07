class Interval:
    index = 0

    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.index = Interval.index
        Interval.index += 1

    def __iter__(self):
        yield self.start
        yield self.end

    def __str__(self):
        return f'{self.start},{self.end}'

    def __repr__(self):
        return f'{self.start} {self.end}'

    def __bool__(self):
        """
        Check if the current interval is valid
        @return: true iff start < end
        """
        return self.start < self.end

    def __or__(self, other):
        """
        Combine other with the current interval
        @param other: An overlapping interval
        @return: an Interval encompassing both the current and the other interval
        """
        return Interval(min(self.start, other.start), max(self.end, other.end))

    def __and__(self, other):
        return Interval(max(self.start, other.start), min(self.end, other.end))


class UnsafeInterval(Interval):
    def __init__(self, start, end, duration, by_train, local_recovery_time):
        super().__init__(start, end)
        self.duration = duration
        self.by_train = by_train
        self.local_recovery_time = local_recovery_time

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.duration
        yield self.by_train
        yield self.local_recovery_time

    def __str__(self):
        return f'{super().__str__()},{self.duration},{self.by_train}'

class SafeInterval(Interval):
    def __init__(self, start, end, train_before, train_after, buffer_before, unsafe_interval_after_duration):
        super().__init__(start, end)
        self.train_before = train_before
        self.train_after = train_after
        self.buffer_before = buffer_before
        self.unsafe_interval_after_duration = unsafe_interval_after_duration

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.train_before
        yield self.train_after
        yield self.buffer_before
        yield self.unsafe_interval_after_duration

    def __str__(self):
        return f'{super().__str__()},{self.train_before},{self.train_after},{self.buffer_before},{self.unsafe_interval_after_duration}'

    # TODO: should be buffer_after i think, but original code used buffer_before
    def __repr__(self):
        return f'{super().__repr__()} {self.train_before} {self.train_after} {self.buffer_before}'

