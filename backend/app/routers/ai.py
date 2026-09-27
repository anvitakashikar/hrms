from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user

router = APIRouter()


@router.post("/assistant")
def ai_assistant(prompt: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    text = str(prompt.get("prompt", "")).strip()
    if not text:
        text = "Review HR operations for this week."
    return {
        "summary": f"HR assistant analyzed the request for {current_user['org_id']} and found key actions around hiring, onboarding, and employee support.",
        "actions": [
            "Review pending onboarding tasks",
            "Audit leave balance and approvals",
            "Check payroll reconciliation status",
            "Assess recruitment pipeline health",
        ],
        "prompt": text,
    }
