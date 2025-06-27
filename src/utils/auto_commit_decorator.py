"""
Auto-commit decorator for automatic version control

Automatically commits data changes without user prompts.
"""

import functools
from typing import Callable, Any
from loguru import logger

def auto_commit_data(data_type: str, symbol_param: str = None):
    """
    Decorator for automatic data commit after successful operations
    
    Args:
        data_type: Type of data operation (e.g., 'snapshot_data', 'historical_data')
        symbol_param: Parameter name that contains the symbol (if any)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Execute the original function
                result = func(*args, **kwargs)
                
                # If successful, auto-commit
                if result is not None:
                    try:
                        # Import here to avoid circular imports
                        from .version_control import auto_version_control
                        
                        # Extract symbol if specified
                        symbol = None
                        if symbol_param:
                            # Try to get symbol from kwargs first
                            if symbol_param in kwargs:
                                symbol = kwargs[symbol_param]
                            # Try to get from args based on function signature
                            elif hasattr(func, '__code__') and symbol_param in func.__code__.co_varnames:
                                param_index = func.__code__.co_varnames.index(symbol_param)
                                if param_index < len(args):
                                    symbol = args[param_index]
                        
                        # Perform auto-commit
                        auto_version_control.auto_commit_data_update(
                            data_type=data_type,
                            symbol=symbol
                        )
                        
                        logger.debug(f"Auto-committed {data_type} update for {symbol or 'all symbols'}")
                        
                    except Exception as e:
                        logger.warning(f"Auto-commit failed for {data_type}: {e}")
                
                return result
                
            except Exception as e:
                # Don't break the original function if auto-commit fails
                logger.error(f"Function {func.__name__} failed: {e}")
                raise
        
        return wrapper
    return decorator


def auto_commit_config(config_type: str = "config_update"):
    """
    Decorator for automatic config commit after successful operations
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                if result is not None:
                    try:
                        from .version_control import auto_version_control
                        
                        auto_version_control.auto_commit_data_update(
                            data_type=config_type,
                            symbol=None
                        )
                        
                        logger.debug(f"Auto-committed {config_type}")
                        
                    except Exception as e:
                        logger.warning(f"Auto-commit failed for {config_type}: {e}")
                
                return result
                
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {e}")
                raise
        
        return wrapper
    return decorator