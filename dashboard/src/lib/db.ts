import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'trade',
  user: process.env.DB_USER || 'adam',
  password: process.env.DB_PASSWORD || '',
  max: 5,
});

export default pool;
