"""Everything an operator configures, in one object."""
from .queues import QueueDefRepo
from .handlers import HandlerDefRepo
from .schedules import ScheduleDefRepo
from .owners import OwnerRepo
from .alerts import AlertRepo
from .silences import SilenceRepo
from .namespaces import NamespaceRepo
from .secrets import SecretRepo
from .hooks import HookRepo
from .labels import LabelRepo
from .runbooks import RunbookRepo
from .incidents import IncidentRepo
from .windows import WindowRepo
from .api_keys import ApiKeyRepo
from .peers import PeerRepo
from .audit_rules import RuleRepo
from .tenants import TenantRepo
from .clusters import ClusterRepo
from .deployments import DeploymentRepo
from .dashboards import DashboardRepo
from .subscriptions import SubscriptionRepo
from .quotas import QuotaRepo
from .retentions import RetentionRepo
from .traces import TraceRepo


class Catalog:
    def __init__(self):
        self.queues = QueueDefRepo()
        self.handlers = HandlerDefRepo()
        self.schedules = ScheduleDefRepo()
        self.owners = OwnerRepo()
        self.alerts = AlertRepo()
        self.silences = SilenceRepo()
        self.namespaces = NamespaceRepo()
        self.secrets = SecretRepo()
        self.hooks = HookRepo()
        self.labels = LabelRepo()
        self.runbooks = RunbookRepo()
        self.incidents = IncidentRepo()
        self.windows = WindowRepo()
        self.api_keys = ApiKeyRepo()
        self.peers = PeerRepo()
        self.audit_rules = RuleRepo()
        self.tenants = TenantRepo()
        self.clusters = ClusterRepo()
        self.deployments = DeploymentRepo()
        self.dashboards = DashboardRepo()
        self.subscriptions = SubscriptionRepo()
        self.quotas = QuotaRepo()
        self.retentions = RetentionRepo()
        self.traces = TraceRepo()

    def counts(self):
        return {name: len(repo) for name, repo in vars(self).items()}
