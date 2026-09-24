from functools import wraps
from pathlib import Path
from time import time

def timing(file_path: Path):
    def decorator(f):
        function_name = str(f).split(" at ", maxsplit=1)[0].split("<function ")[1]
        directory = file_path / "timing"
        directory.mkdir(parents=True, exist_ok=True)
        with open(directory / f"{function_name}.csv" , 'w') as file:
            file.write(f"Seconds\n")
        @wraps(f)
        def wrap(*args, **kw):
            ts = time()
            result = f(*args, **kw)
            te = time()
            print(f'Function {str(f).split(" at ", maxsplit=1)[0].split("<function ")[1]} took {te-ts:2.4f} seconds')
            with open(directory / f"{function_name}.csv", 'a') as file:
                file.write(f'{te-ts:2.4f}\n')
            return result
        return wrap
    return decorator
