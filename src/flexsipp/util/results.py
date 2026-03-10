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
        return f"Found {len(self.found_routes)} start times with unique paths {list(self.unique_routes.keys())}"

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

        # json_decoder does not support direct conversion of -inf/inf to float, thus manual conversion is needed.
        self.segments = [(float(x0), float(x1), float(y0), float(y1)) for x0, x1, y0, y1 in result["segments"]]

        # Last found route is irrelevant
        for found_route in result["payloads"][0:-1]:
            zeta, alpha, beta, delta = found_route["edge_atf"]["atf"]
            atf = (float(zeta), float(alpha), float(beta), float(delta))

            path = [(payload["state"]["loc"], payload["state"]["interval"]) for payload in found_route["payload"]]
            # TODO: rewrite this, this does not make any sense tbh
            path_str = "->".join([node for node, interval in path])
            route_str = "->".join([f"({node}, {interval})" for node, interval in path])
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

            # TODO: make this a route, including the exact edges taken
            node_route = [(g.nodes[node], interval) for node, interval in path]

            self.found_routes.append((atf, {"route": node_route, "delays": delays}))
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

                ax.plot([alpha, beta], [delay_at_alpha, delay_at_beta], color="lightblue")

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

                ax.plot([alpha, beta], [delay_at_alpha, delay_at_beta], color="blue")
        return return_values

    def save(self, file):
        with open(file, "wb") as outp:
            pickle.dump(self, outp, pickle.HIGHEST_PROTOCOL)

    def compare_paths(self, f, original_path:list[str]):
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
        
        for path in paths:
            # Find differences in the paths between original and new
            differences = list(set(path) - set(original_path))
            diff_index = [path.index(i) for i in differences]
            diff_index.sort()

            largest_beta = max([b for z,a,b,d,g in self.unique_path_eatfs[";".join(path)]])

            f.write(f"Path differences when departing before {largest_beta}\n")
            for diffs in split_list_on_gaps(diff_index):
                differences = [path[i] for i in diffs]
                f.write(", ".join(differences))
                f.write("\n")
            f.write("\n")

    # TODO: get_best_route that takes into account the total delay
    def get_fastest_route(self, actual_departure_time: float, agents: dict[int, Agent], **kwargs):
        # To get the correct times, as the continuous intervals are exclusive of the end
        if kwargs.get("discrete", False):
            delay_addition = 1
        else:
            delay_addition = 0
        best_route = None
        best_atf = None
        best_arrival_time = float("inf")
        for atf, route in self.found_routes:
            zeta, alpha, beta, delta = atf
            if kwargs.get("beta_inclusive", False):
                in_range = zeta <= actual_departure_time <= beta
            else:
                in_range = zeta <= actual_departure_time < beta
            if in_range:
                arrival_time = max(alpha, actual_departure_time) + delta
                if arrival_time < best_arrival_time:
                    best_arrival_time = arrival_time
                    best_route = route
                    best_atf = atf
        if best_route is None:
            return [], [], []

        minimum_delays = {}
        for agent in agents.values():
            minimum_delay = {}
            for delay_location, min_delay, min_gamma, max_gamma in best_route["delays"][agent.id]:
                wait_location = agent.get_wait_location(delay_location, {node for node, interval in best_route["route"]})
                delay = min_delay + max(best_atf[1], actual_departure_time) - best_atf[1] + delay_addition
                print(f"Agent {agent} delayed at {delay_location}, should wait at {[x.name for x in wait_location if isinstance(x, Node)]} for at least {delay}")
                for loc in wait_location:
                    minimum_delay[loc] = max(minimum_delay.get(loc, 0), delay)
            minimum_delays[agent] = minimum_delay

        return best_atf, best_route["route"], minimum_delays

    def find_tipping_points(self, agents, **kwargs):
        line_list:list[Line] = []
        tipping_points = []
        original_arrival_time = kwargs.get("original_arrival_time", 0)
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

            if beta - alpha == 0:
                # Cannot construct line over same x coordinates
                continue
            new_line = Line(alpha, beta, delay_at_alpha, delay_at_beta)

            if new_line in line_list:
                continue
            # Check if this new line decreases the total delay as opposed to the previous line
            if line_list and new_line.y0 < line_list[-1].y1:
                # If it decreases, the tipping point is the first(?) point where the y0
                for old_line in line_list[::-1]:
                    if kwargs.get("optimize_total_delay", True):
                        x_intersection = old_line.get_x_value(new_line.y0)
                        if x_intersection < float("inf"):
                            tipping_points.append((x_intersection, new_line.x0, new_line.y0))
                            break
                    else:
                        tipping_points.append((old_line.x1, new_line.x0, new_line.y0))
                        break

            line_list.append(new_line)
        resulting_tipping_points = []
        for tipping_point in tipping_points:
            atf, new_route, minimum_delays = self.get_fastest_route(tipping_point, agents, beta_inclusive=True)
            resulting_tipping_points.append((tipping_point, atf, new_route, minimum_delays))
            if kwargs.get("print_tipping_points", True):
                for agent, delays in minimum_delays.items():
                    if delays:
                        if kwargs.get("optimize_total_delay", True):
                            print(f"Optimal starting time for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")
                        else:
                            print(f"Tipping point for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")
        return resulting_tipping_points

if __name__ == "__main__":
    with open(r"C:\Users\eoss3\Documents\FlexSIPP\FlexSIPP\data\friso\demo_backup\update-00\results.pkl", "rb") as f:
        data = pickle.load(f)

    with open(r"C:\Users\eoss3\Documents\FlexSIPP\FlexSIPP\data\friso\demo_backup\update-00\results2.txt", "w") as f:
        data.compare_paths(f, ['LPE-1284', 'LPE-1264', 'BTL_LPE-1236', 'BTL-1194', 'BTL-1124', 'BTL_TB-1542', 'BTL_TB-1536', 'BTL_TB-1532', 'BTL_TB-1528', 'BTL_TB-1522', 'BTL_TB-528', 'BTL_TB-524', 'BTL_TB-518', 'BTL_TB-512', 'BTL_TB-506', 'TB-168', 'TB-892', 'TB-130', 'TB-116', 'TBU-96', 'TBU-72', 'BD_TBU-874', 'BD_TBU-870', 'BD_TBU-866', 'BD_TBU-862', 'BD_TBU-858', 'BD_TBU-852', 'BD_TBU-846', 'BD_TBU-836', 'BD_TBU-830', 'BD_TBU-826', 'BD_TBU-822', 'BD_TBU-818', 'BD_TBU-812', 'BD-1150', 'BD-1136', 'BD-1080', 'BD-1044', 'BD-1028', 'BD_ZHA-703', 'BD_ZHA-709', 'BD_ZHA-715', 'ZHA-526', 'ZHA-508', 'ZHA-2376', 'RTDBD-2356', 'RTDBD-2346', 'RTDBD-2336', 'RTDBD-2326', 'RTDBD-2316', 'RTDBD-2306', 'RTDBD-2296', 'RTDBD-2286', 'RTDBD-2276', 'RTDBD-2266', 'RTDBD-2256', 'KFHAZ_RTDBD-710'])