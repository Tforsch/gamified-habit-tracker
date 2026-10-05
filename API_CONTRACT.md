# API Contract & Data Exchange Specification

This document defines the REST contract agreed upon between the Frontend and Backend engineers.
All endpoints use JSON payloads and return ISO 8601 timestamps.

---

## Base URL
`/api/v1`

---

## Common Models

### User / Player Stats
```json
{
  "id": "uuid-v4",
  "username": "string",
  "level": 1,
  "currentXp": 120,
  "nextLevelXp": 500,
  "hp": 100,
  "maxHp": 100,
  "streak": 5
}
```

### Habit
```json
{
  "id": "uuid-v4",
  "userId": "uuid-v4",
  "title": "string",
  "difficulty": "EASY | MEDIUM | HARD",
  "xpReward": 25,
  "hpPenalty": 10,
  "streak": 3,
  "completedToday": false,
  "createdAt": "2026-10-05T00:00:00Z"
}
```

---

## Endpoints

### 1. User Endpoints
- `GET /api/v1/users/me` -> Fetch player profile, level, HP, XP, streaks.

### 2. Habit Endpoints
- `GET /api/v1/habits` -> List all habits for current user.
- `POST /api/v1/habits` -> Create a new habit.
- `POST /api/v1/habits/:id/complete` -> Mark habit as completed for today (+XP, streak update).
- `DELETE /api/v1/habits/:id` -> Remove a habit.
