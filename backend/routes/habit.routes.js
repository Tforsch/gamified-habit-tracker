import { Router } from 'express';
import { HabitController } from '../controllers/habit.controller.js';

const router = Router();

router.get('/', HabitController.getAll);
router.post('/', HabitController.create);
router.post('/:id/complete', HabitController.complete);

export default router;
