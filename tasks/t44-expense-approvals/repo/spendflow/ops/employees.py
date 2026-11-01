from .. import validate
from ..models import Employee
from ..views import employee_view
from .registry import operation


@operation("employee.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    manager = None
    if params.get("manager") is not None:
        manager = svc.store.get_employee(validate.require_str(params, "manager"), param="manager").id
    employee = Employee(id=svc.ids.new("employee"), name=name, manager=manager, created_at=now, updated_at=now)
    svc.store.employees[employee.id] = employee
    view = employee_view(employee)
    svc.bus.emit("employee.created", {"employee": view})
    return view


@operation("employee.retrieve")
def retrieve(svc, params):
    return employee_view(svc.store.get_employee(validate.require_str(params, "employee")))
