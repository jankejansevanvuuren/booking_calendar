"""Run: python -m unittest -v"""
import unittest

from booking import Bookings, BookingError

NINE, TEN, ELEVEN, TWELVE = (f"2026-08-12T{h:02d}:00" for h in (9, 10, 11, 12))


class TestBooking(unittest.TestCase):
    def setUp(self):
        self.bookings = Bookings()

    def book(self, room="Atlas", start=TEN, end=ELEVEN, attendees=2, name="Janke"):
        return self.bookings.add(name, room, start, end, attendees)

    def rejected(self, **kwargs):
        with self.assertRaises(BookingError) as caught:
            self.book(**kwargs)
        return str(caught.exception)

    def test_valid_booking_is_accepted(self):
        self.assertEqual(self.book()["room"], "Atlas")
        self.assertEqual(len(self.bookings.all()), 1)

    def test_unknown_room(self):
        self.assertIn("no room called", self.rejected(room="Skyline"))

    def test_too_many_attendees(self):
        self.assertIn("seats 4", self.rejected(room="Atlas", attendees=5))

    def test_end_before_start(self):
        self.assertIn("after the start", self.rejected(start=ELEVEN, end=TEN))

    def test_end_equal_to_start(self):
        self.assertIn("after the start", self.rejected(start=TEN, end=TEN))

    def test_missing_name(self):
        self.assertIn("Name is required", self.rejected(name="  "))

    def test_invalid_date_format(self):
        self.assertIn("date and time", self.rejected(start="next tuesday"))

    def test_invalid_attendee_count(self):
        self.assertIn("whole number", self.rejected(attendees="lots"))
        self.assertIn("at least 1", self.rejected(attendees=0))

    def test_only_whole_numbers_count_as_attendees(self):
        for value in (True, False, 2.5, 2.0, None, [2], {"n": 2}):
            self.assertIn("whole number", self.rejected(attendees=value), f"accepted {value!r}")
        self.assertEqual(self.book(attendees="3")["attendees"], 3)  # the form posts strings

    def test_times_with_a_timezone_are_rejected(self):
        # Both sides aware would store an aware datetime, which then raises TypeError the next
        # time it is compared with a naive one — so neither shape may get past validation.
        self.assertIn("without a time zone", self.rejected(start="2026-08-12T10:00+02:00"))
        self.assertIn("without a time zone", self.rejected(start="2026-08-12T10:00+02:00",
                                                           end="2026-08-12T11:00+02:00"))

    def test_name_length_limit(self):
        self.book(name="A" * 60)  # exactly at the limit is fine
        self.assertIn("60 characters or fewer", self.rejected(name="A" * 61, start=ELEVEN, end=TWELVE))

    def test_booking_completely_inside_an_existing_one(self):
        self.book(start=NINE, end=TWELVE)
        self.assertIn("already booked", self.rejected(start=TEN, end=ELEVEN))

    def test_booking_overlapping_the_start_of_another(self):
        self.book(start=TEN, end=TWELVE)
        self.assertIn("already booked", self.rejected(start=NINE, end=ELEVEN))

    def test_booking_overlapping_the_end_of_another(self):
        self.book(start=NINE, end=ELEVEN)
        self.assertIn("already booked", self.rejected(start=TEN, end=TWELVE))

    def test_booking_surrounding_an_existing_one(self):
        self.book(start=TEN, end=ELEVEN)
        self.assertIn("already booked", self.rejected(start=NINE, end=TWELVE))

    def test_back_to_back_bookings_are_allowed(self):
        self.book(start=NINE, end=TEN)
        self.book(start=TEN, end=ELEVEN)
        self.assertEqual(len(self.bookings.all()), 2)

    def test_same_time_in_a_different_room_is_allowed(self):
        self.book(room="Atlas")
        self.book(room="Beacon")
        self.assertEqual(len(self.bookings.all()), 2)

    def test_available_rooms_filter_on_size_and_clashes(self):
        from booking import parse_slot
        slot = parse_slot(TEN, ELEVEN, 6)
        self.assertEqual(self.bookings.available(*slot), ["Beacon", "Summit"])  # Atlas too small
        self.book(room="Beacon", attendees=6)
        self.assertEqual(self.bookings.available(*slot), ["Summit"])  # Beacon now taken


if __name__ == "__main__":
    unittest.main(verbosity=2)
