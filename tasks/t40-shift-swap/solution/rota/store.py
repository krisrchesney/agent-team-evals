from .errors import NotFound


class Store:
    def __init__(self):
        self.staff = {}
        self.shifts = {}
        self.swaps = {}

    def get_staff(self, staff_id, param="staff"):
        person = self.staff.get(staff_id)
        if person is None:
            raise NotFound(f"no staff member {staff_id!r}", param=param)
        return person

    def get_shift(self, shift_id):
        shift = self.shifts.get(shift_id)
        if shift is None:
            raise NotFound(f"no shift {shift_id!r}", param="shift")
        return shift

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def shifts_of(self, staff_id):
        return sorted((s for s in self.shifts.values() if s.staff == staff_id), key=lambda s: (s.start, s.id))

    def clashes(self, staff_id, start, end, ignore=None):
        """Shifts of this person that overlap [start, end)."""
        return [s for s in self.shifts_of(staff_id) if s.id != ignore and s.start < end and start < s.end]

    def get_swap(self, swap_id):
        swap = self.swaps.get(swap_id)
        if swap is None:
            raise NotFound(f"no swap {swap_id!r}", param="swap")
        return swap

    def expire_swaps(self, now):
        for swap in self.swaps.values():
            if swap.status == "pending" and swap.expires_at <= now:
                swap.status = "expired"
                self.bump(swap, now)

    def pending_for(self, shift_id):
        return [s for s in self.swaps.values() if s.shift == shift_id and s.status == "pending"]
