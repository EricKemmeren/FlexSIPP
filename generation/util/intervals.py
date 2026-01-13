from typing import Generic

from generation.util.types import AgentT


class Interval:
    index = 0

    def __init__(self, start: float, end:float):
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
        return self.start <= self.end

    def __or__(self, other):
        """
        Combine other with the current interval
        @param other: An overlapping interval
        @return: an Interval encompassing both the current and the other interval
        """
        return Interval(min(self.start, other.start), max(self.end, other.end))

    def __and__(self, other):
        return Interval(max(self.start, other.start), min(self.end, other.end))

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __gt__(self, other):
        return self.start > other.start

    def __lt__(self, other):
        return not (self > other)

    def merge(self, other):
        self.start = min(self.start, other.start)
        self.end = max(self.end, other.end)

class UnsafeInterval(Interval, Generic[AgentT]):
    def __init__(self, start, end, duration: float, by_agent: AgentT, local_recovery_time: float):
        super().__init__(start, end)
        self.duration = duration
        self.by_agent = by_agent
        self.local_recovery_time = local_recovery_time

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.duration
        yield self.by_agent
        yield self.local_recovery_time

    def __str__(self):
        return f'{super().__str__()},{self.duration},{self.by_agent}'

    def merge(self, other):
        super().merge(other)
        self.duration += other.duration
        self.local_recovery_time += other.local_recovery_time
        # assert self.by_agent == other.by_agent

class SafeInterval(Interval):
    def __init__(self, start, end, agent_before, agent_after, buffer_after):
        super().__init__(start, end)
        self.agent_before = agent_before
        self.agent_after = agent_after
        self.buffer_after = buffer_after

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.agent_before
        yield self.agent_after
        yield self.buffer_after

    def __str__(self):
        return f'{super().__str__()},{self.agent_before},{self.agent_after},{self.buffer_after}'

    def __repr__(self):
        return f'{super().__repr__()} {self.agent_before} {self.agent_after} {self.buffer_after}'


if __name__ == '__main__':
    a = Interval(8, 10)
    b = Interval(6, 10)

    print(a < b, a > b, a == b)