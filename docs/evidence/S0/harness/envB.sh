unset HTTPS_PROXY HTTP_PROXY https_proxy http_proxy
export PYTHONPATH=$S0_HARNESS_DIR/harness/guard:$S0_HARNESS_DIR/harness/stub
export S0_EGRESS_LOG=$S0_HARNESS_DIR/runB/egress.jsonl
export MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=s0_runB
export LAURENTIA_ENCRYPTION_KEY=s0-test-only-key LAURENTIA_SECRET_SALT=s0-test-only-salt
export LAURENTIA_CVLN_SERVICE_API_KEY=s0-test-only-service-key
export CHANTIER7_SCHEDULERS_DISABLED=1 CHANTIER10_REPORTS_DISABLED=1 ORCHESTRATOR_DISABLED=1
export REACT_APP_BACKEND_URL=http://localhost:8001 CORS_ORIGINS=http://localhost
