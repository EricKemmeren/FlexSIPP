# FlexSIPP: Precomputing Multi-Agent Path Replanning using Temporal Flexibility


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

To run a specific railways scenario on a matching location for a specific agent (id=`1`):
```bash
python experiments/railways/main.py -s data/railways/scenario_test.json -l data/railways/location_test.json -a 1
```
Or for a MAPF scenario, you need to pass the agents paths:
```bash
python experiments/mapf/main.py -s data/mapf/warehouse/paths.txt -l data/mapf/warehouse/warehouse.map
```

We also created three files for the mapf experiments used in our paper, to run these execute them using python:
```bash
python experiments/mapf/warehouse.py
python experiments/mapf/single_delay_experiment.py
python experiments/mapf/sequential_delay_experiment.py 
```

The railway experiment can be found in `experiments/railways/experiment_rotterdam_schiphol.ipynb`

To run the tests use:
```bash
python -m unittest discover -s tests
```

To cite, please use:

    Issa Hanou, Eric Kemmeren, Devin Wild Thomas, and Mathijs de Weerdt. Precomputing Multi-Agent Path Replanning using Temporal Flexibility. (2026). [In Proceedings: 19th International Symposium on Combinatorial Search](https://arxiv.org/abs/2601.04884).

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
