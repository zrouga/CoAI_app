"""
Retry utilities for handling external API failures with exponential backoff
"""
import asyncio
import functools
import logging
import random
import time
from typing import TypeVar, Callable, Any, Optional, Union, Type, Tuple

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Exception raised when all retry attempts fail"""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for synchronous functions with exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt} retries",
                            extra={"function": func.__name__, "attempts": attempt}
                        )
                    
                    return result
                    
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt + 1,
                                "error": str(e)
                            }
                        )
                        raise RetryError(
                            f"Failed after {max_retries} retries: {str(e)}",
                            last_exception
                        )
                    
                    # Calculate next delay
                    if jitter:
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {actual_delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": actual_delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(actual_delay)
                    
                    # Update delay for next attempt
                    delay = min(delay * exponential_base, max_delay)
            
            # Should never reach here
            raise RetryError(
                f"Unexpected retry logic error in {func.__name__}",
                last_exception
            )
        
        return wrapper
    return decorator


def async_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for asynchronous functions with exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 0:
                        logger.info(
                            f"Async function {func.__name__} succeeded after {attempt} retries",
                            extra={"function": func.__name__, "attempts": attempt}
                        )
                    
                    return result
                    
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt + 1,
                                "error": str(e)
                            }
                        )
                        raise RetryError(
                            f"Failed after {max_retries} retries: {str(e)}",
                            last_exception
                        )
                    
                    # Calculate next delay
                    if jitter:
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay
                    
                    logger.warning(
                        f"Async function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {actual_delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": actual_delay,
                            "error": str(e)
                        }
                    )
                    
                    await asyncio.sleep(actual_delay)
                    
                    # Update delay for next attempt
                    delay = min(delay * exponential_base, max_delay)
            
            # Should never reach here
            raise RetryError(
                f"Unexpected retry logic error in {func.__name__}",
                last_exception
            )
        
        return wrapper
    return decorator


# Pre-configured decorators for common use cases
retry_api_call = exponential_backoff(
    max_retries=3,
    initial_delay=1.0,
    max_delay=10.0,
    retry_exceptions=(ConnectionError, TimeoutError, OSError)
)

retry_api_call_async = async_exponential_backoff(
    max_retries=3,
    initial_delay=1.0,
    max_delay=10.0,
    retry_exceptions=(ConnectionError, TimeoutError, OSError)
) 