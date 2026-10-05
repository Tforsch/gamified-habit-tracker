/**
 * User Controller
 * Manages player profile, RPG stats, and inventory queries.
 */

// In-memory mock record until DB connection is configured
let mockPlayer = {
  id: 'usr_001',
  name: 'Hero',
  level: 1,
  currentXp: 45,
  nextLevelXp: 100,
  hp: 100,
  maxHp: 100,
  streak: 3,
};

export const UserController = {
  async getProfile(req, res) {
    try {
      res.json(mockPlayer);
    } catch (err) {
      res.status(500).json({ error: 'Failed to retrieve profile' });
    }
  },

  // Helper for habit completion to update user stats
  updateMockPlayer(updates) {
    mockPlayer = { ...mockPlayer, ...updates };
    return mockPlayer;
  },

  getMockPlayer() {
    return mockPlayer;
  },
};
