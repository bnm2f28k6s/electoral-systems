/** Batch runner used by scripts/check_parity.py; one process covers all profiles. */
import { readFileSync } from 'node:fs';
import { simulate, ElectionError } from '../typescript/electoral.ts';
const requests: unknown[] = JSON.parse(readFileSync(0, 'utf8'));
const answers = requests.map(request => {
  try { return {ok: true, result: simulate(request)}; }
  catch (error) { return {ok: false, status: error instanceof ElectionError ? error.status : 500,
    error: error instanceof Error ? error.message : String(error)}; }
});
process.stdout.write(JSON.stringify(answers));
