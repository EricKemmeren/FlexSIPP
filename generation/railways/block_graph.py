import queue as Q
import sys
from typing import Tuple
from logging import getLogger, Logger
from copy import copy

from tqdm import tqdm

from generation.graphs.graph import Graph, Node, Edge
from generation.railways.track_graph import TrackEdge, TrackNode, TrackGraph, Signal
from generation.util.types import Direction

logger = getLogger('__main__.' + __name__)

class BlockNode(Node["BlockEdge", "BlockNode"]):
    def __init__(self, name):
        super().__init__(name)

class BlockEdge(Edge["BlockEdge", "BlockNode"]):
    def __init__(self, f, t, l, tracknodes_on_route:list[TrackNode], track_route: list[TrackEdge], direction, mv):
        super().__init__(f, t, l, mv)
        # List over the edges in the TrackGraph that this block takes
        self.track_route: list[TrackEdge] = track_route

        self.tn:list[TrackNode] = tracknodes_on_route
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


class TqdmLogger:
    """File-like class redirecting tqdm progress bar to given logging logger."""
    def __init__(self, l: Logger):
        self.logger = l

    def write(self, msg: str) -> None:
        self.logger.info(msg.lstrip("\r"))

    def flush(self) -> None:
        pass

class BlockGraph(Graph[BlockEdge, BlockNode]):
    def __init__(self, g: TrackGraph):
        super().__init__()
        self.tg = g

    @classmethod
    def from_track_graph(cls, g: TrackGraph):
        g_block = cls(g)
        track_to_signal = {signal.track: signal for signal in g.signals}
        for signal in g.signals:
            block = g_block.add_node(BlockNode(f"{signal.id}"))
            signal.track.blk.append(block)
            for track in signal.track.opposites:
                track.blocksOpp.append(block)
        for signal in tqdm(g.signals, file=TqdmLogger(logger), mininterval=1, ascii=False):
            blocks = g_block.generate_signal_blocks(signal, g.signals)
            for idx, (block, route, length, max_velocity) in enumerate(blocks):

                # Create edges in g_block
                from_signal_node = g_block.nodes[f"{signal.id}"]

                # Only add edge if a signal is found at the end of the route
                to_signal = track_to_signal[block[-1]]
                to_signal_node = g_block.nodes[f"{to_signal.id}"]
                direction = "".join(set(signal.direction + to_signal.direction))
                e = g_block.add_edge(BlockEdge(from_signal_node, to_signal_node, length, block, route, direction, max_velocity))
                logger.debug(f"Found block {e} with length {length} and max velocity {max_velocity}")
        return g_block

    def __eq__(self, other):
        return super().__eq__(other)

    def get_block_from_station(self, station: str) -> Tuple[BlockNode, BlockNode]:
        # TODO check if correct
        track_a, track_b = self.tg.stations[station]
        return track_a.blocks(Direction.SAME)[0], track_b.blocks(Direction.SAME)[0]

    def add_edge(self, e: BlockEdge) -> BlockEdge:
        super().add_edge(e)

        for node in e.tracknodes(Direction.SAME):
            node.blk.append(e)
        for node in e.tracknodes(Direction.OPPOSE):
            node.blocksOpp.append(e)

        return e

    def generate_signal_blocks(self, from_signal: Signal, signals: list[Signal]) \
            -> list[Tuple[list[TrackNode], list[TrackEdge], float, float]]:
        end_tracks = {s.track.get_identifier() for s in signals}
        start_tracks = [track.to_node for track in from_signal.track.outgoing]

        result = []

        queue = Q.Queue()
        for start_track in start_tracks:
            queue.put(([start_track], [], set(), 0.0, sys.maxsize))

        while not queue.empty():
            route, edge_route, visited, length, max_velocity = queue.get()

            if len(route[-1].outgoing) == 0:
                #No outgoing edges, what to do?
                # Should only happen when at the end of a track, and it's not allowed to turn around
                logger.debug(f"No outgoing edges at {route[-1]}")
                continue

            for e in route[-1].outgoing:
                next_track = e.to_node

                if route[-1].get_identifier() in end_tracks:
                    croute = copy(route)
                    # route.append(next_track)
                    cedge_route = copy(edge_route)
                    cedge_route.append(e)
                    result.append((croute, cedge_route, length + e.length, min(max_velocity, e.max_speed)))

                elif route[-1] not in visited:
                    croute = copy(route)
                    croute.append(next_track)

                    cvisited = copy(visited)
                    cvisited.add(next_track)

                    cedge_route = copy(edge_route)
                    cedge_route.append(e)

                    queue.put((croute, cedge_route, cvisited, length + e.length, min(max_velocity, e.max_speed)))

        return result