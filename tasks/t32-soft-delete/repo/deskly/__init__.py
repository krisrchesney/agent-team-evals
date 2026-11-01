"""deskly: a small help desk. Customers have tickets, tickets have comments.

    from deskly.desk import Desk
    desk = Desk()
    ann = desk.create_customer("Ann", "ann@example.com")
    desk.open_ticket(ann["id"], "Printer jams", "It jams on page two.", tags=["hardware"])
"""
