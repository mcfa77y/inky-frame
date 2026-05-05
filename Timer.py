import time


class Timer:
    """A simple timer class for tracking elapsed time and expiration.
    
    Useful for periodic updates, timeouts, and timing operations.
    """
    
    def __init__(self, duration_seconds: float = 0.0):
        """Initialize timer with optional duration in seconds.
        
        Args:
            duration_seconds: Duration in seconds before timer expires.
                              Set to 0 for infinite timer.
        """
        self._duration = duration_seconds
        self._start_time = None
        self._elapsed = 0.0
        self._is_running = False
        self._is_paused = False
    
    def start(self) -> None:
        """Start or resume the timer."""
        if not self._is_running:
            if self._is_paused:
                # Resume from pause
                self._start_time = time.time() - self._elapsed
                self._is_paused = False
            else:
                # Fresh start
                self._start_time = time.time()
                self._elapsed = 0.0
            self._is_running = True
    
    def pause(self) -> None:
        """Pause the timer, preserving elapsed time."""
        if self._is_running and not self._is_paused:
            self._elapsed = time.time() - self._start_time
            self._is_paused = True
            self._is_running = False
    
    def stop(self) -> None:
        """Stop the timer (alias for pause)."""
        self.pause()
    
    def reset(self) -> None:
        """Reset the timer to initial state."""
        self._start_time = None
        self._elapsed = 0.0
        self._is_running = False
        self._is_paused = False
    
    def set(self, duration_seconds: float) -> None:
        """Set a new duration for the timer.
        
        Args:
            duration_seconds: New duration in seconds.
        """
        self._duration = duration_seconds
        # Reset to apply new duration
        self.reset()
    
    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds.
        
        Returns:
            Elapsed time in seconds since start (or since pause).
        """
        if self._is_running:
            return time.time() - self._start_time
        return self._elapsed
    
    def get_remaining_seconds(self) -> float:
        """Get remaining time before expiration.
        
        Returns:
            Remaining seconds. Returns 0 if expired or infinite if duration is 0.
        """
        if self._duration == 0:
            return float('inf')
        
        elapsed = self.get_elapsed_seconds()
        remaining = self._duration - elapsed
        return max(0.0, remaining)
    
    def is_expired(self) -> bool:
        """Check if timer has expired.
        
        Returns:
            True if timer has expired, False otherwise.
            Always returns False if duration is 0 (infinite timer).
        """
        if self._duration == 0:
            return False
        return self.get_elapsed_seconds() >= self._duration
    
    def is_running(self) -> bool:
        """Check if timer is currently running.
        
        Returns:
            True if running, False otherwise.
        """
        return self._is_running
    
    def is_paused(self) -> bool:
        """Check if timer is paused.
        
        Returns:
            True if paused, False otherwise.
        """
        return self._is_paused
    
    def get_duration(self) -> float:
        """Get the configured duration.
        
        Returns:
            Duration in seconds.
        """
        return self._duration
    
    def get_elapsed_milliseconds(self) -> float:
        """Get elapsed time in milliseconds.
        
        Returns:
            Elapsed time in milliseconds.
        """
        return self.get_elapsed_seconds() * 1000.0
    
    def get_remaining_milliseconds(self) -> float:
        """Get remaining time in milliseconds.
        
        Returns:
            Remaining milliseconds. Returns 0 if expired or infinite if duration is 0.
        """
        return self.get_remaining_seconds() * 1000.0
