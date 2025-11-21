import os
from copy import deepcopy

import numpy as np
import pandas as pd
import json

from pathlib import Path

from setup import *

class Runner:
    def __init__(self, l: Layout, s_file, save_dir):
        self.r_stop = None
        self.r_start = None
        self.scenario = Scenario(l, s_file)
        self.save_dir = Path(save_dir) / Path(s_file).stem
        self.agent_df = self._calculate_agent_df(s_file)

    def _calculate_agent_df(self, s_file):
        try:
            base_path = Path(__file__).parent
            file_path = (base_path / s_file).resolve()
            data = json.load(open(file_path))
        except:
            data = json.load(open(s_file))
        types = {x["name"]: x for x in data["types"]}
        agents = []
        for trainNumber, entry in enumerate(data["trains"]):
            trainNumber += 1
            move = entry["movements"][0]
            velocity = types[entry["trainUnitTypes"][0]]["speed"] / 3.6

            agent = Agent(trainNumber, move["startLocation"], move["endLocation"], velocity, move["startTime"],
                          endTime=move["endTime"],
                          startTimeHuman=str(timedelta(seconds=move["startTime"])),
                          endTimeHuman=str(timedelta(seconds=move["endTime"])),
                          trainNumber=entry["trainNumber"],
                          trainUnitTypes=entry["trainUnitTypes"],
                          stops=move["stops"]
                          )
            agents.append(agent)

        agent_df = pd.DataFrame([agent.__dict__ for agent in agents])

        return agent_df

    def _get_replanning_agent(self, trainseries, direction, from_stop):
        def filter(row):
            stops = pd.DataFrame(self.get_inclusive_stops(row))
            return stops["location"].str.contains(from_stop).any()

        series = self._get_series(trainseries, direction)
        if series is None:
            logger.warning(f"No agent found that matches train series {trainseries} in direction {direction} starting from stop {from_stop}. Now adding the required train to the agent DataFrame")
            return None
        agent = series.loc[series.apply(filter, axis=1)].iloc[0]
        return agent

    def _get_series(self, trainseries, direction):
        trainseries = str(int(trainseries) // 100) if int(trainseries) > 100 else str(trainseries)
        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0
        series = self.agent_df.loc[(self.agent_df['trainNumber'].str.startswith(trainseries, na=False)) & (
                self.agent_df['trainNumber'].astype(int) % 2 == direction) & (
                                           self.agent_df['trainNumber'].astype(int) < (
                                               int(trainseries) + 1) * 100)].sort_values("endTime")
        if series.empty:
            return None
        else:
            return series

    def get_inclusive_stops(self, agent):
        all_stops = deepcopy(agent["stops"])
        all_stops.insert(0, {
            "expected_arrival": agent["start_time"],
            "time": agent["start_time"],
            "location": agent["origin"]
        })
        all_stops.append({
            "expected_arrival": agent["endTime"],
            "time": agent["endTime"],
            "location": agent["destination"]
        })
        return all_stops

    def filter_nodes(self, f, t, agent):
        stops_df = pd.DataFrame(self.get_inclusive_stops(agent))
        self.r_start = stops_df.loc[stops_df["location"].str.contains(f, na=False)]
        self.r_stop = stops_df.loc[stops_df["location"].str.contains(t, na=False)]
        return calculated_filtered_nodes(self.r_start, self.r_stop, agent, self.scenario.l)
    
    def add_new_agent(self, agent_id, start_time, origin, destination, trainTypes, stops):
        endTime = self.scenario.global_end_time
        # Add the required train to the dataframe
        if len(trainTypes) > 0 and trainTypes[0] in self.scenario.train_unit_types:
            self.agent_df.loc[-1] = Agent(agent_id, origin, destination, self.scenario.train_unit_types[trainTypes[0]]["speed"], start_time,
                                        startTimeHuman=str(timedelta(seconds=start_time)),
                                        endTimeHuman=str(timedelta(seconds=endTime)),
                                        trainUnitTypes=trainTypes,
                                        stops=stops
                                    )
            logger.info("Not filtering any tracks from the safe intervals.")
        else:
            logger.error(f"Could not find train type {trainTypes[0]} in train types {self.scenario.train_unit_types.keys()}")
        # Set up the data frame of the stops for the new train
        stops.insert(0, {
            "expected_arrival": start_time,
            "time": start_time,
            "location": origin
        })
        stops.append({
            "expected_arrival": endTime,
            "time": endTime,
            "location": destination
        })
        stops_df = pd.DataFrame(stops)
        self.r_start = stops_df.loc[stops_df["location"].str.contains(origin, na=False)]
        self.r_stop = stops_df.loc[stops_df["location"].str.contains(destination, na=False)]

class TadRunner(Runner):
    """The parameters startTime, endTime, trainTypes, and stop are only given for planning a new train, not replanning a delayed train"""
    def run(self, trainseries, direction, f, t, timeout=300, default_direction=1, max_buffer_time=900, startTime=0, trainTypes=["EUROSTAR"], stop=[]):
        agent = self._get_replanning_agent(trainseries, direction, f)
        if agent is not None:
            filter_nodes = self.filter_nodes(f, t, agent)
            agent_id = agent["id"]
        else:
            agent_id = trainseries
            filter_nodes = set([])
            self.add_new_agent(agent_id, startTime, f, t, trainTypes, stop)

        # Setup experiment
        experiment_settings = [
            {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "agent_id": agent_id,
                "metadata": {
                    "offset": 0,
                    "search": "repeat"
                },
            },
            {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "max_buffer_time": max_buffer_time,
                "use_recovery_time": True,
                "agent_id": agent_id,
                "metadata": {
                    "color": "Blue",
                    "label": "Recovery time",
                    "search": "repeat"
                }
            },
            {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "agent_id": agent_id,
                "metadata": {
                    "color": "Green",
                    "offset": 0,
                    "search": "sipp"
                }
            }
        ]

        experiments = setup_experiment(self.scenario, experiment_settings, default_direction=default_direction)
        run_experiments(experiments, timeout, filter_tracks=filter_nodes)
        return experiments

    def plot(self, experiments, save=None, x_offset=900, y_range=900, y_offset=0, include_expected_arrival=True):
        if experiments:
            expected_arrival = self.r_stop["expected_arrival"].iloc[0] - self.r_start["time"].iloc[0]
            kwargs = {"min_x": 0, "max_x": x_offset,
                      "min_y": expected_arrival - y_range + y_offset, "max_y": expected_arrival + y_range + y_offset}
            if include_expected_arrival:
                kwargs |= {"expected_arrival_time": expected_arrival + y_offset}
            if save is not None:
                save_path = self.save_dir / save
                save_path.parent.mkdir(exist_ok=True, parents=True)
                plot_experiments(experiments, save_path=save_path, **kwargs)
            plot_experiments(experiments, **kwargs)

class RTRunner(Runner):
    def run(self, trainseries, direction, f, t, timeout=300):
        agent = self._get_replanning_agent(trainseries, direction, f)
        if len(agent) == 0:
            return []
        allowed_nodes = self.allowed_nodes(f, t, agent)
        start_time = self.r_start["time"].iloc[0]
        origin = self.r_start["location"].iloc[0]
        experiment_settings = []

        stops = self.get_inclusive_stops(agent)[self.r_start.index[0] + 1:self.r_stop.index[0] + 1]

        for stop in stops:
            experiment_settings.append({
                "start_time": start_time,
                "origin": origin,
                "destination": stop["location"],
                "max_buffer_time": 900,
                "use_recovery_time": True,
                "filter_agents": agent["id"],
                "metadata": {
                    "expected_arrival": stop["expected_arrival"],
                    "label": f'route to {stop["location"]}'
                }
            })


        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0
        experiments = setup_experiment(self.scenario, experiment_settings, default_direction=direction)
        run_experiments(experiments, timeout, filter_tracks=allowed_nodes)
        return experiments

    def get_path_df(self, experiments):
        def sum_cols(df1, cols, name):
            df2 = df1.drop(columns=cols)
            df2[name] = df1[cols].sum(axis=1)
            return df2

        time_df = pd.DataFrame([exp.get_running_time() for exp in experiments],
                               index=[exp.metadata['label'] for exp in experiments])

        setup_cols = ["track graph creation", "routing graph creation"]
        recompute_cols = ["unsafe interval generation", "safe interval generation", "bt and crt generation",
                          "converting routes to blocks"]
        search_cols = ["FlexSIPP search time"]

        time_df = sum_cols(time_df, setup_cols, "Setup Time")
        time_df = sum_cols(time_df, recompute_cols, "Recompute Time")
        time_df = sum_cols(time_df, search_cols, "Search Time")

        path_data = {}

        for exp in experiments:
            total_paths = 0
            acc_length = 0
            if exp.results:
                for path, occurrences in exp.results[2].items():
                    total_paths += occurrences
                    length = len(path.split(";")) * occurrences
                    acc_length += length
                path_data[exp.metadata["label"]] = {"Average path length": acc_length / total_paths, "Total paths": total_paths} | exp.get_complexity() | exp.get_atfs()

        path_df = pd.DataFrame(path_data).transpose()
        return path_df.join(time_df["Search Time"])

class AgentRunner(Runner):
    def run(self, trainseries, direction, f, t, repeats, interval, timeout=300, i_save_dir=None):
        if i_save_dir == None:
            return []

        agent = self._get_replanning_agent(trainseries, direction, f)
        if len(agent) == 0:
            return []
        allowed_nodes = self.filter_nodes(f, t, agent)

        start_time = self.r_start["time"].iloc[0]
        origin = self.r_start["location"].iloc[0]
        expected_arrival = self.r_stop["time"].iloc[0]
        destination = self.r_stop["location"].iloc[0]

        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0

        n_trains = len(self.agent_df)

        completed_repeats = [int(item[1:-4]) for item in os.listdir(i_save_dir)]

        print(f"Completed repeats: {completed_repeats}")

        for repeat in range(repeats):
            path_data = {}
            train_ids = np.arange(1, n_trains)
            train_ids = train_ids[train_ids != agent["id"]]
            shuffled_ids = np.random.permutation(train_ids)

            if repeat in completed_repeats:
                continue

            for idx in range(0, n_trains, interval):
                filter_agents = set(shuffled_ids[:idx])
                filter_agents.add(agent["id"])

                experiment_settings = {
                    "start_time": start_time,
                    "origin": origin,
                    "destination": destination,
                    "max_buffer_time": 900,
                    "use_recovery_time": True,
                    "filter_agents": filter_agents,
                    "metadata": {
                        "expected_arrival": expected_arrival,
                        "label": f'{idx}',
                        "repeat": f'{repeat}',
                        "trains excluded": filter_agents
                    }
                }

                experiment = setup_experiment(self.scenario, [experiment_settings], default_direction=direction)[0]
                run_experiments([experiment], timeout, filter_tracks=allowed_nodes)

                path_data[experiment.metadata["label"]] = self.get_path_data(experiment)
            path_df = pd.DataFrame(path_data).transpose()
            path_df.to_csv(i_save_dir / f"r{repeat}.csv")

    def get_path_data(self, experiment):
        path_data = {}

        total_paths = 0
        acc_length = 0
        if experiment.results:
            for path, occurences in experiment.results[2].items():
                total_paths += occurences
                length = len(path.split(";")) * occurences
                acc_length += length
            path_data = {"Average path length": acc_length / total_paths, "Total paths": total_paths} | experiment.get_complexity() | experiment.get_metadata() | experiment.get_running_time() | exp.get_atfs()
        return path_data