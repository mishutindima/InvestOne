from typing import Any, List, Optional

from django.test.runner import DiscoverRunner


class SimpleTestRunner(DiscoverRunner):
    def __init__(
        self,
        pattern: Optional[str] = ...,
        top_level: None = ...,
        verbosity: int = ...,
        interactive: bool = ...,
        failfast: bool = ...,
        keepdb: bool = ...,
        reverse: bool = ...,
        debug_mode: bool = ...,
        debug_sql: bool = ...,
        parallel: int = ...,
        tags: Optional[List[str]] = ...,
        exclude_tags: Optional[List[str]] = ...,
        **kwargs: Any
    ) -> None:
        keepdb = True
        debug_mode = True
        verbosity = 2
        super().__init__(
            pattern,
            top_level,
            verbosity,
            interactive,
            failfast,
            keepdb,
            reverse,
            debug_mode,
            debug_sql,
            parallel,
            tags,
            exclude_tags,
            **kwargs
        )
