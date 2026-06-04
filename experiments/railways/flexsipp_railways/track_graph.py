import json
import re
from logging import getLogger
from typing import Tuple

from flexsipp.graphs.graph import Graph, Node, Edge, IntervalStore
from flexsipp.util.intervals import UnsafeInterval
from flexsipp.util.plotting_info import PlottingStore
from flexsipp.util.util import angle_to_speed

logger = getLogger('__main__.' + __name__)

class TrackNode(Node["TrackEdge", "TrackNode"]):
    def __init__(self, name, type):
        super().__init__(name)
        self.opposites: list[TrackNode] = []
        self.associated:list[TrackNode] = []
        self.blocks:set[IntervalStore] = set()
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")

    def merge_unsafe_intervals(self):
        for block in self.blocks:
            IntervalStore.merge_unsafe_intervals(block)

    def add_unsafe_interval(self, interval: UnsafeInterval):
        for block in self.blocks:
            if isinstance(block, Edge):
                super(Edge, block).add_unsafe_interval(interval)
            else:
                super(Node, block).add_unsafe_interval(interval)

    def remove_unsafe_interval(self, interval: UnsafeInterval):
        for block in self.blocks:
            if isinstance(block, Edge):
                super(Edge, block).remove_unsafe_interval(interval)

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

    def merge_unsafe_intervals(self):
        for block in self.blocks:
            IntervalStore.merge_unsafe_intervals(block)

    def add_unsafe_interval(self, interval: UnsafeInterval):
        for block in self.blocks:
            IntervalStore.add_unsafe_interval(block, interval)

    def remove_unsafe_interval(self, interval: UnsafeInterval):
        for block in self.blocks:
            IntervalStore.remove_unsafe_interval(block, interval)

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
    def __init__(self, file):
        super().__init__()
        self.signals: list[Signal] = []
        self.distance_markers = {}
        self.stations:dict[str, Tuple[TrackNode, TrackNode]] = {}

        with open(file) as f:
            data = json.load(f)

        nodes_per_id_A: dict[int, str] = {}
        nodes_per_id_B: dict[int, str] = {}
        track_lengths = {}
        for track in data["trackParts"]:
            track_lengths[track["id"]] = track["length"]
            side_switch_track_side  = track["type"] == "SideSwitch" and (len(track["aSide"]) == 1 or len(track["bSide"]) == 1)
            side_switch_switch_side = track["type"] == "SideSwitch" and (len(track["aSide"]) == 2 or len(track["bSide"]) == 2)
            if track["type"] in {"RailRoad", "Bumper"} or side_switch_track_side:
                a = self.add_node(TrackNode(track["name"] + "A", track["type"]))
                b = self.add_node(TrackNode(track["name"] + "B", track["type"]))
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
            elif track["type"] == "Switch" or side_switch_switch_side or track["type"] == "EnglishSwitch":
                if len(track["aSide"]) > len(track["bSide"]):
                    a = self.add_node(TrackNode(track["name"] + "A", track["type"]))
                    b = self.add_node(TrackNode(track["name"] + "B", track["type"]))
                    nodes_per_id_A[track["id"]] = track["name"] + "A"
                    nodes_per_id_B[track["id"]] = track["name"] + "B"
                else:
                    a = self.add_node(TrackNode(track["name"] + "A", track["type"]))
                    b = self.add_node(TrackNode(track["name"] + "B", track["type"]))
                    nodes_per_id_A[track["id"]] = track["name"] + "A"
                    nodes_per_id_B[track["id"]] = track["name"] + "B"

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
                    e = self.add_edge(TrackEdge(self.nodes[from_node], self.nodes[nodes_per_id_A[a_side_id]], length, wisselhoek))
                    a_edges.append(e)
                # This side is a bumper, it attaches to the other side
                if self.nodes[from_node].type == "Bumper" and track["sawMovementAllowed"]:
                    to_node = nodes_per_id_B[track["id"]]
                    length = track_lengths[track["id"]]
                    self.add_edge(TrackEdge(self.nodes[to_node], self.nodes[from_node], length))
            for b_side_id in track["bSide"]:
                from_node = nodes_per_id_B[track["id"]]
                if b_side_id in nodes_per_id_B:
                    bumper_bside = False
                    # Connect the bSide node(s) to the respective neighbors
                    length = track_lengths[track["id"]]
                    e = self.add_edge(TrackEdge(self.nodes[from_node], self.nodes[nodes_per_id_B[b_side_id]], length, wisselhoek))
                    b_edges.append(e)
                # This side is a bumper, it attaches to the other side
                if self.nodes[from_node].type == "Bumper" and track["sawMovementAllowed"]:
                    to_node = nodes_per_id_A[track["id"]]
                    length = track_lengths[track["id"]]
                    self.add_edge(TrackEdge(self.nodes[to_node], self.nodes[from_node], length))

            if track["type"] == "SideSwitch":
                from_node = None
                to_node_l = None
                to_node_r = None
                if not track["aSide"]:
                    from_node = self.nodes[track["name"] + "A"]
                    to_node_name = track["name"][0:-3] + track["name"][-2:-4:-1] + "-B"
                    if to_node_name in self.nodes:
                        to_node_l = self.nodes[to_node_name]
                    else:
                        to_node_l = self.nodes[to_node_name + "L"]
                        to_node_r = self.nodes[to_node_name + "R"]
                if not track["bSide"]:
                    from_node = self.nodes[track["name"] + "B"]
                    to_node_name = track["name"][0:-3] + track["name"][-2:-4:-1] + "-A"
                    if to_node_name in self.nodes:
                        to_node_l = self.nodes[to_node_name]
                    else:
                        to_node_l = self.nodes[to_node_name + "L"]
                        to_node_r = self.nodes[to_node_name + "R"]

                if from_node is None:
                    raise ValueError("A and B side populated somehow " + track)

                self.add_edge(TrackEdge(from_node, to_node_l, 0))
                if to_node_r is not None:
                    self.add_edge(TrackEdge(from_node, to_node_r, 0))


            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumper_aside and not bumper_bside:
                self.add_edge(TrackEdge(self.nodes[nodes_per_id_A[track["id"]]], self.nodes[nodes_per_id_B[track["id"]]], 0))
                self.add_edge(TrackEdge(self.nodes[nodes_per_id_B[track["id"]]], self.nodes[nodes_per_id_A[track["id"]]], 0))

        # Assign all opposite nodes and edges
        for track_data in data["trackParts"]:
            track_a = self.nodes[nodes_per_id_A[track_data["id"]]]
            track_b = self.nodes[nodes_per_id_B[track_data["id"]]]
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

        for track in self.nodes.values():
            # If a track has multiple outgoing edges, all edges are associated with each other.
            if len(track.outgoing) > 1:
                for e in track.outgoing:
                    for other_e in track.outgoing:
                        if e != other_e:
                            e.associated.append(other_e)

        self.distance_markers = data["distanceMarkers"] if "distanceMarkers" in data and data["distanceMarkers"] else {"Start": 0}
        min_distance = min(self.distance_markers.values())
        for key, val in self.distance_markers.items():
            self.distance_markers[key] = val - min_distance

        # Extract signal locations
        signals = data["signals"] if "signals" in data else []
        for signal in signals:
            if signal["side"] == "A":
                track = self.nodes[nodes_per_id_A[signal["track"]]]
            else:
                track = self.nodes[nodes_per_id_B[signal["track"]]]
            self.add_signal(Signal(signal["name"], track))


        stations = data["stations"] if "stations" in data else []
        for station in stations:
            track_a_str = nodes_per_id_A[station["trackId"]]
            track_b_str = nodes_per_id_B[station["trackId"]]
            self.stations[f"{station['stationName'].upper()}|{station['platform']}"] = (self.nodes[track_a_str], self.nodes[track_b_str])

    def add_signal(self, s):
        if isinstance(s, Signal):
            self.signals.append(s)
