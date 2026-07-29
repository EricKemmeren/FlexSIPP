import json
from typing import Any

from matplotlib.axis import Axis
import pickle
from rapidjson import Decoder, PM_TRAILING_COMMAS

from flexsipp.agent import Agent
from flexsipp.graphs.graph import Graph, Node
from flexsipp.util.lines import Line

json_decoder = Decoder(parse_mode=PM_TRAILING_COMMAS)

class Results:
    def __init__(self):
        self.metadata= {}
        self.unique_paths = {}
        self.unique_path_eatfs = {}
        self.segments = []
        self.found_routes = []
        self.unique_routes = {}
        self.unique_routes_eatfs = {}
    
    def __repr__(self):
        return f"Found {len(self.found_routes)} start times with unique paths:{"\n    ".join([""] + list(self.unique_routes.keys()))}"

    @classmethod
    def parse_json(cls, s: str, g: Graph, search_time: float):
        self = cls()

        input = json_decoder(s)
        self.metadata = input["MetaData"]
        self.metadata["Search Time Python"] = search_time
        self.metadata["Search Time"] = input["Search time"]
        self.metadata["earliest_start_time"] = input["earliest start"]
        self.metadata["max_delay"] = input["max delay"]
        result = input["Result"]

        longest_interval_string = len(str(g.global_end_time))
        longest_node_name = max([len(name) for name in g.nodes.keys()])

        self.segments = result["segments"]

        def rjust_interval(l: list, width: int):
            return "<" + " ".join([str(a).rjust(width) for a in l]) + ">"

        # Last found route is empty - terminated search
        for found_route in result["payloads"][0:-1]:
            atf = found_route["edge_atf"]["atf"]

            node_path = [(payload["state"]["loc"], payload["state"]["interval"]) for payload in found_route["payload"] if "state" in payload]
            path_str = "->".join([node for node, interval in node_path])
            route_str = "->".join([f"({str(node)}, {str(interval)})" for node, interval in node_path])
            if path_str in self.unique_paths:
                self.unique_paths[path_str] += 1
                if atf not in self.unique_path_eatfs[path_str]:
                    self.unique_path_eatfs[path_str].append(atf)
            else:
                self.unique_paths[path_str] = 1
                self.unique_path_eatfs[path_str] = [atf]

            if route_str in self.unique_routes:
                self.unique_routes[route_str] += 1
                if atf not in self.unique_routes_eatfs[route_str]:
                    self.unique_routes_eatfs[route_str].append(atf)
            else:
                self.unique_routes[route_str] = 1
                self.unique_routes_eatfs[route_str] = [atf]

            delays = {}
            for agent, gamma in enumerate(found_route["edge_atf"]["gammas"][1:], 1):
                delays[agent] = []
                for incurred_delay in gamma["incurred_delays"]:
                    location = g.nodes[incurred_delay["location"]]
                    min_delay = incurred_delay["delay"]
                    min_gamma = gamma["min_gamma"]
                    max_gamma = gamma["max_gamma"]
                    delays[agent].append((location, min_delay, min_gamma, max_gamma))

            route = []
            node_route = []
            for pl in found_route["payload"]:
                if "state" in pl:
                    s = pl["state"]
                    route.append((g.nodes[s["loc"]], s["interval"]))
                    node_route.append((g.nodes[s["loc"]], s["interval"]))
                elif "edge" in pl:
                    for edge in g.nodes[pl["from"]["state"]["loc"]].outgoing:
                        if edge.to_node.name == pl["to"]["state"]["loc"]:
                            route.append((edge, pl["edge"]["atf"]))
                            break
            self.found_routes.append((atf, {"route": route, "node_route": node_route, "delays": delays}))
        return self

    linestyles = [
        (0, (5, 10)),
        (5, (5, 10)),
        (10, (5, 10)),
        (0, (5, 0))
    ]

    def plot(self, ax: Axis, **kwargs):
        return_values = []
        if kwargs.get("show_atf", True):
            color = kwargs.get('color', "red")
            label = kwargs.get('label', None)
            linestyle = Results.linestyles[kwargs.get('linestyle', 3)]

            y_offset = kwargs.get('y_offset', 0)

            ax.set_xlabel(kwargs.get('xlabel', 'Departure Time'))
            ax.set_ylabel(kwargs.get('ylabel', 'Arrival Time'))
            ax.set_title( kwargs.get('title', 'Arrival time function'))

            line = None
            for (x0, x1, y0, y1) in self.segments:
                if x0 == float("-inf") and x1 != float("inf") and y1 != float("inf"):
                    ax.hlines(float(y1) + y_offset, 0, float(x1), colors=color, linestyle=linestyle)
                line, = ax.plot([float(x0), float(x1)], [float(y0) + y_offset, float(y1) + y_offset], color=color,
                                linestyle=linestyle)
            line.set_label(label) if line is not None else None

        if kwargs.get("show_additional_delays", False):
            ax.set_xlabel("Departure Time")
            ax.set_ylabel("Additional Delay")
            ax.set_title("Flexibility Used")
            for atf, route in self.found_routes:
                zeta, alpha, beta, delta = atf
                delay_at_alpha = 0
                delay_at_beta  = 0
                for agents_delays in route["delays"].values():
                    current_delay_at_alpha = 0
                    current_delay_at_beta  = 0
                    if agents_delays:
                        for node, delay, min_gamma, max_gamma in agents_delays:
                            current_delay_at_alpha = max(current_delay_at_alpha, min_gamma)
                            current_delay_at_beta  = max(current_delay_at_beta,  max_gamma)
                    delay_at_alpha += current_delay_at_alpha
                    delay_at_beta  += current_delay_at_beta

                ax.plot([min(alpha, beta), beta], [delay_at_alpha, delay_at_beta], color="lightblue")

                print(f"Found ATF {atf} with flexibility between {delay_at_alpha} and {delay_at_beta}")
                return_values.append(((alpha, beta), (delay_at_alpha, delay_at_beta)))
        if kwargs.get("show_total_delays", False):
            ax.set_xlabel("Departure Time")
            ax.set_ylabel("Delay")
            ax.set_title("Flexibility Used")
            original_arrival_time = kwargs.get("original_arrival_time")
            for atf, route in self.found_routes:
                zeta, alpha, beta, delta = atf
                delay_at_alpha = alpha + delta - original_arrival_time
                delay_at_beta  = beta + delta - original_arrival_time
                for agents_delays in route["delays"].values():
                    current_delay_at_alpha = 0
                    current_delay_at_beta  = 0
                    if agents_delays:
                        for node, delay, min_gamma, max_gamma in agents_delays:
                            current_delay_at_alpha = max(current_delay_at_alpha, min_gamma)
                            current_delay_at_beta  = max(current_delay_at_beta,  max_gamma)
                    delay_at_alpha += current_delay_at_alpha
                    delay_at_beta  += current_delay_at_beta

                ax.plot([min(alpha, beta), beta], [delay_at_alpha, delay_at_beta], color="blue")
        return return_values

    def save(self, file):
        with open(file, "wb") as outp:
            pickle.dump(self, outp, pickle.HIGHEST_PROTOCOL)

    def compare_paths(self, original_path:list[str]) -> str:
        paths:list[str] = [key.split("->") for key in self.unique_paths.keys()]
        def split_list_on_gaps(path: list[int]) -> list[list[int]]:
            if not path:
                return [path]
            result = []
            result.append([path[0]])
            for p in path[1:]:
                if p - 1 == result[-1][-1]:
                    result[-1].append(p)
                else:
                    result.append([p])
            return result

        out = {}
        
        for path in paths:
            # Find differences in the paths between original and new
            differences = list(set(path) - set(original_path))
            diff_index = [path.index(i) for i in differences]
            diff_index.sort()

            largest_beta = max([b for z,a,b,d in self.unique_path_eatfs["->".join(path)]])

            temp = []
            f"Path differences when departing before {largest_beta}"
            for diffs in split_list_on_gaps(diff_index):
                differences = [path[i] for i in diffs]
                temp.append(", ".join(differences))

            out[largest_beta] = temp

        return json.dumps(out)

    def get_visiting_time_at_tipping_location(self, tipping_location_and_original_time, wait_location, best_route, agent, delayed_agent):
        visit_time = 0
        wait_location_nodes = [loc for loc in wait_location if isinstance(loc, Node)]
        tipp_loc = wait_location_nodes[-2] if len(wait_location_nodes) > 1 else wait_location_nodes[-1]
        for j, loc in enumerate(best_route["route"]):
            if loc[0] == tipp_loc:
                tipping_location_and_original_time[agent] = (tipp_loc, visit_time)
                break
            if isinstance(loc[0], Node):
                delayed_agent_passed_through = [ui for ui in loc[0].old_unsafe_intervals if ui.by_agent == delayed_agent]
                # If the agent passed through in its original path
                if delayed_agent_passed_through:
                    for ui in delayed_agent_passed_through:
                        # Use the safe intervals to get the actual duration how long an agents visits this node
                        visit_time += ui.duration
                        break
                else:
                    # Otherwise use edge length, as agent is not waiting along new route
                    next_edge = best_route["route"][j+1][0]
                    visit_time += next_edge.length
        return tipping_location_and_original_time

    def get_fastest_route(self, delayed_agent: Agent, original_arrival_time: float, actual_departure_time: float, agents: dict[Any, Agent], **kwargs):
        """
            If the agent is new and has no original arrival time, then pass 0.
            The following parameters can be passed in kwargs:
            - `discrete` used for any discrete applications (such as MAPF) to calculate the correct delay
            - `decide_tipping_point` this is only used by the `find_tipping_points` function to decide the actual tipping point, don't use this when calling this method directly
            - `optimize_total_delay`: determine whether the route should be fastest for the delayed agent or optimal overall.
            - `print_agent_delays`: print the delays of other agents to create this route for the delayed agent
        """
        # To get the correct times, as the continuous intervals are exclusive of the end
        if kwargs.get("discrete", False):
            delay_addition = 1
        else:
            delay_addition = 0
        best_route = None
        best_atf = None
        best_total_delay = float("inf")
        best_arrival_time = float("inf")
        for atf, route in self.found_routes:
            zeta, alpha, beta, delta = atf
            if kwargs.get("decide_tipping_point", False):
                in_range = zeta <= actual_departure_time <= beta
            else:
                in_range = zeta <= actual_departure_time < beta
            if in_range:
                arrival_time = max(alpha, actual_departure_time) + delta
                if kwargs.get("optimize_total_delay", True):
                    counter_own_delay = min(0, arrival_time - original_arrival_time)
                    total_delay_other_agents = counter_own_delay
                    # Computes total delay for the ATF, not on the exact actual_departure_time
                    for agent in agents.values():
                        if route["delays"][agent.id]:
                            # Account for delay of other agents once (max node)
                            total_delay_other_agents += delay_addition + max([min_gamma for delay_location, min_delay, min_gamma, max_gamma in route["delays"][agent.id]])
                    if arrival_time + total_delay_other_agents < best_arrival_time + best_total_delay:
                        best_arrival_time = arrival_time
                        best_route = route
                        best_atf = atf
                        best_total_delay = total_delay_other_agents
                else:
                    if arrival_time < best_arrival_time:
                        best_arrival_time = arrival_time
                        best_route = route
                        best_atf = atf
        minimum_delays = {}
        tipping_location_and_original_time = {}
        if best_route is None:
            return [0, 0, 0, 0], [], minimum_delays, tipping_location_and_original_time
        for agent in agents.values():
            minimum_delay = {}
            for delay_location, min_delay, min_gamma, max_gamma in best_route["delays"][agent.id]:
                wait_location = agent.get_wait_location(delay_location, {tup[0] for tup in best_route["node_route"]})
                # Determine tipping point location (last unsafe location in delay locations) per agent, independent whether same or opposite direction
                if wait_location:
                    tipping_location_and_original_time = self.get_visiting_time_at_tipping_location(tipping_location_and_original_time, wait_location, best_route, agent, delayed_agent)
                delay = min_gamma + max(best_atf[1], actual_departure_time) - best_atf[1] + delay_addition
                if kwargs.get("print_agent_delays", True):
                    print(f"Agent {agent} delayed at {delay_location}, should wait at {[x.name for x in wait_location if isinstance(x, Node)]} for at least {delay}")
                for loc in wait_location:
                    minimum_delay[loc] = max(minimum_delay.get(loc, 0), delay)
            minimum_delays[agent] = minimum_delay
        return best_atf, best_route["route"], minimum_delays, tipping_location_and_original_time
        
    def calculate_intersecting_atfs(self, original_arrival_time, **kwargs):
        line_list:list[Line] = []
        route_list = []
        tipping_points = []
        axis = kwargs.get("plot_on_axis", None)
        for atf, route in self.found_routes:
            # Calculate other agents delay lines
            zeta, alpha, beta, delta = atf
            if beta - alpha == 0:
                # Cannot construct line over same x coordinates
                continue
            delay_at_alpha = alpha + delta - original_arrival_time
            delay_at_beta  = beta + delta - original_arrival_time
            for agents_delays in route["delays"].values():
                current_delay_at_alpha = 0
                current_delay_at_beta  = 0
                if agents_delays:
                    for node, delay, min_gamma, max_gamma in agents_delays:
                        current_delay_at_alpha = max(current_delay_at_alpha, min_gamma)
                        current_delay_at_beta  = max(current_delay_at_beta,  max_gamma)
                delay_at_alpha += current_delay_at_alpha
                delay_at_beta  += current_delay_at_beta
            new_line = Line(alpha, beta, delay_at_alpha, delay_at_beta)
            if new_line in line_list:
                continue
            if line_list:
                if kwargs.get("optimize_total_delay", True):
                    # Check if the new line decreases the total delay as opposed to the previous line
                    if new_line.y0 < line_list[-1].y1:
                        # If it decreases, the tipping point is the first(?) point where the y0
                        for old_line in line_list[::-1]:
                            x_intersection = old_line.get_x_value(new_line.y0)
                            if x_intersection < float("inf"):
                                tipping_points.append(x_intersection)
                                if axis is not None:
                                    axis.plot([x_intersection, new_line.x0], [new_line.y0, new_line.y0], color="blue", linestyle="dashed")
                                break
                else:
                    # Tipping point is the beta parameter of the flexible ATF: previous ATF must have delays, while current should be non-delay
                    current_delays = sum([d[3] for _, r in route["delays"].items() for d in r])
                    previous_delays = sum([d[3] for _, r in route_list[-1]["delays"].items() for d in r])
                    if current_delays == 0 and previous_delays > 0:
                        tipping_points.append(line_list[-1].x1)
            line_list.append(new_line)
            route_list.append(route)
        return tipping_points

    def find_tipping_points(self, delayed_agent, original_arrival_time, agents, **kwargs):
        """
        Compute the tipping points for delayed agent or to optimize total delay with kwargs:
        * optimize_total_delay: whether to return the tipping point with our without optimizing for total delay (default=True)
        * discrete: whether a discrete setting is used, which influences the actual arrival times and delays (default=False)
        * print_tipping_points: whether to print tipping points or simple calculate and return them (default=True)
        * print_agent_delays: whether to print the delays of other agents (default=True)
        * plot_on_axis: the axis object to plot the delays in (default=None)
        """
        tipping_points = self.calculate_intersecting_atfs(original_arrival_time, **kwargs)
        resulting_tipping_points = []
        found = False
        for tipping_point in tipping_points:
            decide_tipping_point = not kwargs.get("optimize_total_delay", True)
            kwargs.setdefault("print_delays", False)
            atf, new_route, minimum_delays, tipping_location = self.get_fastest_route(delayed_agent, original_arrival_time, tipping_point, agents, decide_tipping_point=decide_tipping_point, **kwargs)
            # Only return tipping point and location and delays, not ATF, as these are not correct, use get_fastest_route() at this time to get ATF and route. 
            if kwargs.get("optimize_total_delay", True):
                assert delayed_agent not in tipping_location
                tipping_location[delayed_agent] = (new_route[0][0], tipping_point)
            resulting_tipping_points.append((tipping_point, tipping_location, minimum_delays))
            if kwargs.get("print_tipping_points", True):
                if kwargs.get("optimize_total_delay", True):
                    if delayed_agent.origin != new_route[0][0]:
                        print(f"ERROR: delayed agent {delayed_agent} does not have same origin {new_route[0][0]} that matches new route for starting tipping point {tipping_point}, route {new_route}")
                    print(f"Tipping point to optimize total delay for agent {delayed_agent} to start at {new_route[0][0]} is time {tipping_point}")
                    found = True
                else:
                    for agent, delays in minimum_delays.items():
                        if delays:
                            found = True
                            # Tipping point is time the delayed agent would have reached the tipping location: tipping point (on arrival time) plus its original arrival time
                            print(f"Tipping point between rerouted agent {delayed_agent} and agent {agent} at location {tipping_location[agent][0]} with tipping point t={tipping_point + tipping_location[agent][1]} relates to departure time t={tipping_point} for rerouted agent {delayed_agent} at {delayed_agent.origin} and delay of {', '.join([f'{d} at {n}' for n, d in minimum_delays[agent].items() if isinstance(n, Node)])}")
            if not found:
                print(f"No tipping point found.")
        return resulting_tipping_points
