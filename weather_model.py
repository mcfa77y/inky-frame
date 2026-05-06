"""
WeatherModel - Pure data structure for Weather App state.

Following ELM architecture, this is an immutable data structure
that represents the entire state of the Weather application.
"""


class WeatherModel:
    """Immutable model representing Weather app state."""

    def __init__(
        self,
        zipcode,
        current_view_index,
        weather_views,
        image_path,
        last_update_time,
        is_loading,
        error_message=""
    ):
        self.zipcode = zipcode
        self.current_view_index = current_view_index
        self.weather_views = weather_views
        self.image_path = image_path
        self.last_update_time = last_update_time
        self.is_loading = is_loading
        self.error_message = error_message

    def __repr__(self):
        return (f"WeatherModel(zipcode='{self.zipcode}', "
                f"current_view_index={self.current_view_index}, "
                f"is_loading={self.is_loading}, "
                f"error_message='{self.error_message}')")

    def with_view_index(self, new_index):
        """Return a new WeatherModel with updated view index."""
        return WeatherModel(
            zipcode=self.zipcode,
            current_view_index=new_index,
            weather_views=self.weather_views,
            image_path=self.image_path,
            last_update_time=self.last_update_time,
            is_loading=self.is_loading,
            error_message=self.error_message
        )

    def with_loading(self, loading):
        """Return a new WeatherModel with updated loading state."""
        return WeatherModel(
            zipcode=self.zipcode,
            current_view_index=self.current_view_index,
            weather_views=self.weather_views,
            image_path=self.image_path,
            last_update_time=self.last_update_time,
            is_loading=loading,
            error_message=self.error_message
        )

    def with_error(self, error_message):
        """Return a new WeatherModel with updated error message."""
        return WeatherModel(
            zipcode=self.zipcode,
            current_view_index=self.current_view_index,
            weather_views=self.weather_views,
            image_path=self.image_path,
            last_update_time=self.last_update_time,
            is_loading=False,
            error_message=error_message
        )

    def with_update_time(self, timestamp):
        """Return a new WeatherModel with updated last_update_time."""
        return WeatherModel(
            zipcode=self.zipcode,
            current_view_index=self.current_view_index,
            weather_views=self.weather_views,
            image_path=self.image_path,
            last_update_time=timestamp,
            is_loading=False,
            error_message=self.error_message
        )
