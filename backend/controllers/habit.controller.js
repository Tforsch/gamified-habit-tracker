import { GamificationService } from '../services/gamification.service.js';
import { UserController } from './user.controller.js';

// In-memory mock habit store until DB connection is configured
let mockHabits = [
  {
    id: 'hab_001',
    title: 'Drink 2L Water',
    difficulty: 'EASY',
    xpReward: 15,
    hpPenalty: 5,
    streak: 4,
    completedToday: false,
  },
  {
    id: 'hab_002',
    title: 'Code for 45 minutes',
    difficulty: 'MEDIUM',
    xpReward: 35,
    hpPenalty: 15,
    streak: 2,
    completedToday: false,
  },
];

export const HabitController = {
  async getAll(req, res) {
    try {
      res.json(mockHabits);
    } catch (err) {
      res.status(500).json({ error: 'Failed to retrieve habits' });
    }
  },

  async create(req, res) {
    try {
      const { title, difficulty = 'MEDIUM', xpReward = 25, hpPenalty = 10 } = req.body;
      if (!title) {
        return res.status(400).json({ error: 'Title is required' });
      }

      const newHabit = {
        id: `hab_${Date.now()}`,
        title,
        difficulty,
        xpReward,
        hpPenalty,
        streak: 0,
        completedToday: false,
      };

      mockHabits.push(newHabit);
      res.status(201).json(newHabit);
    } catch (err) {
      res.status(500).json({ error: 'Failed to create habit' });
    }
  },

  async complete(req, res) {
    try {
      const { id } = req.params;
      const habit = mockHabits.find((h) => h.id === id);

      if (!habit) {
        return res.status(404).json({ error: 'Habit not found' });
      }

      if (habit.completedToday) {
        return res.status(400).json({ error: 'Habit already completed today' });
      }

      // Mark completed & update streak
      habit.completedToday = true;
      habit.streak += 1;

      // Calculate XP progression
      const player = UserController.getMockPlayer();
      const progression = GamificationService.processXpGain(player, habit.xpReward);
      const updatedPlayer = UserController.updateMockPlayer(progression);

      res.json({
        message: 'Quest completed successfully!',
        habit,
        player: updatedPlayer,
        habits: mockHabits,
      });
    } catch (err) {
      res.status(500).json({ error: 'Failed to complete habit' });
    }
  },
};
