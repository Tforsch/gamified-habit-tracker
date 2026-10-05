import { Router } from 'express';
import userRoutes from './user.routes.js';
import habitRoutes from './habit.routes.js';

const apiRouter = Router();

apiRouter.use('/users', userRoutes);
apiRouter.use('/habits', habitRoutes);

export default apiRouter;
