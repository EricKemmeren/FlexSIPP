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
To build the flexsipp from source code, in the root folder run `pip install .`
FlexSIPP can now be imported in python using `import flexsipp`.

Building flexsipp requires `boost` to be installed using `msvc`. On windows this can be accomplished by installing 
the [boost binaries](https://www.boost.org/releases/1.90.0/) msvc version 14.3. Install these binaries in `C:\Boost` 
or set the `BOOST_PATH_DLL` environment variable to the folder that contains the .dlls files.

To run a specific scenario on a matching location for a specific agent (id=`1`):
```bash
python experiments/railways/main.py -s tests/scenario_test.json -l tests/location_test.json -a 1
```
Or for a MAPF scenario, you need to pass the agents paths:
```bash
python experiments/mapf/main.py -s data/mapf/corridor/corridor-2agents_paths.txt -l data/mapf/corridor/corridor.map
```

To run the tests use:
```bash
python -m unittest discover -s tests
```

To cite, please use:

    Issa Hanou, Eric Kemmeren, Devin Wild Thomas, and Mathijs de Weerdt.Precomputing Multi-Agent Path Replanning using Temporal Flexibility: A Case Study on the Dutch Railway Network. (2026). [In Proceedings: International Conference on Automated Planning and Scheduling](https://arxiv.org/abs/2601.04884).

# Benchmarks

### MovingAI

The Moving AI benchmark set can be used with FlexSIPP, more information on the map format 
can be found [here](https://movingai.com/benchmarks/formats.html). FlexSIPP requires some initial solution for each instance, 
and the `scenario_file` provided to `experiments/mapf/main.py` should be a list of paths 
for each agent, formatted as follows:
```
Agent <id0>: {node1}->{node2}->{node2}->{node2}->{node3}->...->{nodeN}->
Agent <id1>: {node1}->{node2}->{node2}->{node2}->{node3}->...->{nodeN}->
...
```

### New Benchmark
To add a new benchmark with a different file structure, the `Graph` class must be implemented for this type of location and the `Agent`s must be initialized with their initial routes and predefined flexibility. See `generate_mapf.py` for an example with the Moving AI benchmarks.

### Railways
<TODO explain file structures>
