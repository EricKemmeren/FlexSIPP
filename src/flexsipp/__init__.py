try:
    from _flexsipp import search
except ImportError:
    import os
    boost_path = os.environ.get('BOOST_PATH_DLL', r"C:\Boost\lib64-msvc-14.3")
    os.add_dll_directory(boost_path)  # TODO: maybe this can automatically be detected, I think only needed on windows
    from _flexsipp import search