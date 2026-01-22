import math
from typing import Tuple


from ...railways.track_graph import TrackEdge
from ...railways.train_agent import TrainAgent
from ...util.intervals import UnsafeInterval


class TrainAgentAcceleration(TrainAgent):
    def _occupation_time(self, e: TrackEdge, velocity: float, cur_time: float, station_time: float) -> Tuple[UnsafeInterval, float, float]:
        if e.length > 0:
            max_train_v = min(e.max_speed, self.measures.train_speed)
            acceleration = self.measures.acceleration if max_train_v > 0 else self.measures.deceleration * -1
            l_min = ((max_train_v ** 2) - (velocity ** 2)) / (2 * acceleration)
            if l_min >= e.length:
                train_v = (velocity + math.sqrt(
                    (velocity ** 2) + 2 * acceleration * e.length)) / 2
                end_train_v = velocity + (e.length / train_v) * acceleration
            else:
                train_v = e.length / (((max_train_v - velocity) / acceleration) + (
                        (e.length - l_min) / max_train_v))
                end_train_v = max_train_v
            clearing_time = self.measures.train_length / end_train_v
            end_occupation_time = cur_time + e.length / train_v + clearing_time + station_time

            if self.id in e.stops_at_station:
                recovery_time = max(0.0, station_time - self.measures.minimum_stop_time)
            else:
                # TODO: create variable from the 1.08
                recovery_time = (e.length / train_v) - e.length / (train_v * 1.08)

            return UnsafeInterval(
                cur_time,
                end_occupation_time + self.measures.release_time,
                e.length / train_v + station_time,
                self,
                recovery_time
            ), train_v, end_train_v

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