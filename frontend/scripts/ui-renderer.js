/**
 * UI Renderer responsible for DOM mutations based on state.
 */
export const UiRenderer = {
  renderHUD(player) {
    const levelEl = document.getElementById('player-level');
    const nameEl = document.getElementById('player-name');
    const hpValEl = document.getElementById('hp-value');
    const hpBarEl = document.getElementById('hp-bar');
    const xpValEl = document.getElementById('xp-value');
    const xpBarEl = document.getElementById('xp-bar');

    if (levelEl) levelEl.textContent = `Level ${player.level}`;
    if (nameEl) nameEl.textContent = player.name;

    const hpPercent = Math.max(0, Math.min(100, (player.hp / player.maxHp) * 100));
    if (hpValEl) hpValEl.textContent = `${player.hp} / ${player.maxHp}`;
    if (hpBarEl) hpBarEl.style.width = `${hpPercent}%`;

    const xpPercent = Math.max(0, Math.min(100, (player.currentXp / player.nextLevelXp) * 100));
    if (xpValEl) xpValEl.textContent = `${player.currentXp} / ${player.nextLevelXp}`;
    if (xpBarEl) xpBarEl.style.width = `${xpPercent}%`;
  },

  renderHabits(habits, onComplete) {
    const container = document.getElementById('habit-list');
    if (!container) return;

    container.innerHTML = '';

    if (habits.length === 0) {
      container.innerHTML = `<li style="color: var(--text-muted); text-align: center; padding: 2rem;">No active quests. Click '+ New Quest' to begin!</li>`;
      return;
    }

    habits.forEach((habit) => {
      const li = document.createElement('li');
      li.className = `habit-card ${habit.completedToday ? 'completed' : ''}`;
      li.innerHTML = `
        <div>
          <div class="habit-title">${habit.title}</div>
          <div class="habit-badges">
            <span class="badge-xp">+${habit.xpReward} XP</span>
            <span class="badge-streak">🔥 ${habit.streak || 0}d streak</span>
            ${!habit.completedToday ? `<span class="badge-penalty">💔 -${habit.hpPenalty || 10} HP (опівночі)</span>` : '<span style="color: var(--color-success)">✓ Виконано на сьогодні</span>'}
          </div>
        </div>
        <button class="btn-complete" ${habit.completedToday ? 'disabled' : ''}>
          ${habit.completedToday ? 'Done ✓' : 'Complete'}
        </button>
      `;

      const btn = li.querySelector('.btn-complete');
      if (btn && !habit.completedToday) {
        btn.addEventListener('click', () => onComplete(habit.id));
      }

      container.appendChild(li);
    });
  },

  renderCountdown(timeRemainingMs) {
    const countdownEl = document.getElementById('reset-timer-countdown');
    const bannerEl = document.getElementById('reset-timer-banner');
    if (!countdownEl) return;

    if (timeRemainingMs <= 0) {
      countdownEl.textContent = '00:00:00';
      return;
    }

    const totalSeconds = Math.floor(timeRemainingMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const pad = (n) => String(n).padStart(2, '0');
    countdownEl.textContent = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

    // Urgent warning if less than 2 hours remaining
    if (bannerEl) {
      if (hours < 2) {
        bannerEl.classList.add('urgent');
      } else {
        bannerEl.classList.remove('urgent');
      }
    }
  },
};
