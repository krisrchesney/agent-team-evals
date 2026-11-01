"""lanes: projects, tasks, comments and labels for one team.

    from lanes.service import Lanes
    svc = Lanes()
    project = svc.create_project("Website")
    svc.create_task(project["id"], "Fix the footer")
"""
