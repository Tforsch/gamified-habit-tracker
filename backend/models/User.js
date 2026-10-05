/**
 * User Entity / Schema Definition
 * 
 * Relational Table: `users`
 * -------------------------------------------------------------
 * id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
 * username      VARCHAR(50) NOT NULL UNIQUE
 * email         VARCHAR(255) NOT NULL UNIQUE
 * password_hash VARCHAR(255) NOT NULL
 * level         INT NOT NULL DEFAULT 1
 * current_xp    INT NOT NULL DEFAULT 0
 * next_level_xp INT NOT NULL DEFAULT 100
 * hp            INT NOT NULL DEFAULT 100
 * max_hp        INT NOT NULL DEFAULT 100
 * created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
 * updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
 */

export class User {
  constructor({ id, username, email, level = 1, currentXp = 0, nextLevelXp = 100, hp = 100, maxHp = 100 }) {
    this.id = id;
    this.username = username;
    this.email = email;
    this.level = level;
    this.currentXp = currentXp;
    this.nextLevelXp = nextLevelXp;
    this.hp = hp;
    this.maxHp = maxHp;
  }
}
