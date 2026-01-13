import json
import re
from pathlib import Path
from logging import getLogger
from typing import Tuple

from generation.graphs.graph import Graph, Node, Edge
from generation.util.types import Direction
from generation.util.util import angle_to_speed

logger = getLogger('__main__.' + __name__)

class TrackNode(Node["TrackEdge", "TrackNode"]):
    def __init__(self, name, type):
        super().__init__(name)
        self.associated:list[TrackNode] = []
        self.opposites:list[TrackNode] = []
        self.blk:list = [] #TODO define as type BlockNode/BlockEdge
        self.blocksOpp:list = [] #TODO define as type BlockNode/BlockEdge
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")

    def blocks(self, dir=Direction.SAME):
        if dir == Direction.SAME:
            return self.blk
        if dir == Direction.OPPOSE:
            return self.blocksOpp
        return self.blk + self.blocksOpp

class TrackEdge(Edge["TrackEdge", "TrackNode"]):
    def __init__(self, f, t, l, switch_angle=None):
        super().__init__(f, t, l, angle_to_speed(switch_angle))
        self.plotting_info = {}
        self.opposites:  list[TrackEdge] = []
        self.associated: list[TrackEdge] = []
        self.stops_at_station = {}
        self.direction = ''.join(set(re.findall("[AB]", f"{str(f)[-2:]} {str(t)[-2:]}")))
        # if self.direction != "A" and self.direction != "B":
        #     raise ValueError("Direction must be either A or B")


    def set_plotting_info(self, agent, cur_time, end_time, block_edge):
        self.plotting_info[agent] = {
            "start_time": cur_time,
            "end_time": end_time,
            "block": block_edge,
        }

    def get_affected_blocks(self) -> set:
        '''Return all blocks that are unsafe when this track is used/reserved for a train'''
        affected_blocks = set()
        for blk in self.from_node.blocks(Direction.BOTH):
            affected_blocks.add(blk)
        for blk in self.to_node.blocks(Direction.BOTH):
            affected_blocks.add(blk)
        return affected_blocks

class Signal:
    def __init__(self, id, track: TrackNode):
        self.id = id
        self.track = track
        self.direction = track.direction

    def __repr__(self) -> str:
        return f"Signal {self.id} on track {self.track}"

class TrackGraph(Graph[TrackEdge, TrackNode]):
    def __init__(self):
        super().__init__()
        self.signals: list[Signal] = []
        self.distance_markers = {}
        self.stations:dict[str, Tuple[TrackNode, TrackNode]] = {}

    def add_signal(self, s):
        if isinstance(s, Signal):
            self.signals.append(s)

    @classmethod
    def read_graph(cls, file):
        with open(file) as f:
            data = json.load(f)
        g = cls()
        nodes_per_id_A: dict[int, list[str]] = {}
        nodes_per_id_B: dict[int, list[str]] = {}
        track_lengths = {}
        for track in data["trackParts"]:
            track_lengths[track["id"]] = track["length"]
            side_switch_track_side  = track["type"] == "SideSwitch" and (len(track["aSide"]) == 1 or len(track["bSide"]) == 1)
            side_switch_switch_side = track["type"] == "SideSwitch" and (len(track["aSide"]) == 2 or len(track["bSide"]) == 2)
            if track["type"] in {"RailRoad", "Bumper"} or side_switch_track_side:
                a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                b = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                if track["stationPlatform"]:
                    a.stationPlatform = True
                    b.stationPlatform = True
                # A/B nodes are associated because the have the same interval on the node if train can reverse
                if track["sawMovementAllowed"]:
                    a.associated.append(b)
                    b.associated.append(a)
                    a.canReverse = True
                    b.canReverse = True
                # A/B nodes are opposite because they have opposite edges attaches
                a.opposites.append(b)
                b.opposites.append(a)
                nodes_per_id_A[track["id"]] = [track["name"] + "A"]
                nodes_per_id_B[track["id"]] = [track["name"] + "B"]
            # Nodes on the same side of a switch are not associated -> they do not have same intervals, but the edges do
            elif track["type"] == "Switch" or side_switch_switch_side:
                if len(track["aSide"]) > len(track["bSide"]):
                    a = g.add_node(TrackNode(track["name"] + "AR", track["type"]))
                    b = g.add_node(TrackNode(track["name"] + "AL", track["type"]))
                    c = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                    a.opposites.extend([c])
                    b.opposites.extend([c])
                    c.opposites.extend([a, b])
                    a.associated.append(b)
                    b.associated.append(a)
                    nodes_per_id_A[track["id"]] = [track["name"] + "AR", track["name"] + "AL"]
                    nodes_per_id_B[track["id"]] = [track["name"] + "B"]
                else:
                    a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                    b = g.add_node(TrackNode(track["name"] + "BR", track["type"]))
                    c = g.add_node(TrackNode(track["name"] + "BL", track["type"]))
                    a.opposites.extend([b, c])
                    b.opposites.extend([a])
                    c.opposites.extend([a])
                    b.associated.append(c)
                    c.associated.append(b)
                    nodes_per_id_A[track["id"]] = [track["name"] + "A"]
                    nodes_per_id_B[track["id"]] = [track["name"] + "BR", track["name"] + "BL"]
            elif track["type"] == "EnglishSwitch":
                a = g.add_node(TrackNode(track["name"] + "AR", track["type"]))
                b = g.add_node(TrackNode(track["name"] + "AL", track["type"]))
                c = g.add_node(TrackNode(track["name"] + "BR", track["type"]))
                d = g.add_node(TrackNode(track["name"] + "BL", track["type"]))
                a.opposites.extend([c, d])
                b.opposites.extend([c, d])
                c.opposites.extend([a, b])
                d.opposites.extend([a, b])
                a.associated.append(b)
                b.associated.append(a)
                c.associated.append(d)
                d.associated.append(c)
                nodes_per_id_A[track["id"]] = [track["name"] + "AR", track["name"] + "AL"]
                nodes_per_id_B[track["id"]] = [track["name"] + "BR", track["name"] + "BL"]

        # All nodes are created in the track graph, create the edges between the nodes
        for track in data["trackParts"]:
            wisselhoek = track["wisselhoek"] if "wisselhoek" in track else None
            # if track["type"] != "Bumper":
            aEdges = []
            bEdges = []
            bumperAside, bumperBside = True, True
            for i, aSideId in enumerate(track["aSide"]):
                fromNode = nodes_per_id_A[track["id"]][i]
                if aSideId in nodes_per_id_A:
                    bumperAside = False
                    # Connect the aSide node(s) to the respective edges
                    for aSideToTrack in nodes_per_id_A[aSideId]:
                        length = track_lengths[aSideId]
                        e = g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[aSideToTrack], length, wisselhoek))
                        aEdges.append(e)
                # This side is a bumper, it attaches to the other side
                if g.nodes[fromNode].type == "Bumper" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_B[track["id"]][i]
                    length = track_lengths[track["id"]]
                    g.add_edge(TrackEdge(g.nodes[toNode], g.nodes[fromNode], length))
            for i, bSideId in enumerate(track["bSide"]):
                fromNode = nodes_per_id_B[track["id"]][i]
                if bSideId in nodes_per_id_B:
                    bumperBside = False
                    # Connect the bSide node(s) to the respective neighbors
                    for bSideToTrack in nodes_per_id_B[bSideId]:
                        length = track_lengths[bSideId]
                        e = g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[bSideToTrack], length, wisselhoek))
                        bEdges.append(e)
                # This side is a bumper, it attaches to the other side
                if g.nodes[fromNode].type == "Bumper" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_A[track["id"]][i]
                    length = track_lengths[track["id"]]
                    g.add_edge(TrackEdge(g.nodes[toNode], g.nodes[fromNode], length))


            if track["type"] == "SideSwitch":
                fromNode = None
                toNodeL = None
                toNodeR = None
                if not track["aSide"]:
                    fromNode = g.nodes[track["name"] + "A"]
                    toNodeName = track["name"][0:-3] + track["name"][-2:-4:-1] + "-B"
                    if toNodeName in g.nodes:
                        toNodeL = g.nodes[toNodeName]
                    else:
                        toNodeL = g.nodes[toNodeName + "L"]
                        toNodeR = g.nodes[toNodeName + "R"]
                if not track["bSide"]:
                    fromNode = g.nodes[track["name"] + "B"]
                    toNodeName = track["name"][0:-3] + track["name"][-2:-4:-1] + "-A"
                    if toNodeName in g.nodes:
                        toNodeL = g.nodes[toNodeName]
                    else:
                        toNodeL = g.nodes[toNodeName + "L"]
                        toNodeR = g.nodes[toNodeName + "R"]

                if fromNode is None:
                    raise ValueError("A and B side populated somehow " + track)

                g.add_edge(TrackEdge(fromNode, toNodeL, 0))
                if toNodeR is not None:
                    g.add_edge(TrackEdge(fromNode, toNodeR, 0))


            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumperAside and not bumperBside:
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_A[track["id"]][i]], g.nodes[nodes_per_id_B[track["id"]][i]], 0))
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_B[track["id"]][i]], g.nodes[nodes_per_id_A[track["id"]][i]], 0))
            # Assign the associated edges (same side of switch)
            for x in aEdges:
                for y in aEdges:
                    if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
                        x.associated.append(y)
                        y.associated.append(x)
            for x in bEdges:
                for y in bEdges:
                    if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
                        x.associated.append(y)
                        y.associated.append(x)

        # Assign the opposite edges (opposite direction)
        for node in g.nodes:
            for e in g.nodes[node].outgoing:
                for opposite_node in g.nodes[node].opposites:
                    for other_edge in g.nodes[opposite_node.name].incoming:
                        if other_edge.from_node in e.to_node.opposites:
                            e.opposites.append(other_edge)
            for e in g.nodes[node].incoming:
                for opposite_node in g.nodes[node].opposites:
                    for other_edge in g.nodes[opposite_node.name].outgoing:
                        if other_edge.to_node in e.from_node.opposites:
                            e.opposites.append(other_edge)

        g.distance_markers = data["distanceMarkers"] if "distanceMarkers" in data and data["distanceMarkers"] else {"Start": 0}
        min_distance = min(g.distance_markers.values())
        for key, val in g.distance_markers.items():
            g.distance_markers[key] = val - min_distance

        # Extract signal locations
        signals = data["signals"] if "signals" in data else []
        for signal in signals:
            if signal["side"] == "A":
                track = g.nodes[nodes_per_id_A[signal["track"]][0]]
            else:
                track = g.nodes[nodes_per_id_B[signal["track"]][0]]
            g.add_signal(Signal(signal["name"], track))


        stations = data["stations"] if "stations" in data else []
        for station in stations:
            if len(nodes_per_id_A[station["trackId"]]) != 1 or len(nodes_per_id_B[station["trackId"]]) != 1:
                logger.error(f'Found platform {station["stationName"].upper()}|{station["platform"]} on a switch: A: {nodes_per_id_A[station["trackId"]]} or B: {nodes_per_id_B[station["trackId"]]}')
            track_a_str = nodes_per_id_A[station["trackId"]][0]
            track_b_str = nodes_per_id_B[station["trackId"]][0]
            g.stations[f"{station['stationName'].upper()}|{station['platform']}"] = (g.nodes[track_a_str], g.nodes[track_b_str])
        return g