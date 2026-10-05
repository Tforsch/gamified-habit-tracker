/**
 * API Client module for interacting with the backend REST endpoints.
 */
const BASE_URL = 'http://localhost:5000/api/v1';

export const ApiClient = {
  async getPlayerProfile() {
    const res = await fetch(`${BASE_URL}/users/me`);
    if (!res.ok) throw new Error('Failed to fetch player profile');
    return res.json();
  },

  async getHabits() {
    const res = await fetch(`${BASE_URL}/habits`);
    if (!res.ok) throw new Error('Failed to fetch habits');
    return res.json();
  },

  async createHabit(habitData) {
    const res = await fetch(`${BASE_URL}/habits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(habitData),
    });
    if (!res.ok) throw new Error('Failed to create habit');
    return res.json();
  },

  async completeHabit(id) {
    const res = await fetch(`${BASE_URL}/habits/${id}/complete`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to complete habit');
    return res.json();
  },
};
