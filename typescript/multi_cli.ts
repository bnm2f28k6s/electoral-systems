/** Run: node typescript/multi_cli.ts < election.json */
import {readFileSync} from 'node:fs';
import {simulate, ElectionError} from './multi_winner.ts';
try {
  process.stdout.write(JSON.stringify(simulate(JSON.parse(readFileSync(0, 'utf8')))) + '\n');
} catch (error) {
  process.stderr.write(JSON.stringify({error: error instanceof Error ? error.message : String(error),
    status: error instanceof ElectionError ? error.status : 400}) + '\n');
  process.exitCode = 1;
}
