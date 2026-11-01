def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def employee_view(employee):
    return {"id": employee.id, "name": employee.name, "manager": employee.manager,
            "created_at": stamp(employee.created_at), "updated_at": stamp(employee.updated_at),
            "version": employee.version}


def expense_view(expense):
    return {"id": expense.id, "employee": expense.employee, "amount": expense.amount,
            "date": expense.date.isoformat(), "description": expense.description, "status": expense.status,
            "created_at": stamp(expense.created_at), "updated_at": stamp(expense.updated_at),
            "version": expense.version}
