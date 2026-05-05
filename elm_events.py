"""
Event system for ELM architecture.

Defines unified event types for all interactions in Inky Frame apps.
"""


class ButtonEvent:
    """Event triggered when a button is pressed."""
    def __init__(self, button: str):
        self.button = button  # 'a', 'b', 'c', 'd', 'e'

    def __repr__(self):
        return f"ButtonEvent(button='{self.button}')"


class TimerEvent:
    """Event triggered on periodic timer tick."""
    def __repr__(self):
        return "TimerEvent()"


class NetworkEvent:
    """Event triggered when network data arrives."""
    def __init__(self, data: dict):
        self.data = data

    def __repr__(self):
        return f"NetworkEvent(data={self.data})"


class HomeEvent:
    """Event triggered when user presses E to return to launcher."""
    def __repr__(self):
        return "HomeEvent()"


class RefreshEvent:
    """Event triggered to refresh current data."""
    def __repr__(self):
        return "RefreshEvent()"


class NavigationEvent:
    """Event triggered for navigation (next/previous)."""
    def __init__(self, direction: str):
        self.direction = direction  # 'next' or 'previous'

    def __repr__(self):
        return f"NavigationEvent(direction='{self.direction}')"
