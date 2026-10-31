"""`jobd doctor`: sanity checks on a configuration. Each finding is (level, message)."""
import os


def check(settings, cpu_count=None):
    cpus = cpu_count or os.cpu_count() or 1
    findings = []
    if settings.queue_workers > cpus * 4:
        findings.append(("warn", f"queue_workers ({settings.queue_workers}) is more than 4x the CPU count ({cpus})"))
    if settings.queue_workers == 1:
        findings.append(("info", "queue_workers is 1: jobs run one at a time"))
    if settings.metrics_port == 0:
        findings.append(("info", "metrics endpoint is turned off"))
    if settings.retry_limit == 0:
        findings.append(("warn", "retry_limit is 0: a failed job is never retried"))
    if settings.job_timeout_s > 3600:
        findings.append(("info", f"job_timeout_s is {settings.job_timeout_s:g}: jobs may hold a worker for hours"))
    return findings


def format_findings(findings):
    if not findings:
        return "ok: no findings\n"
    return "".join(f"{level}: {message}\n" for level, message in findings)
