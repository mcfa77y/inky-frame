"""TRMNL setup/pairing screen rendering."""


def render_setup_screen(
    graphics,
    width: int,
    height: int,
    device_id: str,
    base_url: str,
    friendly_id: str = "",
    setup_message: str = "",
):
    """Render pairing and onboarding instructions when device is unconfigured."""
    g = graphics
    w = width
    h = height

    g.set_pen(1)
    g.clear()

    # Header bar
    g.set_pen(0)
    g.rectangle(0, 0, w, 60)
    g.set_pen(1)
    g.set_font("sans")
    g.text("TRMNL DISPLAY  |  SETUP & PAIRING", 20, 40, scale=1.0)

    # Body info
    g.set_pen(0)
    g.set_font("sans")
    g.text("Register this device on your TRMNL server dashboard:", 30, 110, scale=0.8)

    # Box for device credentials
    g.rectangle(30, 140, w - 60, 150)
    g.set_pen(1)
    g.rectangle(32, 142, w - 64, 146)
    g.set_pen(0)
    g.text(f"Device MAC (ID):  {device_id}", 50, 180, scale=0.9)
    g.text(f"Server URL:       {base_url}", 50, 220, scale=0.9)
    if friendly_id:
        g.text(f"Friendly ID:      {friendly_id}", 50, 260, scale=0.9)

    if setup_message:
        g.text(setup_message, 30, 330, scale=0.7)

    # Footer
    g.set_font("bitmap8")
    g.text("Button A: Refresh / Pair    Button B: Reload Current", 30, h - 30, scale=2)
    g.update()
