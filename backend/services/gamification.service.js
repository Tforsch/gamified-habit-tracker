/**
 * Gamification Service
 * Handles XP calculations, level-up milestones, and health penalties.
 */
export const GamificationService = {
  /**
   * Applies XP and checks for level progression.
   * Growth formula: Next Level XP = floor(BaseXP * (Level ^ 1.5))
   */
  processXpGain(user, xpGained) {
    let currentXp = user.currentXp + xpGained;
    let level = user.level;
    let nextLevelXp = user.nextLevelXp;
    let leveledUp = false;

    while (currentXp >= nextLevelXp) {
      currentXp -= nextLevelXp;
      level += 1;
      nextLevelXp = Math.floor(100 * Math.pow(level, 1.5));
      leveledUp = true;
    }

    return {
      level,
      currentXp,
      nextLevelXp,
      leveledUp,
    };
  },

  /**
   * Applies damage to user HP for missed habits.
   */
  processDamage(user, penalty) {
    const updatedHp = Math.max(0, user.hp - penalty);
    return {
      hp: updatedHp,
      isFainted: updatedHp === 0,
    };
  },
};
