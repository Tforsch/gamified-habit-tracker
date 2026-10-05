/**
 * Habit Entity / Schema Definition
 * 
 * Relational Table: `habits`
 * -------------------------------------------------------------
 * id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
 * user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
 * title         VARCHAR(120) NOT NULL
 * description   TEXT
 * difficulty    VARCHAR(10) CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')) DEFAULT 'MEDIUM'
 * xp_reward     INT NOT NULL DEFAULT 25
 * hp_penalty    INT NOT NULL DEFAULT 10
 * streak        INT NOT NULL DEFAULT 0
 * is_active     BOOLEAN NOT NULL DEFAULT TRUE
 * created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
 * updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
 */

export class Habit {
  constructor({ id, userId, title, description = '', difficulty = 'MEDIUM', xpReward = 25, hpPenalty = 10, streak = 0, isActive = true }) {
    this.id = id;
    this.userId = userId;
    this.title = title;
    this.description = description;
    this.difficulty = difficulty;
    this.xpReward = xpReward;
    this.hpPenalty = hpPenalty;
    this.streak = streak;
    this.isActive = isActive;
  }
}
