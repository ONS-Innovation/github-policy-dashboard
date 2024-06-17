import api_interface
import policy_checks

with open("./github-audit-dashboard.pem", "r") as f:
    pem = f.read()

token = api_interface.get_access_token("ONS-Innovation", pem, "Iv23lifHcR6yRDTxa7nk")

gh = api_interface.api_controller(token[0])

# print(policy_checks.check_inactive("https://api.github.com/repos/ONS-Innovation/sml-supporting-info", gh))
# print(policy_checks.check_branch_protection("https://api.github.com/repos/ONS-Innovation/sml-supporting-info/branches", gh))
# print(policy_checks.check_signed_commits("https://api.github.com/repos/ONS-Innovation/code-repo-archive-tool/commits", gh))
print(policy_checks.check_readme_exists("https://api.github.com/repos/ONS-Innovation/code-repo-archive-tool/contents/{+path}", gh))
print(policy_checks.check_license_exists("https://api.github.com/repos/ONS-Innovation/code-repo-archive-tool/contents/{+path}", gh))
print(policy_checks.check_pirr_exists("https://api.github.com/repos/ONS-Innovation/code-repo-archive-tool/contents/{+path}", gh))
print(policy_checks.check_gitignore_exists("https://api.github.com/repos/ONS-Innovation/code-repo-archive-tool/contents/{+path}", gh))