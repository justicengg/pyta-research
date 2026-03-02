"""Feishu (飞书) group-bot webhook pusher.

Usage
-----
    from src.report.pusher import FeishuPusher
    ok = FeishuPusher().push(text='...', webhook_url=settings.feishu_webhook_url)

Feishu group-bot message format (plain text)::

    POST <webhook_url>
    Content-Type: application/json

    {
        "msg_type": "text",
        "content": { "text": "<message>" }
    }

Returns True on HTTP 200, False on any failure.
An empty *webhook_url* short-circuits immediately to False without making any
network request (mirrors the common "not configured → skip silently" pattern).
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class FeishuPusher:
    """Push a plain-text message to a Feishu group-robot webhook."""

    def push(self, text: str, webhook_url: str) -> bool:
        """POST *text* to *webhook_url*.

        Parameters
        ----------
        text:
            Plain-text message body.
        webhook_url:
            Feishu group-bot webhook URL.  If empty the call is a no-op.

        Returns
        -------
        bool
            ``True`` on HTTP 200, ``False`` on any other outcome.
        """
        if not webhook_url:
            logger.warning('feishu_webhook_url is not configured — skipping push')
            return False

        payload = {'msg_type': 'text', 'content': {'text': text}}
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
        except Exception as exc:  # pragma: no cover — network unavailable in CI
            logger.error('feishu push network error: %s', exc)
            return False

        if resp.status_code == 200:
            logger.info('feishu push success status=%s', resp.status_code)
            return True

        logger.error(
            'feishu push failed status=%s body=%s',
            resp.status_code,
            resp.text[:200],
        )
        return False
