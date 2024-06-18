import api_interface
import policy_checks

with open("./github-audit-dashboard.pem", "r") as f:
    pem = f.read()

token = api_interface.get_access_token("ONS-Innovation", pem, "Iv23lifHcR6yRDTxa7nk")

gh = api_interface.api_controller(token[0])