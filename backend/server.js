import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import apiRouter from './routes/index.js';
import { CronService } from './services/cron.service.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Mount API v1 router
app.use('/api/v1', apiRouter);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Initialize background schedulers
CronService.initDailyReset();

// Start Server
app.listen(PORT, () => {
  console.log(`⚔️ Gamified Habit Tracker API running on http://localhost:${PORT}`);
  console.log(`📋 Base Route: http://localhost:${PORT}/api/v1`);
});
