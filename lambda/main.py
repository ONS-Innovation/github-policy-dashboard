import api_interface
import policy_checks

import json

org = "ONS-Innovation"
client_id = "Iv23lifHcR6yRDTxa7nk"

with open("./github-audit-dashboard.pem", "r") as f:
    pem = f.read()

token = api_interface.get_access_token(org, pem, client_id)

gh = api_interface.api_controller(token[0])
    

repos = policy_checks.get_repository_data(gh, org)

with open("repositories.json", "w") as f:
    f.write(json.dumps(repos, indent=4))

secret_scanning_alerts = policy_checks.get_secret_scanning_alerts(gh, org, 5)

with open("secret_scanning.json", "w") as f:
    f.write(json.dumps(secret_scanning_alerts, indent=4))

dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

with open("dependabot.json", "w") as f:
    f.write(json.dumps(dependabot_alerts, indent=4))