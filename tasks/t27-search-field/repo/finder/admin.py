"""Everything an operator configures, in one object."""
from .webhooks import WebhookRepo
from .schedules import ScheduleRepo
from .tenants import TenantRepo
from .quotas import QuotaRepo
from .languages import LanguageRepo
from .dictionaries import DictionaryRepo
from .result_templates import ResultTemplateRepo
from .experiments import ExperimentRepo
from .banners import BannerRepo
from .facet_defs import FacetRepo
from .collections import CollectionRepo
from .saved_searches import SavedSearchRepo
from .pinned_results import PinnedResultRepo
from .synonym_sets import SynonymSetRepo
from .stopword_sets import StopwordSetRepo
from .api_tokens import ApiTokenRepo
from .redirects import RedirectRepo
from .feedback import FeedbackRepo
from .readers import ReaderRepo
from .index_jobs import IndexJobRepo
from .query_rules import QueryRuleRepo
from .aliases import AliasRepo


class Admin:
    def __init__(self):
        self.collections = CollectionRepo()
        self.saved_searches = SavedSearchRepo()
        self.pinned_results = PinnedResultRepo()
        self.synonym_sets = SynonymSetRepo()
        self.stopword_sets = StopwordSetRepo()
        self.api_tokens = ApiTokenRepo()
        self.redirects = RedirectRepo()
        self.feedback = FeedbackRepo()
        self.readers = ReaderRepo()
        self.index_jobs = IndexJobRepo()
        self.query_rules = QueryRuleRepo()
        self.aliases = AliasRepo()
        self.webhooks = WebhookRepo()
        self.schedules = ScheduleRepo()
        self.tenants = TenantRepo()
        self.quotas = QuotaRepo()
        self.languages = LanguageRepo()
        self.dictionaries = DictionaryRepo()
        self.result_templates = ResultTemplateRepo()
        self.experiments = ExperimentRepo()
        self.banners = BannerRepo()
        self.facet_defs = FacetRepo()

    def counts(self):
        return {name: len(repo) for name, repo in vars(self).items()}
