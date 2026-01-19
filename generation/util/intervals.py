from copy import deepcopy

from generation.agent import Agent

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
        @return: true iff start <= end
        """
        return self.start <= self.end

    def __or__(self, other):
        """
        Combine other with the current interval
        @param other: An overlapping interval
        @return: an Interval encompassing both the current and the other interval
        """
        if self & other:
            return Interval(min(self.start, other.start), max(self.end, other.end))
        raise ValueError

    def __and__(self, other):
        return Interval(max(self.start, other.start), min(self.end, other.end))

    def __eq__(self, other):
        if isinstance(other, Interval):
            return self.start == other.start and self.end == other.end
        return False

    def __gt__(self, other):
        return self.start > other.start

    def __lt__(self, other):
        return not self > other

    def merge(self, other):
        self.start = min(self.start, other.start)
        self.end = max(self.end, other.end)


class UnsafeInterval(Interval):
    def __init__(self, start, end, duration: float, by_agent: Agent, local_recovery_time: float):
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
        assert self.by_agent == other.by_agent

    def __deepcopy__(self, memodict={}):
        agent = deepcopy(self.by_agent, memodict)
        return UnsafeInterval(self.start, self.end, self.duration, agent, self.local_recovery_time)


class SafeInterval(Interval):
    def __init__(self, start, end, agent_before: Agent, crt_before: float, agent_after: Agent, buffer_after: float, crt_after: float):
        super().__init__(start, end)
        self.agent_before = agent_before
        self.crt_before = crt_before
        self.agent_after = agent_after
        self.buffer_after = buffer_after
        self.crt_after = crt_after

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.agent_before
        yield self.crt_before
        yield self.agent_after
        yield self.buffer_after
        yield self.crt_after

    def __str__(self):
        return f'{super().__str__()},{self.agent_before},{self.agent_after}'

    def __repr__(self):
        return f'{super().__repr__()} {self.agent_before} {self.crt_before} {self.agent_after} {self.buffer_after} {self.crt_after}'

class ArrivalTimeFunction:
    def __init__(self, from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta: float):
        self.from_id = from_interval.index
        self.to_id   = to_interval.index
        self.train_before = self._check_agent(edge_interval.agent_before)
        self.train_after  = self._check_agent(edge_interval.agent_after)

        self.zeta = from_interval.start
        self.alpha = max(from_interval.start, edge_interval.start, to_interval.start - delta)
        self.beta = min(from_interval.end, edge_interval.end, to_interval.end - delta)
        self.delta = delta

    @staticmethod
    def _check_agent(agent):
        if isinstance(agent, Agent):
            return agent
        if agent == 0:
            agent = Agent([])
            agent.id = 0
            return agent

    def __bool__(self) -> bool:
        return self.zeta <= self.alpha < self.beta


class FlexibleArrivalTimeFunction(ArrivalTimeFunction):
    def __init__(self, from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta: float, heuristic: float):
        super().__init__(from_interval, edge_interval, to_interval, delta)

        # TODO: check if maybe it should not be from the edge but from the from or to node
        self.buffer_after = edge_interval.buffer_after
        self.crt_after = edge_interval.crt_after
        self.crt_before = edge_interval.crt_before

        self.heuristic = heuristic

    def __repr__(self):
        return f"{self.from_id} {self.to_id} {self.zeta} {self.alpha} {self.beta} {self.delta} {self.train_before} {self.crt_before} {self.train_after} {self.buffer_after} {self.crt_after} {self.heuristic}"

    def replace_index(self, interval_index_map: dict[int, int]) -> "FlexibleArrivalTimeFunction":
        new_atf = deepcopy(self)
        new_atf.from_id = interval_index_map[self.from_id]
        new_atf.to_id = interval_index_map[self.to_id]
        return new_atf
