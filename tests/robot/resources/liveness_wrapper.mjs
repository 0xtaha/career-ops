#!/usr/bin/env node
// CLI wrapper around classifyLiveness for Robot Framework tests.
// Usage: node liveness_wrapper.mjs '<json>'
// Output: JSON line with {result, reason}
import { classifyLiveness } from './liveness-core.mjs';

const input = JSON.parse(process.argv[2]);
const result = classifyLiveness(input);
process.stdout.write(JSON.stringify(result) + '\n');
