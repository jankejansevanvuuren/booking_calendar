# Meeting-room booking — notes

## How to run

```
python app.py          # then open http://127.0.0.1:8000
python -m unittest -v  # 18 tests, no dependencies
```

Python 3.12, standard library only — no pip install, no framework.

## Understanding of the problem

Three fixed rooms with fixed capacities. A request (name, room, time range, attendee count)
is either accepted and stored, or rejected with a reason. The interesting rule is the clash
rule: a room may hold only one booking at any instant, but a booking that begins exactly when
another ends is fine.

## Assumptions

- Bookings live in memory for the life of the process.
- Rooms are a fixed constant, not editable data.
- Times are naive local times. No time zones, no working-hours rule. A time carrying an offset is rejected rather than converted, so the store never mixes the two kinds.
- Single process, so no locking. `http.server` handles one request at a time anyway.
- Attendees must be a whole number of at least 1. A meeting for 0 people is not a booking.
- No cancel, edit features

## Questions I would normally ask

1. Should bookings survive a restart? (in-memory vs. a file or database)
2. Should past dates be rejected, and are there office hours or a max duration?
3. Is a minimum attendee count wanted, so 2 people cannot take Summit?
4. One person, many rooms, same time - allowed? (Currently yes; only rooms are checked.)
5. Time zones - is everyone in one office?
6. Should the person's name be validated against a staff list, or is free text fine?
7. On a clash, should the system suggest the next free slot?

## Edge cases identified

- End equal to start (rejected), end before start (rejected).
- Back-to-back bookings: 09:00–10:00 then 10:00–11:00 (allowed - the key case).
- The four clash shapes: inside, overlapping the start, overlapping the end, surrounding.
- Same time in a different room (allowed).
- Attendees exactly equal to capacity (allowed — `>` not `>=`).
- Whitespace-only name or room, missing fields, unparseable dates, non-numeric or zero attendees.
- Room name case: `"atlas"` is rejected. Matching is exact and the error lists the valid names.
- Names are HTML-escaped before being written into the page.


### The UI flow

The brief for the UI was: pick a time, say how many people, then pick a room *based on those
factors*. So the room dropdown is derived, not free: on any change to start, end, or attendees
the page asks `GET /api/rooms?start=…&end=…&attendees=…` and lists only the rooms that are both
big enough and free. Rooms that cannot work are never offered.

The server still re-validates everything on POST. The dropdown is a convenience; it is not the
guard. Two people on separate browsers could pick the same room, and the second POST is rejected.

### API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/rooms?start=&end=&attendees=` | Rooms that fit — `{"rooms": ["Beacon", "Summit"]}` |
| `POST /api/bookings` | JSON body with name, room, start, end, attendees → 201 or 400 `{"error": …}` |
| `GET /api/bookings` | All bookings, earliest first |

## Testing

`python -m unittest -v` — 18 tests, all passing. Each case the brief asked for has a test whose
name says which case it is:

| Required case | Test |
| --- | --- |
| Valid booking | `test_valid_booking_is_accepted` |
| Unknown room | `test_unknown_room` |
| Too many attendees | `test_too_many_attendees` |
| Invalid start/end | `test_end_before_start`, `test_end_equal_to_start` |
| Missing or invalid input | `test_missing_name`, `test_invalid_date_format`, `test_invalid_attendee_count`, `test_only_whole_numbers_count_as_attendees`, `test_name_length_limit`, `test_times_with_a_timezone_are_rejected` |
| Booking inside an existing one | `test_booking_completely_inside_an_existing_one` |
| Overlapping the beginning | `test_booking_overlapping_the_start_of_another` |
| Overlapping the end | `test_booking_overlapping_the_end_of_another` |
| Surrounding an existing one | `test_booking_surrounding_an_existing_one` |
| Ends exactly when the next begins | `test_back_to_back_bookings_are_allowed` |

Plus `test_same_time_in_a_different_room_is_allowed` and a test that the availability filter
drops rooms that are too small *and* rooms already taken.

The tests assert on the message, not just that something was raised, so a booking rejected for
the wrong reason fails the test.
