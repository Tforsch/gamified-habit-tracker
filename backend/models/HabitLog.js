/**
 * HabitLog Entity / Schema Definition
 * 
 * Relational Table: `habit_logs`
 * -------------------------------------------------------------
 * id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
 * habit_id     UUID NOT NULL REFERENCES habits(id) ON DELETE CASCADE
 * user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
 * status       VARCHAR(20) CHECK (status IN ('COMPLETED', 'MISSED', 'SKIPPED')) NOT NULL
 * xp_earned    INT NOT NULL DEFAULT 0
 * hp_lost      INT NOT NULL DEFAULT 0
 * logged_at    DATE NOT NULL DEFAULT CURRENT_DATE
 * created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
 * 
 * UNIQUE(habit_id, logged_at) -- Prevents duplicate check-ins on the same day
 */

export class HabitLog {
  constructor({ id, habitId, userId, status, xpEarned = 0, hpLost = 0, loggedAt = new Date().toISOString() }) {
    this.id = id;
    this.habitId = habitId;
    this.userId = userId;
    this.status = status;
    this.xpEarned = xpEarned;
    this.hpLost = hpLost;
    this.loggedAt = loggedAt;
  }
}
