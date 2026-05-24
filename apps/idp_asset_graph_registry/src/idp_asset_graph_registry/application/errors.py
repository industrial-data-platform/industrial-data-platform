from __future__ import annotations


class ApplicationError(RuntimeError):
    """Base class for Asset Graph Registry application errors."""


class DuplicateResourceError(ApplicationError):
    def __init__(self, resource: str, code: str) -> None:
        super().__init__(f"{resource} {code!r} already exists")
        self.resource = resource
        self.code = code


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str, code: str) -> None:
        super().__init__(f"{resource} {code!r} does not exist")
        self.resource = resource
        self.code = code


class InvalidOperationError(ApplicationError):
    pass


class InvalidReferenceError(ApplicationError):
    def __init__(self, reference_type: str, reference: str) -> None:
        super().__init__(f"{reference_type} reference {reference!r} is not valid")
        self.reference_type = reference_type
        self.reference = reference

