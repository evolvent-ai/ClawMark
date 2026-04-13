"""Environment state management.

Each service has its own sub-package with a fixed structure::

    state/
      base.py              # BaseStateManager ABC
      composite.py         # CompositeStateManager (orchestrates all)
      filesystem/          # Built-in: workspace file management
        __init__.py
        manager.py
      notion/              # Notion: duplicate-from-template lifecycle
        __init__.py
        manager.py         # NotionStateManager
        api.py             # Notion REST API client
      email/               # Email via GreenMail IMAP/SMTP
        __init__.py
        manager.py         # EmailStateManager
        client.py          # IMAP/SMTP client
      calendar/            # Calendar via Radicale CalDAV
        __init__.py
        manager.py         # CalendarStateManager
        client.py          # CalDAV client

To add a new service:
1. Create ``state/<service>/__init__.py`` that imports the manager
2. Create ``state/<service>/manager.py`` with a ``@BaseStateManager.register("<service>")`` class
3. Optionally create ``state/<service>/api.py`` for service-specific API helpers
4. Import the sub-package here to trigger registration
"""
from .base import BaseStateManager
from .composite import CompositeStateManager

# Import sub-packages to trigger @register decorators
from . import filesystem  # noqa: F401
from . import notion  # noqa: F401
from . import email  # noqa: F401
from . import google_sheets  # noqa: F401
from . import calendar  # noqa: F401

__all__ = ["BaseStateManager", "CompositeStateManager"]
