import math
from typing import Tuple

from attr import dataclass
from matplotlib.axis import Axis

from generation.agent import Agent
from generation.railways.block_graph import BlockEdge, BlockNode
from generation.railways.track_graph import TrackEdge
from generation.util.intervals import UnsafeInterval
from generation.util.types import Direction


@dataclass
class TrainItem:
    train_length: float
    train_speed: float
    acceleration: float
    deceleration: float
    walking_speed: float

    minimum_stop_time: float

    sight_reaction_time: float
    setup_time: float
    release_time: float

    start_time: float


class TrainAgent(Agent[BlockEdge, BlockNode]):
    def __init__(self, route: list[BlockEdge], train: TrainItem):
        super().__init__(route)
        self.measures = train

    def _occupation_time(self, e: TrackEdge, velocity: float, cur_time: float, station_time: float) -> Tuple[UnsafeInterval, float, float]:
        if e.length > 0:
            max_train_v = min(e.max_speed, self.measures.train_speed)
            clearing_time = self.measures.train_length / max_train_v
            end_occupation_time = cur_time + e.length / max_train_v + clearing_time + station_time

            if self.id in e.stops_at_station:
                recovery_time = max(0.0, station_time - self.measures.minimum_stop_time)
            else:
                # TODO: create variable from the 1.08
                recovery_time = (e.length / max_train_v) - e.length / (max_train_v * 1.08)

            return UnsafeInterval(
                cur_time,
                end_occupation_time + self.measures.release_time,
                e.length / max_train_v + station_time,
                self,
                recovery_time
            ), max_train_v, max_train_v

        else:
            end_train_v = velocity
            end_occupation_time = cur_time + station_time

            # Recovery time calculation
            if self.id in e.stops_at_station:
                recovery_time = max(0.0, station_time - self.measures.minimum_stop_time)
            else:
                recovery_time = 0

            return UnsafeInterval(
                cur_time,
                end_occupation_time + self.measures.release_time,
                station_time,
                self,
                recovery_time
            ), velocity, end_train_v

    def _approach_time(self, e: TrackEdge, avg_v: float, cur_time: float, station_time: float) -> Tuple[UnsafeInterval, set[BlockEdge]]:
        start_approach_time = cur_time + station_time - self.measures.setup_time - self.measures.sight_reaction_time

        end_approach_time = cur_time + station_time
        if avg_v > 0:
            end_approach_time += (e.length / avg_v)

        interval = UnsafeInterval(
            start_approach_time,
            end_approach_time,
            0,
            self,
            0.0
        )

        # Find current spot in block graph
        bools = [e in block.track_route for block in self.route]
        current_path_index = bools.index(True) if True in bools else None

        approach_blocks: set[BlockEdge] = set()
        # TODO make variable and fix values > 2 in regards to station time, or even better:
        #  change it to actually use the breaking distance of the train at the current time.
        n_blocks = 0

        if current_path_index is not None:
            for path_block in self.route[current_path_index:current_path_index + n_blocks]:
                for tn in path_block.tracknodes(Direction.BOTH):
                    for block in tn.blocks(Direction.BOTH):
                        approach_blocks.add(block)

        return interval, approach_blocks


    # TODO: Maybe make this overwrite a function of Agent
    def calculate_blocking_times(self):
        cur_time = self.measures.start_time
        velocity = 0.0

        for block_e in self.route:
            block_e.add_start_time(self, cur_time)
            for e in block_e.track_route:
                for e_opp in e.opposites + e.associated + [e]:
                    e_opp.add_start_time(self, cur_time)
                station_time = 0
                if self.id in e.stops_at_station:
                    station_time = e.stops_at_station[self.id] - cur_time
                    velocity = 0

                occupation_time, avg_v, velocity = self._occupation_time(e, velocity, cur_time, station_time)

                for block in e.get_affected_blocks():
                    block.add_unsafe_interval(occupation_time)

                approach_interval, approach_blocks = self._approach_time(e, avg_v, cur_time, station_time)

                for block in approach_blocks:
                    block.add_unsafe_interval(approach_interval)

                cur_time = approach_interval.end
                for e_opp in e.opposites + e.associated + [e]:
                    e_opp.add_end_time(self, cur_time)
            block_e.add_end_time(self, cur_time)

    def plot_route(self, ax: Axis, edges_to_plot: dict[TrackEdge, Tuple[float, float]], color):
        for block in self.route:
            for edge in block.track_route:
                if edge in edges_to_plot:
                    from_x, to_x = edges_to_plot[edge]
                    pi = edge.plotting_info[self]
                    ax.plot([from_x, to_x], [pi.start_time, pi.end_time], color=color)
