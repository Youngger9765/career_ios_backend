"""
Credit Billing Service - Business logic for credit system
"""
import math
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.counselor import Counselor
from app.models.credit_log import CreditLog
from app.models.credit_rate import CreditRate
from app.schemas.credit import CreditCalculationResult


class CreditBillingService:
    """Service for managing credit calculations and transactions"""

    def __init__(self, db: Session):
        self.db = db

    def get_active_rate(self, rule_name: str) -> Optional[CreditRate]:
        """
        Get the active rate for a given rule name.
        Returns the latest version of active rate.
        """
        return (
            self.db.query(CreditRate)
            .filter(
                CreditRate.rule_name == rule_name,
                CreditRate.is_active == True,  # noqa: E712
                CreditRate.effective_from <= datetime.utcnow(),
            )
            .order_by(desc(CreditRate.version))
            .first()
        )

    def calculate_credits(
        self, duration_seconds: int, rule_name: str
    ) -> CreditCalculationResult:
        """
        Calculate credits based on duration and billing rule.

        Supports three calculation methods:
        1. per_second: rate_config = {"credits_per_second": 0.0278}
        2. per_minute: rate_config = {"credits_per_minute": 10} (rounds up)
        3. tiered: rate_config = {
             "tiers": [
               {"max_seconds": 600, "credits_per_second": 1},
               {"max_seconds": 1800, "credits_per_second": 0.8},
               {"max_seconds": null, "credits_per_second": 0.5}
             ]
           }
        """
        rate = self.get_active_rate(rule_name)
        if not rate:
            raise ValueError(f"No active billing rate found for rule: {rule_name}")

        calculation_method = rate.calculation_method
        rate_config = rate.rate_config

        if calculation_method == "per_second":
            credits_per_second = rate_config.get("credits_per_second", 1)
            credits = duration_seconds * credits_per_second
            details = {
                "method": "per_second",
                "duration_seconds": duration_seconds,
                "credits_per_second": credits_per_second,
                "total_credits": credits,
            }

        elif calculation_method == "per_minute":
            # Round up to nearest minute
            minutes = math.ceil(duration_seconds / 60)
            credits_per_minute = rate_config.get("credits_per_minute", 10)
            credits = minutes * credits_per_minute
            details = {
                "method": "per_minute",
                "duration_seconds": duration_seconds,
                "minutes_rounded_up": minutes,
                "credits_per_minute": credits_per_minute,
                "total_credits": credits,
            }

        elif calculation_method == "tiered":
            # Tiered pricing: apply different rates for different time ranges
            tiers = rate_config.get("tiers", [])
            credits = 0
            remaining_seconds = duration_seconds
            details = {
                "method": "tiered",
                "duration_seconds": duration_seconds,
                "tier_breakdown": [],
            }

            for tier in tiers:
                max_seconds = tier.get("max_seconds")
                credits_per_second = tier.get("credits_per_second", 1)

                if max_seconds is None:
                    # Last tier, apply to all remaining
                    tier_credits = remaining_seconds * credits_per_second
                    details["tier_breakdown"].append(
                        {
                            "tier": "unlimited",
                            "seconds_in_tier": remaining_seconds,
                            "credits_per_second": credits_per_second,
                            "tier_credits": tier_credits,
                        }
                    )
                    credits += tier_credits
                    break
                else:
                    # Apply to this tier only
                    seconds_in_tier = min(remaining_seconds, max_seconds)
                    tier_credits = seconds_in_tier * credits_per_second
                    details["tier_breakdown"].append(
                        {
                            "tier": f"0-{max_seconds}s",
                            "seconds_in_tier": seconds_in_tier,
                            "credits_per_second": credits_per_second,
                            "tier_credits": tier_credits,
                        }
                    )
                    credits += tier_credits
                    remaining_seconds -= seconds_in_tier
                    if remaining_seconds <= 0:
                        break

            details["total_credits"] = credits

        else:
            raise ValueError(f"Unknown calculation method: {calculation_method}")

        return CreditCalculationResult(
            credits=int(credits),
            rate_snapshot={
                "rule_name": rate.rule_name,
                "calculation_method": rate.calculation_method,
                "rate_config": rate.rate_config,
                "version": rate.version,
            },
            calculation_details=details,
        )

    def add_credits(
        self,
        counselor_id: UUID,
        credits_delta: int,
        transaction_type: str,
        raw_data: Optional[Dict] = None,
        session_id: Optional[UUID] = None,
        rate_snapshot: Optional[Dict] = None,
        calculation_details: Optional[Dict] = None,
    ) -> CreditLog:
        """
        Add or remove credits from a counselor's account.

        Args:
            counselor_id: UUID of the counselor
            credits_delta: Positive = add, negative = use/remove
            transaction_type: purchase, usage, admin_adjustment, refund
            raw_data: Optional raw data (e.g., duration_seconds)
            session_id: Optional session ID if related to a session
            rate_snapshot: Optional rate configuration snapshot
            calculation_details: Optional calculation breakdown

        Returns:
            Created CreditLog

        Raises:
            ValueError: If counselor not found
        """
        # Get counselor
        counselor = (
            self.db.query(Counselor).filter(Counselor.id == counselor_id).first()
        )
        if not counselor:
            raise ValueError(f"Counselor not found: {counselor_id}")

        # Update counselor credits
        if credits_delta > 0:
            # Adding credits
            counselor.total_credits += credits_delta
        else:
            # Using/removing credits
            counselor.credits_used += abs(credits_delta)

        # Create log entry
        credit_log = CreditLog(
            counselor_id=counselor_id,
            session_id=session_id,
            credits_delta=credits_delta,
            transaction_type=transaction_type,
            raw_data=raw_data,
            rate_snapshot=rate_snapshot,
            calculation_details=calculation_details,
        )

        self.db.add(credit_log)
        self.db.commit()
        self.db.refresh(credit_log)

        return credit_log

    def get_counselor_balance(self, counselor_id: UUID) -> Dict:
        """
        Get counselor's credit balance.

        Returns:
            Dictionary with total_credits, credits_used, available_credits, subscription_expires_at
        """
        counselor = (
            self.db.query(Counselor).filter(Counselor.id == counselor_id).first()
        )
        if not counselor:
            raise ValueError(f"Counselor not found: {counselor_id}")

        return {
            "total_credits": counselor.total_credits,
            "credits_used": counselor.credits_used,
            "available_credits": counselor.available_credits,
            "subscription_expires_at": counselor.subscription_expires_at,
        }
