import http from 'k6/http';
import { check, group, sleep } from 'k6';

export const options = {
    vus: 10,     
    duration: '30s', 
    thresholds: {
        //99% of requests to /health must finish in under 200ms
        'http_req_duration{tag:health}': ['p(99)<200'], 
        //The rate limit test should have a high failure rate
        'http_req_failed{tag:rate_limit_test}': ['rate>0.7'], //70% or more to fail
    },
};


export default function () {
    //This test will pass
    group('Health Check Test', function () {
        const health_res = http.get('http://127.0.0.1:8000/health', {
            tags: { tag: 'health' }
        });
        check(health_res, {
            'status is 200': (r) => r.status === 200,
        });
    });

    //This test will fail
    group('Rate Limit Test', function () {
        const rate_limit_res = http.get('http://127.0.0.1:8000/', {
            tags: { tag: 'rate_limit_test' }
        });
        
        check(rate_limit_res, {
            'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
        });
    });
    
    sleep(0.5); 
}