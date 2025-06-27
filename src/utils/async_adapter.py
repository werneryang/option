"""
Async Adapter for Streamlit

Provides safe async execution in Streamlit's synchronous context
"""

import asyncio
import threading
from typing import Any, Callable, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, Future
import functools
from loguru import logger


class StreamlitAsyncAdapter:
    """
    Adapter to safely run async functions in Streamlit
    """
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="streamlit_async")
        self._active_tasks: Dict[str, Future] = {}
    
    def run_async(self, coro, task_id: Optional[str] = None) -> Any:
        """
        Run an async coroutine in a separate thread with proper event loop handling
        
        Args:
            coro: The coroutine to run
            task_id: Optional task identifier for tracking
        
        Returns:
            The result of the coroutine
        """
        def run_in_thread():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Error running async task: {e}")
                raise
        
        # Submit to thread pool
        future = self._executor.submit(run_in_thread)
        
        if task_id:
            self._active_tasks[task_id] = future
        
        try:
            # Wait for result with timeout
            result = future.result(timeout=300)  # 5 minute timeout
            return result
        except Exception as e:
            logger.error(f"Async task failed: {e}")
            raise
        finally:
            if task_id and task_id in self._active_tasks:
                del self._active_tasks[task_id]
    
    def run_async_with_progress(self, coro, progress_callback: Optional[Callable] = None, 
                               task_id: Optional[str] = None) -> Any:
        """
        Run async function with progress updates
        
        Args:
            coro: The coroutine to run
            progress_callback: Function to call with progress updates
            task_id: Optional task identifier
        
        Returns:
            The result of the coroutine
        """
        def run_with_progress():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Add progress monitoring if callback provided
                if progress_callback:
                    # Simple progress simulation - real implementation would need
                    # the async function to support progress reporting
                    progress_callback(0.1, "Starting...")
                
                try:
                    result = loop.run_until_complete(coro)
                    
                    if progress_callback:
                        progress_callback(1.0, "Completed")
                    
                    return result
                finally:
                    loop.close()
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Error: {str(e)}")
                raise
        
        future = self._executor.submit(run_with_progress)
        
        if task_id:
            self._active_tasks[task_id] = future
        
        try:
            return future.result(timeout=300)
        finally:
            if task_id and task_id in self._active_tasks:
                del self._active_tasks[task_id]
    
    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is currently running"""
        return task_id in self._active_tasks and not self._active_tasks[task_id].done()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self._active_tasks:
            future = self._active_tasks[task_id]
            result = future.cancel()
            if result:
                del self._active_tasks[task_id]
            return result
        return False
    
    def get_active_tasks(self) -> Dict[str, bool]:
        """Get status of all active tasks"""
        return {
            task_id: not future.done() 
            for task_id, future in self._active_tasks.items()
        }
    
    def cleanup_completed_tasks(self):
        """Remove completed tasks from tracking"""
        completed_tasks = [
            task_id for task_id, future in self._active_tasks.items() 
            if future.done()
        ]
        for task_id in completed_tasks:
            del self._active_tasks[task_id]
    
    def shutdown(self):
        """Shutdown the thread pool executor"""
        self._executor.shutdown(wait=True)


# Global adapter instance
streamlit_async = StreamlitAsyncAdapter()


def async_to_sync(timeout: int = 300):
    """
    Decorator to convert async functions for safe use in Streamlit
    
    Usage:
        @async_to_sync(timeout=60)
        async def my_async_function():
            return await some_async_operation()
        
        # Can now be called directly in Streamlit
        result = my_async_function()
    """
    def decorator(async_func):
        @functools.wraps(async_func)
        def wrapper(*args, **kwargs):
            coro = async_func(*args, **kwargs)
            return streamlit_async.run_async(coro)
        return wrapper
    return decorator


def run_async_safely(coro, timeout: int = 300) -> Any:
    """
    Convenience function to safely run async code in Streamlit
    
    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds
    
    Returns:
        The result of the coroutine
    """
    return streamlit_async.run_async(coro)


def run_async_with_spinner(coro, spinner_text: str = "Processing...", timeout: int = 300) -> Any:
    """
    Run async code with Streamlit spinner
    
    Args:
        coro: The coroutine to run
        spinner_text: Text to show in spinner
        timeout: Timeout in seconds
    
    Returns:
        The result of the coroutine
    """
    import streamlit as st
    
    with st.spinner(spinner_text):
        return streamlit_async.run_async(coro)