import sys
import queue as Q
import math
from logging import getLogger

from old_generation.graph import BlockEdge, Graph, Node, TrackEdge, TrackGraph, BlockGraph, Direction
from old_generation.signal_sections import convertMovesToBlock

logger = getLogger('__main__.' + __name__)

class Scenario:
    def __init__(self, data, g: TrackGraph, g_block: BlockGraph):
        self.walkingSpeed = data["walkingSpeed"]
        self.releaseTime = data["releaseTime"]
        self.setupTime = data["setupTime"]
        self.trains = data["trains"]
        self.sightReactionTime = data["sightReactionTime"]
        self.types = {x["name"]: x for x in data["types"]}
        self.g_track = g
        self.g_block = g_block

        g.global_end_time = max([2 * entry["movements"]["endTime"] for entry in data["trains"]])
        g_block.global_end_time = g.global_end_time

    def process(self, **kwargs):
        block_intervals = {}
        moves_per_agent = {}
        for trainNumber, train in enumerate(self.trains, start=1):
            train_type = self.types[train["trainUnitTypes"][0]]

            measures = {}
            measures["trainLength"] = sum([self.types[x]["length"] for x in train["trainUnitTypes"]])
            measures["trainSpeed"] = train_type["speed"] / 3.6
            measures["acceleration"] = train_type["acceleration"]
            measures["deceleration"] = train_type["deceleration"]
            measures["minimumStopTime"] = train_type["minimum_station_time"]

            move = train["movements"]

            moves, intervals = self.process_moves(move, measures, trainNumber, **kwargs)

            moves_per_agent[trainNumber] = moves
            block_intervals[trainNumber] = intervals
        return block_intervals, moves_per_agent

    def process_moves(self, move, measures, trainNumber, **kwargs):
        path = self.g_track.construct_path(move, current_agent=trainNumber, agent_velocity=measures["trainSpeed"])
        block_routes = convertMovesToBlock(path, self.g_track, original_agent=trainNumber)
        current_block_intervals = self.generate_unsafe_intervals(self.g_block, path, block_routes, move, measures, trainNumber)
        block_intervals = {}

        for node in current_block_intervals:
            for tup in current_block_intervals[node]:
                if node in block_intervals:
                    block_intervals[node].append(tup)
                else:
                    block_intervals[node] = [tup]

        return path, block_intervals


    def calculate_blocking_time(self, e: TrackEdge, cur_time, blocking_intervals, measures, current_train, path: list[BlockEdge], initial_velocity: float):
        station_time = 0
        if current_train in e.stops_at_station:
            station_time = e.stops_at_station[current_train] - cur_time
            initial_velocity = 0

        max_train_speed = min(e.max_speed, measures["trainSpeed"])
        if max_train_speed >= initial_velocity:
            acceleration = measures["acceleration"]
        else:
            acceleration = -1 * measures["deceleration"]

        if e.length > 0:
            l_min = (( max_train_speed ** 2) - (initial_velocity ** 2)) / (2 * acceleration)
            if l_min >= e.length:
                train_speed = (initial_velocity + math.sqrt((initial_velocity ** 2) + 2 * acceleration * e.length )) / 2
                end_train_speed = initial_velocity + (e.length / train_speed) * acceleration
            else:
                train_speed = e.length / (((max_train_speed - initial_velocity) / acceleration) + ((e.length - l_min) / max_train_speed))
                end_train_speed = max_train_speed
            logger.debug(f"start: {initial_velocity}, avg: {train_speed}, end: {end_train_speed}, max: {max_train_speed}, acceleration: {acceleration}, acceleration_distance: {l_min}, edge: {e.length}")


            clearing_time = measures["trainLength"] / train_speed
            end_occupation_time = cur_time + e.length / train_speed + clearing_time + station_time

            # Recovery time calculation
            if current_train in e.stops_at_station:
                recovery_time = max(0, station_time - measures["minimumStopTime"])
            else:
                recovery_time = (e.length / train_speed) - e.length / (train_speed * 1.08)

            # Calculate running time, clearing time and release time for current track
            occupation_time = (
                    cur_time,
                    end_occupation_time + self.releaseTime,
                    e.length / train_speed + station_time,
                    current_train,
                    recovery_time
                )

            # Calculate the approach time for the next piece of track,
            end_approach_time = cur_time + station_time + (e.length / train_speed)

        else:
            end_train_speed = initial_velocity
            logger.debug(f"velocity: {initial_velocity}")
            end_occupation_time = cur_time + station_time

            # Recovery time calculation
            if current_train in e.stops_at_station:
                recovery_time = max(0, station_time - measures["minimumStopTime"])
            else:
                recovery_time = 0

            occupation_time = (
                cur_time,
                end_occupation_time + self.releaseTime,
                station_time,
                current_train,
                recovery_time
            )
            end_approach_time = cur_time + station_time

        for block in e.from_node.blocks(Direction.BOTH):
            blocking_intervals[block.get_identifier()].append(occupation_time)

        # Recovery time calculation
        start_approach_time = cur_time + station_time - self.setupTime - self.sightReactionTime

        N_BLOCKS = 1

        # Find current spot in block graph
        bools = [e.to_node in block.tracknodes(Direction.SAME) for block in path]
        current_path_index = bools.index(True) if True in bools else None

        if current_path_index is not None:
            logger.debug(f"belongs to block: {path[current_path_index]}")
        else:
            logger.debug(f"does not belong to any block in path: {path}")

        next_blocks_approach_time = (
            start_approach_time,
            end_approach_time,
            0,
            current_train,
            0.0
        )

        approach_blocks = set()

        if current_path_index is not None:
            for path_block in path[current_path_index:current_path_index + N_BLOCKS]:
                for tn in path_block.tracknodes(Direction.BOTH):
                    for block in tn.blocks(Direction.BOTH):
                        approach_blocks.add(block.get_identifier())

        for block in approach_blocks:
            blocking_intervals[block].append(next_blocks_approach_time)

        if current_path_index is not None:
            e.set_plotting_info(current_train, cur_time, end_approach_time, path[current_path_index])

        return end_approach_time, end_train_speed

    def generate_unsafe_intervals(self, g_block, path: list[TrackEdge], block_path: list[BlockEdge], move, measures, current_train):
        cur_time = move["startTime"]
        block_intervals = {e.get_identifier():[] for e in g_block.edges} | {n: [] for n in g_block.nodes}
        agent_velocity = 0.0
        for e in path:
            logger.debug(f"Edge: {e}")
            # If the train reverses: going from an A to B side -> use walking speed
            # if ("A" in e.from_node.name and "B" in e.to_node.name) or ("B" in e.from_node.name and "A" in e.to_node.name):
            #     # When turning around, the headway is also included in the end time, so the train has to wait until it can depart after reversing
            #     end_time = cur_time + (e.length + measures["trainLength"]) / measures["trainSpeed"] + measures["trainLength"] / measures["walkingSpeed"] + measures["headwayFollowing"]
            #     e.set_start_time(current_train, cur_time)
            #     e.set_depart_time(current_train, end_time)
            #     cur_time = end_time
            # In all other cases use train speed
            # else:
            end_time, agent_velocity = self.calculate_blocking_time(e, cur_time, block_intervals, measures, current_train, block_path, agent_velocity)
            # Time train leaves the node
            cur_time = end_time
        return block_intervals

def combine_intervals(intervals, combined, agents):
    if not type(agents) is set:
        agents = [int(agents)]
    for train in intervals:
        for n in intervals[train]:
            intervals[train][n].sort()
            for tup in intervals[train][n]:
                double = False
                for x in combined[n]:
                    # If the new (tup) fits in existing (x)
                    if tup[0] >= x[0] and tup[0] <= x[1] and tup[1] <= x[1] and tup[1] >= x[0]:
                        double = True
                    # if the existing (x) fits in the new (tup) -> replace
                    elif x[0] >= tup[0] and x[0] <= tup[1] and x[1] <= tup[1] and x[1] >= tup[0]:
                        combined[n].remove(x)
                if not double:
                    if train not in agents:
                        combined[n].append(tup)

def sort_and_merge(combined):
    for n in combined:
        combined[n].sort()
        i = 0
        while i < len(combined[n]) - 1:
            # As list is sorted and contains no subcontained interval, we can simply check for overlap.
            if combined[n][i+1][0] <= combined[n][i][1]:
                duration = combined[n][i+1][2] + combined[n][i][2]
                recovery = combined[n][i+1][4] + combined[n][i][4]
                # Replace the two intervals with one combined interval
                new_interval = (combined[n][i][0], combined[n][i+1][1], duration, combined[n][i+1][3], recovery)
                combined[n].remove(combined[n][i+1])
                combined[n].remove(combined[n][i])
                combined[n].insert(i, new_interval)
            else:
                i += 1

def combine_intervals_per_train(block_intervals, g_block, agent=None):
    """Combine the intervals for individual trains together per node/edge and remove duplicates/overlap."""
    combined_blocks = {e.get_identifier(): [] for e in g_block.edges} | {n: [] for n in g_block.nodes}

    combine_intervals(block_intervals, combined_blocks, agent)

    # Sort again to order mixed traffic and merge overlapping
    sort_and_merge(combined_blocks)

    return combined_blocks