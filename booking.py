"""Booking rules. Pure logic, no I/O, so the rules can be tested on their own."""
from datetime import datetime

ROOMS = {"Atlas": 4, "Beacon": 8, "Summit": 12}
MAX_TEXT = 60  # characters allowed in a name or room; mirrored by maxlength in the form


class BookingError(ValueError):
    """A booking request that must be rejected, with a human-readable reason."""


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise BookingError(f"{field} is required")
    if len(value.strip()) > MAX_TEXT:
        raise BookingError(f"{field} must be {MAX_TEXT} characters or fewer")
    return value.strip()


def _time(value, field):
    raw = _text(value, field)  # outside the try: a missing field is not a format error
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        raise BookingError(f"{field} must be a date and time like 2026-08-12T09:00")
    # Everything here is naive local time. Storing one aware datetime would make every later
    # comparison against a naive one raise TypeError, so they are refused at the door.
    if moment.tzinfo is not None:
        raise BookingError(f"{field} must be a local time, without a time zone")
    return moment


def _count(value):
    # bool is a subclass of int, so True would otherwise book a meeting for one person.
    # Floats are refused too: 2.5 people is not a number of attendees.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise BookingError("Number of attendees must be a whole number")
    try:
        count = int(value)
    except ValueError:
        raise BookingError("Number of attendees must be a whole number")
    if count < 1:
        raise BookingError("Number of attendees must be at least 1")
    return count


def parse_slot(start, end, attendees):
    """Validate the parts that do not depend on a room, and return them parsed."""
    start, end = _time(start, "Start time"), _time(end, "End time")
    attendees = _count(attendees)
    if end <= start:
        raise BookingError("End time must be after the start time")
    return start, end, attendees


class Bookings:
    """In-memory list of confirmed bookings."""

    def __init__(self):
        self._items = []

    def is_free(self, room, start, end):
        # Half-open [start, end): a booking may start exactly when another ends.
        return not any(b["room"] == room and b["start"] < end and start < b["end"]
                       for b in self._items)

    def available(self, start, end, attendees):
        """Rooms that are big enough and free for the whole period."""
        return [r for r, capacity in ROOMS.items()
                if capacity >= attendees and self.is_free(r, start, end)]

    def add(self, name, room, start, end, attendees):
        name = _text(name, "Name")
        room = _text(room, "Room")
        if room not in ROOMS:
            raise BookingError(f"There is no room called '{room}' "
                               f"(choose {', '.join(ROOMS)})")
        start, end, attendees = parse_slot(start, end, attendees)
        if attendees > ROOMS[room]:
            raise BookingError(f"{room} seats {ROOMS[room]}, so it cannot take {attendees}")
        if not self.is_free(room, start, end):
            raise BookingError(f"{room} is already booked for part of that period")
        booking = {"name": name, "room": room, "start": start, "end": end,
                   "attendees": attendees}
        self._items.append(booking)
        return booking

    def all(self):
        return sorted(self._items, key=lambda b: (b["start"], b["room"]))
