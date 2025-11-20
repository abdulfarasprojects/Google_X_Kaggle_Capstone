"""
Hero stat generation tools for progress highlights.

This module provides tools for identifying and generating impressive
achievements and milestones from user progress data.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class HeroStat:
    """A hero stat representing an impressive achievement."""
    title: str
    value: str
    description: str
    category: str  # 'streak', 'volume', 'consistency', 'milestone'
    impact_level: int  # 1-5, higher = more impressive


class HeroStatsGeneratorTool(BaseTool):
    """
    Tool for generating hero stats and achievements from user data.

    Identifies impressive accomplishments and milestones to celebrate
    user progress and maintain motivation.
    """

    def __init__(self):
        super().__init__(
            name="generate_hero_stats",
            description="Generate impressive achievements and milestones from user progress data",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to generate hero stats for"
                    },
                    "period_days": {
                        "type": "integer",
                        "minimum": 7,
                        "maximum": 90,
                        "description": "Number of days to analyze for achievements"
                    },
                    "top_n": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Number of top hero stats to return"
                    }
                },
                "required": ["user_id"]
            }
        )

    async def execute(
        self,
        user_id: str,
        period_days: int = 30,
        top_n: int = 3,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Generate hero stats for a user.

        Args:
            user_id: User ID to analyze
            period_days: Number of days to analyze (default 30)
            top_n: Number of top stats to return (default 3)
            tool_context: ADK tool context

        Returns:
            ToolResult with hero stats
        """
        try:
            if period_days < 7 or period_days > 90:
                return ToolResult(
                    success=False,
                    error="period_days must be between 7 and 90"
                )

            if top_n < 1 or top_n > 5:
                return ToolResult(
                    success=False,
                    error="top_n must be between 1 and 5"
                )

            db = get_db()
            try:
                # Get user profile
                user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=f"User not found: {user_id}"
                    )

                # Generate hero stats
                hero_stats = await self._generate_hero_stats(db, user, period_days)

                # Sort by impact level and take top N
                hero_stats.sort(key=lambda x: x.impact_level, reverse=True)
                top_stats = hero_stats[:top_n]

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "period_days": period_days,
                        "hero_stats": [
                            {
                                "title": stat.title,
                                "value": stat.value,
                                "description": stat.description,
                                "category": stat.category,
                                "impact_level": stat.impact_level
                            }
                            for stat in top_stats
                        ]
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Hero stats generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Hero stats generation failed: {str(e)}"
            )

    async def _generate_hero_stats(self, db, user: UserProfile, period_days: int) -> List[HeroStat]:
        """
        Generate all possible hero stats for the user.

        Args:
            db: Database session
            user: User profile
            period_days: Analysis period

        Returns:
            List of HeroStat objects
        """
        hero_stats = []

        end_date = date.today()
        start_date = end_date - timedelta(days=period_days-1)

        # Streak-based hero stats
        hero_stats.extend(self._generate_streak_stats(db, user, start_date, end_date))

        # Volume-based hero stats
        hero_stats.extend(self._generate_volume_stats(db, user, start_date, end_date))

        # Consistency-based hero stats
        hero_stats.extend(self._generate_consistency_stats(db, user, start_date, end_date))

        # Milestone-based hero stats
        hero_stats.extend(self._generate_milestone_stats(db, user, start_date, end_date))

        return hero_stats

    def _generate_streak_stats(self, db, user: UserProfile, start_date: date, end_date: date) -> List[HeroStat]:
        """Generate streak-based hero stats."""
        stats = []

        # Current streak
        current_streak = self._calculate_current_streak(db, user, end_date)

        if current_streak >= 30:
            stats.append(HeroStat(
                title="Unstoppable Streak",
                value=f"{current_streak} days",
                description=f"Maintained a {current_streak}-day logging streak - that's dedication!",
                category="streak",
                impact_level=5
            ))
        elif current_streak >= 14:
            stats.append(HeroStat(
                title="Consistency Champion",
                value=f"{current_streak} days",
                description=f"Built a {current_streak}-day streak of consistent tracking",
                category="streak",
                impact_level=4
            ))
        elif current_streak >= 7:
            stats.append(HeroStat(
                title="Week Warrior",
                value=f"{current_streak} days",
                description=f"Achieved a {current_streak}-day logging streak",
                category="streak",
                impact_level=3
            ))

        # Longest streak in period
        longest_streak = self._calculate_longest_streak_in_period(db, user, start_date, end_date)

        if longest_streak >= 21 and longest_streak > current_streak:
            stats.append(HeroStat(
                title="Streak Master",
                value=f"{longest_streak} days",
                description=f"Hit a peak streak of {longest_streak} consecutive days",
                category="streak",
                impact_level=4
            ))

        return stats

    def _generate_volume_stats(self, db, user: UserProfile, start_date: date, end_date: date) -> List[HeroStat]:
        """Generate volume-based hero stats."""
        stats = []

        # Total calories logged
        total_calories = db.query(MealLog.total_calories).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date >= start_date,
            MealLog.log_date <= end_date
        ).all()

        calories_sum = sum(cal[0] for cal in total_calories)

        if calories_sum >= 50000:  # 50k+ calories tracked
            stats.append(HeroStat(
                title="Calorie Tracker Extraordinaire",
                value=f"{calories_sum:,} calories",
                description=f"Tracked {calories_sum:,} calories - that's serious dedication!",
                category="volume",
                impact_level=5
            ))
        elif calories_sum >= 25000:  # 25k+ calories tracked
            stats.append(HeroStat(
                title="Nutrition Detective",
                value=f"{calories_sum:,} calories",
                description=f"Logged {calories_sum:,} calories in detailed tracking",
                category="volume",
                impact_level=4
            ))

        # Workout volume
        total_workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date >= start_date,
            WorkoutLog.log_date <= end_date
        ).count()

        if total_workouts >= 20:
            stats.append(HeroStat(
                title="Workout Warrior",
                value=f"{total_workouts} sessions",
                description=f"Completed {total_workouts} workout sessions - keep crushing it!",
                category="volume",
                impact_level=4
            ))

        # Best single workout volume
        max_volume = db.query(WorkoutLog.total_volume).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date >= start_date,
            WorkoutLog.log_date <= end_date
        ).order_by(WorkoutLog.total_volume.desc()).first()

        if max_volume and max_volume[0] >= 10000:  # 10k+ volume score
            stats.append(HeroStat(
                title="Volume King",
                value=f"{max_volume[0]:,} volume",
                description=f"Achieved a massive {max_volume[0]:,} volume score in one session!",
                category="volume",
                impact_level=4
            ))

        return stats

    def _generate_consistency_stats(self, db, user: UserProfile, start_date: date, end_date: date) -> List[HeroStat]:
        """Generate consistency-based hero stats."""
        stats = []

        # Calculate logging consistency
        total_days = (end_date - start_date).days + 1
        active_days = 0

        for check_date in [start_date + timedelta(days=i) for i in range(total_days)]:
            logs = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()
            logs += db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()
            logs += db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()

            if logs > 0:
                active_days += 1

        consistency_rate = active_days / total_days if total_days > 0 else 0

        if consistency_rate >= 0.9:  # 90%+ consistency
            stats.append(HeroStat(
                title="Consistency Champion",
                value=f"{consistency_rate:.0%}",
                description=f"Maintained {consistency_rate:.0%} logging consistency - you're unstoppable!",
                category="consistency",
                impact_level=5
            ))
        elif consistency_rate >= 0.8:  # 80%+ consistency
            stats.append(HeroStat(
                title="Reliability Rockstar",
                value=f"{consistency_rate:.0%}",
                description=f"Achieved {consistency_rate:.0%} consistency in tracking",
                category="consistency",
                impact_level=4
            ))
        elif consistency_rate >= 0.7:  # 70%+ consistency
            stats.append(HeroStat(
                title="Steady Tracker",
                value=f"{consistency_rate:.0%}",
                description=f"Maintained {consistency_rate:.0%} logging consistency",
                category="consistency",
                impact_level=3
            ))

        return stats

    def _generate_milestone_stats(self, db, user: UserProfile, start_date: date, end_date: date) -> List[HeroStat]:
        """Generate milestone-based hero stats."""
        stats = []

        # Total days since profile creation
        days_since_start = (date.today() - user.created_at.date()).days

        if days_since_start >= 100:
            stats.append(HeroStat(
                title="Century Club",
                value=f"{days_since_start} days",
                description=f"{days_since_start} days of committed weight loss journey!",
                category="milestone",
                impact_level=5
            ))
        elif days_since_start >= 30:
            stats.append(HeroStat(
                title="Month Milestone",
                value=f"{days_since_start} days",
                description=f"Completed {days_since_start} days on your weight loss journey",
                category="milestone",
                impact_level=3
            ))

        # Perfect weeks (7 days of logging)
        perfect_weeks = self._count_perfect_weeks(db, user, start_date, end_date)

        if perfect_weeks >= 4:
            stats.append(HeroStat(
                title="Perfect Month",
                value=f"{perfect_weeks} weeks",
                description=f"Completed {perfect_weeks} perfect weeks of consistent logging!",
                category="milestone",
                impact_level=5
            ))
        elif perfect_weeks >= 2:
            stats.append(HeroStat(
                title="Week Warrior",
                value=f"{perfect_weeks} weeks",
                description=f"Achieved {perfect_weeks} perfect weeks of complete tracking",
                category="milestone",
                impact_level=4
            ))

        return stats

    def _calculate_current_streak(self, db, user: UserProfile, current_date: date) -> int:
        """Calculate current streak length."""
        streak = 0
        check_date = current_date

        for i in range(60):
            logs = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()
            logs += db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()
            logs += db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()

            if logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_longest_streak_in_period(self, db, user: UserProfile, start_date: date, end_date: date) -> int:
        """Calculate longest streak within the analysis period."""
        # Simplified - just return current streak for now
        # Could be enhanced to find peak streaks within period
        return self._calculate_current_streak(db, user, end_date)

    def _count_perfect_weeks(self, db, user: UserProfile, start_date: date, end_date: date) -> int:
        """Count weeks with complete logging (all 7 days)."""
        perfect_weeks = 0

        # Get all weeks in the period
        current_date = start_date
        while current_date <= end_date:
            week_logs = 0
            for i in range(7):
                check_date = current_date + timedelta(days=i)
                if check_date > end_date:
                    break

                logs = db.query(MealLog).filter(
                    MealLog.user_id == user.user_id,
                    MealLog.log_date == check_date
                ).count()
                logs += db.query(WorkoutLog).filter(
                    WorkoutLog.user_id == user.user_id,
                    WorkoutLog.log_date == check_date
                ).count()
                logs += db.query(WellnessLog).filter(
                    WellnessLog.user_id == user.user_id,
                    WellnessLog.log_date == check_date
                ).count()

                if logs > 0:
                    week_logs += 1

            if week_logs >= 7:  # All 7 days logged
                perfect_weeks += 1

            current_date += timedelta(days=7)

        return perfect_weeks


# Create singleton instance
hero_stats_generator = HeroStatsGeneratorTool()


# Convenience function for direct use
async def generate_hero_stats(
    user_id: str,
    period_days: int = 30,
    top_n: int = 3,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate hero stats for a user.

    Args:
        user_id: User ID
        period_days: Analysis period in days
        top_n: Number of top stats to return
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await hero_stats_generator.execute(
        user_id=user_id,
        period_days=period_days,
        top_n=top_n,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['HeroStatsGeneratorTool', 'hero_stats_generator', 'generate_hero_stats']