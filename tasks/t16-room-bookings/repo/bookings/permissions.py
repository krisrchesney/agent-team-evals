"""Who may do what."""
from .errors import NotAllowed


def check_can_book(user, room):
    if user.role == "guest":
        raise NotAllowed("guests cannot book rooms")
    if room.tier == "premium" and user.role == "staff":
        raise NotAllowed("premium rooms need a manager")


def can_cancel(user, booking):
    """Admins cancel anything, managers cancel their team's bookings, everyone else only their own."""
    if user.role == "admin":
        return True
    if user.role == "manager":
        return booking.team == user.team
    return booking.user_id == user.id and user.role != "guest"


def check_can_cancel(user, booking):
    if not can_cancel(user, booking):
        raise NotAllowed("you cannot cancel this booking")
