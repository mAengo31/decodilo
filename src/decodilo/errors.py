"""Domain-specific exceptions for invariant and cost-accounting failures."""


class DecodiloError(Exception):
    """Base exception for decodilo failures."""


class InvariantViolation(DecodiloError):
    """Raised when an impossible learner, syncer, or event-log state is observed."""


class PricingAmbiguityError(DecodiloError):
    """Raised when pricing data is missing or a query matches multiple prices."""


class BudgetExceededError(DecodiloError):
    """Raised when a planned run fails a fail-closed budget guard."""


class ReplayMismatchError(DecodiloError):
    """Raised when replay cannot validate the event log deterministically."""


class OptionalDependencyMissing(DecodiloError):
    """Raised when an optional trainer dependency is requested but unavailable."""


class LaunchDisabledError(DecodiloError):
    """Raised when a cloud launch path is invoked while launches are disabled."""
