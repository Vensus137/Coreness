"""
ChatAction - restrict chat member via Telegram API (restrictChatMember).
Maps simplified permission groups to ChatPermissions.
"""

from typing import Any, Dict


def _build_permissions(data: dict) -> Dict[str, bool]:
    """Build ChatPermissions only from permission groups explicitly present in data (no defaults)."""
    permissions: Dict[str, bool] = {}
    if "messages" in data:
        permissions["can_send_messages"] = bool(data["messages"])
    if "attachments" in data:
        v = bool(data["attachments"])
        permissions["can_send_audios"] = v
        permissions["can_send_documents"] = v
        permissions["can_send_photos"] = v
        permissions["can_send_videos"] = v
        permissions["can_send_video_notes"] = v
        permissions["can_send_voice_notes"] = v
    if "other" in data:
        v = bool(data["other"])
        permissions["can_send_polls"] = v
        permissions["can_send_other_messages"] = v
        permissions["can_add_web_page_previews"] = v
    if "management" in data:
        v = bool(data["management"])
        permissions["can_change_info"] = v
        permissions["can_invite_users"] = v
        permissions["can_pin_messages"] = v
        permissions["can_manage_topics"] = v
    return permissions


class ChatAction:
    """Actions for chat member restrictions via Telegram API."""

    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs["logger"]

    async def restrict_chat_member(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Restrict a user in a supergroup. Uses simplified permission groups:
        messages, attachments, other, management. Optional until_date (Unix time; 0 or omit = forever).
        """
        try:
            chat_id = data.get("chat_id")
            user_id = data.get("target_user_id")
            if chat_id is None:
                return {
                    "result": "error",
                    "error": {"code": "VALIDATION_ERROR", "message": "chat_id is required"},
                }
            if user_id is None:
                return {
                    "result": "error",
                    "error": {"code": "VALIDATION_ERROR", "message": "target_user_id or user_id is required"},
                }

            permissions = _build_permissions(data)

            payload = {
                "chat_id": chat_id,
                "user_id": user_id,
                "permissions": permissions,
                "use_independent_chat_permissions": True,
            }

            until_date = data.get("until_date")
            if until_date is not None:
                payload["until_date"] = int(until_date)

            result = await self.api_client.make_request_with_limit(
                bot_token, "restrictChatMember", payload, bot_id
            )

            if result.get("result") == "success":
                return {"result": "success"}
            error_data = result.get("error", {})
            if isinstance(error_data, dict):
                error_obj = error_data
            else:
                error_obj = {
                    "code": "API_ERROR",
                    "message": str(error_data) if error_data else "Unknown error",
                }
            return {"result": result.get("result", "error"), "error": error_obj}

        except Exception as e:
            self.logger.error(f"Error restricting chat member: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            }
