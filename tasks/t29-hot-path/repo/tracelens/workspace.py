"""Everything an analyst configures, in one object."""
from .sites import SiteRepo
from .segments import SegmentRepo
from .goals import GoalRepo
from .cohorts import CohortRepo
from .dashboards import DashboardRepo
from .alerts import AlertRepo
from .export_jobs import ExportJobRepo
from .api_keys import ApiKeyRepo
from .members import MemberRepo
from .annotations import AnnotationRepo
from .funnel_defs import FunnelRepo
from .channels import ChannelRepo
from .webhooks import WebhookRepo
from .filters import FilterRepo
from .samplings import SamplingRepo
from .retentions import RetentionRepo
from .invites import InviteRepo
from .tags import TagRepo
from .reports_saved import ReportRepo
from .embeds import EmbedRepo
from .dimensions import DimensionRepo
from .metrics import MetricRepo
from .experiments import ExperimentRepo
from .variants import VariantRepo
from .consent_rules import ConsentRuleRepo
from .pixels import PixelRepo
from .allowlist import AllowedRepo
from .blocklist import BlockedRepo
from .digests import DigestRepo
from .quotas import QuotaRepo


class Workspace:
    def __init__(self):
        self.sites = SiteRepo()
        self.segments = SegmentRepo()
        self.goals = GoalRepo()
        self.cohorts = CohortRepo()
        self.dashboards = DashboardRepo()
        self.alerts = AlertRepo()
        self.export_jobs = ExportJobRepo()
        self.api_keys = ApiKeyRepo()
        self.members = MemberRepo()
        self.annotations = AnnotationRepo()
        self.funnel_defs = FunnelRepo()
        self.channels = ChannelRepo()
        self.webhooks = WebhookRepo()
        self.filters = FilterRepo()
        self.samplings = SamplingRepo()
        self.retentions = RetentionRepo()
        self.invites = InviteRepo()
        self.tags = TagRepo()
        self.reports_saved = ReportRepo()
        self.embeds = EmbedRepo()
        self.dimensions = DimensionRepo()
        self.metrics = MetricRepo()
        self.experiments = ExperimentRepo()
        self.variants = VariantRepo()
        self.consent_rules = ConsentRuleRepo()
        self.pixels = PixelRepo()
        self.allowlist = AllowedRepo()
        self.blocklist = BlockedRepo()
        self.digests = DigestRepo()
        self.quotas = QuotaRepo()

    def counts(self):
        return {name: len(repo) for name, repo in vars(self).items()}
