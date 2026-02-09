"""Twilio Content API — template CRUD operations.

Manages WhatsApp message templates via the Twilio Content API.
Covers creation, approval submission, status polling, and listing.

This module does NOT handle message delivery (that's ``TwilioProvider.send``).
"""

from __future__ import annotations

import contextlib
import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from twilio.base.exceptions import TwilioRestException  # type: ignore[import-untyped]
from twilio.rest import Client  # type: ignore[import-untyped]
from twilio.rest.content.v1.content import ApprovalCreateList  # type: ignore[import-untyped]

from messaging.types import TwilioConfig

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────


class TwilioContentAPIError(RuntimeError):
    """Raised when Twilio Content API calls fail."""

    def __init__(self, message: str, *, status: int | None = None, code: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


# ── Types ─────────────────────────────────────────────────────────────


@dataclass
class TwilioTemplateResponse:
    """Response data from Twilio Content API template operations."""

    sid: str
    friendly_name: str
    language: str | None = None
    types: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    approval_requests: dict[str, Any] | None = None
    status: str | None = None
    template_name: str | None = None
    rejection_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TwilioTemplateResponse:
        """Parse a Twilio API response into a TwilioTemplateResponse."""
        approval_requests = data.get("approval_requests")
        status = data.get("status")
        template_name = data.get("template_name")
        rejection_reason = data.get("rejection_reason")

        if isinstance(approval_requests, dict):
            status = status or approval_requests.get("status")
            template_name = template_name or approval_requests.get("name")
            rejection_reason = rejection_reason or approval_requests.get("rejection_reason")

        return cls(
            sid=data.get("sid", ""),
            friendly_name=data.get("friendly_name", ""),
            language=data.get("language"),
            types=data.get("types"),
            variables=data.get("variables"),
            approval_requests=approval_requests,
            status=status,
            template_name=template_name,
            rejection_reason=rejection_reason,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary suitable for downstream processing."""
        result: dict[str, Any] = {
            "sid": self.sid,
            "friendly_name": self.friendly_name,
        }

        if self.language is not None:
            result["language"] = self.language
        if self.types is not None:
            result["types"] = self.types
        if self.variables is not None:
            result["variables"] = self.variables
        if self.status is not None:
            result["status"] = self.status
        if self.template_name is not None:
            result["template_name"] = self.template_name
        if self.rejection_reason is not None:
            result["rejection_reason"] = self.rejection_reason
        if self.approval_requests is not None:
            result["approval_requests"] = self.approval_requests

        return result


# ── Internal helpers ──────────────────────────────────────────────────


_TYPE_RENAME_MAP: dict[str, str] = {
    "twilio_text": "twilio/text",
    "twilio_quick_reply": "twilio/quick-reply",
    "twilio_list_picker": "twilio/list-picker",
    "twilio_call_to_action": "twilio/call-to-action",
    "twilio_card": "twilio/card",
    "twilio_catalog": "twilio/catalog",
    "twilio_carousel": "twilio/carousel",
    "twilio_location": "twilio/location",
    "twilio_media": "twilio/media",
    "twilio_schedule": "twilio/schedule",
    "whatsapp_card": "whatsapp/card",
    "whatsapp_authentication": "whatsapp/authentication",
    "whatsapp_flows": "whatsapp/flows",
}

_WHATSAPP_UNSUPPORTED_TYPES: set[str] = {"twilio/list-picker"}


def format_types_for_content_api(types: dict[str, Any]) -> dict[str, Any]:
    """Normalize internal payload keys to Twilio's slash-delimited names.

    Example: ``"twilio_text"`` → ``"twilio/text"``.
    """
    normalized: dict[str, Any] = {}
    for key, value in types.items():
        normalized_key = _TYPE_RENAME_MAP.get(key, key if "/" in key else key.replace("_", "/"))
        normalized[normalized_key] = value
    return normalized


def _serialize_template(resource: Any) -> dict[str, Any]:
    """Extract a serializable representation from a Twilio template resource."""
    return {
        "sid": getattr(resource, "sid", None),
        "friendly_name": getattr(resource, "friendly_name", None),
        "status": getattr(resource, "approval_status", getattr(resource, "status", None)),
        "template_name": getattr(resource, "template_name", getattr(resource, "whatsapp_template_name", None)),
        "rejection_reason": getattr(resource, "rejection_reason", None),
    }


def _serialize_content_with_approvals(resource: Any) -> dict[str, Any]:
    """Return a structured payload for content templates with approval metadata."""
    payload: dict[str, Any] = {
        "sid": getattr(resource, "sid", None),
        "friendly_name": getattr(resource, "friendly_name", None),
        "language": getattr(resource, "language", None),
        "types": getattr(resource, "types", None),
        "variables": getattr(resource, "variables", None),
    }
    approval_requests = getattr(resource, "approval_requests", None)
    if approval_requests is not None:
        payload["approval_requests"] = approval_requests
    return payload


# ── Public API ────────────────────────────────────────────────────────


class TwilioContentAPI:
    """Twilio Content API client for managing WhatsApp message templates.

    Usage::

        from messaging import TwilioContentAPI, TwilioConfig

        api = TwilioContentAPI(TwilioConfig(
            account_sid="AC...",
            auth_token="...",
            whatsapp_number="whatsapp:+14155238886",
        ))
        template = api.create_template(
            friendly_name="order_update",
            language="en",
            types={"twilio_text": {"body": "Your order {{1}} is {{2}}."}},
        )
    """

    def __init__(self, config: TwilioConfig) -> None:
        self._client = Client(config.account_sid, config.auth_token)

    def create_template(
        self,
        *,
        friendly_name: str,
        language: str,
        types: dict[str, Any],
        category: str | None = None,
        template_sid: str | None = None,
        whatsapp_template_name: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new content template or replace an existing one.

        If ``template_sid`` is provided, the existing template is deleted
        before creating the new one.

        If ``whatsapp_template_name`` is provided, the template is also
        submitted for WhatsApp approval.

        Raises:
            TwilioContentAPIError: On API failure or unsupported types.
        """
        formatted_types = format_types_for_content_api(types)
        payload: dict[str, Any] = {
            "friendly_name": friendly_name,
            "language": language,
            "types": formatted_types,
        }
        if variables:
            if "placeholders" in variables:
                api_variables = {}
                for p in variables["placeholders"]:
                    api_variables[str(p["index"])] = p["example"]
                payload["variables"] = api_variables
            else:
                payload["variables"] = variables

        try:
            content_api = self._client.content.v1.contents

            if template_sid:
                with contextlib.suppress(TwilioRestException):
                    content_api(template_sid).delete()

            response = self._client.request(
                "POST",
                "https://content.twilio.com/v1/Content",
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            try:
                response_payload: dict[str, Any] = json.loads(response.content or "{}")
            except json.JSONDecodeError:
                response_payload = {}

            if response.status_code >= 400:
                error_message = (
                    response_payload.get("message")
                    or response_payload.get("detail")
                    or "Twilio Content API request failed"
                )
                error_code = response_payload.get("code")
                logger.error(
                    "Twilio Content API error response: status=%s code=%s payload=%s",
                    response.status_code,
                    error_code,
                    response_payload,
                )
                raise TwilioContentAPIError(
                    error_message,
                    status=response.status_code,
                    code=error_code,
                )

            try:
                resource = TwilioTemplateResponse.from_dict(response_payload)
            except KeyError as exc:
                logger.error(
                    "Twilio Content API response missing required field: %s; payload=%s",
                    exc,
                    response_payload,
                )
                raise TwilioContentAPIError(
                    "Twilio Content API response was missing required fields",
                    status=response.status_code,
                ) from exc

            if not resource.sid:
                return resource.to_dict()

            if whatsapp_template_name:
                unsupported = _WHATSAPP_UNSUPPORTED_TYPES & set(formatted_types.keys())
                if unsupported:
                    raise TwilioContentAPIError(
                        f"WhatsApp approvals do not support the configured content types: "
                        f"{', '.join(sorted(unsupported))}",
                        status=400,
                        code=92004,
                    )

                approval_payload: dict[str, Any] = {"name": whatsapp_template_name}
                if category:
                    approval_payload["category"] = category

                content_api(resource.sid).approval_create.create(
                    ApprovalCreateList.ContentApprovalRequest(approval_payload)
                )

        except TwilioContentAPIError:
            raise
        except TwilioRestException as exc:
            logger.error(
                "Twilio Content API error: status=%s code=%s msg=%s details=%s",
                getattr(exc, "status", None),
                getattr(exc, "code", None),
                getattr(exc, "msg", None),
                getattr(exc, "details", None),
            )
            raise TwilioContentAPIError(
                exc.msg or str(exc),
                status=getattr(exc, "status", None),
                code=getattr(exc, "code", None),
            ) from exc
        except Exception as exc:
            raise TwilioContentAPIError(f"Failed to create template: {exc}") from exc

        return resource.to_dict()

    def get_template_status(self, *, template_sid: str) -> dict[str, Any]:
        """Fetch the latest status for a Twilio content template.

        Raises:
            TwilioContentAPIError: On API failure.
        """
        try:
            resource = self._client.content.v1.contents(template_sid).fetch()
        except TwilioRestException as exc:
            raise TwilioContentAPIError(
                str(exc), status=getattr(exc, "status", None), code=getattr(exc, "code", None)
            ) from exc
        return _serialize_template(resource)

    def list_templates(self, *, page_size: int = 50) -> list[dict[str, Any]]:
        """Return all Twilio content templates alongside their approval metadata.

        Raises:
            TwilioContentAPIError: On API failure.
        """
        try:
            resources = self._client.content.v1.content_and_approvals.stream(page_size=page_size)
            templates: list[dict[str, Any]] = []
            for resource in resources:
                logger.debug("Twilio template resource: %s", resource.__dict__)
                templates.append(_serialize_content_with_approvals(resource))
        except TwilioRestException as exc:
            raise TwilioContentAPIError(
                str(exc), status=getattr(exc, "status", None), code=getattr(exc, "code", None)
            ) from exc
        except Exception as exc:
            raise TwilioContentAPIError(f"Failed to list templates: {exc}") from exc

        return templates

    def create_quick_reply(
        self,
        *,
        body: str,
        buttons: list[dict[str, str]],
        header: str | None = None,
    ) -> dict[str, Any]:
        """Create a quick-reply content template for session messages.

        This creates a content template that can be sent immediately within
        a 24-hour session window without needing WhatsApp approval.

        Args:
            body: The message body text.
            buttons: List of button dicts with ``id`` and ``title`` keys (max 3).
            header: Optional header text.

        Returns:
            Dict with ``sid`` (content_sid) and other metadata.

        Raises:
            TwilioContentAPIError: If content creation fails.
        """
        quick_reply_payload: dict[str, Any] = {
            "body": body,
            "actions": [{"id": btn["id"], "title": btn["title"]} for btn in buttons[:3]],
        }

        types_payload: dict[str, Any] = {"twilio/quick-reply": quick_reply_payload}

        if header:
            types_payload["twilio/text"] = {"body": f"*{header}*\n\n{body}"}

        friendly_name = f"quick_reply_{secrets.token_hex(8)}"

        payload: dict[str, Any] = {
            "friendly_name": friendly_name,
            "language": "en",
            "types": format_types_for_content_api(types_payload),
        }

        try:
            response = self._client.request(
                "POST",
                "https://content.twilio.com/v1/Content",
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            try:
                response_payload: dict[str, Any] = json.loads(response.content or "{}")
            except json.JSONDecodeError:
                response_payload = {}

            if response.status_code >= 400:
                error_message = (
                    response_payload.get("message")
                    or response_payload.get("detail")
                    or "Failed to create quick-reply content"
                )
                raise TwilioContentAPIError(
                    error_message,
                    status=response.status_code,
                    code=response_payload.get("code"),
                )

            return {
                "sid": response_payload.get("sid"),
                "friendly_name": friendly_name,
                "status": "created",
            }

        except TwilioContentAPIError:
            raise
        except TwilioRestException as exc:
            raise TwilioContentAPIError(
                exc.msg or str(exc),
                status=getattr(exc, "status", None),
                code=getattr(exc, "code", None),
            ) from exc
        except Exception as exc:
            raise TwilioContentAPIError(f"Failed to create quick-reply: {exc}") from exc
