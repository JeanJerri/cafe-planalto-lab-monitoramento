import http from 'k6/http';
import { check } from 'k6';

const TARGET_URL = (__ENV.TARGET_URL || 'http://loja.cafeplanalto.lab').replace(/\/+$/, '');
const TARGET_RPS = Number(__ENV.TARGET_RPS || 10);
const DURATION = __ENV.DURATION || '24h';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    trafego_continuo: {
      executor: 'constant-arrival-rate',
      rate: TARGET_RPS,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 15,
      maxVUs: 40,
    },
  },
};

const HEADERS_JSON = {
  'Content-Type': 'application/json',
  'User-Agent': 'cafeplanalto-cliente-carga-k6',
};

const HEADERS_GET = {
  'User-Agent': 'cafeplanalto-cliente-carga-k6',
};

export default function () {
  const roll = Math.random();

  if (roll < 0.65) {
    const res = http.get(`${TARGET_URL}/produtos`, { headers: HEADERS_GET, timeout: '3s' });
    check(res, { 'GET /produtos status < 500': (r) => r.status > 0 && r.status < 500 });
    return;
  }

  if (roll < 0.90) {
    const produtoId = Math.floor(Math.random() * 5) + 1;
    const quantidade = Math.floor(Math.random() * 3) + 1;
    const payload = JSON.stringify({
      produto_id: produtoId,
      quantidade: quantidade,
      cliente: 'filial-carga',
    });
    const res = http.post(`${TARGET_URL}/pedidos`, payload, { headers: HEADERS_JSON, timeout: '3s' });
    check(res, { 'POST /pedidos status 201': (r) => r.status === 201 });
    return;
  }

  if (roll < 0.95) {
    const res = http.get(`${TARGET_URL}/`, { headers: HEADERS_GET, timeout: '3s' });
    check(res, { 'GET / status 200': (r) => r.status === 200 });
    return;
  }

  const res = http.get(`${TARGET_URL}/health`, { headers: HEADERS_GET, timeout: '3s' });
  check(res, { 'GET /health respondeu': (r) => r.status > 0 });
}
