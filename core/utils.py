import inspect
from typing import Callable, Any, List

def rename_path_argument(func: Callable[..., Any], dynamic_name: str, type_hint: Any = int) -> None:
    """
    Mutates a function's signature to replace **kwargs with a specific named parameter.
    This allows FastAPI to correctly identify and document dynamic path parameters.
    """
    # 1. Get the original signature
    sig: inspect.Signature = inspect.signature(func)
    
    # 2. Filter out 'VAR_KEYWORD' (the **kwargs)
    new_params: List[inspect.Parameter] = [
        p for p in sig.parameters.values() 
        if p.kind != inspect.Parameter.VAR_KEYWORD
    ]

    # 3. Create the new dynamic parameter
    new_param = inspect.Parameter(
        name=dynamic_name,
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=type_hint
    )
    
    # Insert at the beginning so it appears as a primary path argument
    new_params.insert(0, new_param)

    # 4. Reconstruct and attach using setattr to bypass Pylance/Pyright "unknown member" errors
    new_sig = sig.replace(parameters=new_params)
    setattr(func, "__signature__", new_sig)