# Replanning in Advance for Instant Delay Recovery

This project has the following directories:
- `generation`: Python module to generate the @SIPP search graph
- `search` (atSIPP): C++ module to search for any-start-time plans in the @SIPP search graph
- `data`: two dutch shunting yard layouts: Enkhuizen and Heerlen. This also includes code to generate new scenarios and explanation of how the real-life scenario was created.
- `experiments`: the notebook contains all the code to run experiments for our paper

Dependencies (version tested):
- msvc  (14.3)
- boost (1.90)

To create a package that can be installed from the flexsipp source code, run the following command:
```bash
    pip install .
```
Flexsipp can now be imported in python with `import flexsipp`.

This requires `boost` to be installed using `msvc`. On windows this can be accomplished by installing 
the [boost binaries](https://www.boost.org/releases/1.90.0/) msvc version 14.3. Install these binaries in `C:\Boost` 
or set the `BOOST_PATH_DLL` environment variable to the folder that contains the .dlls files.



[//]: # ()
[//]: # (To cite, please use:)

[//]: # ()
[//]: # (    Issa Hanou, Devin W. Thomas, Wheeler Ruml, and Mathijs de Weerdt. Replanning in Advance for Instant Delay Recovery in Multi-Agent Applications: Rerouting Trains in a Railway Hub. &#40;2024&#41;. In Proceedings: International Conference on Automated Planning and Scheduling.)

[//]: # (To run the tests directory, make sure atstipp.exe is added to the PATH)