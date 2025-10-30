from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# Status codes map to the four rows on a standard driver's log
# 1: Off Duty, 2: Sleeper Berth, 3: Driving, 4: On Duty (not driving)


@dataclass
class LogSegment:
    start_hour: float  # hours since midnight, 0-24
    end_hour: float
    status: int  # 1..4


def _clip_to_day(hours_remaining: float, max_hours: float) -> float:
    if hours_remaining <= 0:
        return 0.0
    return float(min(hours_remaining, max_hours))


def generate_day_segments(remaining_drive_hours: float) -> List[LogSegment]:
    """
    Generate one day's log using a simplified HOS model:
      - Duty window: 14h
      - Max driving per day: up to 11h (bounded by remaining_drive_hours)
      - 30m break after 8h of on-duty time (we place it at hour 8 as Off Duty)
      - Start day at midnight with On Duty (not driving) 1h for pre/post trip split (0.5 + 0.5)
      - Remaining time in duty window as Driving until min(11h, remaining)
      - After duty window, Off Duty to complete 24h day to enable 10h reset implicitly across days
    """
    segments: List[LogSegment] = []
    t = 0.0
    duty_window_h = 14.0
    max_drive_today = _clip_to_day(remaining_drive_hours, 11.0)
    if max_drive_today == 0:
        # Entire day off-duty
        segments.append(LogSegment(0.0, 24.0, 1))
        return segments

    # On-duty not driving pre-trip 0.5h
    segments.append(LogSegment(t, t + 0.5, 4))
    t += 0.5

    drive_before_break = _clip_to_day(max_drive_today, 8.0 - t)
    if drive_before_break > 0:
        segments.append(LogSegment(t, t + drive_before_break, 3))
        t += drive_before_break

    # 30m break if still within duty and still have driving left
    if t < 8.0 and max_drive_today > (segments[-1].end_hour - segments[0].end_hour if segments else 0):
        break_len = min(0.5, 8.0 - t)
        segments.append(LogSegment(t, t + break_len, 1))
        t += break_len

    # Continue driving until max_drive_today or duty window minus 0.5h post-trip
    remaining_drive_today = max_drive_today - sum(
        s.end_hour - s.start_hour for s in segments if s.status == 3
    )
    remaining_duty_before_post = max(0.0, duty_window_h - 0.5 - t)
    drive_after_break = _clip_to_day(remaining_drive_today, remaining_duty_before_post)
    if drive_after_break > 0:
        segments.append(LogSegment(t, t + drive_after_break, 3))
        t += drive_after_break

    # Post-trip 0.5h on-duty if still within duty window
    if t < duty_window_h:
        end = min(duty_window_h, t + 0.5)
        segments.append(LogSegment(t, end, 4))
        t = end

    # Remaining hours of day off-duty
    if t < 24.0:
        segments.append(LogSegment(t, 24.0, 1))

    return segments


def generate_eld_logs(total_drive_seconds: float) -> List[Dict]:
    """
    Produce a list of daily logs. Each log contains drawable segments.
    Input is total driving seconds from the trip plan (plus any service time accounted outside).
    """
    remaining_hours = max(0.0, total_drive_seconds / 3600.0)
    days: List[Dict] = []

    while True:
        day_drive = min(remaining_hours, 11.0)
        segments = generate_day_segments(remaining_hours)
        days.append(
            {
                "segments": [
                    {"start": s.start_hour, "end": s.end_hour, "status": s.status}
                    for s in segments
                ]
            }
        )
        remaining_hours -= day_drive
        if remaining_hours <= 0.0001:
            break

    return days


