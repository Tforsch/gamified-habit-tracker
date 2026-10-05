/**
 * Central client-side application state store.
 */
class StateStore {
  constructor() {
    this.state = {
      player: {
        name: 'Hero',
        level: 1,
        hp: 100,
        maxHp: 100,
        currentXp: 0,
        nextLevelXp: 100,
      },
      habits: [],
      loading: false,
    };
    this.listeners = [];
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.notify();
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  notify() {
    this.listeners.forEach((listener) => listener(this.state));
  }
}

export const store = new StateStore();
