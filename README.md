# Replanning in Advance for Instant Delay Recovery

This project has the following directories:
- `src/flexsipp`: Python module to generate the FlexSIPP search graph
- `src/search` (atSIPP): C++ module to search for flexible any-start-time plans in the FlexSIPP search graph
- `tests`: Tests and examples for how to use the flexsipp code.
- `experiments`: Folders containing experiments with code specific to the implementation that is being tested.
  - `mapf`: Multi Agent Path Finding problems, replanning agents in a 2d grid world.
  - `railways`: Replanning delayed trains specific to the Dutch railway network.

Dependencies (version tested):
- msvc  (14.3)
- boost (1.90)

FlexSIPP can be installed in two ways, using `pip install flexsipp` or by building the package from the source code.
We recommend using a virtual environment.
To build the flexsipp from source code, in the root folder run `pip install .`
FlexSIPP can now be imported in python using `import flexsipp`.

Building flexsipp requires `boost` to be installed using `msvc`. On Windows this can be accomplished by installing 
the [boost binaries](https://www.boost.org/releases/1.90.0/) msvc version 14.3. Install these binaries in `C:\Boost` 
or set the `BOOST_PATH_DLL` environment variable to the folder that contains the .dlls files.

### How to run + Experiments
To run a specific railways scenario on a matching location for a specific agent (id=`1`):
```bash
python experiments/railways/main.py -s data/railways/scenario_test.json -l data/railways/location_test.json -a 1
```
Or for a MAPF scenario, you need to pass the agents paths:
```bash
python experiments/mapf/main.py -s data/mapf/example_warehouse/paths.txt -l data/mapf/example_warehouse/warehouse.map
```

We also created three files for the mapf experiments used in our paper, to run these execute them using python.

The `warehouse.py` has a scenario with four agents, where one agent breaks down and another agent needs to reroute, using the flexibility of a third agent that cannot influence the fourth agent.
```bash
python experiments/mapf/warehouse.py
```
The `warehouse_delay.py` is the running example in our published paper, where we assume one agent is delayed so it either forces a second agent to use flexibility (not influencing the third agent), or finds a different route.
```bash
python experiments/mapf/warehouse_delay.py
```
The `single_delay_experiment` runs the scenarios with 0 or added flexibility in the original paths, and finds a new route for a single random delay.
```bash
python experiments/mapf/single_delay_experiment.py
```
The `sequential_delay_experiment.py` runs one single scenario where it delays half of the agent sequentially, recovering from a delay and then handling the next.
```bash
python experiments/mapf/sequential_delay_experiment.py
```

The railway experiment can be found in `experiments/railways/experiment_rotterdam_schiphol.ipynb`

To run the tests use:
```bash
python -m unittest discover -s tests
```

To cite, please use:

    Issa Hanou, Eric Kemmeren, Devin Wild Thomas, and Mathijs de Weerdt.Precomputing Multi-Agent Path Replanning using Temporal Flexibility: A Case Study on the Dutch Railway Network. (2026). [In Proceedings: Nineteenth International Symposium on Combinatorial Search](https://arxiv.org/abs/2601.04884).

# Benchmarks

### MovingAI

The Moving AI benchmark set can be used with FlexSIPP, more information on the map format 
can be found [here](https://movingai.com/benchmarks/formats.html). 
FlexSIPP requires some initial solution for each instance, 
and the `scenario_file` provided to `experiments/mapf/main.py` should be a list of paths for each agent, for example the output from [PBS](https://github.com/Jiaoyang-Li/PBS), which is formatted as follows:
```
Agent <id0>: (y0,x0)->(y1,x1)->(y1,x1)->(y1,x1)->(y2,x2)->...->(yN,xN)->
Agent <id1>: (y0,x0)->(y1,x1)->(y1,x1)->(y1,x1)->(y2,x2)->...->(yN,xN)->
...
```

### New Benchmark
To add a new benchmark with a different file structure, the `Graph` class must be implemented for this type of location and the `Agent`s must be initialized with their initial routes and predefined flexibility. See `generate_mapf.py` for an example with the Moving AI benchmarks.

### Railways
The railway specific code can be found in `experiments/railways`. 
The railway is divided into two graphs, `track_graph.py` contains a view of the railway network using the smallest possible section on the track that can be reserved by a train. 
The graph defined in `block_graph.py` uses blocking time theory, where the nodes are the signal and the edges the route between these.
The experiment in the paper can not be reproduced due to proprietary data, a mockup experiment could be run as in the test cases or the first code block in this README.

# Cluster 
To run FlexSIPP experiments on a slurm cluster, ensure that the virtual environment is used by the Python version running the experiment. Therefore, first run in a login-node
```
$ bash create_venv.sh
```
Then, you can schedule the experiments, using
```
$ sbatch experiments/mapf/run-on-cluster.sh
```
which can be adjusted to different experiments.
