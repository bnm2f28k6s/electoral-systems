import {simulateRequest, simulateMultiRequest} from './engine/api.js';
import {parseRequest} from './simulator.mjs';
self.onmessage = ({data}) => {
  const {id, scope, text} = data;
  try {
    const input = parseRequest(text, scope);
    const result = scope === 'single' ? simulateRequest(input) : simulateMultiRequest(input);
    self.postMessage({id, result});
  } catch (error) {
    self.postMessage({id, error: error instanceof Error ? error.message : String(error)});
  }
};
self.postMessage({type: 'ready'});
