# Azure Container Apps Plan

Placeholder for deploying the Streamlit dashboard as a containerized app.

Current target:

- Build the healthcare capacity app with `Dockerfile`
- Run Streamlit on port `8501`
- Use Container Apps HTTP ingress
- Set minimum replicas to `0`
- Keep data ephemeral inside the container session

No persistent cloud storage or database is required for the current demo. If long-term user data retention becomes necessary later, add a separate storage layer.
