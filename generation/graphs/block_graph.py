import logging
import queue as Q
import sys

from tqdm import tqdm
from copy import copy
from logging import getLogger

from generation.util.intervals import UnsafeInterval, SafeInterval
from graph import Graph, Node, Edge, Direction, Signal
from track_graph import TrackNode, TrackGraph


logger = getLogger('__main__.' + __name__)

class BlockNode(Node):
    def __init__(self, name):
        super().__init__(name)

class BlockEdge(Edge):
    def __init__(self, f, t, l, tracknodes_on_route:list[TrackNode], direction, mv):
        super().__init__(f, t, l, mv)
        self.tn:list[TrackNode] = list(tracknodes_on_route)
        self.tnAssociated:list[TrackNode] = list()
        self.tnOpposites:list[TrackNode] = list()
        for n in tracknodes_on_route:
            self.tnAssociated.extend(n.associated)
            self.tnOpposites.extend(n.opposites)
        self.direction = direction
        if self.direction == "BA":
            self.direction = "AB"

    def tracknodes(self, direction:Direction) -> list[TrackNode]:
        if direction == Direction.BOTH:
            return self.tn + self.tnAssociated + self.tnOpposites
        if direction == Direction.SAME:
            return self.tn + self.tnAssociated
        return self.tnOpposites

    def get_affected_blocks(self) -> list:
        affected_blocks = set()
        for node in self.tracknodes(Direction.BOTH):
            affected_blocks = affected_blocks.union(set(node.blocks(Direction.BOTH)))
        return list(affected_blocks)


class TqdmLogger:
    """File-like class redirecting tqdm progress bar to given logging logger."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def write(self, msg: str) -> None:
        self.logger.info(msg.lstrip("\r"))

    def flush(self) -> None:
        pass

class BlockGraph(Graph):
    def __init__(self, g: TrackGraph):
        super().__init__()
        logger.info("Creating initial signals")
        track_to_signal = {signal.track: signal for signal in g.signals}
        for signal in g.signals:
            block = self.add_node(BlockNode(f"r-{signal.id}"))
            signal.track.blk.append(block)
        for signal in tqdm(g.signals, file=TqdmLogger(logger), mininterval=1, ascii=False):
            logger.debug(f"Expanding blocks of {signal}")
            blocks = self.generate_signal_blocks(signal, g.signals)
            for idx, (block, length, max_velocity) in enumerate(blocks):

                # Create edges in g_block
                from_signal_node = self.nodes[f"r-{signal.id}"]

                # Only add edge if a signal is found at the end of the route
                to_signal = track_to_signal[block[-1]]
                to_signal_node = self.nodes[f"r-{to_signal.id}"]
                direction = "".join(set(signal.direction + to_signal.direction))
                e = self.add_edge(BlockEdge(from_signal_node, to_signal_node, length, block, direction, max_velocity))
                logger.debug(f"Found block {e} with length {length} and max velocity {max_velocity}")
        for station, track_nodes in g.stations.items():
            node_a, node_b = track_nodes

            station_track_a = g.nodes[node_a]
            station_block_a = {edge.to_node.name for edge in station_track_a.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_a.direction in edge.direction}
            if len(station_block_a) == 0:
                logger.error(f"Found no blocks corresponding to track {station_track_a}")
                continue

            station_track_b = g.nodes[node_b]
            station_block_b = {edge.to_node.name for edge in station_track_b.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_b.direction in edge.direction}
            if len(station_block_b) == 0:
                logger.error(f"Found no blocks corresponding to track {station_block_b}")
                continue

            self.stations[station] = (station_block_a.pop(), station_block_b.pop())

    def __eq__(self, other):
        return super().__eq__(other)

    def add_edge(self, e):
        super().add_edge(e)

        for node in e.tracknodes(Direction.SAME):
            node.blk.append(e)
        for node in e.tracknodes(Direction.OPPOSE):
            node.blocksOpp.append(e)

        return e

    def generate_signal_blocks(self, from_signal: Signal, signals: list[Signal]):
        end_tracks = {s.track.get_identifier() for s in signals}
        start_track = from_signal.track

        result = []

        queue = Q.Queue()
        queue.put(([start_track], {start_track}, 0, sys.maxsize))

        while not queue.empty():
            route, visited, length, max_velocity = queue.get()

            if len(route[-1].outgoing) == 0:
                #No outgoing edges, what to do?
                # Should only happen when at the end of a track, and it's not allowed to turn around
                logger.debug(f"No outgoing edges at {route[-1]}")
                continue

            for e in route[-1].outgoing:
                next_track = e.to_node

                if next_track.get_identifier() in end_tracks:
                    route = copy(route)
                    route.append(next_track)
                    result.append((route[1:], length + e.length, min(max_velocity, e.max_speed)))

                elif next_track not in visited:
                    route = copy(route)
                    visited = copy(visited)

                    visited.add(next_track)
                    route.append(next_track)
                    queue.put((route, visited, length + e.length, min(max_velocity, e.max_speed)))

        return result