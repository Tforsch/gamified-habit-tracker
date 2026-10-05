import { ApiClient } from './api-client.js';
import { store } from './state.js';
import { UiRenderer } from './ui-renderer.js';

/**
 * Main application bootstrap and controller.
 */
class App {
  static async init() {
    // Subscribe UI renders to state changes
    store.subscribe((state) => {
      UiRenderer.renderHUD(state.player);
      UiRenderer.renderHabits(state.habits, App.handleCompleteHabit);
    });

    // Render initial state
    const initialState = store.getState();
    UiRenderer.renderHUD(initialState.player);
    UiRenderer.renderHabits(initialState.habits, App.handleCompleteHabit);

    // Setup event listeners & live countdown ticker
    App.setupEventListeners();
    App.startCountdownTimer();

    // Fetch initial data from backend API
    await App.loadInitialData();
  }

  static startCountdownTimer() {
    const update = () => {
      const now = new Date();
      const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
      const diff = midnight.getTime() - now.getTime();
      UiRenderer.renderCountdown(diff);
    };

    update();
    setInterval(update, 1000);
  }

  static setupEventListeners() {
    const addBtn = document.getElementById('btn-add-habit');
    if (addBtn) {
      addBtn.addEventListener('click', async () => {
        const title = prompt('Enter quest (habit) title:');
        if (!title) return;

        try {
          const newHabit = await ApiClient.createHabit({
            title,
            difficulty: 'MEDIUM',
            xpReward: 25,
            hpPenalty: 10,
          });
          const currentHabits = store.getState().habits;
          store.setState({ habits: [...currentHabits, newHabit] });
        } catch (err) {
          console.warn('API unavailable, applying optimistic local state:', err);
          const mockHabit = {
            id: Date.now().toString(),
            title,
            xpReward: 25,
            hpPenalty: 10,
            streak: 0,
            completedToday: false,
          };
          store.setState({ habits: [...store.getState().habits, mockHabit] });
        }
      });
    }
  }

  static async loadInitialData() {
    try {
      const [player, habits] = await Promise.all([
        ApiClient.getPlayerProfile(),
        ApiClient.getHabits(),
      ]);
      store.setState({ player, habits });
    } catch (err) {
      console.warn('Backend server not connected yet. Running in offline/mock mode.');
    }
  }

  static async handleCompleteHabit(habitId) {
    try {
      const result = await ApiClient.completeHabit(habitId);
      if (result.player && result.habits) {
        store.setState({ player: result.player, habits: result.habits });
      }
    } catch (err) {
      console.warn('Backend offline, completing locally:', err);
      const habits = store.getState().habits.map((h) => {
        if (h.id === habitId) {
          return { ...h, completedToday: true, streak: (h.streak || 0) + 1 };
        }
        return h;
      });

      const player = { ...store.getState().player };
      player.currentXp += 25;
      if (player.currentXp >= player.nextLevelXp) {
        player.level += 1;
        player.currentXp -= player.nextLevelXp;
        player.nextLevelXp = Math.floor(player.nextLevelXp * 1.5);
      }

      store.setState({ habits, player });
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
