import json
import re
from copy import deepcopy
from logging import getLogger
from typing import Tuple

from generation.graphs.graph import Graph, Node, Edge, IntervalStore
from generation.util.plotting_info import PlottingStore
from generation.util.util import angle_to_speed

logger = getLogger('__main__.' + __name__)

class TrackNode(Node["TrackEdge", "TrackNode"]):
    def __init__(self, name, type):
        super().__init__(name)
        self.opposites: list[TrackNode] = []
        self.associated:list[TrackNode] = []
        self.blocks:set[IntervalStore] = set() #TODO define as type BlockNode/BlockEdge
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")

    def __deepcopy__(self, memodict={}):
        parent = super().__deepcopy__(memodict)
        tn = TrackNode(self.name, self.type)
        for a,b in parent.__dict__.items():
            setattr(tn, a, b)
        tn.opposites = deepcopy(self.opposites, memodict)
        tn.associated = deepcopy(self.associated, memodict)
        tn.blocks = deepcopy(self.blocks, memodict)
        tn.canReverse = self.canReverse
        tn.stationPlatform = self.stationPlatform
        tn.direction = self.direction
        return tn


class TrackEdge(Edge["TrackEdge", "TrackNode"], PlottingStore):
    def __init__(self, f, t, l, switch_angle=None):
        super().__init__(f, t, l, angle_to_speed(switch_angle))
        self.plotting_info = {}
        self.opposites:  list[TrackEdge] = []
        self.associated: list[TrackEdge] = []
        self.stops_at_station = {}
        self.blocks:set[IntervalStore] = set()
        self.direction = ''.join(set(re.findall("[AB]", f"{str(f)[-2:]} {str(t)[-2:]}")))
        # if self.direction != "A" and self.direction != "B":
        #     raise ValueError("Direction must be either A or B")

    def __deepcopy__(self, memodict={}):
        parent = super().__deepcopy__(memodict)
        te = TrackEdge(parent.from_node, parent.to_node, parent.length)
        for a,b in parent.__dict__.items():
            setattr(te, a, b)
        te.plotting_info = deepcopy(self.plotting_info, memodict)
        te.opposites = deepcopy(self.opposites, memodict)
        te.associated = deepcopy(self.associated, memodict)
        te.stops_at_station = deepcopy(self.stops_at_station, memodict)
        te.blocks = deepcopy(self.blocks, memodict)
        te.direction = self.direction
        return te


    def set_plotting_info(self, agent, cur_time, end_time, block_edge):
        self.plotting_info[agent] = {
            "start_time": cur_time,
            "end_time": end_time,
            "block": block_edge,
        }


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
        nodes_per_id_A: dict[int, str] = {}
        nodes_per_id_B: dict[int, str] = {}
        track_lengths = {}
        for track in data["trackParts"]:
            track_lengths[track["id"]] = track["length"]
            side_switch_track_side  = track["type"] == "SideSwitch" and (len(track["aSide"]) == 1 or len(track["bSide"]) == 1)
            side_switch_switch_side = track["type"] == "SideSwitch" and (len(track["aSide"]) == 2 or len(track["bSide"]) == 2)
            if track["type"] in {"RailRoad", "Bumper"} or side_switch_track_side:
                a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                b = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                nodes_per_id_A[track["id"]] = track["name"] + "A"
                nodes_per_id_B[track["id"]] = track["name"] + "B"
                if track["stationPlatform"]:
                    a.stationPlatform = True
                    b.stationPlatform = True
                if track["sawMovementAllowed"]:
                    # A/B nodes are associated because they have the same interval on the node if train can reverse
                    a.associated.append(b)
                    b.associated.append(a)
                    a.canReverse = True
                    b.canReverse = True
                # A/B nodes are opposite because they have opposite edges attaches
            # Nodes on the same side of a switch are not associated -> they do not have same intervals, but the edges do
            elif track["type"] == "Switch" or side_switch_switch_side:
                if len(track["aSide"]) > len(track["bSide"]):
                    a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                    b = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                    nodes_per_id_A[track["id"]] = track["name"] + "A"
                    nodes_per_id_B[track["id"]] = track["name"] + "B"
                else:
                    a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                    b = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                    nodes_per_id_A[track["id"]] = track["name"] + "A"
                    nodes_per_id_B[track["id"]] = track["name"] + "B"
            elif track["type"] == "EnglishSwitch":
                assert False

        # All nodes are created in the track graph, create the edges between the nodes
        for track in data["trackParts"]:
            wisselhoek = track["wisselhoek"] if "wisselhoek" in track else None
            # if track["type"] != "Bumper":
            a_edges = []
            b_edges = []
            bumper_aside, bumper_bside = True, True
            for a_side_id in track["aSide"]:
                from_node = nodes_per_id_A[track["id"]]
                if a_side_id in nodes_per_id_A:
                    bumper_aside = False
                    # Connect the aSide node(s) to the respective edges
                    length = track_lengths[track["id"]]
                    e = g.add_edge(TrackEdge(g.nodes[from_node], g.nodes[nodes_per_id_A[a_side_id]], length, wisselhoek))
                    a_edges.append(e)
                # This side is a bumper, it attaches to the other side
                if g.nodes[from_node].type == "Bumper" and track["sawMovementAllowed"]:
                    to_node = nodes_per_id_B[track["id"]]
                    length = track_lengths[track["id"]]
                    g.add_edge(TrackEdge(g.nodes[to_node], g.nodes[from_node], length))
            for b_side_id in track["bSide"]:
                from_node = nodes_per_id_B[track["id"]]
                if b_side_id in nodes_per_id_B:
                    bumper_bside = False
                    # Connect the bSide node(s) to the respective neighbors
                    length = track_lengths[track["id"]]
                    e = g.add_edge(TrackEdge(g.nodes[from_node], g.nodes[nodes_per_id_B[b_side_id]], length, wisselhoek))
                    b_edges.append(e)
                # This side is a bumper, it attaches to the other side
                if g.nodes[from_node].type == "Bumper" and track["sawMovementAllowed"]:
                    to_node = nodes_per_id_A[track["id"]]
                    length = track_lengths[track["id"]]
                    g.add_edge(TrackEdge(g.nodes[to_node], g.nodes[from_node], length))


            if track["type"] == "SideSwitch":
                from_node = None
                to_node_l = None
                to_node_r = None
                if not track["aSide"]:
                    from_node = g.nodes[track["name"] + "A"]
                    to_node_name = track["name"][0:-3] + track["name"][-2:-4:-1] + "-B"
                    if to_node_name in g.nodes:
                        to_node_l = g.nodes[to_node_name]
                    else:
                        to_node_l = g.nodes[to_node_name + "L"]
                        to_node_r = g.nodes[to_node_name + "R"]
                if not track["bSide"]:
                    from_node = g.nodes[track["name"] + "B"]
                    to_node_name = track["name"][0:-3] + track["name"][-2:-4:-1] + "-A"
                    if to_node_name in g.nodes:
                        to_node_l = g.nodes[to_node_name]
                    else:
                        to_node_l = g.nodes[to_node_name + "L"]
                        to_node_r = g.nodes[to_node_name + "R"]

                if from_node is None:
                    raise ValueError("A and B side populated somehow " + track)

                g.add_edge(TrackEdge(from_node, to_node_l, 0))
                if to_node_r is not None:
                    g.add_edge(TrackEdge(from_node, to_node_r, 0))


            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumper_aside and not bumper_bside:
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_A[track["id"]][i]], g.nodes[nodes_per_id_B[track["id"]][i]], 0))
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_B[track["id"]][i]], g.nodes[nodes_per_id_A[track["id"]][i]], 0))
            # Assign the associated edges (same side of switch)
            # for x in a_edges:
            #     for y in a_edges:
            #         if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
            #             x.associated.append(y)
            #             y.associated.append(x)
            # for x in b_edges:
            #     for y in b_edges:
            #         if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
            #             x.associated.append(y)
            #             y.associated.append(x)

        # Assign all opposite nodes and edges
        for track_data in data["trackParts"]:
            track_a = g.nodes[nodes_per_id_A[track_data["id"]]]
            track_b = g.nodes[nodes_per_id_B[track_data["id"]]]
            for e in track_a.outgoing:
                to_node = e.to_node
                # As long as it's not turning around, assign the opposite node
                if to_node != track_b:
                    to_node.opposites.append(track_b)
                # Assign the edge as opposite
                for opp_e in track_b.outgoing:
                    e.opposites.append(opp_e)

            for e in track_b.outgoing:
                to_node = e.to_node
                if to_node != track_a:
                    to_node.opposites.append(track_a)
                for opp_e in track_a.outgoing:
                    e.opposites.append(opp_e)

        for track in g.nodes.values():
            # If a track has multiple outgoing edges, all edges are associated with each other.
            if len(track.outgoing) > 1:
                for e in track.outgoing:
                    for other_e in track.outgoing:
                        if e != other_e:
                            e.associated.append(other_e)


        # for node in g.nodes:
        #     for e in g.nodes[node].outgoing:
        #         for opposite_node in g.nodes[node].opposites:
        #             for other_edge in g.nodes[opposite_node.name].incoming:
        #                 if other_edge.from_node in e.to_node.opposites:
        #                     e.opposites.append(other_edge)
            # for e in g.nodes[node].incoming:
            #     for opposite_node in g.nodes[node].opposites:
            #         for other_edge in g.nodes[opposite_node.name].outgoing:
            #             if other_edge.to_node in e.from_node.opposites:
            #                 e.opposites.append(other_edge)

        g.distance_markers = data["distanceMarkers"] if "distanceMarkers" in data and data["distanceMarkers"] else {"Start": 0}
        min_distance = min(g.distance_markers.values())
        for key, val in g.distance_markers.items():
            g.distance_markers[key] = val - min_distance

        # Extract signal locations
        signals = data["signals"] if "signals" in data else []
        for signal in signals:
            if signal["side"] == "A":
                track = g.nodes[nodes_per_id_A[signal["track"]]]
            else:
                track = g.nodes[nodes_per_id_B[signal["track"]]]
            g.add_signal(Signal(signal["name"], track))


        stations = data["stations"] if "stations" in data else []
        for station in stations:
            if len(nodes_per_id_A[station["trackId"]]) != 1 or len(nodes_per_id_B[station["trackId"]]) != 1:
                logger.error(f'Found platform {station["stationName"].upper()}|{station["platform"]} on a switch: A: {nodes_per_id_A[station["trackId"]]} or B: {nodes_per_id_B[station["trackId"]]}')
            track_a_str = nodes_per_id_A[station["trackId"]]
            track_b_str = nodes_per_id_B[station["trackId"]]
            g.stations[f"{station['stationName'].upper()}|{station['platform']}"] = (g.nodes[track_a_str], g.nodes[track_b_str])
        return g