"""
Batch state management tool for Weight Loss Chat Agent.

This tool manages session state for batch processing workflows.
"""

import logging
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# In-memory session storage (in production, this would be a database)
_session_store: Dict[str, Dict[str, Any]] = {}


async def get_batch_state(context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """
    Get current batch state for user.

    Args:
        context: Additional context
        tool_context: Tool context containing session information

    Returns:
        Dict with batch state information
    """
    try:
        try:
            user_id = tool_context._invocation_context.session.user_id if tool_context and hasattr(tool_context, '_invocation_context') else "unknown"
        except AttributeError:
            user_id = "unknown"
        session_data = _session_store.get(user_id, {})

        return {
            "has_active_batch": bool(session_data.get("batch_type")),
            "batch_type": session_data.get("batch_type"),
            "meal_type": session_data.get("meal_type"),
            "current_items": session_data.get("batch_items", []),
            "item_count": len(session_data.get("batch_items", [])),
            "session_data": session_data
        }

    except Exception as e:
        logger.error(f"Failed to get batch state for user {user_id}: {e}")
        return {
            "has_active_batch": False,
            "error": str(e)
        }


async def update_batch_state(
    user_id: str,
    action: str,
    data: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update batch state for user.

    Args:
        user_id: User identifier
        action: Action to perform (start_batch, add_item, complete_batch, clear_batch)
        data: Action-specific data
        context: Additional context

    Returns:
        Dict with update result
    """
    try:
        if action == "start_batch":
            batch_type = data.get("batch_type", "meal") if data else "meal"
            if batch_type == "meal":
                meal_type = data.get("meal_type", "snack") if data else "snack"
                _session_store[user_id] = {
                    "batch_type": "meal",
                    "meal_type": meal_type,
                    "batch_items": []
                }
                return {"success": True, "action": "started", "batch_type": "meal", "meal_type": meal_type}
            elif batch_type == "workout":
                _session_store[user_id] = {
                    "batch_type": "workout",
                    "batch_items": []
                }
                return {"success": True, "action": "started", "batch_type": "workout"}
            elif batch_type == "wellness":
                _session_store[user_id] = {
                    "batch_type": "wellness",
                    "batch_items": []
                }
                return {"success": True, "action": "started", "batch_type": "wellness"}
            else:
                return {"success": False, "error": f"Unknown batch type: {batch_type}"}

        elif action == "add_item":
            session_data = _session_store.get(user_id, {})
            batch_type = session_data.get("batch_type")
            if not batch_type:
                return {"success": False, "error": "No active batch"}

            items = session_data.get("batch_items", [])
            new_item = data.get("item") if data else None
            if new_item:
                items.append(new_item)
                session_data["batch_items"] = items
                _session_store[user_id] = session_data

            return {
                "success": True,
                "action": "added",
                "batch_type": batch_type,
                "item_count": len(items),
                "new_item": new_item
            }

        elif action == "complete_batch":
            session_data = _session_store.get(user_id, {})
            batch_type = session_data.get("batch_type")
            if not batch_type:
                return {"success": False, "error": "No active batch"}

            batch_data = {
                "batch_type": batch_type,
                "items": session_data.get("batch_items", [])
            }
            
            if batch_type == "meal":
                batch_data["meal_type"] = session_data.get("meal_type")

            # Clear the session
            _session_store[user_id] = {}

            return {
                "success": True,
                "action": "completed",
                "batch_data": batch_data
            }

        elif action == "clear_batch":
            _session_store[user_id] = {}
            return {"success": True, "action": "cleared"}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Failed to update batch state for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


__all__ = ['get_batch_state', 'update_batch_state']