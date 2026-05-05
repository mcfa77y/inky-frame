# ELM Architecture Refactoring Plan

## Overview

This document outlines the refactoring of the Inky Frame application architecture to follow the ELM (Model-View-Update) pattern. ELM provides a clear separation of concerns that improves maintainability, testability, and responsiveness—critical for the resource-constrained Raspberry Pi Pico environment.

## Current Architecture Analysis

### Existing Structure

**Base Class: `InkyAppBase`** (`inky_app_base.py`)

- Provides common initialization (graphics, display dimensions, logger)
- Defines abstract methods: `update()`, `draw()`, `teardown()`
- Button press handlers: `button_a_press()` through `button_e_press()`
- Update interval property

**Example App: `WeatherApp`** (`weather.py`)

- Inherits from `InkyAppBase`
- State: `zipcode`, `current_view_index`, `weather_views` list
- Methods mix state mutations, API calls, and rendering logic
- Button handlers directly mutate state and trigger downloads

**Main Loop** (`main.py`)

- Handles button press detection and dispatch
- Calls app's `update()` and `draw()` methods
- Manages button state tracking

### Current Issues

1. **Mixed Concerns**: State, business logic, and rendering are intertwined in app classes
2. **Mutable State**: State is scattered across instance variables and mutated directly
3. **Impure Functions**: Button handlers have side effects and mix concerns
4. **Limited Testability**: Hard to test state transitions in isolation
5. **No Clear Data Flow**: It's difficult to trace how events affect state

## ELM Architecture

### Core Concepts

**Model**: Pure data structure representing application state (immutable)

- No methods, only data
- Represents the entire state of the application at a point in time

**View**: Pure function that renders the Model to the display

- Takes Model as input
- Returns display commands
- No side effects

**Update**: Pure function that handles events and returns new Model

- Takes current Model and Event as input
- Returns new Model (immutable update)
- No side effects

### Data Flow

```
Event → Update(Model, Event) → New Model → View(New Model) → Display
```

## Proposed Architecture

### New Base Class: `ElmInkyAppBase`

```python
from dataclasses import dataclass
from typing import Callable, TypeVar, Generic, Optional
from abc import ABC, abstractmethod

Model = TypeVar('Model')
Event = TypeVar('Event')

@dataclass
class ElmInkyAppBase(Generic[Model, Event], ABC):
    """Base class for ELM-architected Inky Frame apps with lifecycle hooks."""

    graphics: PicoGraphics
    width: int
    height: int
    logger: Logger

    @abstractmethod
    def init(self) -> Model:
        """Initialize the initial Model state."""
        pass

    @abstractmethod
    def update(self, model: Model, event: Event) -> Model:
        """Pure function: return new Model based on current Model and Event."""
        pass

    @abstractmethod
    def view(self, model: Model) -> None:
        """Pure function: render Model to display (no side effects)."""
        pass

    # Lifecycle hooks (optional overrides)
    def on_init(self, model: Model) -> None:
        """Called after model initialization. Override for setup logic (e.g., network requests)."""
        pass

    def on_exit(self, model: Model) -> None:
        """Called before app exits. Override for cleanup logic (e.g., unmount SD card)."""
        pass

    def on_frame(self, model: Model) -> Optional[Event]:
        """Called every frame before event processing. Return an Event to inject, or None."""
        return None

    def on_button_press(self, button: str, model: Model) -> Optional[Event]:
        """Called when a button is pressed. Return an Event to process, or None to ignore."""
        return None

    def on_timer(self, model: Model) -> Optional[Event]:
        """Called on timer tick. Return an Event to process, or None."""
        return None

    def on_network_response(self, data: dict, model: Model) -> Optional[Event]:
        """Called when network data arrives. Return an Event to process, or None."""
        return None

    def run_event_loop(self, model: Model) -> None:
        """Main event loop: handle button events and update display."""
        # Call on_init lifecycle hook
        self.on_init(model)

        try:
            while True:
                # Call on_frame lifecycle hook
                frame_event = self.on_frame(model)
                if frame_event:
                    model = self.update(model, frame_event)

                # Wait for and process next event
                event = self.wait_for_event()
                model = self.update(model, event)
                self.view(model)
        finally:
            # Call on_exit lifecycle hook
            self.on_exit(model)

    def wait_for_event(self) -> Event:
        """Wait for and return the next Event (button press, timer, etc.)."""
        pass
```

### Event System

Define a unified event type for all interactions:

```python
@dataclass
class ButtonEvent:
    button: str  # 'a', 'b', 'c', 'd', 'e'

@dataclass
class TimerEvent:
    pass  # Periodic update trigger

@dataclass
class NetworkEvent:
    data: dict  # API response data

@dataclass
class HomeEvent:
    """Event triggered when user presses E to return to launcher"""
    pass

Event = ButtonEvent | TimerEvent | NetworkEvent | HomeEvent
```

### Default App Behavior

Instead of using `state.json` to remember the previous app, the system will default to the Weather app:

- On device boot/reset, launch Weather app by default
- When E button is pressed to return to launcher, the launcher will be shown
- User can then select any app from the launcher
- This simplifies state management and provides a consistent entry point

### Example: Refactored WeatherApp

**Model** (pure data):

```python
@dataclass
class WeatherModel:
    zipcode: str
    current_view_index: int
    weather_views: list[str]
    image_path: str
    last_update_time: int
    is_loading: bool
    error_message: str | None = None
```

**Update** (pure function):

```python
class WeatherApp(ElmInkyAppBase[WeatherModel, Event]):
    def init(self) -> WeatherModel:
        return WeatherModel(
            zipcode="94102",
            current_view_index=0,
            weather_views=["current", "forecast", "today"],
            image_path="/sd/weather-daily.jpg",
            last_update_time=0,
            is_loading=False
        )

    def update(self, model: WeatherModel, event: Event) -> WeatherModel:
        if isinstance(event, ButtonEvent):
            if event.button == 'a':
                # Previous view
                new_index = (model.current_view_index - 1) % len(model.weather_views)
                return dataclasses.replace(model, current_view_index=new_index, is_loading=True)
            elif event.button == 'b':
                # Next view
                new_index = (model.current_view_index + 1) % len(model.weather_views)
                return dataclasses.replace(model, current_view_index=new_index, is_loading=True)
            elif event.button == 'c':
                # Refresh current view
                return dataclasses.replace(model, is_loading=True)

        elif isinstance(event, NetworkEvent):
            # Update with new data
            return dataclasses.replace(model, is_loading=False, last_update_time=time.time())

        elif isinstance(event, TimerEvent):
            # Periodic refresh
            if time.time() - model.last_update_time > model.update_interval:
                return dataclasses.replace(model, is_loading=True)

        return model
```

**View** (pure function):

```python
def view(self, model: WeatherModel) -> None:
    self.graphics.set_pen(1)
    self.graphics.clear()

    if model.is_loading:
        self.show_loading_indicator()
    elif model.error_message:
        self.show_error(model.error_message)
    else:
        # Display the weather image
        jpeg = jpegdec.JPEG(self.graphics)
        try:
            jpeg.open_file(model.image_path)
            jpeg.decode()
        except Exception as e:
            self.show_error("Unable to display weather image!")

    self.graphics.update()
```

## Migration Strategy

### Phase 1: Foundation (Week 1-2) ✅ COMPLETED

1. **Create new base class** ✅
   - Implemented `ElmInkyAppBase` with lifecycle hooks
   - Added abstract methods: `init()`, `update()`, `view()`
   - Added lifecycle hooks: `on_init()`, `on_exit()`, `on_frame()`, `on_button_press()`, `on_timer()`, `on_network_response()`
   - File: `elm_inky_app_base.py`

2. **Define event system** ✅
   - Created `ButtonEvent`, `TimerEvent`, `NetworkEvent`, `HomeEvent` types
   - Added `RefreshEvent` and `NavigationEvent` for convenience
   - File: `elm_events.py`

3. **Update main loop** ⏳ IN PROGRESS
   - Refactor `main.py` to use event-driven architecture
   - Remove direct button handler calls
   - Implement event queue processing
   - Remove `state.json` dependency, default to Weather app on boot

### Phase 2: Refactor Existing Apps (Week 3-4)

4. **Refactor WeatherApp** ✅ COMPLETED
   - Extracted Model as dataclass (WeatherModel)
   - Implemented pure update function with event handling
   - Implemented pure view function
   - Added lifecycle hooks implementation
   - Files: `weather_model. ⏳ PENDINGpy`, `weather_elm.py`

5. **Refactor LauncherApp**
   - Extract Model (menu items, selection state)
   - Implement pure update for app selection
   - Implement pure view f ⏳ PENDINGor menu rendering

6. **Refactor other apps**
   - NASA APOD, XKCD, News Headlines, etc.
   - Follow same pattern as WeatherApp

### Phase 3: Testing & Optimization (Week 5)

7. **Add unit tests**
   - Test update functions with various events
   - Test Model immutability
   - Test view rendering (mock graphics)

8. **Performance optimization**
   - Profile memory usage
   - Optimize event queue
   - Ensure smooth UI updates

9. **Documentation**
   - Update app development guide
   - Add ELM pattern examples
   - Document event system

## Benefits of ELM Architecture

### For the Pico Environment

1. **Reduced Memory Footprint**: Immutable data structures can be more memory-efficient with careful design
2. **Predictable State**: No hidden state mutations make debugging easier
3. **Easier Testing**: Pure functions can be tested without hardware
4. **Better Responsiveness**: Clear separation ensures UI updates don't block event handling

### For Development

1. **Clearer Code**: Separation of concerns makes code easier to understand
2. **Easier Maintenance**: Changes to one aspect (view, logic, data) don't affect others
3. **Better Reusability**: Pure functions can be reused across apps
4. **Improved Debugging**: State transitions are explicit and traceable

## Button Mapping Strategy

With 5 buttons, we need a consistent mapping strategy:

### Standard Navigation Pattern

- **Button A**: Previous / Back / Left
- **Button B**: Next / Forward / Right
- **Button C**: Select / Confirm / Action
- **Button D**: Secondary Action / Refresh
- **Button E**: **Home / Return to Launcher** (universal for all apps)

### App-Specific Adaptations

**WeatherApp**:

- A: Previous weather view
- B: Next weather view
- C: Refresh current view
- D: Change location
- E: Return to launcher

**LauncherApp**:

- A-E: Direct app selection (one button per app)
- E: Not used (already in launcher)

**Comic/XKCD App**:

- A: Previous comic
- B: Next comic
- C: Favorite/Save
- D: Random comic
- E: Return to launcher

**NASA APOD App**:

- A: Previous day
- B: Next day
- C: Save/Download
- D: Random date
- E: Return to launcher

**News Headlines App**:

- A: Previous headline
- B: Next headline
- C: Read full story (if available)
- D: Refresh headlines
- E: Return to launcher

**Word Clock App**:

- A: Previous style/theme
- B: Next style/theme
- C: Toggle seconds display
- D: Refresh time
- E: Return to launcher

## Implementation Considerations

### MicroPython Limitations

1. **No native dataclasses**: Use `@dataclass` from micropython-lib or simple tuples/dicts
2. **Limited type hints**: Use comments for documentation instead
3. **Memory constraints**: Keep Models small and avoid deep copying
4. **No generics**: Use concrete types or duck typing

### Performance Optimizations

1. **Model updates**: Use `dataclasses.replace()` or manual copying for immutability
2. **Event queue**: Keep queue size bounded to prevent memory bloat
3. **View rendering**: Only redraw when Model actually changes
4. **Lazy loading**: Download data only when needed (triggered by events)

### Backward Compatibility

Maintain compatibility during migration:

- Keep old `InkyAppBase` alongside new `ElmInkyAppBase`
- Allow apps to migrate incrementally
- Provide adapter pattern if needed

## Success Criteria

- [ ] All apps refactored to use ELM architecture
- [ ] Unit tests for update functions
- [ ] Memory usage unchanged or reduced
- [ ] Button responsiveness maintained or improved
- [ ] Documentation updated
- [ ] New apps can be created using ELM pattern easily

## Resources

- ELM Architecture: https://elmarcheut.com/elm-architecture/
- The ELM Architecture (official): https://guide.elm-lang.org/architecture/
- MicroPython documentation: https://docs.micropython.org/
- Pimoroni Inky Frame documentation: https://shop.pimoroni.com/products/inky-frame-7-3

## Next Steps

1. Review and approve this plan
2. Create new `elm_inky_app_base.py` with generic base class
3. Implement event system in `main.py`
4. Refactor WeatherApp as proof of concept
5. Iterate on remaining apps
